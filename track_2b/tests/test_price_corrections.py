"""Isolated software QA for audited human edits, never model evaluation or seed data."""
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from tenderproof.api import create_app
from tenderproof.service import Conflict,digest


@pytest.fixture
def review_case(tmp_path,monkeypatch):
    monkeypatch.setenv('RUNTIME_DIR',str(tmp_path/'runtime'))
    principals={role:{'actor':'qa-'+role,'role':role,'projects':['default']}
                for role in ('engineer','inspector','commercial')}
    principals['outside']={'actor':'qa-outside','role':'engineer','projects':['another-project']}
    app=create_app(database_url='sqlite:///'+str(tmp_path/'corrections.db'),principals=principals)
    s=app.state.service
    s.set_metadata('default',s.get('default')['snapshot_hash'],'QA package','QA customer','QA transformer','qa-engineer','engineer')
    for doc in [
        {'id':'qa-bid','name':'QA source','spans':[
            {'id':'qa-bid:1','page':1,'text':'Constructed QA numeric source'},
            {'id':'qa-bid:2','page':2,'text':'Constructed QA handwritten-price locator'}]},
        {'id':'other-doc','name':'Other QA source','spans':[
            {'id':'qa-bid:foreign','page':1,'text':'Different document despite ID prefix'}]},
    ]:s.add_document('default',doc,s.get('default')['snapshot_hash'],'qa-engineer')
    data={'name':'QA offer','configuration':'QA configuration','revision':None,'serial':None,'family':None,
          'price_cents':1099,'currency':'USD','price_basis':'unit','delivery_weeks':4,'delivery_basis':'project_start','expedite_cents':0,'rework_cents':0,
          'facts':[{'property':'rated_power','operator':'eq','value':'750','unit':'kVA','conditions':{},'source_ids':['qa-bid:1']}]}
    trace={'coverage':{'all_original_spans_present':True},'planned_call_count':1,'calls':[{'role':'controlled QA','trace_id':'qa-only'}],'inference':'constructed software QA only','roles':[{'raw_output':{'price_cents':1099}}]}
    q=s.add_proposal('default','qa-bid','supplier',data,None,s.get('default')['snapshot_hash'],'qa-engineer',trace)
    client=TestClient(app)
    return s,client,q


def correction(s,**overrides):
    return {'snapshot_hash':s.get('default')['snapshot_hash'],'price_cents':1299,'currency':'USD',
            'source_id':'qa-bid:2','reason':'QA: checked the original price cell',**overrides}


def post(client,q,body,token='engineer'):
    return client.post('/api/projects/default/proposals/'+q['id']+'/correct-price',json=body,
        headers={'Authorization':'Bearer '+token} if token else {})


def test_correction_keeps_raw_output_trace_and_snapshot_with_explicit_pending_history(review_case):
    s,client,q=review_case;before=s.get('default')
    response=post(client,q,correction(s))
    assert response.status_code==200,response.text
    fixed=response.json();after=s.get('default')
    assert fixed['status']=='pending' and after['suppliers']==[]
    assert fixed['data']=={**q['data'],'price_cents':1299}
    assert fixed['original_data']==q['data'] and fixed['trace']==q['trace']
    history=fixed['price_corrections'];assert len(history)==1
    assert history[0]=={'id':history[0]['id'],'at':history[0]['at'],'actor':'qa-engineer',
        'document_id':'qa-bid','source_id':'qa-bid:2','page':2,'reason':'QA: checked the original price cell',
        'before':{'price_cents':1099,'currency':'USD'},'after':{'price_cents':1299,'currency':'USD'}}
    assert history[0]['id'] and history[0]['at']
    assert after['version']==before['version']+1 and after['snapshot_hash']!=before['snapshot_hash']
    event=next(e for e in after['events'] if e['type']=='supplier_price_corrected')
    assert event['actor']=='qa-engineer' and event['details']['correction']==history[0]
    assert event['details']['proposal_id']==q['id']
    for event in after['events']:assert event['hash']==digest({k:v for k,v in event.items() if k!='hash'})
    with s.engine.connect() as conn:
        old=conn.execute(select(s.snapshots.c.state).where(s.snapshots.c.project_id=='default',s.snapshots.c.hash==before['snapshot_hash'])).scalar_one()
    assert old['proposals']==before['proposals']
    public=client.get('/api/projects/default',headers={'Authorization':'Bearer engineer'}).json()
    assert public['proposals'][0]==fixed


def test_repeated_edits_preserve_original_and_history_and_allow_explicit_unknowns(review_case):
    s,client,q=review_case
    first=post(client,q,correction(s)).json()
    response=post(client,q,correction(s,price_cents=None,currency=None,source_id='qa-bid:1',reason='QA: price is not legible'))
    assert response.status_code==200,response.text
    second=response.json()
    assert second['original_data']==q['data'] and second['trace']==q['trace']
    assert second['price_corrections'][0]==first['price_corrections'][0]
    assert second['price_corrections'][1]['before']=={'price_cents':1299,'currency':'USD'}
    assert second['price_corrections'][1]['after']=={'price_cents':None,'currency':None}
    assert second['data']['price_cents'] is None and second['data']['currency'] is None
    assert second['status']=='pending' and s.get('default')['suppliers']==[]


@pytest.mark.parametrize('missing',['price_cents','currency'])
def test_correction_requires_explicit_amount_and_currency_even_when_unknown(review_case,missing):
    s,client,q=review_case;before=s.get('default');body=correction(s);del body[missing]
    assert post(client,q,body).status_code==422
    assert s.get('default')==before


@pytest.mark.parametrize('token,status',[('',401),('inspector',403),('commercial',403),('outside',403)])
def test_correction_requires_engineer_and_project_access(review_case,token,status):
    s,client,q=review_case;before=s.get('default')
    assert post(client,q,correction(s),token).status_code==status
    assert s.get('default')==before


@pytest.mark.parametrize('source',['missing','qa-bid:foreign'])
def test_correction_source_must_belong_to_exact_proposal_document(review_case,source):
    s,client,q=review_case;before=s.get('default')
    assert post(client,q,correction(s,source_id=source)).status_code==409
    assert s.get('default')==before


def test_stale_correction_cannot_overwrite_newer_review(review_case):
    s,client,q=review_case;body=correction(s)
    assert post(client,q,body).status_code==200
    before=s.get('default')
    assert post(client,q,{**body,'price_cents':9999}).status_code==409
    assert s.get('default')==before


@pytest.mark.parametrize('invalid',[
    {'price_cents':-1},{'price_cents':10**14+1},{'price_cents':True},{'price_cents':1.5},{'price_cents':'1299'},
    {'currency':'GBP'},{'reason':'   '},{'reason':'x'*2001},{'source_id':''},{'trace':{'modified':True}},
])
def test_invalid_correction_is_rejected_without_any_state_change(review_case,invalid):
    s,client,q=review_case;before=s.get('default')
    assert post(client,q,correction(s,**invalid)).status_code==422
    assert s.get('default')==before


def test_approved_supplier_and_pending_evidence_cannot_be_price_corrected(review_case):
    s,client,q=review_case
    s.approve_proposal('default',q['id'],s.get('default')['snapshot_hash'],'qa-engineer','engineer')
    before=s.get('default')
    assert post(client,q,correction(s)).status_code==409
    assert s.get('default')==before
    evidence=s.add_proposal('default','qa-bid','evidence',{'title':'QA evidence','kind':'routine',
        'configuration':'QA configuration','source_ids':['qa-bid:1'],'measurements':[]},q['id'],
        before['snapshot_hash'],'qa-inspector',{})
    before=s.get('default')
    assert post(client,evidence,correction(s)).status_code==409
    assert s.get('default')==before


def prepare_purchase(s):
    candidate={'title':'QA rating','property':'rated_power','operator':'eq','value':'750','unit':'kVA',
               'conditions':{},'source_ids':['qa-bid:1'],'phase':'purchase','equipment_type':'transformer'}
    requirement=s.add_candidates('default','qa-bid',[candidate],s.get('default')['snapshot_hash'],'qa-engineer',{'coverage':{'all_original_spans_present':True},'planned_call_count':1,'calls':[{'role':'controlled QA','trace_id':'qa-only'}]})['candidates'][0]
    s.review('default',requirement['id'],s.get('default')['snapshot_hash'],True,requirement['witness_expected'],'qa-engineer','engineer')
    s.set_schedule('default',s.get('default')['snapshot_hash'],10,'qa-bid:1','qa-engineer','engineer')


@pytest.mark.parametrize('unknown',[{'price_cents':None},{'currency':None}])
def test_independently_unknown_amount_or_currency_remains_conditional_after_approval(review_case,unknown):
    s,client,q=review_case
    response=post(client,q,correction(s,**unknown));assert response.status_code==200,response.text
    s.approve_proposal('default',q['id'],s.get('default')['snapshot_hash'],'qa-engineer','engineer')
    prepare_purchase(s)
    assert s.get('default')['comparisons'][0]['status']=='conditional'
    with pytest.raises(Conflict):
        s.create_decision('default',q['id'],'purchase',s.get('default')['snapshot_hash'],'qa-engineer')


def test_separate_approval_and_released_packet_retain_manual_correction_provenance(review_case):
    s,client,q=review_case
    fixed=post(client,q,correction(s)).json()
    assert s.get('default')['suppliers']==[]
    response=client.post('/api/projects/default/proposals/'+q['id']+'/approve',
        json={'snapshot_hash':s.get('default')['snapshot_hash']},headers={'Authorization':'Bearer engineer'})
    assert response.status_code==200,response.text
    supplier=s.get('default')['suppliers'][0]
    assert supplier['price_cents']==1299 and supplier['proposal_id']==q['id']
    assert supplier['original_data']==q['data'] and supplier['price_corrections']==fixed['price_corrections']
    prepare_purchase(s)
    decision=s.create_decision('default',supplier['id'],'purchase',s.get('default')['snapshot_hash'],'qa-engineer')
    for actor,role in [('qa-engineer','engineer'),('qa-commercial','commercial')]:
        s.approve('default',decision['id'],s.get('default')['snapshot_hash'],actor,role)
    artifact=s.release('default',decision['id'],s.get('default')['snapshot_hash'],'qa-release','qa-commercial','commercial')
    saved=artifact['engineering_snapshot']['suppliers'][0]
    assert saved['price_corrections']==fixed['price_corrections'] and saved['original_data']==q['data']
    assert artifact['engineering_snapshot']['proposals'][0]['trace']==q['trace']


def test_correction_conservatively_invalidates_existing_decision(review_case):
    s,client,q=review_case;other=deepcopy(q['data']);other['name']='QA second offer'
    second=s.add_proposal('default','qa-bid','supplier',other,None,s.get('default')['snapshot_hash'],'qa-engineer',{'coverage':{'all_original_spans_present':True},'planned_call_count':1,'calls':[{'role':'controlled QA','trace_id':'qa-only'}]})
    s.approve_proposal('default',second['id'],s.get('default')['snapshot_hash'],'qa-engineer','engineer')
    prepare_purchase(s)
    decision=s.create_decision('default',second['id'],'purchase',s.get('default')['snapshot_hash'],'qa-engineer')
    assert decision['status']=='pending'
    assert post(client,q,correction(s)).status_code==200
    assert s.get('default')['decisions'][0]['status']=='stale'
