from fastapi.testclient import TestClient
from tenderproof.api import create_app
from support.fixtures import TEST_PRINCIPALS, auth, seed_service


def test_missing_model_endpoint_abstains_before_temporal_dispatch(tmp_path, monkeypatch):
    from tenderproof import workflows
    monkeypatch.setenv('TEMPORAL_ADDRESS', 'unreachable:7233')
    monkeypatch.delenv('LLM_BASE_URL', raising=False)
    async def unexpected_dispatch(request):
        raise AssertionError('Missing model configuration must fail before queueing')
    monkeypatch.setattr(workflows, 'dispatch_extraction', unexpected_dispatch)
    app=create_app(database_url='sqlite:///'+str(tmp_path/'db'),principals=TEST_PRINCIPALS)
    seed_service(app.state.service)
    client = TestClient(app,headers=auth())
    p = client.get('/api/projects/default').json()
    result = client.post('/api/projects/default/documents/owner/extract', json={'snapshot_hash':p['snapshot_hash']})
    assert result.status_code == 503
    assert 'not configured' in result.json()['detail']
