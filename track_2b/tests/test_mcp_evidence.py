"""MCP transport boundary tests. No demonstration records or model output."""
from urllib.parse import parse_qs, urlsplit
import httpx
import pytest
from tenderproof import mcp_server as server


def test_search_query_cannot_change_project_or_parameters(monkeypatch):
    seen=[]
    monkeypatch.setattr(server,'call',lambda method,path,body=None: seen.append((method,path,body)) or {'results':[]})
    query='750 kVA &document_id=other?limit=999#part'
    server.search_evidence('default',query,document_id='span:document',limit=7)
    method,path,body=seen[0]
    assert method=='GET' and body is None
    assert urlsplit(path).path=='/api/projects/default/search'
    assert parse_qs(urlsplit(path).query)=={'q':[query],'document_id':['span:document'],'limit':['7']}


@pytest.mark.parametrize('limit',[0,-1,51,1000,True])
def test_search_rejects_unbounded_limits(monkeypatch,limit):
    monkeypatch.setattr(server,'call',lambda *a,**k: pytest.fail('Invalid input reached transport'))
    with pytest.raises(ValueError):server.search_evidence('default','transformer',limit=limit)


@pytest.mark.parametrize('query',['','   ','x'*301])
def test_search_rejects_empty_and_oversize_queries(monkeypatch,query):
    monkeypatch.setattr(server,'call',lambda *a,**k: pytest.fail('Invalid query reached transport'))
    with pytest.raises(ValueError):server.search_evidence('default',query)


@pytest.mark.parametrize('project_id',['../other','default/../../other','default?x=1','default#other',''])
def test_new_read_tools_reject_path_injection(monkeypatch,project_id):
    monkeypatch.setattr(server,'call',lambda *a,**k: pytest.fail('Invalid project reached transport'))
    with pytest.raises(ValueError):server.inspect_review_queue(project_id)
    with pytest.raises(ValueError):server.export_review_dossier(project_id)


def test_revision_diff_requires_exact_hashes(monkeypatch):
    seen=[]
    monkeypatch.setattr(server,'call',lambda method,path,body=None:seen.append((method,path,body)) or {})
    with pytest.raises(ValueError):server.compare_package_revisions('default','other', 'b'*64)
    server.compare_package_revisions('default','a'*64,'b'*64)
    method,path,body=seen[0]
    assert method=='GET' and body is None
    assert parse_qs(urlsplit(path).query)=={'from_hash':['a'*64],'to_hash':['b'*64]}


def test_review_tools_use_get_and_preserve_draft_state(monkeypatch):
    seen=[]
    def capture(method,path,body=None):
        seen.append((method,path,body));return {'status':'draft','release_count':0}
    monkeypatch.setattr(server,'call',capture)
    server.inspect_review_queue('default')
    result=server.export_review_dossier('default')
    assert result['status']=='draft' and result['release_count']==0
    assert seen==[('GET','/api/projects/default/analysis',None),('GET','/api/projects/default/dossier',None)]


def test_mcp_call_requires_token_and_preserves_denial(monkeypatch):
    monkeypatch.delenv('TENDERPROOF_MCP_TOKEN',raising=False)
    with pytest.raises(ValueError,match='required'):server.call('GET','/api/projects/default/analysis')
    monkeypatch.setenv('TENDERPROOF_MCP_TOKEN','test-transport-only')
    request=httpx.Request('GET','http://localhost/api/projects/default/analysis')
    denied=httpx.Response(403,request=request,json={'detail':'Forbidden'})
    class DeniedClient:
        def __init__(self,**kwargs):assert kwargs['trust_env'] is False
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def request(self,*args,**kwargs):return denied
    monkeypatch.setattr(server.httpx,'Client',DeniedClient)
    with pytest.raises(httpx.HTTPStatusError):server.call('GET','/api/projects/default/analysis')
