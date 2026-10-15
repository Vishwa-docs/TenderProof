"""Unknown equipment identity stays unknown; isolated software regression cases."""
from copy import deepcopy
import json
import pytest
from pydantic import ValidationError
from tenderproof.models import Supplier,Evidence
from tenderproof.domain import assess_evidence,compare_options
from tenderproof.service import Service,Conflict
from support.fixtures import qa_package,qa_service
from test_integrations import invoke_controlled_response,qa_fact


@pytest.mark.parametrize('model,data',[
    (Supplier,{'name':'QA offer','facts':[qa_fact()]}),
    (Evidence,{'title':'QA report','kind':'routine','source_ids':['s1']}),
])
@pytest.mark.parametrize('missing',[False,True])
def test_schema_preserves_null_or_omitted_configuration_without_fabricating_identity(model,data,missing):
    row=deepcopy(data)
    if not missing:row['configuration']=None
    assert model.model_validate(row).model_dump()['configuration'] is None


@pytest.mark.parametrize('model,data',[
    (Supplier,{'name':'QA offer','facts':[qa_fact()]}),
    (Evidence,{'title':'QA report','kind':'routine','source_ids':['s1']}),
])
@pytest.mark.parametrize('value',['','  ','x'*121])
def test_present_configuration_keeps_existing_nonempty_length_bounds(model,data,value):
    with pytest.raises(ValidationError):model.model_validate({**data,'configuration':value})


@pytest.mark.parametrize('kind,proposal',[
    ('supplier',{'supplier':{'name':'QA offer','configuration':None,'facts':[qa_fact()]}}),
    ('evidence',{'evidence':{'title':'QA report','kind':'routine','configuration':None,'source_ids':['s1']}}),
])
def test_adapter_accepts_raw_null_configuration_and_retains_original_response_trace(tmp_path,monkeypatch,kind,proposal):
    monkeypatch.setenv('APERTUS_TRACE_DIR',str(tmp_path/'traces'))
    result,_,_,_=invoke_controlled_response(kind,proposal)
    assert result['data'][0]['configuration'] is None
    mapper=next(c for c in result['trace']['calls'] if c['role']=='obligation mapper')
    envelope=json.loads((tmp_path/'traces'/mapper['trace_id']/'response.json').read_text())
    assert json.loads(envelope['choices'][0]['message']['content'])==proposal


@pytest.mark.parametrize('missing',['supplier','evidence','both'])
def test_missing_configuration_cannot_support_acceptance_or_shipment(missing):
    p=qa_package();p['suppliers']=[p['suppliers'][1]];p['evidence']=[p['evidence'][1]]
    s=p['suppliers'][0];e=p['evidence'][0];e['revision']=s['revision']
    for requirement in p['requirements']:requirement['status']='approved'
    assert assess_evidence(e,s,p['requirements'])['status']=='supported'
    if missing in ('supplier','both'):s['configuration']=None
    if missing in ('evidence','both'):e['configuration']=None
    result=assess_evidence(e,s,p['requirements'])
    assert result['status']=='unknown' and 'configuration' in result['reason']
    with pytest.raises(Conflict):Service._gate(None,p,s['id'],'shipment')


def test_missing_supplier_configuration_is_conditional_and_blocks_purchase_even_with_all_other_inputs():
    p=qa_package();p['suppliers']=[p['suppliers'][1]]
    for requirement in p['requirements']:requirement['status']='approved'
    assert compare_options(p)[0]['status']=='feasible'
    p['suppliers'][0]['configuration']=None
    result=compare_options(p)[0]
    assert result['status']=='conditional'
    assert any('configuration' in reason.lower() for reason in result['issues'])
    with pytest.raises(Conflict):Service._gate(None,p,p['suppliers'][0]['id'],'purchase')


def test_null_identity_survives_proposal_approval_and_other_supplier_decision_export(tmp_path):
    service=qa_service('sqlite:///'+str(tmp_path/'unknown-configuration.db'))
    for row in service.get('default')['requirements']:
        service.review('default',row['id'],service.get('default')['snapshot_hash'],True,row['witness_expected'],'qa-engineer','engineer')
    data=deepcopy(service.get('default')['suppliers'][1]);data.pop('id');data.update(name='QA unconfigured offer',configuration=None)
    data=Supplier.model_validate(data).model_dump()
    trace={'coverage':{'all_original_spans_present':True},'planned_call_count':1,'calls':[{'role':'controlled QA','trace_id':'qa-only'}],'origin':'isolated software QA','raw_mapper_configuration':None}
    q=service.add_proposal('default','helvetic-offer','supplier',data,None,service.get('default')['snapshot_hash'],'qa-engineer',trace)
    assert q['status']=='pending' and q['data']['configuration'] is None and q['trace']==trace
    service.approve_proposal('default',q['id'],service.get('default')['snapshot_hash'],'qa-engineer','engineer')
    unknown=next(s for s in service.get('default')['suppliers'] if s['id']==q['id'])
    assert unknown['configuration'] is None
    for gate in ('purchase','shipment'):
        with pytest.raises(Conflict):service.create_decision('default',q['id'],gate,service.get('default')['snapshot_hash'],'qa-engineer')
    # A separate known configuration remains eligible; its package export retains
    # the unselected unknown offer faithfully without approving that offer's gate.
    decision=service.create_decision('default','helvetic','purchase',service.get('default')['snapshot_hash'],'qa-engineer')
    for actor,role in [('qa-engineer','engineer'),('qa-commercial','commercial')]:
        service.approve('default',decision['id'],service.get('default')['snapshot_hash'],actor,role)
    artifact=service.release('default',decision['id'],service.get('default')['snapshot_hash'],'qa-known-release','qa-commercial','commercial')
    exported=artifact['engineering_snapshot']
    assert next(s for s in exported['suppliers'] if s['id']==q['id'])['configuration'] is None
    assert next(p for p in exported['proposals'] if p['id']==q['id'])['trace']==trace


def type_coverage_case(tmp_path,field=None,missing=None):
    service=qa_service('sqlite:///'+str(tmp_path/'type-coverage.db'))
    for row in service.get('default')['requirements']:
        service.review('default',row['id'],service.get('default')['snapshot_hash'],True,row['witness_expected'],'qa-engineer','engineer')
    original=service.get('default');supplier=deepcopy(original['suppliers'][1]);supplier.pop('id')
    supplier['name']='QA type coverage supplier'
    if missing in ('supplier','both'):supplier[field]=None
    supplier=Supplier.model_validate(supplier).model_dump()
    offer=service.add_proposal('default','helvetic-offer','supplier',supplier,None,
        service.get('default')['snapshot_hash'],'qa-engineer',{'origin':'isolated coverage QA'})
    service.approve_proposal('default',offer['id'],service.get('default')['snapshot_hash'],'qa-engineer','engineer')
    evidence=deepcopy(original['evidence'][1])
    for key in ('id','supplier_id'):evidence.pop(key)
    evidence.update(kind='type',revision=original['suppliers'][1]['revision'])
    if missing in ('report','both'):evidence[field]=None
    evidence=Evidence.model_validate(evidence).model_dump()
    report=service.add_proposal('default','fat-helvetic','evidence',evidence,offer['id'],
        service.get('default')['snapshot_hash'],'qa-inspector',{'origin':'isolated coverage QA'})
    return service,offer,report


@pytest.mark.parametrize('field',['configuration','revision'])
@pytest.mark.parametrize('missing',['supplier','report','both'])
def test_type_family_confirmation_requires_nonempty_identity_on_both_sides_atomically(tmp_path,field,missing):
    service,offer,report=type_coverage_case(tmp_path,field,missing)
    before=service.get('default')
    with pytest.raises(Conflict,match='nonempty family, configuration and revision'):
        service.approve_proposal('default',report['id'],before['snapshot_hash'],'qa-inspector','inspector',family_coverage_confirmed=True)
    # No reviewed status, appended evidence, audit event or snapshot changes.
    assert service.get('default')==before
    # An inspector may retain the report without claiming family applicability.
    service.approve_proposal('default',report['id'],before['snapshot_hash'],'qa-inspector','inspector',family_coverage_confirmed=False)
    after=service.get('default')
    evidence=next(e for e in after['evidence'] if e['id']==report['id'])
    assert evidence['approved_family_coverage'] is False
    assert next(a for a in after['evidence_assessments'] if a['evidence_id']==report['id'])['status']=='unknown'


def test_type_family_confirmation_with_known_matching_identity_remains_supported(tmp_path):
    service,offer,report=type_coverage_case(tmp_path)
    service.approve_proposal('default',report['id'],service.get('default')['snapshot_hash'],'qa-inspector','inspector',family_coverage_confirmed=True)
    after=service.get('default')
    assert next(e for e in after['evidence'] if e['id']==report['id'])['approved_family_coverage'] is True
    assert next(a for a in after['evidence_assessments'] if a['evidence_id']==report['id'])['status']=='supported'
