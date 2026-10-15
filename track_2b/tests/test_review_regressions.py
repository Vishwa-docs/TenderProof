from copy import deepcopy
import pytest
from pydantic import ValidationError
from tenderproof.models import Fact, Evidence
from tenderproof.domain import assess_evidence, witness_for, compare_options
from support.fixtures import qa_package, document, qa_service
from tenderproof.service import Service, Conflict, Forbidden

def test_invalid_decimal_is_controlled_validation_error():
    with pytest.raises(ValidationError):Fact(property='rated_power',operator='ge',value='garbage',unit='MVA',source_ids=['a'])

def test_model_cannot_preapprove_type_family_coverage():
    data=deepcopy(qa_package()['evidence'][1])
    for key in ('id','supplier_id'):data.pop(key)
    data.update(kind='type',approved_family_coverage=True)
    with pytest.raises(ValidationError):Evidence.model_validate(data)

def test_upper_bound_witness_does_not_assert_wrong_meaning():
    r=qa_package()['requirements'][0];r['operator']='le'
    assert witness_for(r)['expected'] is True

def test_evidence_cannot_borrow_measurements_from_supplier_quote():
    p=qa_package();e=p['evidence'][0];e['measurements'][0]['source_ids']=['atlas-offer:2']
    for r in p['requirements']:r['status']='approved'
    assert assess_evidence(e,p['suppliers'][0],p['requirements'])['status']=='unknown'

def test_blank_family_never_counts_as_approved_type_coverage():
    p=qa_package();s=p['suppliers'][1];s['family']='';e=p['evidence'][1]
    for r in p['requirements']:r['status']='approved'
    e.update(kind='type',revision='B',family='',approved_family_coverage=True)
    assert assess_evidence(e,s,p['requirements'])['status']=='unknown'

def test_qa_fat_does_not_claim_unstated_forced_cooling_measurements(tmp_path):
    s=qa_service('sqlite:///'+str(tmp_path/'fat.db'))
    p=s.get('default')
    for report in p['evidence']:
        assert {f['conditions'].get('cooling') for f in report['measurements'] if f['property']=='rated_power'}=={'ONAN'}

def test_live_does_not_inherit_synthetic_delivery_deadline(tmp_path):
    s=Service('sqlite:///'+str(tmp_path/'live.db'),mode='live')
    assert s.get('default')['required_delivery_week'] is None

def test_unknown_delivery_baseline_and_mixed_currencies_are_conditional():
    p=qa_package()
    for r in p['requirements']:r['status']='approved'
    p['required_delivery_week']=None
    assert next(r for r in compare_options(p) if r['supplier_id']=='helvetic')['status']=='conditional'
    p['required_delivery_week']=24;p['suppliers'][0]['currency']='EUR'
    assert next(r for r in compare_options(p) if r['supplier_id']=='helvetic')['status']=='conditional'

def test_artifact_survives_content_change_and_restart(tmp_path):
    s=qa_service('sqlite:///'+str(tmp_path/'db'))
    for r in s.get('default')['requirements']:
        s.review('default',r['id'],s.get('default')['snapshot_hash'],True,r['witness_expected'],'e','engineer')
    h=s.get('default')['snapshot_hash'];d=s.create_decision('default','helvetic','purchase',h,'e')
    s.approve('default',d['id'],h,'e','engineer');s.approve('default',d['id'],h,'c','commercial')
    result=s.release('default',d['id'],h,'reset-check','c','commercial')
    s.set_schedule('default',h,25,'owner:5','e','engineer')
    assert s.get_artifact('default',d['id'])==result
    assert Service(s.database_url).get_artifact('default',d['id'])==result

def test_live_style_evidence_can_explicitly_supersede_wrong_revision(tmp_path):
    s=qa_service('sqlite:///'+str(tmp_path/'db'))
    for r in s.get('default')['requirements']:
        s.review('default',r['id'],s.get('default')['snapshot_hash'],True,r['witness_expected'],'e','engineer')
    with pytest.raises(Conflict):
        s.create_decision('default','helvetic','shipment',s.get('default')['snapshot_hash'],'i')
    doc=document('corrected-fat','Corrected FAT',
        'SYNTHETIC TEST\nHP-31 revision B; serial HP-042.\n25 MVA ONAN; primary voltage 33 kV; load losses 110 kW at 75 C.',
        revision='B',authority='test_report')
    s.add_document('default',doc,s.get('default')['snapshot_hash'],'i')
    p=s.get('default');data=deepcopy(p['evidence'][1])
    for k in ['id','supplier_id']:data.pop(k)
    data.update(revision='B',source_ids=['corrected-fat:2','corrected-fat:3'])
    for f in data['measurements']:f['source_ids']=['corrected-fat:3']
    q=s.add_proposal('default',doc['id'],'evidence',data,'helvetic',p['snapshot_hash'],'i',{'coverage':{'all_original_spans_present':True},'planned_call_count':1,'calls':[{'role':'controlled QA','trace_id':'qa-only'}]})
    with pytest.raises(Forbidden):
        s.approve_proposal('default',q['id'],s.get('default')['snapshot_hash'],'e','engineer',supersedes_evidence_id='evidence-helvetic')
    with pytest.raises(Conflict):
        s.approve_proposal('default',q['id'],s.get('default')['snapshot_hash'],'i','inspector',supersedes_evidence_id='evidence-atlas')
    s.approve_proposal('default',q['id'],s.get('default')['snapshot_hash'],'i','inspector',supersedes_evidence_id='evidence-helvetic')
    p=s.get('default')
    assert next(e for e in p['evidence'] if e['id']=='evidence-helvetic')['superseded']
    assert not next(e for e in p['evidence'] if e['id']=='evidence-atlas').get('superseded')
    assert s.create_decision('default','helvetic','shipment',p['snapshot_hash'],'i')['status']=='pending'
