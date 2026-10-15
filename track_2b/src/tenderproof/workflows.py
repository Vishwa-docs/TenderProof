"""Temporal separates slow model work from idempotent SQL persistence."""
import asyncio
import os
from datetime import timedelta
from temporalio import activity, workflow
from temporalio.common import RetryPolicy, WorkflowIDReusePolicy
from temporalio.exceptions import ApplicationError, WorkflowAlreadyStartedError

with workflow.unsafe.imports_passed_through():
    from .service import Service, Conflict, Forbidden, find, digest
    from .integrations import Apertus, ModelUnavailable, inference_timeout_seconds, plan_extraction

QUEUE='tenderproof-extraction'

def service():
    return Service(os.environ['DATABASE_URL'],mode=os.getenv('APP_MODE','live'))

@activity.defn
async def run_inference(request:dict)->dict:
    try:
        s=service();p=s.get(request['pid'])
        if p['snapshot_hash']!=request['body']['snapshot_hash']:raise Conflict('Source snapshot changed before inference.')
        doc=find(p['documents'],request['docid'])
        result=await asyncio.to_thread(Apertus().extract,doc,request['body']['kind'],scope=request.get('scope'),plan=request.get('extraction_plan'))
        result['trace']['workflow_budget_seconds']=request.get('inference_budget_seconds')
        result['trace']['api_wait_seconds']=request.get('api_wait_seconds')
        return {**request,'result':result}
    except (Conflict,Forbidden,KeyError,ModelUnavailable) as exc:
        raise ApplicationError(str(exc),non_retryable=True) from exc

@activity.defn
async def persist_extraction(request:dict)->dict:
    s=service();body=request['body'];result=request['result'];op=request['workflow_id']
    try:
        if body['kind']=='requirements':
            return s.add_candidates(request['pid'],request['docid'],result['data'],body['snapshot_hash'],request['actor'],result['trace'],operation_key=op)
        if body['kind']=='supplier':
            batch=s.add_proposals(request['pid'],request['docid'],body['kind'],result['data'],None,body['snapshot_hash'],request['actor'],result['trace'],operation_key=op)
            return batch['proposals'][0] if len(batch['proposals'])==1 else batch
        if not isinstance(result['data'],list) or len(result['data'])!=1:raise Conflict('Expected one evidence proposal.')
        return s.add_proposal(request['pid'],request['docid'],body['kind'],result['data'][0],body.get('supplier_id'),body['snapshot_hash'],request['actor'],result['trace'],operation_key=op)
    except (Conflict,Forbidden,KeyError) as exc:raise ApplicationError(str(exc),non_retryable=True) from exc

@workflow.defn
class ExtractionWorkflow:
    @workflow.run
    async def run(self,request:dict)->dict:
        result=await workflow.execute_activity(run_inference,request,
            start_to_close_timeout=timedelta(seconds=request.get('inference_budget_seconds',1320)),
            retry_policy=RetryPolicy(maximum_attempts=1))
        return await workflow.execute_activity(persist_extraction,result,start_to_close_timeout=timedelta(seconds=60),retry_policy=RetryPolicy(maximum_attempts=3))

async def dispatch_extraction(request):
    from temporalio.client import Client
    from temporalio.exceptions import TemporalError
    # Capture the same complete source plan outside deterministic execution.
    # Each bounded window uses four calls; SQL persistence happens once at the end.
    p=service().get(request['pid'])
    if p['snapshot_hash']!=request['body']['snapshot_hash']:raise Conflict('Source snapshot changed before workflow planning.')
    plan=plan_extraction(find(p['documents'],request['docid']),request['body']['kind'])
    budget=plan['window_count']*4*inference_timeout_seconds()+120
    request={**request,'extraction_plan':plan,'planned_window_count':plan['window_count'],
             'inference_budget_seconds':budget,'api_wait_seconds':budget+240}
    client=await Client.connect(os.environ['TEMPORAL_ADDRESS'])
    wid='extract-'+digest(request)
    request={**request,'workflow_id':wid}
    try:
        # Repeated requests attach to active/completed results, including empty
        # outputs whose package snapshot never changed. An explicit request after
        # a failed run may start one replacement run; its failed history remains.
        # Inference activities themselves still have maximum_attempts=1.
        handle=await client.start_workflow(ExtractionWorkflow.run,request,id=wid,task_queue=QUEUE,
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY)
    except WorkflowAlreadyStartedError:handle=client.get_workflow_handle(wid)
    try:return await asyncio.wait_for(handle.result(),timeout=request['api_wait_seconds'])
    except asyncio.TimeoutError as exc:
        # Cancelling a result-history wait is not WorkflowHandle.cancel/terminate.
        raise ModelUnavailable(f'Result wait expired. Workflow {wid} remains persisted and was not cancelled. Refresh the project or retry the same extraction; no approval was granted.') from exc
    except TemporalError as exc:raise ModelUnavailable(f'Durable extraction {wid} did not complete. Check the endpoint and worker, then explicitly retry extraction; a failed run can start a new attempt and its history is retained. No approvals were granted.') from exc

async def main():
    from temporalio.client import Client
    from temporalio.worker import Worker
    client=await Client.connect(os.getenv('TEMPORAL_ADDRESS','localhost:7233'))
    async with Worker(client,task_queue=QUEUE,workflows=[ExtractionWorkflow],activities=[run_inference,persist_extraction]):
        await asyncio.Event().wait()

if __name__=='__main__':asyncio.run(main())
