import json
import pytest
import httpx
from tenderproof.integrations import Apertus, ModelUnavailable, parse_document


def test_text_sources_have_stable_content_identity_and_page_pins():
    d=parse_document('owner.md',b'# Specification\n25 MVA ONAN\f33 kV')
    assert d['sha256']==parse_document('renamed.md',b'# Specification\n25 MVA ONAN\f33 kV')['sha256']
    assert any(s['page']==2 and '33 kV' in s['text'] for s in d['spans'])


def test_missing_endpoint_never_substitutes_demo_output():
    with pytest.raises(ModelUnavailable): Apertus(base_url='').extract({'spans':[]},'requirements')


def test_structured_model_output_is_validated_and_sources_bound():
    responses=[{'summary':'25 MVA ONAN'}, {'requirements':[{'title':'Power','property':'rated_power','operator':'ge',
        'value':'25','unit':'MVA','conditions':{'cooling':'ONAN'},'phase':'purchase','source_ids':['doc:1']}]},
        {'issues':[]}, {'issues':[]}]
    def responder(request):
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(responses.pop(0))}}]})
    a=Apertus(base_url='http://localhost:9999/v1',transport=httpx.MockTransport(responder))
    result=a.extract({'spans':[{'id':'doc:1','text':'25 MVA ONAN','page':1}]},'requirements')
    assert result['data'][0]['conditions']=={'cooling':'ONAN'}
    assert result['trace']['inference']=='live_endpoint'
    assert len(result['trace']['roles'])==4


def test_model_cannot_invent_source_or_approval_status():
    responses=[{'summary':'x'}, {'requirements':[{'title':'Power','property':'rated_power','operator':'ge',
        'value':'25','unit':'MVA','conditions':{},'phase':'purchase','source_ids':['invented']}]}]
    def responder(request):return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(responses.pop(0))}}]})
    a=Apertus(base_url='http://localhost:9999/v1',transport=httpx.MockTransport(responder))
    with pytest.raises(ModelUnavailable):a.extract({'spans':[{'id':'doc:1','text':'x','page':1}]},'requirements')


def test_null_model_content_is_controlled_abstention():
    transport=httpx.MockTransport(lambda request: httpx.Response(200,json={'choices':[{'message':{'content':None}}]}))
    a=Apertus(base_url='http://localhost:9999/v1',transport=transport)
    with pytest.raises(ModelUnavailable):
        a.extract({'spans':[{'id':'doc:1','text':'25 MVA ONAN','page':1}]},'requirements')


@pytest.mark.parametrize('malformed_issues',[None,'not a list',[{'message':'not a string'}]])
def test_malformed_audit_issues_are_disclosed_not_fatal_and_never_become_audit_findings(malformed_issues):
    responses=[{'summary':'25 MVA ONAN'}, {'requirements':[{'title':'Power','property':'rated_power','operator':'ge',
        'value':'25','unit':'MVA','conditions':{'cooling':'ONAN'},'source_ids':['doc:1']}]},
        {'issues':malformed_issues}, {'issues':[]}]
    def responder(request):
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(responses.pop(0))}}]})
    a=Apertus(base_url='http://localhost:9999/v1',transport=httpx.MockTransport(responder))
    result=a.extract({'spans':[{'id':'doc:1','text':'25 MVA ONAN','page':1}]},'requirements')
    assert len(result['data'])==1 and result['trace']['roles'][-2:]==['evidence analyst','adversarial challenger']
    assert [f['role'] for f in result['trace']['audit_failures']]==['evidence analyst']
    assert any('evidence analyst' in i and 'no result from that role' in i for i in result['trace']['issues'])
    assert 'not a list' not in json.dumps(result['trace']['issues']) and 'not a string' not in json.dumps(result['trace']['issues'])


def invoke_controlled_response(kind, proposal):
    """Isolated transport QA; this is not an Apertus performance evaluation."""
    requests=[]
    responses=[{'summary':'Selected equipment only'},proposal,{'issues':[]},{'issues':[]}]
    def responder(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(responses.pop(0))}}]})
    doc={'sha256':'a'*64,'spans':[
        {'id':'original-document:17','page':2,'text':'Selected item: 750 kVA','bbox':{'l':1}},
        {'id':'original-document:36','page':5,'text':'Selected item alternate: 750 kVA; USD 100','bbox':None}]}
    scope={'equipment':'Selected item 2, 750 kVA; exclude item 1'}
    result=Apertus(base_url='http://localhost:9999/v1',transport=httpx.MockTransport(responder)).extract(doc,kind,scope)
    return result,requests,doc,scope


def qa_fact(source='s1'):
    return {'property':'rated_power','operator':'eq','value':'750','unit':'kVA','source_ids':[source]}


@pytest.mark.parametrize('kind,proposal',[
    ('requirements',{'requirements':[{'title':'Rating',**qa_fact()}]}),
    ('supplier',{'supplier':{'name':'QA supplier','configuration':'item 2','facts':[qa_fact('s2')]}}),
    ('evidence',{'evidence':{'title':'QA report','kind':'routine','configuration':'item 2',
                             'source_ids':['s1'],'measurements':[qa_fact('s2')]}}),
])
def test_compact_aliases_restore_original_nested_sources_and_preserve_selected_scope(kind,proposal):
    result,requests,doc,scope=invoke_controlled_response(kind,proposal)
    row=result['data'][0]
    if kind=='requirements':assert row['source_ids']==['original-document:17']
    if kind=='supplier':assert row['facts'][0]['source_ids']==['original-document:36']
    if kind=='evidence':
        assert row['source_ids']==['original-document:17']
        assert row['measurements'][0]['source_ids']==['original-document:36']
    assert len(requests)==4
    for request in requests:
        payload=json.loads(request['messages'][1]['content'])
        assert payload['selected_equipment_scope']==scope
        assert payload['source_spans']==[['s1',2,doc['spans'][0]['text']],['s2',5,doc['spans'][1]['text']]]
    assert result['trace']['source_id_mapping']=={'s1':'original-document:17','s2':'original-document:36'}
    assert result['trace']['selected_equipment_scope']==scope
    assert result['trace']['source_span_count']==2
    assert result['trace']['document_sha256']==doc['sha256']


def test_supplier_mapper_preserves_distinct_basic_and_alternate_offers():
    suppliers=[{'name':'QA supplier','configuration':configuration,'facts':[qa_fact(source)]}
               for configuration,source in [('basic','s1'),('alternate','s2')]]
    result,requests,_,_=invoke_controlled_response('supplier',{'suppliers':suppliers})
    assert [x['configuration'] for x in result['data']]==['basic','alternate']
    assert [x['facts'][0]['source_ids'] for x in result['data']]==[['original-document:17'],['original-document:36']]
    assert all(x['price_cents'] is None and x['delivery_weeks'] is None for x in result['data'])
    assert '"suppliers"' in requests[1]['messages'][0]['content']


def test_supplier_mapper_can_abstain_with_no_applicable_offers():
    result,_,_,_=invoke_controlled_response('supplier',{'suppliers':[]})
    assert result['data']==[]


def test_supplier_mapper_rejects_entire_batch_when_one_offer_invents_source():
    suppliers=[{'name':'QA supplier','configuration':'basic','facts':[qa_fact()]},
               {'name':'QA supplier','configuration':'alternate','facts':[qa_fact('s999')]}]
    with pytest.raises(ModelUnavailable):invoke_controlled_response('supplier',{'suppliers':suppliers})


def price_only_offer(**changes):
    # Constructed software-regression input shaped like a bid tabulation: a price, no guarantees.
    return {'name':'QA supplier','configuration':'basic','price_cents':1000,'currency':'USD','source_ids':['s2'],'facts':[],**changes}


def test_price_only_supplier_offer_keeps_its_own_source_citation_and_no_invented_facts():
    # Real-run defect: a bid abstract has prices but no guarantees, so a mandatory
    # non-empty `facts` list forced the model to invent facts or fail validation.
    result,_,_,_=invoke_controlled_response('supplier',{'suppliers':[price_only_offer()]})
    row=result['data'][0]
    assert row['facts']==[] and row['source_ids']==['original-document:36']
    assert row['price_cents']==1000 and row['currency']=='USD'


def test_supplier_offer_with_an_invented_source_fails_the_whole_run_even_if_otherwise_invalid():
    for offer in ({'source_ids':['s999']},{'source_ids':['s999'],'currency':'XYZ'}):
        with pytest.raises(ModelUnavailable):invoke_controlled_response('supplier',{'suppliers':[price_only_offer(**offer)]})


def test_offer_without_any_citation_is_rejected_verbatim_and_disclosed_not_saved():
    offer=price_only_offer(source_ids=[],price_cents=None,currency=None)
    result,_,_,_=invoke_controlled_response('supplier',{'suppliers':[offer]})
    assert result['data']==[] and result['trace']['rejected_row_count']==1
    rejected=result['trace']['rejected_rows'][0]
    assert rejected['reason']=='No source citation' and rejected['window']==1 and json.loads(rejected['raw_row'])==offer
    assert result['trace']['windows'][0]['rejected_row_count']==1


@pytest.mark.parametrize('field,value',[('price_cents',1000),('currency','USD'),('delivery_weeks',24),('expedite_cents',0),('rework_cents',0)])
def test_commercial_values_must_cite_the_offer_not_only_a_fact(field,value):
    offer={'name':'QA supplier','price_cents':None,'currency':None,field:value,'source_ids':[],'facts':[qa_fact('s2')]}
    result,_,_,_=invoke_controlled_response('supplier',{'suppliers':[offer]})
    assert result['data']==[] and "commercial value needs the offer's own source citation" in result['trace']['rejected_rows'][0]['reason']
    offer['source_ids']=['s2']
    result,_,_,_=invoke_controlled_response('supplier',{'suppliers':[offer]})
    assert result['data'][0]['source_ids']==['original-document:36'] and result['trace']['rejected_row_count']==0


def test_a_schema_invalid_row_is_rejected_and_disclosed_while_valid_rows_are_saved_unchanged():
    # Real-run defect: one junk row from the 8B model used to discard everything.
    good=price_only_offer();bad=price_only_offer(name='Junk offer',currency='XYZ')
    result,_,_,_=invoke_controlled_response('supplier',{'suppliers':[good,bad]})
    assert [row['name'] for row in result['data']]==['QA supplier']
    rejected=result['trace']['rejected_rows']
    assert len(rejected)==1 and rejected[0]['index']==1 and 'currency' in rejected[0]['reason']
    assert json.loads(rejected[0]['raw_row'])==bad
    assert result['trace']['rejected_row_count']==1


def test_non_numeric_requirement_values_are_rejected_not_fatal():
    rows=[{'title':'Not a requirement','property':'Equipment Type','operator':'eq','value':'transformer','unit':'none','source_ids':['s1']},
          {'title':'Rating',**qa_fact()}]
    result,_,_,_=invoke_controlled_response('requirements',{'requirements':rows})
    assert [row['title'] for row in result['data']]==['Rating']
    assert result['trace']['rejected_row_count']==1 and 'value' in result['trace']['rejected_rows'][0]['reason']


def test_every_role_requests_server_enforced_bounded_json_schema_decoding():
    # Real-run defect: json_object mode let the model count source ids upward until truncation.
    _,requests,_,_=invoke_controlled_response('supplier',{'suppliers':[price_only_offer()]})
    formats=[r['response_format'] for r in requests]
    assert all(f['type']=='json_schema' and f['json_schema']['strict'] is True for f in formats)
    interpreter,mapper,analyst,challenger=[f['json_schema']['schema'] for f in formats]
    assert interpreter['properties']['summary']['maxLength']==2000
    assert mapper['properties']['suppliers']['maxItems']==20
    assert mapper['properties']['suppliers']['items']['properties']['source_ids']['maxItems']==8
    fact=mapper['$defs']['Fact']['properties']
    assert fact['source_ids']['maxItems']==8 and fact['value']['pattern']=='^-?[0-9]+(\\.[0-9]+)?$'
    for audit in (analyst,challenger):
        assert audit['properties']['issues']['maxItems']==8 and audit['properties']['issues']['items']=={'type':'string','maxLength':200}


def test_finish_reason_is_traced_and_truncation_is_named_in_the_failure():
    def truncated(request):
        return httpx.Response(200,json={'choices':[{'finish_reason':'length','message':{'content':'{"summary": "cut off'}}]})
    a=Apertus(base_url='http://localhost:9999/v1',transport=httpx.MockTransport(truncated))
    with pytest.raises(ModelUnavailable,match='max_tokens'):
        a.extract({'spans':[{'id':'doc:1','text':'x','page':1}]},'requirements')
    ok=httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]},request=httpx.Request('POST','http://x'))
    from tenderproof.integrations import _response_trace
    assert _response_trace(ok,'qa',0)['finish_reason']=='stop'


def test_requirement_prompt_asks_for_short_citations_and_an_empty_list_when_nothing_fits():
    _,requests,_,_=invoke_controlled_response('requirements',{'requirements':[{'title':'Rating',**qa_fact()}]})
    prompt=requests[1]['messages'][0]['content']
    assert 'never a range of unrelated spans' in prompt and '{"requirements": []}' in prompt
    assert 'not a requirement' in prompt and 'value must be a number' in prompt


def test_audit_roles_have_distinct_focus_and_a_bounded_plain_string_format():
    # Real-run defect: one vague shared audit prompt made the 8B model emit span-id
    # lists, truncated JSON and objects instead of strings. Audits stay mandatory.
    _,requests,_,_=invoke_controlled_response('supplier',{'suppliers':[price_only_offer()]})
    analyst,challenger=[r['messages'][0]['content'] for r in requests[2:4]]
    assert 'You are the evidence analyst' in analyst and 'You are the adversarial challenger' in challenger
    assert 'Focus on support' in analyst and 'Focus on challenge' in challenger
    assert 'Focus on challenge' not in analyst and 'Focus on support' not in challenger
    for prompt in (analyst,challenger):
        assert 'one plain string, never an object' in prompt and 'at most 8 issues' in prompt
        assert 'Never list span ids on their own' in prompt
    assert 'multiplied by 100' in analyst
    for request in requests[2:4]:
        payload=json.loads(request['messages'][1]['content'])
        assert payload['proposals'][0]['name']=='QA supplier' and len(payload['source_spans'])==2


def test_supplier_prompt_does_not_force_unknown_commercial_fields_to_null():
    _,requests,_,_=invoke_controlled_response('supplier',{'suppliers':[price_only_offer()]})
    prompt=requests[1]['messages'][0]['content']
    assert '"delivery_weeks": <integer weeks> or null' in prompt
    assert '"expedite_cents": <integer cents> or null' in prompt and '"rework_cents": <integer cents> or null' in prompt


def test_response_trace_binds_each_role_to_actual_content_without_prompts_or_credentials(monkeypatch):
    import hashlib
    monkeypatch.setenv('LLM_TIMEOUT_SECONDS','120')
    outputs=[{'summary':'QA scope'}, {'requirements':[]}, {'issues':[]}, {'issues':[]}]
    contents=[json.dumps(x) for x in outputs]
    observed=[]
    def responder(request):
        i=len(observed);observed.append(request)
        return httpx.Response(200,json={'id':f'qa-response-{i}','model':'qa-controlled-apertus',
            'usage':{'prompt_tokens':10+i,'completion_tokens':3,'total_tokens':13+i},
            'choices':[{'message':{'content':contents[i]}}]})
    result=Apertus(base_url='http://localhost:9999/v1',api_key='qa-secret',transport=httpx.MockTransport(responder)).extract(
        {'spans':[{'id':'doc:1','text':'qa source private text','page':1}]},'requirements')
    calls=result['trace']['calls']
    assert len(calls)==4
    for i,call in enumerate(calls):
        assert call['role']==result['trace']['roles'][i]
        assert call['response_id']==f'qa-response-{i}'
        assert call['response_model']=='qa-controlled-apertus'
        assert call['usage']=={'prompt_tokens':10+i,'completion_tokens':3,'total_tokens':13+i}
        assert call['assistant_content_sha256']==hashlib.sha256(contents[i].encode()).hexdigest()
        assert call['duration_seconds']>=0
        assert observed[i].extensions['timeout']['read']==120
    assert 'qa-secret' not in json.dumps(calls)
    assert 'qa source private text' not in json.dumps(calls)


def test_response_trace_allows_omitted_provider_metadata():
    result,_,_,_=invoke_controlled_response('requirements',{'requirements':[]})
    assert all(call['response_id'] is None and call['response_model'] is None and call['usage'] is None
               for call in result['trace']['calls'])


@pytest.mark.parametrize('timeout',['0','901','nan','invalid'])
def test_http_timeout_is_bounded_and_invalid_settings_abstain(monkeypatch,timeout):
    monkeypatch.setenv('LLM_TIMEOUT_SECONDS',timeout)
    with pytest.raises(ModelUnavailable):
        invoke_controlled_response('requirements',{'requirements':[]})


def test_native_pdf_supplement_preserves_omitted_clauses_operators_and_page_identity():
    from tenderproof.integrations import _merge_native_page_text
    doc={'id':'original','spans':[{'id':'original:1','page':1,'text':'Rating  750 kVA\nLimit >= 5','bbox':None},
                                {'id':'original:2','page':2,'text':'Clause G. Guaranteed loss','bbox':None}]}
    _merge_native_page_text(doc,1,'Rating 750 kVA\nLimit <= 5\nClause G. Guaranteed loss')
    assert len(doc['spans'])==3
    supplement=doc['spans'][-1]
    assert supplement=={'id':'original:native:1','page':1,'text':'Limit <= 5\nClause G. Guaranteed loss',
                        'bbox':None,'source_kind':'pdf_native_text'}
    _merge_native_page_text(doc,1,'Rating 750 kVA\nLimit <= 5\nClause G. Guaranteed loss')
    assert len(doc['spans'])==3
    _merge_native_page_text(doc,3,'')
    assert len(doc['spans'])==3


def test_opt_in_call_archives_are_private_exact_and_exclude_authorization(monkeypatch,tmp_path):
    import hashlib
    import stat
    trace_dir=tmp_path/'inference-traces'
    monkeypatch.setenv('APERTUS_TRACE_DIR',str(trace_dir))
    result,requests,_,_=invoke_controlled_response('requirements',{'requirements':[]})
    assert len(list(trace_dir.iterdir()))==4
    for call,request in zip(result['trace']['calls'],requests):
        directory=trace_dir/call['trace_id']
        assert len(call['trace_id'])==32 and all(c in '0123456789abcdef' for c in call['trace_id'])
        assert call['trace_path']==call['trace_id']
        assert stat.S_IMODE(directory.stat().st_mode)==0o700
        for name in ['request.json','response.json','metadata.json']:
            assert stat.S_IMODE((directory/name).stat().st_mode)==0o600
        request_bytes=(directory/'request.json').read_bytes()
        response_bytes=(directory/'response.json').read_bytes()
        assert json.loads(request_bytes)==request
        assert 'authorization' not in request_bytes.decode().lower()
        assert call['request_sha256']==hashlib.sha256(request_bytes).hexdigest()
        assert call['response_sha256']==hashlib.sha256(response_bytes).hexdigest()
        assert json.loads(directory.joinpath('metadata.json').read_text())=={k:v for k,v in call.items() if k!='status'}
        assert call['status']=='parsed'  # parsing outcome is downstream of immutable HTTP capture


def test_invalid_provider_content_is_archived_for_investigation(monkeypatch,tmp_path):
    monkeypatch.setenv('APERTUS_TRACE_DIR',str(tmp_path))
    a=Apertus(base_url='http://localhost:9999/v1',transport=httpx.MockTransport(
        lambda request:httpx.Response(200,json={'id':'qa-bad','choices':[{'message':{'content':'not json'}}]})))
    with pytest.raises(ModelUnavailable):a.extract({'spans':[]},'requirements')
    directories=list(tmp_path.iterdir())
    assert len(directories)==1
    response=json.loads((directories[0]/'response.json').read_text())
    assert response['choices'][0]['message']['content']=='not json'


def test_event_summary_discloses_rejected_rows_only_when_there_are_some():
    from tenderproof.service import rejected_note
    assert rejected_note({}) == '' and rejected_note(None) == '' and rejected_note({'rejected_row_count': 0}) == ''
    assert '3 model rows failed validation and were not saved' in rejected_note({'rejected_row_count': 3})


def test_requirement_decoding_is_bounded_numeric_and_cites_few_spans_but_pydantic_limits_are_unchanged():
    # Real-run defect: free-string values let the model emit dozens of junk rows until truncation.
    from tenderproof.models import Candidate
    _,requests,_,_=invoke_controlled_response('requirements',{'requirements':[{'title':'Rating',**qa_fact()}]})
    schema=requests[1]['response_format']['json_schema']['schema']
    rows=schema['properties']['requirements']
    assert rows['maxItems']==15
    item=rows['items']['properties']
    assert item['value']['pattern']=='^-?[0-9]+(\\.[0-9]+)?$' and item['value']['maxLength']==24 and item['source_ids']['maxItems']==8
    assert Candidate.model_json_schema()['properties']['source_ids']['maxItems']==30   # validation bound stays 30


def test_a_window_that_reaches_the_row_cap_says_so_instead_of_silently_dropping_obligations():
    rows=[{'title':f'Rating {i}',**qa_fact()} for i in range(15)]
    result,_,_,_=invoke_controlled_response('requirements',{'requirements':rows})
    assert len(result['data'])==1 or len(result['data'])==15   # exact duplicates may merge across windows
    assert any('15-row output cap' in issue for issue in result['trace']['issues'])
    short,_,_,_=invoke_controlled_response('requirements',{'requirements':rows[:3]})
    assert not any('output cap' in issue for issue in short['trace']['issues'])


def audit_boundary(audit_response):
    """Transport that serves valid interpreter/mapper output and a controlled audit response."""
    calls=[]
    def responder(request):
        body=json.loads(request.content);role=body['messages'][0]['content'];calls.append((role.split(' for an engineering')[0],body['max_tokens']))
        if 'You are the document interpreter' in role:return httpx.Response(200,json={'choices':[{'message':{'content':'{"summary":"x"}'}}]})
        if 'You are the obligation mapper' in role:
            row={'title':'Power','property':'rated_power','operator':'ge','value':'25','unit':'MVA','source_ids':['doc:1']}
            return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'requirements':[row]})}}]})
        return audit_response(request)
    return Apertus(base_url='http://localhost:9999/v1',transport=httpx.MockTransport(responder)),calls


def test_truncated_audit_output_is_disclosed_and_the_validated_proposals_are_still_returned():
    # Real-run defect: an audit looped on whitespace until max_tokens and discarded a whole extraction.
    truncated=lambda request:httpx.Response(200,json={'choices':[{'finish_reason':'length','message':{'content':'{"issues": ["cut off   '}}]})
    model,calls=audit_boundary(truncated)
    result=model.extract({'spans':[{'id':'doc:1','text':'25 MVA','page':1}]},'requirements')
    assert len(result['data'])==1 and len(result['trace']['audit_failures'])==2
    assert all('max_tokens' in f['reason'] for f in result['trace']['audit_failures'])
    assert sum('no result from that role' in i for i in result['trace']['issues'])==2


def test_audit_transport_failure_is_still_fatal_and_audits_get_a_small_token_budget():
    model,calls=audit_boundary(lambda request:httpx.Response(500,json={}))
    with pytest.raises(ModelUnavailable):model.extract({'spans':[{'id':'doc:1','text':'25 MVA','page':1}]},'requirements')
    budgets=dict((role,tokens) for role,tokens in calls)
    assert budgets['You are the obligation mapper']==4096 and budgets['You are the evidence analyst']==800


def test_failed_json_is_linked_once_before_parse_and_failed_audit_retains_trace_id(tmp_path,monkeypatch):
    monkeypatch.setenv('APERTUS_TRACE_DIR',str(tmp_path/'qa-traces'))
    truncated=lambda request:httpx.Response(200,json={'usage':{'completion_tokens':800},'choices':[{'finish_reason':'length','message':{'content':'{"issues": ['}}]})
    model,_=audit_boundary(truncated)
    result=model.extract({'id':'qa-audit','sha256':'a'*64,'spans':[{'id':'doc:1','page':1,'text':'QA rating'}]},'requirements')
    calls=result['trace']['calls'];failures=result['trace']['audit_failures']
    assert len(calls)==4 and len({c['trace_id'] for c in calls})==4
    assert len(failures)==2
    for failure in failures:
        call=next(c for c in calls if c['role']==failure['role'])
        assert failure['trace_id']==call['trace_id']
        assert call['status']=='invalid_structured_output' and call['usage']['completion_tokens']==800
        assert (tmp_path/'qa-traces'/call['trace_id']/'response.json').exists()
