"""Transactional package state, immutable snapshots and exact-snapshot approvals."""
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, MetaData, Table, Column, String, JSON, select, insert, update, func
from pydantic import ValidationError
from .domain import assess_requirement, assess_evidence, compare_options, witness_for
from .models import Supplier, SupplierPriceCorrectionRequest
from .assurance import extraction_run, legacy_runs
from . import evidence_workbench

class Conflict(Exception): pass
class Forbidden(Exception): pass

CONTENT_KEYS = ('id','name','customer','equipment','mode','requirements','suppliers','evidence','documents','proposals','required_delivery_week','schedule_source_id','extraction_runs')

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def snapshot(package):
    return digest({k:package.get(k, [] if k in ('requirements','suppliers','evidence','documents','proposals','extraction_runs') else None) for k in CONTENT_KEYS})

def now(): return datetime.now(timezone.utc).isoformat()

def event(p,actor,kind,summary,details=None):
    row=dict(id=str(uuid4()),at=now(),actor=actor,type=kind,summary=summary,details=details or {},
             previous_hash=p['events'][0]['hash'] if p['events'] else None)
    row['hash']=digest(row); p['events'].insert(0,row)

def rejected_note(trace):
    count=(trace or {}).get('rejected_row_count') or 0
    return f' {count} model rows failed validation and were not saved; their raw content is in the trace.' if count else ''

def find(rows, identity):
    for row in rows:
        if row['id']==identity:return row
    raise KeyError(identity)

class Service:
    def __init__(self, database_url, mode='live'):
        if mode!='live':raise ValueError('Only live application mode is supported.')
        self.database_url=database_url; self.mode=mode
        self.engine=create_engine(database_url,connect_args={'check_same_thread':False,'timeout':30} if database_url.startswith('sqlite') else {})
        meta=MetaData()
        self.projects=Table('packages',meta,Column('id',String,primary_key=True),Column('state',JSON,nullable=False))
        self.snapshots=Table('package_snapshots',meta,Column('project_id',String,primary_key=True),Column('hash',String,primary_key=True),Column('state',JSON,nullable=False))
        self.operations=Table('completed_operations',meta,Column('project_id',String,primary_key=True),Column('key',String,primary_key=True),Column('result',JSON,nullable=False))
        self.artifacts=Table('decision_artifacts',meta,Column('project_id',String,primary_key=True),Column('decision_id',String,primary_key=True),Column('artifact',JSON,nullable=False))
        meta.create_all(self.engine)
        with self.engine.begin() as conn:
            if not conn.execute(select(self.projects.c.id).where(self.projects.c.id=='default')).first():
                p=dict(id='default',name='Engineering package',customer='',equipment='',mode='live',version=1,
                    required_delivery_week=None,schedule_source_id=None,requirements=[],suppliers=[],evidence=[],
                    documents=[],proposals=[],extraction_runs=[],decisions=[],events=[])
                p['snapshot_hash']=snapshot(p)
                event(p,'system','created','Empty live project created. Add actual source documents and define the equipment scope.')
                conn.execute(insert(self.projects).values(id=p['id'],state=p))
                conn.execute(insert(self.snapshots).values(project_id=p['id'],hash=p['snapshot_hash'],state=deepcopy(p)))
            # One transactional forward migration. Historical snapshots/artifacts are never rewritten.
            for project_id,state in conn.execute(select(self.projects.c.id,self.projects.c.state)).all():
                if 'extraction_runs' in state:continue
                p=deepcopy(state);previous=p['snapshot_hash']
                p['extraction_runs']=legacy_runs(p)
                p['version']=p.get('version',0)+1
                for decision in p.get('decisions',[]):decision['status']='stale'
                p['snapshot_hash']=snapshot(p)
                event(p,'system','extraction_assurance_migrated',
                      'Preserved extraction facts added to the decision basis; prior decisions require fresh review.',
                      {'previous_snapshot_hash':previous,'extraction_run_ids':[r['id'] for r in p['extraction_runs']]})
                conn.execute(update(self.projects).where(self.projects.c.id==project_id).values(state=p))
                if not conn.execute(select(self.snapshots.c.hash).where(self.snapshots.c.project_id==project_id,self.snapshots.c.hash==p['snapshot_hash'])).first():
                    conn.execute(insert(self.snapshots).values(project_id=project_id,hash=p['snapshot_hash'],state=deepcopy(p)))


    def _read(self,conn,pid,lock=False):
        q=select(self.projects.c.state).where(self.projects.c.id==pid)
        if lock:q=q.with_for_update()
        row=conn.execute(q).first()
        if row is None:raise KeyError(pid)
        return deepcopy(row[0])

    def get(self,pid):
        with self.engine.connect() as conn:p=self._read(conn,pid)
        p['assessments']=[assess_requirement(r,s) for s in p['suppliers'] for r in p['requirements']]
        p['comparisons']=compare_options(p)
        p['evidence_assessments']=[assess_evidence(e,find(p['suppliers'],e['supplier_id']),p['requirements']) for e in p['evidence']]
        return p

    def _workbench_eligible_gates(self,p):
        """Read the existing preparation checks; never create or approve a decision."""
        eligible=[]
        for gate in ('purchase','shipment'):
            for supplier in p['suppliers']:
                try:self._gate(p,supplier['id'],gate)
                except Conflict:continue
                eligible.append(gate)
                break
        return eligible

    def _verify_workbench_snapshot(self,p,pid,expected_hash=None,legacy=False):
        """Do not attach a preserved snapshot identity to corrupt or misplaced JSON."""
        if not isinstance(p,dict) or p.get('id')!=pid:
            raise evidence_workbench.ViewProblem(409,'Stored package identity does not match its project snapshot.')
        expected_hash=expected_hash or p.get('snapshot_hash')
        matches=p.get('snapshot_hash')==expected_hash and snapshot(p)==expected_hash
        if not matches and legacy and 'extraction_runs' not in p and p.get('snapshot_hash')==expected_hash:
            # This is the one historical content schema before extraction assurance.
            old_content={k:p.get(k,[] if k in ('requirements','suppliers','evidence','documents','proposals') else None)
                for k in CONTENT_KEYS if k!='extraction_runs'}
            matches=digest(old_content)==expected_hash
        if not matches:
            raise evidence_workbench.ViewProblem(409,'Stored package content does not match its snapshot hash; evidence view unavailable.')
        return p

    def _workbench_read(self,pid,assess=False):
        with self.engine.connect() as conn:
            p=self._verify_workbench_snapshot(self._read(conn,pid),pid)
        if assess:
            p['comparisons']=compare_options(p)
            p['evidence_assessments']=[assess_evidence(e,find(p['suppliers'],e['supplier_id']),p['requirements']) for e in p['evidence']]
        return p

    def evidence_analysis(self,pid):
        p=self._workbench_read(pid,assess=True)
        return evidence_workbench.analyze(p,self._workbench_eligible_gates(p))

    def search_evidence(self,pid,q,document_id=None,limit=12):
        p=self._workbench_read(pid)
        return evidence_workbench.search(p,q,document_id,limit)

    def list_snapshots(self,pid):
        with self.engine.connect() as conn:
            p=self._verify_workbench_snapshot(self._read(conn,pid),pid)
            scope=self.snapshots.c.project_id==pid
            total=conn.execute(select(func.count()).select_from(self.snapshots).where(scope)).scalar_one()
            rows=conn.execute(select(self.snapshots.c.hash,self.snapshots.c.state).where(scope)
                .order_by(self.snapshots.c.state['version'].as_integer().desc(),self.snapshots.c.hash).limit(100)).all()
            if not any(row[0]==p['snapshot_hash'] for row in rows):
                current=conn.execute(select(self.snapshots.c.hash,self.snapshots.c.state)
                    .where(scope,self.snapshots.c.hash==p['snapshot_hash'])).first()
                if current is None:
                    raise evidence_workbench.ViewProblem(409,'The current package snapshot is missing from stored history.')
                rows=rows[:99]+[current]
            states=[self._verify_workbench_snapshot(state,pid,value,legacy=True) for value,state in rows]
        return dict(project_id=pid,snapshot_hash=p['snapshot_hash'],current_snapshot_hash=p['snapshot_hash'],
            total_count=total,truncated=total>100,limit=100,
            snapshots=[evidence_workbench.snapshot_metadata(state,p['snapshot_hash']) for state in states])

    def diff_snapshots(self,pid,from_hash,to_hash):
        import re
        if any(not isinstance(h,str) or not re.fullmatch(r'[0-9a-f]{64}',h) for h in (from_hash,to_hash)):
            raise evidence_workbench.ViewProblem(422,'Snapshot hashes must be 64 lowercase hexadecimal characters.')
        with self.engine.connect() as conn:
            p=self._verify_workbench_snapshot(self._read(conn,pid),pid)
            states=[]
            for value in (from_hash,to_hash):
                row=conn.execute(select(self.snapshots.c.state).where(self.snapshots.c.project_id==pid,self.snapshots.c.hash==value)).first()
                if row is None:raise KeyError(value)
                states.append(self._verify_workbench_snapshot(deepcopy(row[0]),pid,value,legacy=True))
        return evidence_workbench.diff(*states,p['snapshot_hash'])

    def review_dossier(self,pid):
        p=self._workbench_read(pid,assess=True)
        return evidence_workbench.dossier(p,self._workbench_eligible_gates(p))

    def _mutate(self,pid,expected,actor,fn,operation_key=None):
        with self.engine.connect() as conn:
            try:
                if self.engine.dialect.name=='sqlite':conn.exec_driver_sql('BEGIN IMMEDIATE')
                else:conn.begin()
                p=self._read(conn,pid,True)
                if operation_key:
                    existing=conn.execute(select(self.operations.c.result).where(self.operations.c.project_id==pid,self.operations.c.key==operation_key)).first()
                    if existing:conn.commit();return deepcopy(existing[0])
                if expected!=p['snapshot_hash']:raise Conflict('The package changed. Refresh and review the current snapshot.')
                result=fn(p)
                new_hash=snapshot(p)
                if new_hash!=p['snapshot_hash']:
                    p['version']+=1
                    stale=[]
                    for d in p['decisions']:
                        if d['status']!='stale':d['status']='stale';stale.append(d['id'])
                    p['snapshot_hash']=new_hash
                    event(p,actor,'reassessed','Applicability recomputed; decisions for the changed package require review.',
                          {'affected_requirements':[r['id'] for r in p['requirements']], 'stale_decisions':stale,
                           'strategy':'conservative full package scope; discovers new requirements'})
                    if not conn.execute(select(self.snapshots.c.hash).where(self.snapshots.c.project_id==pid,self.snapshots.c.hash==new_hash)).first():
                        conn.execute(insert(self.snapshots).values(project_id=pid,hash=new_hash,state=deepcopy(p)))
                conn.execute(update(self.projects).where(self.projects.c.id==pid).values(state=p))
                for d in p['decisions']:
                    if d.get('artifact'):
                        stored=conn.execute(select(self.artifacts.c.artifact).where(self.artifacts.c.project_id==pid,self.artifacts.c.decision_id==d['id'])).first()
                        if not stored:conn.execute(insert(self.artifacts).values(project_id=pid,decision_id=d['id'],artifact=d['artifact']))
                        elif stored[0]!=d['artifact']:raise Conflict('Release artifacts are immutable.')
                if operation_key:conn.execute(insert(self.operations).values(project_id=pid,key=operation_key,result=result))
                conn.commit()
                return deepcopy(result)
            except Exception:
                conn.rollback();raise

    def review(self,pid,rid,expected,accepted,answer,actor,role):
        if role!='engineer':raise Forbidden('An engineer must review the interpretation.')
        def change(p):
            r=find(p['requirements'],rid)
            if accepted and not p.get('equipment'):raise Conflict('Define the equipment scope before approving interpretations.')
            if accepted and r.get('witness_expected') is not None and answer is not r['witness_expected']:
                raise Conflict('The answer does not support this interpretation. Reject it or reconsider the source conditions.')
            r.update(status='approved' if accepted else 'rejected',reviewer=actor)
            event(p,actor,'interpretation_reviewed',f"{r['title']}: {r['status']}")
            return r
        return self._mutate(pid,expected,actor,change)

    def _gate(self,p,sid,gate):
        if not p.get('equipment'):raise Conflict('Define the equipment scope before preparing a decision.')
        if gate not in ('purchase','shipment'):raise Conflict('Unknown release gate.')
        if any(r.get('status')!='recorded' or r.get('conditions') for r in p.get('extraction_runs',[])):
            raise Conflict('Extraction assurance is incomplete or unknown. Review the source/run conditions; purchase and shipment releases are blocked.')
        comparison=next((x for x in compare_options(p) if x['supplier_id']==sid),None)
        if not comparison or comparison['status']!='feasible':raise Conflict('Resolve technical deviations, interpretations and delivery conditions before approval.')
        if gate=='shipment':
            s=find(p['suppliers'],sid)
            checks=[assess_evidence(e,s,p['requirements']) for e in p['evidence'] if e['supplier_id']==sid and not e.get('superseded')]
            if not checks or not any(c['status']=='supported' for c in checks) or any(c['status'] in ('contradicted','conflicting') for c in checks):
                raise Conflict('Applicable acceptance evidence is missing, contradictory or for the wrong equipment revision.')

    def create_decision(self,pid,sid,gate,expected,actor):
        def change(p):
            self._gate(p,sid,gate)
            d=dict(id=str(uuid4()),supplier_id=sid,gate=gate,snapshot_hash=p['snapshot_hash'],status='pending',approvals=[],created_at=now(),artifact=None)
            p['decisions'].insert(0,d);event(p,actor,'decision_prepared',f'{gate.title()} release prepared for {sid}.')
            return d
        return self._mutate(pid,expected,actor,change)

    def approve(self,pid,did,expected,actor,role):
        def change(p):
            d=find(p['decisions'],did)
            required={'engineer','commercial'} if d['gate']=='purchase' else {'inspector','commercial'}
            if role not in required:raise Forbidden('Your role cannot approve this gate.')
            if d['status'] in ('stale','released') or d['snapshot_hash']!=p['snapshot_hash']:raise Conflict('This decision is stale or already released.')
            self._gate(p,d['supplier_id'],d['gate'])
            if any(a['actor']==actor and a['role']!=role for a in d['approvals']):raise Forbidden('Separate people must provide the two approvals.')
            if not any(a['role']==role for a in d['approvals']):
                d['approvals'].append(dict(actor=actor,role=role,at=now()))
                event(p,actor,'approved',f'{role.title()} approved {d["gate"]} release.')
            if required.issubset({a['role'] for a in d['approvals']}):d['status']='approved'
            return d
        return self._mutate(pid,expected,actor,change)

    def release(self,pid,did,expected,key,actor,role):
        if role!='commercial':raise Forbidden('Commercial authorization is required to release.')
        if not key or len(key)>200:raise Conflict('A bounded idempotency key is required.')
        def change(p):
            d=find(p['decisions'],did)
            for existing in p['decisions']:
                if existing.get('idempotency_key')==key and existing['id']!=did:raise Conflict('Idempotency key is already bound to another decision.')
            if d['status']=='released' and d.get('idempotency_key')==key:return d['artifact']
            if d['status']!='approved' or d['snapshot_hash']!=p['snapshot_hash']:raise Conflict('Both current approvals are required before release.')
            self._gate(p,d['supplier_id'],d['gate'])
            artifact=dict(project_id=pid,decision_id=did,gate=d['gate'],supplier_id=d['supplier_id'],snapshot_hash=p['snapshot_hash'],
                          issued_at=now(),simulator=True,approvals=deepcopy(d['approvals']),
                          engineering_snapshot={k:deepcopy(p.get(k)) for k in CONTENT_KEYS},
                          assessments=[assess_requirement(r,find(p['suppliers'],d['supplier_id'])) for r in p['requirements']],
                          meaning='ERP simulator decision packet; no external order or shipment was executed. Checks cover reviewed encoded numeric requirements; unencoded obligations require engineering review. This packet does not certify physical equipment compliance.')
            artifact['artifact_hash']=digest(artifact)
            d.update(status='released',artifact=artifact,idempotency_key=key)
            event(p,actor,'released',f'{d["gate"].title()} decision exported to the ERP simulator.',{'artifact_hash':artifact['artifact_hash']})
            return artifact
        return self._mutate(pid,expected,actor,change)

    def add_document(self,pid,doc,expected,actor):
        def change(p):
            if any(d['id']==doc['id'] for d in p['documents']):return find(p['documents'],doc['id'])
            p['documents'].append(doc);event(p,actor,'document_added',f'Source added: {doc["name"]}')
            return doc
        return self._mutate(pid,expected,actor,change)

    def add_candidates(self,pid,docid,candidates,expected,actor,trace,operation_key=None):
        def change(p):
            if not p.get('equipment'):raise Conflict('Define the equipment scope before extracting requirements.')
            source={span['id']:span['text'] for d in p['documents'] for span in d['spans']}
            find(p['documents'],docid)
            added=[]
            for candidate in candidates:
                c=deepcopy(candidate)
                if not c['source_ids'] or any(s not in source or not s.startswith(docid+':') for s in c['source_ids']):raise Conflict('Model proposal has unsupported source references.')
                cid=digest({'document':docid,'candidate':c})[:20]
                if any(r['id']==cid for r in p['requirements']):continue
                c.update(id=cid,status='pending',reviewer=None)
                w=witness_for(c);c.update(witness_question=w['question'],witness_expected=w['expected'])
                p['requirements'].append(c);added.append(c)
            run=extraction_run(docid,'requirements',trace,run_id=str(uuid4()))
            p.setdefault('extraction_runs',[]).append(run)
            event(p,actor,'extracted',f'{len(added)} Apertus proposals require engineering review.'+rejected_note(trace),{'trace':trace,'document_id':docid,'kind':'requirements','run_id':run['id']})
            return {'candidates':added,'trace':trace}
        return self._mutate(pid,expected,actor,change,operation_key)

    def add_proposals(self,pid,docid,kind,rows,supplier_id,expected,actor,trace,operation_key=None):
        """Save an extraction batch in one transaction; approval remains per record."""
        def change(p):
            if not p.get('equipment'):raise Conflict('Define the equipment scope before extracting proposals.')
            if kind not in ('supplier','evidence'):raise Conflict('Unsupported proposal kind.')
            if not isinstance(rows,list) or len(rows)>100:raise Conflict('Expected a bounded proposal list.')
            if kind=='evidence' and len(rows)!=1:raise Conflict('Expected one evidence proposal.')
            doc=find(p['documents'],docid)
            if kind=='evidence':find(p['suppliers'],supplier_id)
            allowed={s['id'] for s in doc['spans']}
            selected=[];added=[]
            for data in rows:
                if not isinstance(data,dict):raise Conflict('Expected a proposal object.')
                refs=data.get('source_ids',[])
                facts=data.get('facts',[]);measurements=data.get('measurements',[])
                if any(not isinstance(value,list) for value in (refs,facts,measurements)):raise Conflict('Unsupported source references.')
                refs=list(refs)
                for field in facts+measurements:
                    if not isinstance(field,dict) or not isinstance(field.get('source_ids'),list):raise Conflict('Unsupported source references.')
                    refs.extend(field['source_ids'])
                if not refs or any(not isinstance(ref,str) for ref in refs) or not set(refs).issubset(allowed):raise Conflict('Unsupported source references.')
                identity=digest({'document':docid,'kind':kind,'data':data,'supplier':supplier_id})[:20]
                existing=next((q for q in p['proposals'] if q['id']==identity),None)
                if existing is None:
                    existing=dict(id=identity,document_id=docid,kind=kind,data=deepcopy(data),supplier_id=supplier_id,
                        source_ids=sorted(set(refs)),status='pending',trace=deepcopy(trace))
                    p['proposals'].append(existing);added.append(existing)
                if not any(q['id']==identity for q in selected):selected.append(existing)
            run=extraction_run(docid,kind,trace,run_id=str(uuid4()))
            p.setdefault('extraction_runs',[]).append(run)
            event(p,actor,'proposal_added',f'{len(added)} Apertus {kind} proposals require individual human review.'+rejected_note(trace),{'trace':trace,'document_id':docid,'kind':kind,'run_id':run['id']})
            return {'proposals':selected,'trace':trace}
        return self._mutate(pid,expected,actor,change,operation_key)

    def add_proposal(self,pid,docid,kind,data,supplier_id,expected,actor,trace,operation_key=None):
        result=self.add_proposals(pid,docid,kind,[data],supplier_id,expected,actor,trace,operation_key)
        return result['proposals'][0]

    def correct_supplier_price(self,pid,proposal_id,expected,price_cents,currency,source_id,reason,actor,role):
        """Record a human commercial-field correction; approval remains separate."""
        if role!='engineer':raise Forbidden('An engineer must review a supplier price correction.')
        try:
            correction=SupplierPriceCorrectionRequest(snapshot_hash=expected,price_cents=price_cents,
                currency=currency,source_id=source_id,reason=reason)
        except ValidationError as exc:raise Conflict('Price correction needs bounded integer cents, a supported currency, a source and a reason.') from exc
        def change(p):
            q=find(p['proposals'],proposal_id)
            if q['kind']!='supplier' or q['status']!='pending':raise Conflict('Only a pending supplier proposal can receive a price correction.')
            doc=find(p['documents'],q['document_id'])
            source=next((span for span in doc['spans'] if span['id']==correction.source_id),None)
            if source is None:raise Conflict('Price correction must reference a source in this proposal document.')
            before={key:q['data'].get(key) for key in ('price_cents','currency')}
            after={'price_cents':correction.price_cents,'currency':correction.currency}
            try:Supplier.model_validate({**q['data'],**after})
            except ValidationError as exc:raise Conflict('Corrected commercial fields must satisfy the supplier schema.') from exc
            q.setdefault('original_data',deepcopy(q['data']))
            entry=dict(id=str(uuid4()),at=now(),actor=actor,document_id=doc['id'],source_id=source['id'],
                       page=source['page'],reason=correction.reason,before=before,after=after)
            q.setdefault('price_corrections',[]).append(entry)
            q['data'].update(after)
            event(p,actor,'supplier_price_corrected','Supplier price corrected; proposal still requires separate approval.',
                  {'proposal_id':proposal_id,'correction':deepcopy(entry)})
            return q
        return self._mutate(pid,expected,actor,change)

    def get_artifact(self,pid,did):
        with self.engine.connect() as conn:
            self._read(conn,pid)
            row=conn.execute(select(self.artifacts.c.artifact).where(self.artifacts.c.project_id==pid,self.artifacts.c.decision_id==did)).first()
            if row is None:raise KeyError(did)
            return row[0]

    def approve_proposal(self,pid,proposal_id,expected,actor,role,family_coverage_confirmed=False,supersedes_evidence_id=None):
        def change(p):
            if not p.get('equipment'):raise Conflict('Define the equipment scope before approving proposals.')
            q=find(p['proposals'],proposal_id)
            required='engineer' if q['kind']=='supplier' else 'inspector'
            if role!=required:raise Forbidden(f'A {required} must approve this proposal.')
            if q['status']!='pending':raise Conflict('Proposal was already reviewed.')
            record={**deepcopy(q['data']),'id':q['id']}
            if q['kind']=='evidence':
                s=find(p['suppliers'],q['supplier_id'])
                if family_coverage_confirmed:
                    if record['kind']!='type' or any(not record.get(field) or not s.get(field) or record[field]!=s[field]
                        for field in ('family','configuration','revision')):
                        raise Conflict('Type coverage requires a matching, nonempty family, configuration and revision.')
                    record['approved_family_coverage']=True
                if supersedes_evidence_id:
                    previous=find(p['evidence'],supersedes_evidence_id)
                    if previous['supplier_id']!=q['supplier_id'] or previous['kind']!=record['kind']:raise Conflict('Superseded evidence must belong to the same supplier and evidence kind.')
                    previous['superseded']=True
                    record['supersedes_evidence_id']=supersedes_evidence_id
                record['supplier_id']=q['supplier_id'];p['evidence'].append(record)
            else:
                if q.get('price_corrections'):
                    record.update(proposal_id=q['id'],original_data=deepcopy(q['original_data']),
                                  price_corrections=deepcopy(q['price_corrections']))
                p['suppliers'].append(record)
            q.update(status='approved',reviewer=actor)
            event(p,actor,'proposal_approved',f'{q["kind"].title()} proposal approved for assessment.')
            return q
        return self._mutate(pid,expected,actor,change)

    def set_metadata(self,pid,expected,name,customer,equipment,actor,role):
        if role!='engineer':raise Forbidden('An engineer must define the equipment scope.')
        def change(p):
            if equipment!=p['equipment'] and any(p[key] for key in ('requirements','suppliers','evidence','proposals')):
                raise Conflict('Equipment scope cannot change after extraction. Use a separate package for another equipment item.')
            p.update(name=name,customer=customer,equipment=equipment)
            event(p,actor,'scope_reviewed','Project metadata and equipment scope reviewed.',{'equipment':equipment})
            return {'name':name,'customer':customer,'equipment':equipment}
        return self._mutate(pid,expected,actor,change)

    def set_schedule(self,pid,expected,week,source_id,actor,role):
        if role!='engineer':raise Forbidden('An engineer must approve the delivery milestone.')
        def change(p):
            if source_id not in {s['id'] for d in p['documents'] for s in d['spans']}:raise Conflict('Milestone must reference an existing source passage.')
            p.update(required_delivery_week=week,schedule_source_id=source_id)
            event(p,actor,'schedule_reviewed',f'Required delivery milestone set to project week {week}.',{'source_id':source_id})
            return {'required_delivery_week':week,'source_id':source_id}
        return self._mutate(pid,expected,actor,change)
