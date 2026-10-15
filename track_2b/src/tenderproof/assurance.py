"""Snapshot-bound extraction facts. Recorded coverage never certifies obligation completeness."""
from copy import deepcopy
import hashlib
import json


def identity(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()[:24]


def extraction_run(document_id,kind,trace,*,event_id=None,legacy=False,run_id=None):
    trace=deepcopy(trace) if isinstance(trace,dict) else {}
    conditions=[]
    if not document_id:conditions.append('Extraction source document could not be established from preserved facts.')
    if kind not in ('requirements','supplier','evidence'):conditions.append('Extraction purpose could not be established from preserved facts.')
    if trace.get('coverage',{}).get('all_original_spans_present') is not True:
        conditions.append('Complete source-span coverage is missing or unverified.')
    rejected=max(trace.get('rejected_row_count') or 0,len(trace.get('rejected_rows') or []))
    if rejected:conditions.append(f'{rejected} model row(s) failed validation; omitted obligations or offers remain unreviewed.')
    for failure in trace.get('audit_failures') or []:
        window=f" (window {failure['window']})" if failure.get('window') is not None else ''
        conditions.append(f"Audit failed: {failure.get('role','unknown role')}{window}. {failure.get('reason','No valid audit result was retained.')}")
    caps=trace.get('row_caps') or []
    for cap in caps:
        conditions.append(f"Window {cap.get('window','unknown')} reached the {cap.get('cap','unknown')}-row output cap; source obligations or offers may be omitted.")
    for note in trace.get('issues') or []:
        if isinstance(note,str) and note.strip():
            conditions.append('Unresolved extraction finding: '+note.strip())
    planned=trace.get('planned_call_count')
    if not isinstance(planned,int) or isinstance(planned,bool) or planned<1 or not trace.get('calls'):
        conditions.append('Expected role-call count and linked call telemetry are missing; extraction assurance is unverified.')
    elif len(trace.get('calls') or [])!=planned:
        conditions.append(f"Call telemetry is incomplete: {len(trace.get('calls') or [])} of {planned} planned calls are linked; missing raw trace references require reconciliation.")
    if trace.get('global_consistency_review_required') and (trace.get('window_count') or 1)>1:
        conditions.append('Cross-window consistency and unencoded obligations have no recorded scoped engineering assurance review.')
    return dict(id=run_id or identity({'document_id':document_id,'kind':kind,'trace':trace,'event_id':event_id}),
                document_id=document_id,kind=kind,status='incomplete' if conditions else 'recorded',
                conditions=conditions,trace=trace,event_id=event_id,legacy=legacy)


def legacy_runs(package):
    """Derive only preserved facts, never replay inference or rewrite event/raw trace bytes."""
    docs=package.get('documents') or [];proposals=package.get('proposals') or [];runs=[]
    for e in reversed(package.get('events') or []):
        if e.get('type') not in ('extracted','proposal_added'):continue
        details=e.get('details') or {};trace=details.get('trace') or {}
        kind=details.get('kind') or ('requirements' if e['type']=='extracted' else None)
        matching=[q for q in proposals if q.get('trace')==trace]
        if not kind:
            kinds={q['kind'] for q in matching}
            if len(kinds)==1:kind=kinds.pop()
            elif 'supplier' in e.get('summary','').lower():kind='supplier'
            elif 'evidence' in e.get('summary','').lower():kind='evidence'
        document_id=details.get('document_id')
        if not document_id:
            hashes=[d['id'] for d in docs if trace.get('document_sha256') and d.get('sha256')==trace['document_sha256']]
            sources=set((trace.get('source_id_mapping') or {}).values())
            cited=[d['id'] for d in docs if sources & {s['id'] for s in d.get('spans',[])}]
            candidates=set(hashes or cited or [q['document_id'] for q in matching])
            if len(candidates)==1:document_id=candidates.pop()
        runs.append(extraction_run(document_id,kind,trace,event_id=e.get('id'),legacy=True))
    # Some legacy versions saved proposal traces but emitted no event on empty/deduplicated batches.
    for q in proposals:
        if not any(r['document_id']==q.get('document_id') and r['kind']==q.get('kind') and r['trace']==q.get('trace',{}) for r in runs):
            runs.append(extraction_run(q.get('document_id'),q.get('kind'),q.get('trace'),legacy=True))
    for key,kind in (('requirements','requirements'),('suppliers','supplier'),('evidence','evidence')):
        for row in package.get(key) or []:
            refs=set(row.get('source_ids') or [])
            for fact in (row.get('facts') or [])+(row.get('measurements') or []):refs.update(fact.get('source_ids') or [])
            docids=[d['id'] for d in docs if refs & {s['id'] for s in d.get('spans',[])}] or [None]
            for docid in docids:
                if not any(r['document_id']==docid and r['kind']==kind for r in runs):
                    runs.append(extraction_run(docid,kind,{},legacy=True))
    return runs
