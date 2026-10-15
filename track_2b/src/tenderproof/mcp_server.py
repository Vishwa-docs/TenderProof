"""Narrow MCP tools. Server-side API authorization remains authoritative."""
import os
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
def prepare_purchase_draft(project_id:str,supplier_id:str,snapshot_hash:str)->dict:
    """Prepare a draft after checks; this never approves or releases a purchase."""
    return call('POST',project_path(project_id)+'/decisions',{'supplier_id':supplier_id,'snapshot_hash':snapshot_hash,'gate':'purchase'})

if __name__=='__main__':mcp.run()
