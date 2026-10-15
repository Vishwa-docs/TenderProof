import pytest
from fastapi.testclient import TestClient
from tenderproof.api import create_app
from support.fixtures import TEST_PRINCIPALS, auth, seed_service

@pytest.fixture
def client(tmp_path):
    app=create_app(database_url='sqlite:///'+str(tmp_path/'api.db'),principals=TEST_PRINCIPALS)
    seed_service(app.state.service)
    return TestClient(app,headers=auth())

def test_api_requires_snapshot_and_rejects_role_spoofing_in_live(tmp_path,client):
    p=client.get('/api/projects/default').json()
    assert client.post('/api/projects/default/requirements/req-rating/review',json={'snapshot_hash':p['snapshot_hash'],'accepted':True,'witness_answer':False},headers=auth('commercial')).status_code==403
    live=TestClient(create_app(database_url='sqlite:///'+str(tmp_path/'live.db'),mode='live',principals={'secret':{'actor':'ann','role':'engineer','projects':['default']}}))
    assert live.get('/api/projects/default',headers={'X-Demo-Role':'engineer'}).status_code==401
    assert live.get('/api/projects/default',headers={'Authorization':'Bearer secret'}).status_code==200
    assert live.get('/api/projects/other',headers={'Authorization':'Bearer secret'}).status_code==403

def test_upload_extract_unconfigured_and_source_persistence(client):
    p=client.get('/api/projects/default').json()
    r=client.post('/api/projects/default/documents',data={'snapshot_hash':p['snapshot_hash']},files={'file':('spec.md',b'25 MVA ONAN','text/plain')})
    assert r.status_code==200
    p=client.get('/api/projects/default').json()
    result=client.post('/api/projects/default/documents/'+r.json()['id']+'/extract',json={'snapshot_hash':p['snapshot_hash']})
    assert result.status_code==503
    assert 'Apertus' in result.json()['detail']

@pytest.mark.parametrize('invalid_url',['file:///private/source.txt','http://[invalid','https://example.org:bad-port/source'])
def test_uploaded_source_url_is_provenance_only_and_invalid_url_is_rejected(client,invalid_url):
    before=client.get('/api/projects/default').json()
    invalid=client.post('/api/projects/default/documents',data={'snapshot_hash':before['snapshot_hash'],'source_url':invalid_url},
        files={'file':('qa.txt',b'Constructed source URL regression input.')})
    assert invalid.status_code==422
    assert client.get('/api/projects/default').json()['snapshot_hash']==before['snapshot_hash']
    valid=client.post('/api/projects/default/documents',data={'snapshot_hash':before['snapshot_hash'],'source_url':'https://example.org/source.pdf'},
        files={'file':('qa.txt',b'Constructed source URL regression input.')})
    assert valid.status_code==200
    assert valid.json()['source_url']=='https://example.org/source.pdf'
    stored=client.get('/api/projects/default').json()['documents'][-1]
    assert stored['source_url']=='https://example.org/source.pdf'

def test_api_end_to_end_purchase(client):
    for r in client.get('/api/projects/default').json()['requirements']:
        p=client.get('/api/projects/default').json()
        assert client.post('/api/projects/default/requirements/'+r['id']+'/review',json={'snapshot_hash':p['snapshot_hash'],'accepted':True,'witness_answer':r['witness_expected']}).status_code==200
    p=client.get('/api/projects/default').json(); h=p['snapshot_hash']
    d=client.post('/api/projects/default/decisions',json={'snapshot_hash':h,'supplier_id':'helvetic','gate':'purchase'}).json()
    for role in ['engineer','commercial']:
        assert client.post('/api/projects/default/decisions/'+d['id']+'/approve',json={'snapshot_hash':h},headers=auth(role)).status_code==200
    a=client.post('/api/projects/default/decisions/'+d['id']+'/release',json={'snapshot_hash':h,'idempotency_key':'test'},headers=auth('commercial'))
    assert a.status_code==200 and a.json()['artifact_hash']


@pytest.mark.parametrize('confirmed, expected_status',[(False,'unknown'),(True,'supported')])
def test_type_coverage_requires_explicit_inspector_confirmation(client,confirmed,expected_status):
    from copy import deepcopy
    from support.fixtures import document
    svc=client.app.state.service
    for r in svc.get('default')['requirements']:
        svc.review('default',r['id'],svc.get('default')['snapshot_hash'],True,r['witness_expected'],'eng','engineer')
    doc=document('type-b','Type report B',
        'SYNTHETIC TEST\nHP design family; HP-31 revision B.\n25 MVA ONAN; primary 33 kV; load losses 110 kW at 75 C.',
        revision='B',authority='test_report')
    svc.add_document('default',doc,svc.get('default')['snapshot_hash'],'inspector')
    data=deepcopy(svc.get('default')['evidence'][1])
    for key in ('id','supplier_id'): data.pop(key)
    data.update(kind='type',revision='B',serial='different-unit',source_ids=['type-b:2','type-b:3'])
    for measurement in data['measurements']: measurement['source_ids']=['type-b:3']
    q=svc.add_proposal('default',doc['id'],'evidence',data,'helvetic',svc.get('default')['snapshot_hash'],'inspector',{})
    request={'snapshot_hash':svc.get('default')['snapshot_hash'],'family_coverage_confirmed':confirmed}
    endpoint='/api/projects/default/proposals/'+q['id']+'/approve'

    assert client.post(endpoint,json=request,headers=auth('engineer')).status_code==403
    assert client.post(endpoint,json=request,headers=auth('inspector')).status_code==200
    p=svc.get('default')
    evidence=next(e for e in p['evidence'] if e['id']==q['id'])
    assessment=next(e for e in p['evidence_assessments'] if e['evidence_id']==q['id'])
    assert evidence['approved_family_coverage'] is confirmed
    assert assessment['status']==expected_status
    assert next(q for q in p['proposals'] if q['id']==evidence['id'])['reviewer']=='inspector-qa'


def test_original_image_requires_authenticated_project_access(tmp_path,monkeypatch):
    import base64
    monkeypatch.setenv('RUNTIME_DIR',str(tmp_path/'runtime'))
    live=TestClient(create_app(database_url='sqlite:///'+str(tmp_path/'image.db'),mode='live',principals={
        'owner':{'actor':'ann','role':'engineer','projects':['default']},
        'outsider':{'actor':'bob','role':'engineer','projects':['other']}}))
    headers={'Authorization':'Bearer owner'}
    png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a0ioAAAAASUVORK5CYII=')
    p=live.get('/api/projects/default',headers=headers).json()
    uploaded=live.post('/api/projects/default/documents',headers=headers,data={'snapshot_hash':p['snapshot_hash']},
        files={'file':('nameplate.png',png,'image/png')})
    assert uploaded.status_code==200
    doc=uploaded.json();url='/api/projects/default/documents/'+doc['id']+'/content'

    assert live.get(url).status_code==401
    assert live.get(url,headers={'Authorization':'Bearer outsider'}).status_code==403
    assert live.get(url.replace('/default/','/other/'),headers=headers).status_code==403
    original=live.get(url,headers=headers)
    assert original.status_code==200
    assert original.content==png
    assert original.headers['content-type']=='image/png'
    assert original.headers['x-content-type-options']=='nosniff'
    assert 'image_data_url' not in live.get('/api/projects/default',headers=headers).json()['documents'][0]
