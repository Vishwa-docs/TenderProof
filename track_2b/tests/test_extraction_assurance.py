"""Constructed isolated QA; no runtime model output or canonical package is modified."""
from copy import deepcopy
import pytest
from sqlalchemy import insert, select, update
from tenderproof.service import Service, Conflict, event
from support.fixtures import qa_service


def ready_service(tmp_path):
    svc=qa_service('sqlite:///'+str(tmp_path/'assurance.db'))
    for r in svc.get('default')['requirements']:
        svc.review('default',r['id'],svc.get('default')['snapshot_hash'],True,r['witness_expected'],'qa-engineer','engineer')
    return svc


def clean_trace():
    return {'coverage':{'all_original_spans_present':True,'source_span_count':5},
            'rejected_row_count':0,'rejected_rows':[],'audit_failures':[],
            'issues':[],'window_count':1,'planned_call_count':1,'calls':[{'role':'mapper','trace_id':'qa-raw'}]}


@pytest.mark.parametrize('gap',[
    {'coverage':{'all_original_spans_present':False}},
    {'rejected_row_count':1,'rejected_rows':[{'raw_row':'QA invalid row'}]},
    {'audit_failures':[{'role':'adversarial challenger','trace_id':'qa-failed'}]},
    {'issues':['This window returned the 15-row output cap, so more obligations may exist.']},
    {'window_count':2,'global_consistency_review_required':True},
    {},
])
@pytest.mark.parametrize('gate',['purchase','shipment'])
def test_known_incomplete_or_unknown_assurance_blocks_both_gates_even_after_rows_approved(tmp_path,gap,gate):
    svc=ready_service(tmp_path)
    trace={**clean_trace(),**gap} if gap else {}
    p=svc.get('default')
    svc.add_candidates('default','owner',[],p['snapshot_hash'],'qa-model',trace)
    with pytest.raises(Conflict,match='[Ee]xtraction assurance'):
        svc.create_decision('default','helvetic',gate,svc.get('default')['snapshot_hash'],'qa-engineer')


def test_run_facts_are_snapshot_bound_and_survive_an_immutable_release_packet(tmp_path):
    svc=ready_service(tmp_path);before=svc.get('default')['snapshot_hash'];trace=clean_trace()
    svc.add_candidates('default','owner',[],before,'qa-model',trace,operation_key='qa-run')
    p=svc.get('default');run=p['extraction_runs'][-1]
    assert p['snapshot_hash']!=before
    assert run['document_id']=='owner' and run['kind']=='requirements'
    assert run['trace']==trace and run['status']=='recorded' and run['conditions']==[]
    svc.add_candidates('default','owner',[],before,'qa-model',trace,operation_key='qa-run')
    assert svc.get('default')['extraction_runs']==p['extraction_runs']
    h=p['snapshot_hash'];d=svc.create_decision('default','helvetic','purchase',h,'qa-engineer')
    svc.approve('default',d['id'],h,'qa-engineer','engineer');svc.approve('default',d['id'],h,'qa-buyer','commercial')
    packet=svc.release('default',d['id'],h,'qa-packet','qa-buyer','commercial')
    assert packet['engineering_snapshot']['extraction_runs']==p['extraction_runs']
    assert svc.get_artifact('default',d['id'])==packet


def test_legacy_backfill_preserves_original_snapshots_events_and_stales_decisions_once(tmp_path):
    svc=ready_service(tmp_path);p=svc.get('default');p.pop('extraction_runs',None)
    event(p,'qa-model','extracted','Legacy extraction',{'trace':{**clean_trace(),'document_sha256':p['documents'][0]['sha256'],'audit_failures':[{'role':'challenger','reason':'truncated'}]}})
    original_events=deepcopy(p['events']);old_hash=p['snapshot_hash'];old_version=p['version']
    p['decisions']=[{'id':'legacy-decision','status':'approved','snapshot_hash':old_hash}]
    with svc.engine.begin() as conn:
        conn.execute(update(svc.projects).values(state=p))
        conn.execute(update(svc.snapshots).where(svc.snapshots.c.hash==old_hash).values(state=deepcopy(p)))
    migrated=Service(svc.database_url).get('default')
    assert migrated['snapshot_hash']!=old_hash and migrated['version']==old_version+1
    assert migrated['decisions'][0]['status']=='stale'
    run=next(r for r in migrated['extraction_runs'] if r.get('event_id')==original_events[0]['id'])
    assert run['document_id']=='owner' and run['kind']=='requirements'
    assert run['trace']['audit_failures'][0]['reason']=='truncated' and run['conditions']
    assert migrated['events'][1:]==original_events
    assert Service(svc.database_url).get('default')==migrated
    with svc.engine.connect() as conn:
        historical=conn.execute(select(svc.snapshots.c.state).where(svc.snapshots.c.hash==old_hash)).scalar_one()
    assert historical==p and 'extraction_runs' not in historical


def test_untraceable_legacy_rows_get_unknown_assurance_not_silent_completeness(tmp_path):
    svc=ready_service(tmp_path);p=svc.get('default');p.pop('extraction_runs',None)
    with svc.engine.begin() as conn:conn.execute(update(svc.projects).values(state=p))
    restored=Service(svc.database_url);p=restored.get('default')
    assert any(r['status']=='incomplete' and r['conditions'] for r in p['extraction_runs'])
    with pytest.raises(Conflict,match='[Ee]xtraction assurance'):
        restored.create_decision('default','helvetic','purchase',p['snapshot_hash'],'qa-engineer')

@pytest.mark.parametrize('trace',[
    {'coverage':{'all_original_spans_present':True}},
    {**clean_trace(),'issues':['A required delivery obligation was omitted from the mapper result.']},
])
def test_coverage_flag_or_unresolved_audit_finding_cannot_establish_assurance(tmp_path,trace):
    svc=ready_service(tmp_path)
    svc.add_candidates('default','owner',[],svc.get('default')['snapshot_hash'],'qa-model',trace)
    with pytest.raises(Conflict,match='[Ee]xtraction assurance'):
        svc.create_decision('default','helvetic','purchase',svc.get('default')['snapshot_hash'],'qa-engineer')
