"""Narrow MCP tools. Server-side API authorization remains authoritative."""
import os
import re
from urllib.parse import urlencode
import httpx
from mcp.server.fastmcp import FastMCP

mcp=FastMCP('TenderProof Engineering')

def call(method,path,body=None):
    token=os.getenv('TENDERPROOF_MCP_TOKEN','')
    if not token:raise ValueError('TENDERPROOF_MCP_TOKEN is required for authenticated project access.')
    headers={'Authorization':'Bearer '+token}
    with httpx.Client(base_url=os.getenv('TENDERPROOF_API_URL','http://127.0.0.1:8000'),headers=headers,timeout=30,trust_env=False) as client:
        r=client.request(method,path,json=body);r.raise_for_status();return r.json()

def project_path(project_id):
    if not project_id or not all(c.isalnum() or c in '-_' for c in project_id):raise ValueError('Invalid project identifier')
    return '/api/projects/'+project_id

@mcp.tool()
def read_package(project_id:str)->dict:
    """Read requirements, supplier comparisons and evidence for an authorized project."""
    return call('GET',project_path(project_id))

@mcp.tool()
def read_document_revision(project_id:str,document_id:str)->dict:
    """Retrieve an exact source document revision, never an arbitrary path or URL."""
    p=call('GET',project_path(project_id))
    for d in p['documents']:
        if d['id']==document_id:return d
    raise ValueError('Document not found')

@mcp.tool()
def inspect_review_queue(project_id:str)->dict:
    """Read source-linked review issues, document coverage and release blockers. This never clears a gate."""
    return call('GET',project_path(project_id)+'/analysis')

@mcp.tool()
def search_evidence(project_id:str,query:str,document_id:str|None=None,limit:int=10)->dict:
    """Rank original source passages with page citations. Scores measure lexical relevance, not factual confidence."""
    path=project_path(project_id)
    if not isinstance(query,str) or not query.strip() or len(query)>300:
        raise ValueError('Query must contain 1 to 300 characters.')
    if type(limit) is not int or not 1<=limit<=50:
        raise ValueError('Result limit must be an integer from 1 to 50.')
    params={'q':query,'limit':limit}
    if document_id is not None:
        if not isinstance(document_id,str) or not document_id or len(document_id)>200:
            raise ValueError('Document identifier must contain 1 to 200 characters.')
        params['document_id']=document_id
    return call('GET',path+'/search?'+urlencode(params))

@mcp.tool()
def compare_package_revisions(project_id:str,from_hash:str,to_hash:str)->dict:
    """Compare two stored snapshots from the same authorized project. This never edits a record or approves a change."""
    path=project_path(project_id)
    if any(not isinstance(value,str) or not re.fullmatch(r'[0-9a-f]{64}',value) for value in (from_hash,to_hash)):
        raise ValueError('Revisions must be exact lowercase SHA-256 snapshot hashes.')
    return call('GET',path+'/diff?'+urlencode({'from_hash':from_hash,'to_hash':to_hash}))

@mcp.tool()
def export_review_dossier(project_id:str)->dict:
    """Read a reproducible draft review dossier. Its hash proves content identity; the dossier is not release approval."""
    return call('GET',project_path(project_id)+'/dossier')

@mcp.tool()
def prepare_purchase_draft(project_id:str,supplier_id:str,snapshot_hash:str)->dict:
    """Prepare a draft after checks; this never approves or releases a purchase."""
    return call('POST',project_path(project_id)+'/decisions',{'supplier_id':supplier_id,'snapshot_hash':snapshot_hash,'gate':'purchase'})

if __name__=='__main__':mcp.run()
