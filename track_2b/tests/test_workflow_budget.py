"""Temporal boundary QA: four bounded model calls must fit without full-run retry."""
import asyncio
from datetime import timedelta
import pytest
from temporalio.client import Client
from types import SimpleNamespace
from tenderproof.workflows import ExtractionWorkflow, dispatch_extraction


@pytest.mark.parametrize('kind,result',[('requirements',{'candidates':[]}),('supplier',{'proposals':[]})])
def test_completed_empty_extraction_reattaches_without_repeating_inference(monkeypatch,kind,result):
    from temporalio.common import WorkflowIDReusePolicy
    from temporalio.exceptions import WorkflowAlreadyStartedError
    from tenderproof import workflows
    monkeypatch.setenv('TEMPORAL_ADDRESS','qa-temporal:7233')
    doc={'id':'qa','spans':[{'id':'qa:1','page':1,'text':'QA source with no applicable rows'}]}
    monkeypatch.setattr(workflows,'service',lambda:SimpleNamespace(get=lambda pid:{'snapshot_hash':'unchanged','documents':[doc]}))
    runs={};attached=[];inference_runs=[]
    class Handle:
        async def result(self):return result
    class BoundaryClient:
        async def start_workflow(self,run,request,**kwargs):
            wid=kwargs['id']
            if wid in runs and kwargs.get('id_reuse_policy') in (
                WorkflowIDReusePolicy.REJECT_DUPLICATE,WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY):
                raise WorkflowAlreadyStartedError(wid,'ExtractionWorkflow')
            inference_runs.append(wid);runs[wid]=Handle();return runs[wid]
        def get_workflow_handle(self,wid):attached.append(wid);return runs[wid]
    async def connect(address):return BoundaryClient()
    monkeypatch.setattr(Client,'connect',connect)
    request={'pid':'default','docid':'qa','body':{'kind':kind,'snapshot_hash':'unchanged'},'actor':'qa'}
    assert asyncio.run(dispatch_extraction(request))==result
    assert asyncio.run(dispatch_extraction(request))==result
    assert len(inference_runs)==1
    assert attached==inference_runs


def test_explicit_retry_can_replace_failed_run_without_automatic_inference_retry(monkeypatch):
    from temporalio.common import WorkflowIDReusePolicy
    from temporalio.exceptions import WorkflowAlreadyStartedError,TemporalError
    from tenderproof.integrations import ModelUnavailable
    from tenderproof import workflows
    monkeypatch.setenv('TEMPORAL_ADDRESS','qa-temporal:7233')
    doc={'id':'qa','spans':[{'id':'qa:1','page':1,'text':'QA source'}]}
    monkeypatch.setattr(workflows,'service',lambda:SimpleNamespace(get=lambda pid:{'snapshot_hash':'unchanged','documents':[doc]}))
    runs=[]
    class Handle:
        def __init__(self,failed):self.failed=failed
        async def result(self):
            if self.failed:raise TemporalError('Controlled endpoint failure')
            return {'candidates':[]}
    class BoundaryClient:
        async def start_workflow(self,run,request,**kwargs):
            if runs and kwargs.get('id_reuse_policy')==WorkflowIDReusePolicy.REJECT_DUPLICATE:
                raise WorkflowAlreadyStartedError(kwargs['id'],'ExtractionWorkflow')
            handle=Handle(failed=not runs);runs.append((kwargs['id'],handle));return handle
        def get_workflow_handle(self,wid):return runs[-1][1]
    async def connect(address):return BoundaryClient()
    monkeypatch.setattr(Client,'connect',connect)
    request={'pid':'default','docid':'qa','body':{'kind':'requirements','snapshot_hash':'unchanged'},'actor':'qa'}
    with pytest.raises(ModelUnavailable):asyncio.run(dispatch_extraction(request))
    assert len(runs)==1
    assert asyncio.run(dispatch_extraction(request))=={'candidates':[]}
    assert len(runs)==2 and runs[0][0]==runs[1][0]
    assert runs[0][1].failed


@pytest.mark.parametrize('call_timeout,budget',[('1',124),('300',1320),('900',3720)])
def test_dispatch_snapshots_configured_budget_in_durable_request(monkeypatch,call_timeout,budget):
    monkeypatch.setenv('LLM_TIMEOUT_SECONDS',call_timeout)
    monkeypatch.setenv('TEMPORAL_ADDRESS','qa-temporal:7233')
    document={'id':'gpa-bid-abstract-qa','spans':[{'id':'gpa-bid-abstract-qa:1','page':1,'text':'QA source'}]}
    monkeypatch.setattr('tenderproof.workflows.service',lambda:SimpleNamespace(get=lambda pid:{
        'snapshot_hash':'reviewed-package-snapshot','documents':[document]}))
    submitted=[]
    class Handle:
        async def result(self):return {'proposals':[]}
    class BoundaryClient:
        async def start_workflow(self,run,request,**kwargs):
            submitted.append(request)
            return Handle()
    async def connect(address):return BoundaryClient()
    monkeypatch.setattr(Client,'connect',connect)
    result=asyncio.run(dispatch_extraction({'pid':'default','docid':'gpa-bid-abstract-qa',
        'body':{'kind':'supplier','snapshot_hash':'reviewed-package-snapshot'},'actor':'qa-engineer'}))
    assert result=={'proposals':[]}
    assert submitted[0]['inference_budget_seconds']==budget
    assert submitted[0]['api_wait_seconds']==budget+240


def test_workflow_uses_durable_budget_without_repeating_slow_inference(monkeypatch):
    calls=[]
    async def execute(fn,request,**kwargs):
        calls.append((fn.__name__,kwargs))
        return request
    monkeypatch.setattr('tenderproof.workflows.workflow.execute_activity',execute)
    asyncio.run(ExtractionWorkflow().run({'inference_budget_seconds':1320}))
    inference,persistence=calls
    assert inference[1]['start_to_close_timeout']==timedelta(seconds=1320)
    assert inference[1]['retry_policy'].maximum_attempts==1
    assert persistence[1]['retry_policy'].maximum_attempts==3


def test_api_wait_timeout_leaves_started_durable_workflow_uncancelled(monkeypatch):
    from tenderproof.integrations import ModelUnavailable
    from tenderproof import workflows
    monkeypatch.setenv('LLM_TIMEOUT_SECONDS','300');monkeypatch.setenv('TEMPORAL_ADDRESS','qa-temporal:7233')
    doc={'id':'qa','spans':[{'id':'qa:1','page':1,'text':'QA source'}]}
    monkeypatch.setattr(workflows,'service',lambda:SimpleNamespace(get=lambda pid:{'snapshot_hash':'qa-snapshot','documents':[doc]}))
    started=[];waits=[]
    class Handle:
        async def result(self):raise asyncio.TimeoutError()
        async def cancel(self):raise AssertionError('API deadline must not cancel durable work')
        async def terminate(self):raise AssertionError('API deadline must not terminate durable work')
    class BoundaryClient:
        async def start_workflow(self,run,request,**kwargs):started.append(kwargs['id']);return Handle()
    async def connect(address):return BoundaryClient()
    async def wait_for(awaitable,timeout):waits.append(timeout);return await awaitable
    monkeypatch.setattr(Client,'connect',connect);monkeypatch.setattr(workflows.asyncio,'wait_for',wait_for)
    with pytest.raises(ModelUnavailable,match='remains persisted') as caught:
        asyncio.run(dispatch_extraction({'pid':'default','docid':'qa','body':{'kind':'requirements','snapshot_hash':'qa-snapshot'},'actor':'qa'}))
    assert len(started)==1 and started[0] in str(caught.value)
    assert waits==[1560]
