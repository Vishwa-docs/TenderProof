"""Controlled QA records from actual GPA-070-25 bid prices; never runtime seed data.

Primary source: https://go.opengovguam.com/uploads/ggbids/packet_1765520985_GPA-070-25%20Bid%20Abstract.pdf
The prices were visually checked in docs/REAL_PACKAGE_REVIEW.md. Missing technical
and identity fields stay unknown. Model/network work is replaced at its boundary;
HTTP handlers, transactions, source validation, approvals and retries are real.
"""
import asyncio
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from temporalio.exceptions import ApplicationError
from tenderproof.api import create_app
from tenderproof.service import Service, Conflict, Forbidden
from tenderproof.workflows import persist_extraction

DOC_ID='gpa-bid-abstract-qa'
TRACE={'inference':'controlled_QA_response_not_live_inference','document':'GPA-070-25 bid abstract'}


def prepare(service):
    p=service.get('default')
    service.set_metadata('default',p['snapshot_hash'],'GPA-070-25','Guam Power Authority',
        '750 kVA three-phase pad-mounted transformer, line item 2','qa-engineer','engineer')
    # Faithful price-cell transcriptions, not a stand-in fabricated document.
    doc={'id':DOC_ID,'name':'GPA-070-25 bid abstract QA transcriptions',
         'revision':'unreviewed','language':'en','authority':'source_checked_QA',
         'sha256':'ea238725bcf796aa9df08ba0d7cffacd105943a0782fd05b736f9cc5ed9a4b8b',
         'source_url':'https://go.opengovguam.com/uploads/ggbids/packet_1765520985_GPA-070-25%20Bid%20Abstract.pdf',
         'spans':[{'id':DOC_ID+':1','page':1,'text':'R&D Marketing; line item 2 unit cost 37,105.50'},
                  {'id':DOC_ID+':2','page':3,'text':'Benson Guam Enterprises Inc.; line item 2 basic unit cost 25,600.00'}]}
    service.add_document('default',doc,service.get('default')['snapshot_hash'],'qa-engineer')
    return service.get('default')


def offers():
    records=[]
    for name,cents,amount,ref in [('R&D Marketing',3710550,'37105.50',':1'),
                                  ('Benson Guam Enterprises Inc.',2560000,'25600.00',':2')]:
        records.append({'name':name,'configuration':'Line item 2 basic offer',
            'revision':None,'serial':None,'family':None,'price_cents':cents,'currency':'USD',
            'delivery_weeks':None,'expedite_cents':0,'rework_cents':0,
            'facts':[{'property':'bid_unit_price','operator':'eq','value':amount,'unit':'USD',
                      'conditions':{'line_item':'2','offer':'basic'},'source_ids':[DOC_ID+ref]}]})
    return records


@pytest.fixture
def service(tmp_path):
    s=Service('sqlite:///'+str(tmp_path/'batch.db'))
    prepare(s)
    return s


def save_batch(s,rows=None,operation_key=None):
    return s.add_proposals('default',DOC_ID,'supplier',offers() if rows is None else rows,None,
        s.get('default')['snapshot_hash'],'qa-engineer',TRACE,operation_key=operation_key)


def test_batch_saves_every_offer_in_one_snapshot_with_individual_source_links(service):
    before=service.get('default')
    result=save_batch(service)
    after=service.get('default')
    assert len(result['proposals'])==2
    assert after['version']==before['version']+1
    assert after['snapshot_hash']!=before['snapshot_hash']
    assert len(after['proposals'])==2 and after['suppliers']==[]
    assert [q['source_ids'] for q in after['proposals']]==[[DOC_ID+':1'],[DOC_ID+':2']]
    assert all(q['status']=='pending' for q in after['proposals'])
    assert all(q['data']['revision'] is None and q['data']['delivery_weeks'] is None for q in after['proposals'])
    assert result['trace']==TRACE


def test_invalid_second_offer_rolls_back_entire_batch_and_retry_key(service):
    before=service.get('default')
    rows=offers();rows[1]['facts'][0]['source_ids']=['another-document:1']
    with pytest.raises(Conflict,match='source'):
        save_batch(service,rows,operation_key='qa-batch-rollback')
    after=service.get('default')
    assert after['proposals']==[]
    assert after['snapshot_hash']==before['snapshot_hash']
    assert after['version']==before['version'] and after['events']==before['events']
    assert len(save_batch(service,operation_key='qa-batch-rollback')['proposals'])==2


def test_durable_batch_retry_is_idempotent_after_snapshot_has_changed(service):
    expected=service.get('default')['snapshot_hash']
    first=save_batch(service,operation_key='qa-batch-retry')
    current=service.get('default')
    service.approve_proposal('default',first['proposals'][0]['id'],current['snapshot_hash'],'qa-engineer','engineer')
    before_retry=service.get('default')
    repeated=service.add_proposals('default',DOC_ID,'supplier',offers(),None,expected,
        'qa-engineer',TRACE,operation_key='qa-batch-retry')
    assert repeated==first
    assert service.get('default')==before_retry
    assert len(before_retry['suppliers'])==1
    assert [q['status'] for q in before_retry['proposals']]==['approved','pending']


def test_duplicate_rows_do_not_duplicate_proposals_or_approval(service):
    rows=offers();rows.append(deepcopy(rows[0]))
    saved=save_batch(service,rows)
    assert len(saved['proposals'])==2
    before=service.get('default')
    repeated=save_batch(service)
    assert len(repeated['proposals'])==2
    after=service.get('default')
    assert after['proposals']==before['proposals'] and after['suppliers']==before['suppliers']
    assert len(after['extraction_runs'])==len(before['extraction_runs'])+1
    before=after
    with pytest.raises(Forbidden):
        service.approve_proposal('default',saved['proposals'][0]['id'],before['snapshot_hash'],'qa-inspector','inspector')
    service.approve_proposal('default',saved['proposals'][0]['id'],before['snapshot_hash'],'qa-engineer','engineer')
    p=service.get('default')
    assert [s['name'] for s in p['suppliers']]==['R&D Marketing']
    assert next(q for q in p['proposals'] if q['data']['name']=='Benson Guam Enterprises Inc.')['status']=='pending'


def test_empty_supplier_result_records_assurance_without_inventing_a_bid(service):
    before=service.get('default')
    assert save_batch(service,[])=={'proposals':[],'trace':TRACE}
    after=service.get('default')
    assert after['proposals']==before['proposals']==[] and after['suppliers']==[]
    assert after['snapshot_hash']!=before['snapshot_hash']
    assert len(after['extraction_runs'])==1 and after['extraction_runs'][0]['trace']==TRACE


@pytest.mark.parametrize('rows',[{},[{},{}]])
def test_batch_does_not_allow_multiple_or_malformed_evidence(service,rows):
    before=service.get('default')
    with pytest.raises(Conflict):
        service.add_proposals('default',DOC_ID,'evidence',rows,None,before['snapshot_hash'],'qa-inspector',TRACE)
    assert service.get('default')==before


def test_temporal_persistence_keeps_all_supplier_rows_and_retries_atomically(tmp_path,monkeypatch):
    url='sqlite:///'+str(tmp_path/'temporal-batch.db');monkeypatch.setenv('DATABASE_URL',url);monkeypatch.setenv('APP_MODE','live')
    s=Service(url);p=prepare(s)
    request={'pid':'default','docid':DOC_ID,'body':{'kind':'supplier','snapshot_hash':p['snapshot_hash']},
             'actor':'qa-engineer','workflow_id':'qa-source-batch', 'result':{'data':offers(),'trace':TRACE}}
    first=asyncio.run(persist_extraction(request));second=asyncio.run(persist_extraction(request))
    assert first==second
    assert len(s.get('default')['proposals'])==2
    assert s.get('default')['version']==p['version']+1


def test_temporal_persistence_rejects_multiple_evidence_instead_of_taking_first(service,monkeypatch):
    monkeypatch.setenv('DATABASE_URL',service.database_url);monkeypatch.setenv('APP_MODE','live')
    request={'pid':'default','docid':DOC_ID,'body':{'kind':'evidence','snapshot_hash':service.get('default')['snapshot_hash']},
             'actor':'qa-inspector','workflow_id':'qa-multiple-evidence','result':{'data':[{},{}],'trace':TRACE}}
    with pytest.raises(ApplicationError,match=r'^Expected one evidence proposal\.$'):
        asyncio.run(persist_extraction(request))
    assert service.get('default')['proposals']==[]


@pytest.mark.parametrize('row_count',[0,1,2])
def test_http_supplier_extraction_keeps_all_offers_and_legacy_single_response(tmp_path,monkeypatch,row_count):
    monkeypatch.setenv('RUNTIME_DIR',str(tmp_path/'runtime'))
    monkeypatch.setenv('LLM_BASE_URL','http://qa-boundary.invalid/v1')
    monkeypatch.delenv('TEMPORAL_ADDRESS',raising=False)
    app=create_app(database_url='sqlite:///'+str(tmp_path/'http-batch.db'),principals={
        'qa-engineer':{'actor':'qa-engineer','role':'engineer','projects':['default']}})
    p=prepare(app.state.service)
    rows=offers()[:row_count]
    class ModelBoundary:
        def extract(self,doc,kind,scope=None):
            return {'data':deepcopy(rows),'trace':TRACE}
    monkeypatch.setattr('tenderproof.api.Apertus',ModelBoundary)
    client=TestClient(app,headers={'Authorization':'Bearer qa-engineer'})
    result=client.post('/api/projects/default/documents/'+DOC_ID+'/extract',json={'kind':'supplier','snapshot_hash':p['snapshot_hash']})
    assert result.status_code==200,result.text
    body=result.json()
    proposals=[body] if row_count==1 else body['proposals']
    assert len(proposals)==row_count
    assert len(app.state.service.get('default')['proposals'])==row_count
    assert app.state.service.get('default')['suppliers']==[]

@pytest.mark.parametrize('invalid_field',[
    {'facts':None}, {'facts':{}}, {'measurements':None}, {'source_ids':None},
])
def test_malformed_nested_source_lists_fail_without_partial_save(service,invalid_field):
    before=service.get('default')
    rows=offers();rows[1].update(invalid_field)
    with pytest.raises(Conflict,match='source'):
        save_batch(service,rows)
    assert service.get('default')==before
