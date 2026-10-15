"""Isolated software QA for complete source windows; no actual model inference."""
import asyncio
import hashlib
import json
from copy import deepcopy
from types import SimpleNamespace
import httpx
import pytest
from fastapi.testclient import TestClient
from tenderproof.integrations import Apertus,ModelUnavailable
from tenderproof.api import create_app


def source_document():
    sizes=[(1,16000),(1,0),(1,16000),(2,24000),(3,24000),(4,40000)]
    return {'id':'qa-full','name':'Constructed window regression only','sha256':'a'*64,
            'spans':[{'id':f'qa-full:{i+1}','page':page,'text':('Ω' if i==0 else str(i))*size,'bbox':None}
                     for i,(page,size) in enumerate(sizes)]}


def model_boundary(invalid_window=None,invalid_source='invented:outside-window',vary_window=None):
    observed=[]
    def respond(request):
        body=json.loads(request.content);payload=json.loads(body['messages'][1]['content'])
        observed.append(payload)
        role=body['messages'][0]['content']
        if 'You are the document interpreter' in role:result={'summary':'QA local window only'}
        elif 'You are the obligation mapper' in role:
            ref=payload['source_spans'][0][0]
            if payload['document_context']['window_index']==invalid_window:ref=invalid_source
            result={'requirements':[{'title':'QA repeated rating','property':'rated_power','operator':'eq',
                                    'value':'751' if payload['document_context']['window_index']==vary_window else '750',
                                    'unit':'kVA','source_ids':[ref]}]}
        else:result={'issues':[]}
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(result)}}]})
    return Apertus(base_url='http://qa.invalid/v1',transport=httpx.MockTransport(respond)),observed


def test_plan_preserves_every_ordered_span_and_character_with_page_aware_windows():
    from tenderproof.integrations import plan_extraction
    doc=source_document();plan=plan_extraction(doc,'requirements')
    assert plan==plan_extraction(deepcopy(doc),'requirements')
    assert plan['window_count']==3
    assert [(w['start'],w['stop']) for w in plan['windows']]==[(0,3),(3,5),(5,6)]
    restored=[s for w in plan['windows'] for s in doc['spans'][w['start']:w['stop']]]
    assert restored==doc['spans']
    assert sum(w['source_character_count'] for w in plan['windows'])==120000
    assert plan['source_span_count']==6
    assert all(w['source_character_count']<=48000 for w in plan['windows'])
    for w in plan['windows']:
        spans=doc['spans'][w['start']:w['stop']]
        canonical=json.dumps([[s['id'],s['page'],s['text']] for s in spans],ensure_ascii=False,separators=(',',':'))
        assert w['source_sha256']==hashlib.sha256(canonical.encode()).hexdigest()


def test_large_single_page_splits_only_between_spans_and_empty_span_is_kept():
    from tenderproof.integrations import plan_extraction
    doc=source_document()
    for span in doc['spans']:span['page']=1
    plan=plan_extraction(doc,'requirements')
    assert sum(w['span_count'] for w in plan['windows'])==6
    assert all(w['pages']==[1] for w in plan['windows'])


def payload_boundary_document(length):
    overhead=len(json.dumps([['s1',1,'']],ensure_ascii=False,separators=(',',':')))
    escaped,remainder=divmod(length-overhead,6)
    return {'id':'qa-boundary','spans':[{'id':'qa-boundary:1','page':1,'text':'\x00'*escaped+'x'*remainder}]}


def test_source_payload_exact_limit_is_preserved_in_all_actual_role_requests():
    from tenderproof.integrations import plan_extraction
    doc=payload_boundary_document(56000);plan=plan_extraction(doc,'requirements')
    assert plan['window_count']==1
    assert plan['windows'][0]['source_payload_characters']==56000
    lengths=[]
    def respond(request):
        content=json.loads(request.content)['messages'][1]['content']
        offset=content.index('"source_spans":')+len('"source_spans":')
        remainder=content[offset:].lstrip()
        spans,end=json.JSONDecoder().raw_decode(remainder)
        lengths.append(end)
        assert spans==[['s1',1,doc['spans'][0]['text']]]
        result={'requirements':[]} if 'obligation mapper' in json.loads(request.content)['messages'][0]['content'] else {'issues':[]}
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(result)}}]})
    Apertus(base_url='http://qa.invalid/v1',transport=httpx.MockTransport(respond)).extract(doc,'requirements')
    assert lengths==[56000]*4


def test_single_span_payload_one_character_over_limit_abstains_before_calls():
    model,observed=model_boundary()
    with pytest.raises(ModelUnavailable,match='source span exceeds'):
        model.extract(payload_boundary_document(56001),'requirements')
    assert observed==[]


def test_combined_payload_one_character_over_limit_splits_without_losing_content():
    from tenderproof.integrations import plan_extraction
    overhead=len(json.dumps([['s1',1,''],['s2',1,'']],ensure_ascii=False,separators=(',',':')))
    escaped,remainder=divmod(56001-overhead,6)
    doc={'id':'qa-boundary','spans':[{'id':'qa-boundary:1','page':1,'text':'\x00'*(escaped//2)},
                  {'id':'qa-boundary:2','page':1,'text':'\x00'*(escaped-escaped//2)+'x'*remainder}]}
    combined=json.dumps([[f's{i+1}',s['page'],s['text']] for i,s in enumerate(doc['spans'])],ensure_ascii=False,separators=(',',':'))
    assert len(combined)==56001
    before=deepcopy(doc['spans']);plan=plan_extraction(doc,'requirements')
    assert plan['window_count']==2
    assert [s for w in plan['windows'] for s in doc['spans'][w['start']:w['stop']]]==before
    for w in plan['windows']:
        payload=[[f's{i+1}',doc['spans'][i]['page'],doc['spans'][i]['text']] for i in range(w['start'],w['stop'])]
        assert len(json.dumps(payload,ensure_ascii=False,separators=(',',':')))==w['source_payload_characters']<=56000


@pytest.mark.parametrize('mode',['oversized_span','too_many_windows','duplicate_id','invalid_text'])
def test_invalid_or_unbounded_plan_abstains_before_any_model_call(mode):
    doc=source_document()
    if mode=='oversized_span':doc['spans']=doc['spans'][:1];doc['spans'][0]['text']='x'*48001
    elif mode=='too_many_windows':doc['spans']=[{'id':f'qa-full:{i}','page':i+1,'text':'x'*48000} for i in range(13)]
    elif mode=='duplicate_id':doc['spans'][1]['id']=doc['spans'][0]['id']
    else:doc['spans'][1]['text']=None
    model,observed=model_boundary()
    with pytest.raises(ModelUnavailable):model.extract(doc,'requirements')
    assert observed==[]


def test_all_four_roles_see_every_exact_window_and_only_exact_rows_are_deduplicated():
    doc=source_document();before=deepcopy(doc);model,observed=model_boundary()
    result=model.extract(doc,'requirements',scope={'equipment':'QA selected item'})
    assert len(observed)==12 and doc==before
    mapped=result['trace']['source_id_mapping']
    for role_index in range(4):
        received=[(mapped[ref],page,text) for payload in observed[role_index::4]
                  for ref,page,text in payload['source_spans']]
        assert received==[(s['id'],s['page'],s['text']) for s in doc['spans']]
    assert len(result['data'])==1
    assert result['data'][0]['source_ids']==['qa-full:1','qa-full:4','qa-full:6']
    assert result['trace']['window_count']==3 and len(result['trace']['calls'])==12
    assert result['trace']['planned_call_count']==12
    assert result['trace']['planned_inference_budget_seconds']==3720
    assert result['trace']['coverage']['all_original_spans_present'] is True
    assert result['trace']['coverage']['source_character_count']==120000
    assert result['trace']['global_consistency_review_required'] is True
    assert all(len(w['calls'])==4 and w['source_sha256'] for w in result['trace']['windows'])
    assert [p['document_context']['window_index'] for p in observed]==[1]*4+[2]*4+[3]*4
    assert all(p['document_context']['window_count']==3 for p in observed)
    assert all(p['selected_equipment_scope']=={'equipment':'QA selected item'} for p in observed)


@pytest.mark.parametrize('kind',['supplier','evidence'])
def test_other_extraction_kinds_never_silently_window_or_drop_a_large_document(kind):
    model,observed=model_boundary()
    with pytest.raises(ModelUnavailable):model.extract(source_document(),kind)
    assert observed==[]


def test_deduplication_keeps_conflicting_values_and_all_their_original_citations():
    model,_=model_boundary(vary_window=2)
    result=model.extract(source_document(),'requirements')
    assert [(r['value'],r['source_ids']) for r in result['data']]==[
        ('750',['qa-full:1','qa-full:6']),('751',['qa-full:4'])]


def test_a_window_cannot_cite_unseen_content_from_another_window():
    model,observed=model_boundary(invalid_window=2,invalid_source='qa-full:1')
    with pytest.raises(ModelUnavailable):model.extract(source_document(),'requirements')
    assert len(observed)==6


def test_invalid_later_window_saves_no_candidates_or_partial_snapshot(tmp_path,monkeypatch):
    monkeypatch.setenv('RUNTIME_DIR',str(tmp_path/'runtime'))
    monkeypatch.setenv('LLM_BASE_URL','http://qa.invalid/v1');monkeypatch.delenv('TEMPORAL_ADDRESS',raising=False)
    app=create_app(database_url='sqlite:///'+str(tmp_path/'window.db'),principals={
        'qa':{'actor':'qa-engineer','role':'engineer','projects':['default']}})
    service=app.state.service;p=service.get('default')
    service.set_metadata('default',p['snapshot_hash'],'QA','QA','QA selected item','qa-engineer','engineer')
    service.add_document('default',source_document(),service.get('default')['snapshot_hash'],'qa-engineer')
    before=service.get('default');model,observed=model_boundary(invalid_window=2)
    monkeypatch.setattr('tenderproof.api.Apertus',lambda:model)
    response=TestClient(app).post('/api/projects/default/documents/qa-full/extract',
        headers={'Authorization':'Bearer qa'},json={'snapshot_hash':before['snapshot_hash'],'kind':'requirements'})
    assert response.status_code==503 and len(observed)==6
    assert service.get('default')==before


def test_temporal_dispatch_captures_exact_multiwindow_plan_and_budget(monkeypatch):
    from temporalio.client import Client
    from tenderproof import workflows
    from tenderproof.integrations import plan_extraction
    doc=source_document();submitted=[]
    monkeypatch.setenv('TEMPORAL_ADDRESS','qa-temporal:7233');monkeypatch.setenv('LLM_TIMEOUT_SECONDS','300')
    monkeypatch.setattr(workflows,'service',lambda:SimpleNamespace(get=lambda pid:{'snapshot_hash':'qa-hash','documents':[doc]}))
    class Handle:
        async def result(self):return {'candidates':[]}
    class ClientBoundary:
        async def start_workflow(self,run,request,**kwargs):submitted.append(request);return Handle()
    async def connect(address):return ClientBoundary()
    monkeypatch.setattr(Client,'connect',connect)
    asyncio.run(workflows.dispatch_extraction({'pid':'default','docid':doc['id'],
        'body':{'kind':'requirements','snapshot_hash':'qa-hash'},'actor':'qa'}))
    assert submitted[0]['extraction_plan']==plan_extraction(doc,'requirements')
    assert submitted[0]['inference_budget_seconds']==3720
    assert submitted[0]['planned_window_count']==3


def test_persisting_all_windows_is_one_pending_batch_and_retry_is_idempotent(tmp_path,monkeypatch):
    from tenderproof.service import Service
    from tenderproof.workflows import persist_extraction
    url='sqlite:///'+str(tmp_path/'atomic.db');monkeypatch.setenv('DATABASE_URL',url)
    service=Service(url);p=service.get('default')
    service.set_metadata('default',p['snapshot_hash'],'QA','QA','QA item','qa','engineer')
    doc=source_document();service.add_document('default',doc,service.get('default')['snapshot_hash'],'qa')
    before=service.get('default');model,_=model_boundary()
    result=model.extract(doc,'requirements')
    request={'pid':'default','docid':doc['id'],'body':{'kind':'requirements','snapshot_hash':before['snapshot_hash']},
             'actor':'qa','workflow_id':'qa-all-windows','result':result}
    first=asyncio.run(persist_extraction(request));second=asyncio.run(persist_extraction(request))
    after=service.get('default')
    assert first==second and after['version']==before['version']+1
    assert len(after['requirements'])==1 and after['requirements'][0]['status']=='pending'
    assert after['requirements'][0]['source_ids']==['qa-full:1','qa-full:4','qa-full:6']


def test_tampered_or_incomplete_saved_plan_cannot_start_inference():
    from tenderproof.integrations import plan_extraction
    doc=source_document();plan=plan_extraction(doc,'requirements');plan['windows'].pop()
    model,observed=model_boundary()
    with pytest.raises(ModelUnavailable):model.extract(doc,'requirements',plan=plan)
    assert observed==[]
