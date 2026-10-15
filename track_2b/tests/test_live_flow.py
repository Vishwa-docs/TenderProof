"""The model transport is mocked; schema checks, HTTP handlers, SQL and gates are real."""
import json
import httpx
from fastapi.testclient import TestClient
from tenderproof.api import create_app
from tenderproof.integrations import Apertus


def test_authenticated_live_review_releases_only_after_source_bound_schedule(tmp_path,monkeypatch):
    monkeypatch.setenv('RUNTIME_DIR',str(tmp_path/'runtime'))
    monkeypatch.setenv('LLM_BASE_URL','http://review-test.invalid/v1')
    monkeypatch.delenv('TEMPORAL_ADDRESS',raising=False)
    roles=('engineer','inspector','commercial')
    app=create_app(database_url='sqlite:///'+str(tmp_path/'live.db'),mode='live',
        principals={role:{'actor':role,'role':role,'projects':['default']} for role in roles})
    client=TestClient(app)
    def headers(role):return {'Authorization':'Bearer '+role}
    def state():return client.get('/api/projects/default',headers=headers('engineer')).json()
    def request(path,data,role='engineer'):
        return client.post('/api/projects/default'+path,headers=headers(role),json={'snapshot_hash':state()['snapshot_hash'],**data})
    def mutate(path,data,role='engineer'):
        response=request(path,data,role)
        assert response.status_code==200,response.text
        return response.json()

    uploaded=client.post('/api/projects/default/documents',headers=headers('engineer'),data={'snapshot_hash':state()['snapshot_hash']},
        files={'file':('package.md',b'Customer requires at least 25 MVA ONAN. Delivery required by week 24.\n'
            b'Supplier S: config C, rev B, family C, serial 001; 25 MVA ONAN; USD 100; expedite USD 0; rework USD 0; delivery week 24.\n'
            b'Routine FAT: config C, rev B, serial 001; measured 25 MVA ONAN.')})
    assert uploaded.status_code==200
    doc=uploaded.json();refs=[span['id'] for span in doc['spans']]
    fact={'property':'rated_power','operator':'eq','value':'25','unit':'MVA','conditions':{'cooling':'ONAN'},'source_ids':[refs[1]]}
    requirement={**fact,'operator':'ge','source_ids':[refs[0]],'title':'Rated power','phase':'purchase'}
    supplier={'name':'S','configuration':'C','revision':'B','serial':'001','family':'C','price_cents':10000,
        'currency':'USD','price_basis':'unit','delivery_weeks':24,'delivery_basis':'project_start','expedite_cents':0,'rework_cents':0,'facts':[fact],'source_ids':[refs[1]]}
    evidence={'title':'Routine FAT','kind':'routine','serial':'001','family':'C','configuration':'C','revision':'B',
        'measurements':[{**fact,'source_ids':[refs[2]]}],'source_ids':[refs[2]]}
    responses=[]
    for kind,record in [('requirements',[requirement]),('supplier',supplier),('evidence',evidence)]:
        responses.extend([{'summary':'Explicit source facts only'},{kind:record},{'issues':[]},{'issues':[]}])
    def responder(request):
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(responses.pop(0))}}]})
    adapter=Apertus(base_url='http://review-test.invalid/v1',transport=httpx.MockTransport(responder))
    monkeypatch.setattr('tenderproof.api.Apertus',lambda:adapter)

    configured=client.patch('/api/projects/default',headers=headers('engineer'),json={'snapshot_hash':state()['snapshot_hash'],
        'name':'QA integration package','customer':'Constructed software test','equipment':'25 MVA ONAN transformer'})
    assert configured.status_code==200,configured.text
    q=mutate('/documents/'+doc['id']+'/extract',{'kind':'requirements'})
    mutate('/requirements/'+q['candidates'][0]['id']+'/review',{'accepted':True,'witness_answer':False})
    q=mutate('/documents/'+doc['id']+'/extract',{'kind':'supplier'})
    mutate('/proposals/'+q['id']+'/approve',{})
    sid=state()['suppliers'][0]['id']
    q=mutate('/documents/'+doc['id']+'/extract',{'kind':'evidence','supplier_id':sid},'inspector')
    mutate('/proposals/'+q['id']+'/approve',{},'inspector')

    assert state()['required_delivery_week'] is None
    assert request('/decisions',{'supplier_id':sid,'gate':'purchase'}).status_code==409
    assert request('/schedule',{'required_delivery_week':24,'source_id':refs[0]},'inspector').status_code==403
    mutate('/schedule',{'required_delivery_week':24,'source_id':refs[0]})
    issued=[]
    for gate,first_role in [('purchase','engineer'),('shipment','inspector')]:
        decision=mutate('/decisions',{'supplier_id':sid,'gate':gate},first_role)
        for role in (first_role,'commercial'):
            mutate('/decisions/'+decision['id']+'/approve',{},role)
        artifact=mutate('/decisions/'+decision['id']+'/release',{'idempotency_key':gate},'commercial')
        assert artifact['gate']==gate and artifact['simulator'] is True
        assert {a['role'] for a in artifact['approvals']}=={first_role,'commercial'}
        assert artifact['engineering_snapshot']['schedule_source_id']==refs[0]
        issued.append(artifact)

    mutate('/schedule',{'required_delivery_week':25,'source_id':refs[0]})
    assert all(d['status']=='stale' for d in state()['decisions'])
    for artifact in issued:
        saved=client.get('/api/projects/default/decisions/'+artifact['decision_id']+'/artifact',headers=headers('engineer'))
        assert saved.status_code==200 and saved.json()==artifact
