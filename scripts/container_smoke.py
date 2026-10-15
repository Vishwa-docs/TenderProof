#!/usr/bin/env python3
"""Read-only deployment checks against actual live project data; never seed or approve records."""
import argparse
import asyncio
import json
import hashlib
from urllib.parse import quote
import os
from pathlib import Path
import subprocess
import sys
import httpx


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['health','sources','artifacts','mcp','egress'])
    parser.add_argument('--base-url',default='http://127.0.0.1:8001')
    parser.add_argument('--project-id',default='default')
    parser.add_argument('--artifact-id',action='append',default=[])
    args=parser.parse_args()
    if args.phase=='egress':
        check_egress();return
    token=os.getenv('TENDERPROOF_API_TOKEN') or os.getenv('TENDERPROOF_MCP_TOKEN','')
    if args.phase!='health' and not token:parser.error('Set TENDERPROOF_API_TOKEN to an authorized project token.')
    if args.phase=='mcp':
        asyncio.run(check_mcp(args.base_url,args.project_id,token));return
    with httpx.Client(base_url=args.base_url,headers={'Authorization':'Bearer '+token} if token else {},timeout=60,trust_env=False) as client:
        health=client.get('/api/health');health.raise_for_status();health=health.json()
        assert health['mode']=='live' and health['database']=='postgresql',health
        if args.phase=='health':
            print(json.dumps(health,indent=2));return
        prefix='/api/projects/'+quote(args.project_id,safe='')
        response=client.get(prefix);response.raise_for_status();package=response.json()
        assert package['mode']=='live'
        if args.phase=='sources':
            sources=[]
            for doc in package['documents']:
                original=client.get(prefix+'/documents/'+quote(doc['id'],safe='')+'/content');original.raise_for_status()
                assert hashlib.sha256(original.content).hexdigest()==doc['sha256'],doc['id']
                sources.append({'id':doc['id'],'name':doc['name'],'source_url':doc.get('source_url'),
                    'sha256':doc['sha256'],'original_bytes':len(original.content),'spans':len(doc['spans'])})
            print(json.dumps({'phase':'sources','project_id':args.project_id,'equipment_scope':package['equipment'],
                'source_count':len(sources),'sources':sources,'state_mutated':False},indent=2))
        else:
            if not args.artifact_id:parser.error('Supply at least one existing --artifact-id; this script never creates decisions.')
            artifacts=[]
            for identity in args.artifact_id:
                response=client.get(prefix+'/decisions/'+quote(identity,safe='')+'/artifact');response.raise_for_status()
                artifact=response.json();expected=artifact.pop('artifact_hash')
                actual=hashlib.sha256(json.dumps(artifact,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
                assert actual==expected,identity
                artifacts.append({'decision_id':identity,'artifact_hash':actual,'snapshot_hash':artifact['snapshot_hash']})
            print(json.dumps({'phase':'artifacts','artifacts':artifacts,'state_mutated':False},indent=2))


async def check_mcp(base_url,project_id,token):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    root=Path(__file__).resolve().parents[1]
    env={**os.environ,'PYTHONPATH':str(root/'track_2b/src'),'TENDERPROOF_API_URL':base_url,'TENDERPROOF_MCP_TOKEN':token}
    params=StdioServerParameters(command=sys.executable,args=['-m','tenderproof.mcp_server'],env=env)
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            initialized=await session.initialize()
            listed=await session.list_tools()
            names={tool.name for tool in listed.tools}
            assert names=={'read_package','read_document_revision','prepare_purchase_draft'},names
            result=await session.call_tool('read_package',{'project_id':project_id})
            assert not result.isError,result
            data=result.structuredContent
            if data is None:
                data=json.loads(next(content.text for content in result.content if content.type=='text'))
            assert data['id']==project_id and data['mode']=='live',data
            print(json.dumps({'phase':'mcp','protocol':initialized.protocolVersion,'tools':sorted(names),
                'project_id':data['id'],'requirements':len(data['requirements']),'read_package':'passed'},indent=2))


def check_egress():
    code='''import json,socket
checks={}
for host,port in [('database',5432),('temporal',7233)]:
    with socket.create_connection((host,port),timeout=3):checks[host+':'+str(port)]='reachable'
for host,port in [('1.1.1.1',443),('8.8.8.8',53)]:
    try:
        with socket.create_connection((host,port),timeout=3):pass
    except OSError as exc:checks[host+':'+str(port)]='blocked: '+type(exc).__name__
    else:raise AssertionError('Unexpected public egress: '+host)
print(json.dumps(checks))
'''
    root=Path(__file__).resolve().parents[1]
    results={}
    for service in ('app','worker'):
        run=subprocess.run(['docker','compose','exec','-T',service,'python','-c',code],cwd=root,
            check=True,capture_output=True,text=True)
        results[service]=json.loads(run.stdout)
    network=subprocess.run(['docker','network','inspect','tenderproof_sovereign','--format','{{.Internal}}'],
        cwd=root,check=True,capture_output=True,text=True)
    assert network.stdout.strip()=='true'
    print(json.dumps({'phase':'egress','sovereign_network_internal':True,'containers':results},indent=2))


if __name__=='__main__':main()
