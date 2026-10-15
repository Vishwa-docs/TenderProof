"""Constructed software QA cases; these are never application seed data."""
import pytest
from fastapi.testclient import TestClient
from tenderproof.api import create_app
from tenderproof.service import Service


PRINCIPALS={
    'qa-engineer':{'actor':'qa-engineer','role':'engineer','projects':['default']},
    'qa-inspector':{'actor':'qa-inspector','role':'inspector','projects':['default']},
}


def test_service_starts_with_empty_live_package(tmp_path):
    p=Service('sqlite:///'+str(tmp_path/'empty.db')).get('default')
    assert p['mode']=='live'
    assert p['customer']==p['equipment']==''
    assert p['required_delivery_week'] is None
    assert all(p[key]==[] for key in ('requirements','suppliers','evidence','documents','proposals','decisions'))


def test_product_disallows_demo_mode_and_role_headers(tmp_path):
    with pytest.raises(ValueError):
        create_app(database_url='sqlite:///'+str(tmp_path/'demo.db'),mode='demo',principals=PRINCIPALS)
    client=TestClient(create_app(database_url='sqlite:///'+str(tmp_path/'live.db'),principals=PRINCIPALS))
    assert client.get('/api/projects/default',headers={'X-Demo-Role':'engineer'}).status_code==401
    assert client.get('/api/projects/default',headers={'Authorization':'Bearer qa-engineer'}).status_code==200
    assert client.post('/api/projects/default/reset',json={}).status_code in (404,405)


def test_scope_is_engineer_owned_and_required_before_extraction(tmp_path,monkeypatch):
    monkeypatch.setenv('RUNTIME_DIR',str(tmp_path/'runtime'))
    client=TestClient(create_app(database_url='sqlite:///'+str(tmp_path/'scope.db'),principals=PRINCIPALS))
    engineer={'Authorization':'Bearer qa-engineer'};inspector={'Authorization':'Bearer qa-inspector'}
    state=lambda:client.get('/api/projects/default',headers=engineer).json()
    uploaded=client.post('/api/projects/default/documents',headers=engineer,data={'snapshot_hash':state()['snapshot_hash']},
        files={'file':('qa.txt',b'Constructed QA requirement: 25 MVA ONAN.')})
    assert uploaded.status_code==200
    extract='/api/projects/default/documents/'+uploaded.json()['id']+'/extract'
    assert client.post(extract,headers=engineer,json={'snapshot_hash':state()['snapshot_hash']}).status_code==409
    metadata={'snapshot_hash':state()['snapshot_hash'],'name':'QA scope verification','customer':'QA only','equipment':'Selected transformer unit'}
    assert client.patch('/api/projects/default',headers=inspector,json=metadata).status_code==403
    assert client.patch('/api/projects/default',headers=engineer,json=metadata).status_code==200
    assert state()['equipment']=='Selected transformer unit'


def test_scope_cannot_relabel_previously_extracted_claims(tmp_path):
    from support.fixtures import seed_service
    service=seed_service(Service('sqlite:///'+str(tmp_path/'frozen-scope.db')))
    from tenderproof.service import Conflict
    before=service.get('default')
    with pytest.raises(Conflict):
        service.set_metadata('default',before['snapshot_hash'],'A different package','QA','Different equipment item','eng','engineer')
    assert service.get('default')['snapshot_hash']==before['snapshot_hash']


def test_supplier_unknowns_remain_null_instead_of_invented_defaults():
    from tenderproof.models import Supplier
    supplier=Supplier(name='QA supplier',configuration='QA stated configuration',facts=[{
        'property':'rated_power','operator':'eq','value':'25','unit':'MVA','source_ids':['qa:1']}]).model_dump()
    assert all(supplier[field] is None for field in ('revision','serial','family','price_cents','currency','delivery_weeks'))
