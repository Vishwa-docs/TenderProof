"""Unknown commercial amounts: isolated software QA, no live model evaluation."""
from copy import deepcopy
import json
import pytest
from pydantic import ValidationError
from tenderproof.domain import compare_options
from tenderproof.models import Supplier
from tenderproof.service import Service,Conflict
from support.fixtures import qa_package,qa_service
from test_integrations import invoke_controlled_response,qa_fact


@pytest.mark.parametrize('omitted',[False,True])
def test_unknown_ancillary_amounts_validate_and_remain_null(omitted):
    row={'name':'QA unknown cost offer','facts':[qa_fact()]}
    if not omitted:row.update(expedite_cents=None,rework_cents=None)
    parsed=Supplier.model_validate(row).model_dump()
    assert parsed['expedite_cents'] is None and parsed['rework_cents'] is None


@pytest.mark.parametrize('field',['expedite_cents','rework_cents'])
@pytest.mark.parametrize('value',[-1,10**14+1])
def test_present_ancillary_amounts_keep_existing_bounds(field,value):
    with pytest.raises(ValidationError):
        Supplier.model_validate({'name':'QA cost bounds','facts':[qa_fact()],field:value})


@pytest.mark.parametrize('amount',[None,0,12500])
def test_mapper_schema_and_raw_response_preserve_unknown_zero_and_known_amounts(tmp_path,monkeypatch,amount):
    monkeypatch.setenv('APERTUS_TRACE_DIR',str(tmp_path/'traces'))
    proposal={'supplier':{'name':'QA commercial offer','facts':[qa_fact()],'source_ids':['s1'],
                          'expedite_cents':amount,'rework_cents':amount}}
    result,requests,_,_=invoke_controlled_response('supplier',proposal)
    row=result['data'][0]
    assert row['expedite_cents']==amount and row['rework_cents']==amount
    instruction=requests[1]['messages'][0]['content']
    assert 'Use null for unknown commercial' in instruction
    mapper=next(call for call in result['trace']['calls'] if call['role']=='obligation mapper')
    envelope=json.loads((tmp_path/'traces'/mapper['trace_id']/'response.json').read_text())
    assert json.loads(envelope['choices'][0]['message']['content'])==proposal


def reviewed_package():
    package=qa_package();package['suppliers']=[package['suppliers'][1]]
    for row in package['requirements']:row['status']='approved'
    return package


@pytest.mark.parametrize('expedite,rework,addition,missing',[
    (None,None,0,['expedite','rework']),
    (None,2500,2500,['expedite']),
    (1250,None,1250,['rework']),
])
def test_unknown_ancillary_cost_keeps_documented_subtotal_conditional_and_blocks_gates(expedite,rework,addition,missing):
    package=reviewed_package();supplier=package['suppliers'][0]
    supplier.update(expedite_cents=expedite,rework_cents=rework)
    comparison=compare_options(package)[0]
    assert comparison['total_cents']==supplier['price_cents']+addition
    assert comparison['status']=='conditional'
    issue=next(reason for reason in comparison['issues'] if 'ancillary' in reason.lower())
    assert 'subtotal' in issue.lower() and all(field in issue.lower() for field in missing)
    for gate in ('purchase','shipment'):
        with pytest.raises(Conflict):Service._gate(None,package,supplier['id'],gate)


def test_explicit_zero_and_known_ancillary_costs_remain_literal_and_purchase_eligible():
    package=reviewed_package();supplier=package['suppliers'][0]
    supplier.update(expedite_cents=0,rework_cents=1250)
    parsed=Supplier.model_validate({k:v for k,v in supplier.items() if k!='id'}).model_dump()
    assert parsed['expedite_cents']==0 and parsed['rework_cents']==1250
    comparison=compare_options(package)[0]
    assert comparison['total_cents']==supplier['price_cents']+1250
    assert comparison['status']=='feasible'
    Service._gate(None,package,supplier['id'],'purchase')


def test_missing_base_price_does_not_present_ancillary_only_subtotal_as_offer_price():
    package=reviewed_package();package['suppliers'][0].update(price_cents=None,expedite_cents=1500,rework_cents=None)
    comparison=compare_options(package)[0]
    assert comparison['total_cents'] is None and comparison['status']=='conditional'


def test_null_ancillary_amounts_survive_pending_approval_and_export_without_unlocking_gate(tmp_path):
    service=qa_service('sqlite:///'+str(tmp_path/'unknown-costs.db'))
    for row in service.get('default')['requirements']:
        service.review('default',row['id'],service.get('default')['snapshot_hash'],True,row['witness_expected'],'qa-engineer','engineer')
    data=deepcopy(service.get('default')['suppliers'][1]);data.pop('id')
    data.update(name='QA unresolved ancillary offer',expedite_cents=None,rework_cents=None)
    data=Supplier.model_validate(data).model_dump()
    trace={'coverage':{'all_original_spans_present':True},'planned_call_count':1,'calls':[{'role':'controlled QA','trace_id':'qa-only'}],'origin':'isolated software QA','raw_ancillary_amounts':[None,None]}
    proposal=service.add_proposal('default','helvetic-offer','supplier',data,None,
        service.get('default')['snapshot_hash'],'qa-engineer',trace)
    assert proposal['status']=='pending' and proposal['data']['expedite_cents'] is None
    service.approve_proposal('default',proposal['id'],service.get('default')['snapshot_hash'],'qa-engineer','engineer')
    after=service.get('default')
    supplier=next(row for row in after['suppliers'] if row['id']==proposal['id'])
    assert supplier['expedite_cents'] is None and supplier['rework_cents'] is None
    before=deepcopy(after)
    with pytest.raises(Conflict):
        service.create_decision('default',proposal['id'],'purchase',after['snapshot_hash'],'qa-engineer')
    assert service.get('default')==before
    # Export of a separate eligible offer must retain the unknown values faithfully.
    decision=service.create_decision('default','helvetic','purchase',after['snapshot_hash'],'qa-engineer')
    for actor,role in [('qa-engineer','engineer'),('qa-commercial','commercial')]:
        service.approve('default',decision['id'],service.get('default')['snapshot_hash'],actor,role)
    artifact=service.release('default',decision['id'],service.get('default')['snapshot_hash'],'qa-cost-export','qa-commercial','commercial')
    snapshot=artifact['engineering_snapshot']
    exported=next(row for row in snapshot['suppliers'] if row['id']==proposal['id'])
    assert exported['expedite_cents'] is None and exported['rework_cents'] is None
    assert next(row for row in snapshot['proposals'] if row['id']==proposal['id'])['trace']==trace
