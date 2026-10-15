#!/usr/bin/env python3
"""Read actual Temporal history without starting a workflow or altering data.

Supply an existing workflow ID and optionally save/compare its result around an
operator-controlled restart. No fixtures or model responses are created.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
from temporalio.api.enums.v1 import EventType
from temporalio.client import Client

async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workflow_id')
    parser.add_argument('--address',default=os.getenv('TEMPORAL_ADDRESS','temporal:7233'))
    parser.add_argument('--save-receipt',type=Path)
    parser.add_argument('--compare-receipt',type=Path)
    args=parser.parse_args()
    client=await Client.connect(args.address)
    handle=client.get_workflow_handle(args.workflow_id)
    description=await handle.describe()
    assert description.status.name=='COMPLETED',description.status.name
    result=await asyncio.wait_for(handle.result(),timeout=30)
    history=await handle.fetch_history()
    completed=sum(event.event_type==EventType.EVENT_TYPE_ACTIVITY_TASK_COMPLETED for event in history.events)
    assert completed>=2,completed
    receipt={'workflow_id':args.workflow_id,'run_id':description.run_id,'result':result}
    if args.compare_receipt:
        assert json.loads(args.compare_receipt.read_text())==receipt
    if args.save_receipt:
        args.save_receipt.write_text(json.dumps(receipt,indent=2))
    result_hash=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    print(json.dumps({'workflow_id':args.workflow_id,'status':description.status.name,'completed_activities':completed,
        'history_events':len(history.events),'result_hash':result_hash,'matched_receipt':bool(args.compare_receipt),
        'state_mutated':False,'model_quality_evaluated':False},indent=2))

if __name__=='__main__':asyncio.run(main())
