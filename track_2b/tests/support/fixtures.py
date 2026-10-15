"""Constructed software QA fixtures. Never imported or seeded by the application."""
import hashlib
from copy import deepcopy


def document(doc_id, name, text, revision='A', language='en', authority='approved_customer'):
    return dict(id=doc_id, name=name, revision=revision, language=language,
                authority=authority, sha256=hashlib.sha256(text.encode()).hexdigest(),
                spans=[dict(id=f'{doc_id}:{i+1}', page=1, text=line, bbox=None)
                       for i, line in enumerate(text.splitlines()) if line.strip()])


def qa_package(project_id='default'):
    docs = [
        document('owner', 'Customer technical specification',
                 'SYNTHETIC ENGINEERING EXAMPLE — not a real procurement.\n'
                 'The transformer shall provide at least 25 MVA with ONAN cooling.\n'
                 'Rated primary voltage shall be 33 kV.\n'
                 'Guaranteed load losses shall not exceed 120 kW at 75 °C.\n'
                 'Equipment is required by project week 24.'),
        document('annex', 'Bilingual clarification',
                 'SYNTHETIC EXAMPLE\n25 MVA müssen ohne Lüfter erreicht werden.\n'
                 'Les 25 MVA doivent être disponibles sans ventilation forcée.', language='de/fr'),
        document('atlas-offer', 'Atlas Electric · GTP and commercial offer',
                 'SYNTHETIC SUPPLIER\nAX-25 revision A; ONAN 20 MVA; ONAF 25 MVA.\n'
                 'Primary voltage 33 kV; load losses 112 kW at 75 °C.\n'
                 'Price USD 1,200,000; delivery week 22.', authority='supplier_offer'),
        document('helvetic-offer', 'Helvetic Power · GTP and commercial offer',
                 'SYNTHETIC SUPPLIER\nHP-31 revision B; ONAN 25 MVA; ONAF 31.5 MVA.\n'
                 'Primary voltage 33 kV; load losses 110 kW at 75 °C.\n'
                 'Price USD 1,360,000; delivery week 24.', revision='B', authority='supplier_offer'),
        document('fat-atlas', 'Atlas routine FAT report',
                 'SYNTHETIC TEST RECORD\nAX-25 revision A, serial AX-001.\n'
                 'ONAN 20 MVA; primary voltage 33 kV; load losses 112 kW at 75 °C.', authority='test_report'),
        document('fat-helvetic', 'Helvetic routine FAT report',
                 'SYNTHETIC TEST RECORD\nHP-31 revision A, serial HP-042.\n'
                 'ONAN 25 MVA; primary voltage 33 kV; load losses 110 kW at 75 °C.', authority='test_report'),
    ]
    requirements = []
    for rid, title, prop, op, value, unit, cond, source in [
        ('req-rating', 'Natural-cooling capacity', 'rated_power', 'ge', '25', 'MVA', {'cooling':'ONAN'}, 'owner:2'),
        ('req-voltage', 'Primary voltage', 'primary_voltage', 'eq', '33', 'kV', {}, 'owner:3'),
        ('req-losses', 'Guaranteed load losses', 'load_losses', 'le', '120', 'kW', {'temperature_c':'75'}, 'owner:4'),
    ]:
        requirements.append(dict(id=rid,title=title,property=prop,operator=op,value=value,unit=unit,
            conditions=cond,phase='purchase',source_ids=[source],status='pending',reviewer=None,
            witness_question=('Would 20 MVA without fans and 25 MVA with fans satisfy this requirement?' if rid=='req-rating' else None),
            witness_expected=(False if rid=='req-rating' else None), equipment_type='transformer'))
    suppliers=[]
    for sid,name,config,rev,serial,family,rating,forced,losses,price,week in [
        ('atlas','Atlas Electric','AX-25','A','AX-001','AX', '20','25','112',120000000,22),
        ('helvetic','Helvetic Power','HP-31','B','HP-042','HP','25','31.5','110',136000000,24),
    ]:
        facts=[]
        for prop,value,unit,cond,line in [('rated_power',rating,'MVA',{'cooling':'ONAN'},2),
            ('rated_power',forced,'MVA',{'cooling':'ONAF'},2),('primary_voltage','33','kV',{},3),
            ('load_losses',losses,'kW',{'temperature_c':'75'},3)]:
            facts.append(dict(property=prop,operator='eq',value=value,unit=unit,conditions=cond,source_ids=[f'{sid}-offer:{line}']))
        suppliers.append(dict(id=sid,name=name,configuration=config,revision=rev,serial=serial,family=family,
                              price_cents=price,currency='USD',price_basis='unit',delivery_weeks=week,delivery_basis='project_start',expedite_cents=0,rework_cents=0,facts=facts))
    evidence=[]
    for s in suppliers:
        measurements=deepcopy([f for f in s['facts'] if f['conditions'].get('cooling')!='ONAF'])
        for measurement in measurements:measurement['source_ids']=[f"fat-{s['id']}:3"]
        evidence.append(dict(id=f"evidence-{s['id']}",title=f"{s['name']} · routine FAT",supplier_id=s['id'],kind='routine',
            serial=s['serial'],family=s['family'],configuration=s['configuration'],revision='A',
            conditions={},measurements=measurements,
            source_ids=[f"fat-{s['id']}:2",f"fat-{s['id']}:3"],approved_family_coverage=False))
    return dict(id=project_id,name='Aare Valley · Substation 04',customer='Northline Energy · synthetic project',
                equipment='33/11 kV power transformer',mode='live',version=1,required_delivery_week=24,schedule_source_id='owner:5',
                requirements=requirements,suppliers=suppliers,evidence=evidence,documents=docs,proposals=[],extraction_runs=[],decisions=[],events=[])


TEST_PRINCIPALS={role+'-qa':{'actor':role+'-qa','role':role,'projects':['default']} for role in ('engineer','inspector','commercial')}

def auth(role='engineer'):
    return {'Authorization':'Bearer '+role+'-qa'}

def seed_service(service):
    from sqlalchemy import insert, update
    from tenderproof.service import snapshot, event
    package=qa_package()
    package['snapshot_hash']=snapshot(package)
    event(package,'qa-only','created','Constructed regression fixtures loaded into isolated test database.')
    with service.engine.begin() as conn:
        conn.execute(update(service.projects).where(service.projects.c.id=='default').values(state=package))
        conn.execute(insert(service.snapshots).values(project_id='default',hash=package['snapshot_hash'],state=package))
    return service

def qa_service(database_url):
    from tenderproof.service import Service
    return seed_service(Service(database_url))

def add_corrected_evidence(service):
    doc=document('corrected-fat','QA corrected test report',
        'CONSTRUCTED QA TEST RECORD\nHP-31 revision B, serial HP-042.\nONAN 25 MVA; primary voltage 33 kV; load losses 110 kW at 75 C.',
        revision='B',authority='test_report')
    service.add_document('default',doc,service.get('default')['snapshot_hash'],'inspector-qa')
    data=deepcopy(service.get('default')['evidence'][1])
    for key in ('id','supplier_id'):data.pop(key)
    data.update(revision='B',source_ids=['corrected-fat:2','corrected-fat:3'])
    data['measurements']=[f for f in data['measurements'] if f.get('conditions',{}).get('cooling')!='ONAF']
    for measurement in data['measurements']:measurement['source_ids']=['corrected-fat:3']
    proposal=service.add_proposal('default',doc['id'],'evidence',data,'helvetic',service.get('default')['snapshot_hash'],'inspector-qa',{'coverage':{'all_original_spans_present':True},'planned_call_count':1,'calls':[{'role':'controlled QA','trace_id':'qa-only'}],'issues':[],'audit_failures':[]})
    service.approve_proposal('default',proposal['id'],service.get('default')['snapshot_hash'],'inspector-qa','inspector',supersedes_evidence_id='evidence-helvetic')
    return next(e for e in service.get('default')['evidence'] if e['id']==proposal['id'])
