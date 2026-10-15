"""Review API. Live identities and project membership are server-controlled."""
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File, Form, Query, Path as PathParameter
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import HttpUrl, TypeAdapter, ValidationError
from starlette.concurrency import run_in_threadpool
from .service import Service, Conflict, Forbidden, find
from .models import SnapshotRequest, ReviewRequest, DecisionRequest, ReleaseRequest, ExtractRequest, ProposalApprovalRequest, SupplierPriceCorrectionRequest, ScheduleRequest, ProjectMetadataRequest
from .integrations import Apertus, ModelUnavailable, parse_document
from .page_preview import PDF_ACCESS_LOCK, MAX_ORIGINAL_BYTES, PreviewProblem, read_original_bytes, verify_original_bytes, render_original_pdf_page

def create_app(database_url=None,mode=None,principals=None):
    mode=mode or os.getenv('APP_MODE','live')
    if mode!='live':raise ValueError('Only live application mode is supported.')
    runtime=Path(os.getenv('RUNTIME_DIR','.runtime'));runtime.mkdir(parents=True,exist_ok=True)
    database_url=database_url or os.getenv('DATABASE_URL',f'sqlite:///{runtime}/{mode}.db')
    service=Service(database_url,mode)
    if service.get('default')['mode']!=mode:raise ValueError('Database belongs to a different runtime mode; use a separate database.')
    principal_map=principals if principals is not None else json.loads(os.getenv('TENDERPROOF_PRINCIPALS_JSON','{}'))
    if mode=='live' and not principal_map:raise ValueError('Live mode requires TENDERPROOF_PRINCIPALS_JSON with server-owned roles and project membership.')
    app=FastAPI(title='TenderProof Engineering',version='0.1.0');app.state.service=service

    @app.middleware('http')
    async def origin_guard(request,call_next):
        origin=request.headers.get('origin')
        if request.method not in ('GET','HEAD','OPTIONS') and origin:
            if urlparse(origin).netloc!=request.headers.get('host') and urlparse(origin).hostname not in ('localhost','127.0.0.1'):
                return JSONResponse({'detail':'Cross-origin writes are not allowed.'},status_code=403)
        return await call_next(request)

    @app.exception_handler(Conflict)
    async def conflict(request,exc):return JSONResponse({'detail':str(exc)},status_code=409)
    @app.exception_handler(Forbidden)
    async def forbidden(request,exc):return JSONResponse({'detail':str(exc)},status_code=403)
    @app.exception_handler(KeyError)
    async def missing(request,exc):return JSONResponse({'detail':'Project or record not found.'},status_code=404)
    @app.exception_handler(ModelUnavailable)
    async def unavailable(request,exc):return JSONResponse({'detail':str(exc)},status_code=503)

    def identity(request:Request):
        pid=request.path_params.get('pid')
        token=request.headers.get('Authorization','').removeprefix('Bearer ')
        principal=principal_map.get(token)
        if not principal:raise HTTPException(401,'A valid project access token is required.')
        if pid and pid not in principal.get('projects',[]):raise Forbidden('This identity does not have access to the project.')
        return principal

    def require_role(who,roles):
        if who['role'] not in roles:raise Forbidden('Your role cannot perform this action.')

    def parse_uploaded_document(name,content):
        if Path(name).suffix.lower()=='.pdf':
            with PDF_ACCESS_LOCK:return parse_document(name,content)
        return parse_document(name,content)

    def original_source_hash(doc):
        source_hash=doc.get('sha256')
        if not isinstance(source_hash,str) or not re.fullmatch(r'[0-9a-f]{64}',source_hash):
            raise HTTPException(404,'The original source hash is unavailable.')
        return source_hash

    @app.get('/api/health')
    def health():
        return dict(status='ok',mode=mode,model=os.getenv('LLM_NAME','swiss-ai/Apertus-v1.5-8B'),
                    model_configured=bool(os.getenv('LLM_BASE_URL')),workflow='temporal' if os.getenv('TEMPORAL_ADDRESS') else 'direct',
                    database='postgresql' if database_url.startswith('postgresql') else 'sqlite-development')

    @app.get('/api/projects/{pid}')
    def project(pid:str,who=Depends(identity)):
        p=service.get(pid)
        for doc in p['documents']:doc.pop('image_data_url',None)
        return p

    @app.patch('/api/projects/{pid}')
    def metadata(pid:str,body:ProjectMetadataRequest,who=Depends(identity)):
        return service.set_metadata(pid,body.snapshot_hash,body.name,body.customer,body.equipment,who['actor'],who['role'])

    @app.post('/api/projects/{pid}/requirements/{rid}/review')
    def review(pid:str,rid:str,body:ReviewRequest,who=Depends(identity)):
        return service.review(pid,rid,body.snapshot_hash,body.accepted,body.witness_answer,who['actor'],who['role'])

    @app.post('/api/projects/{pid}/decisions')
    def prepare(pid:str,body:DecisionRequest,who=Depends(identity)):
        require_role(who,{'engineer'} if body.gate=='purchase' else {'inspector'})
        return service.create_decision(pid,body.supplier_id,body.gate,body.snapshot_hash,who['actor'])

    @app.post('/api/projects/{pid}/decisions/{did}/approve')
    def approve(pid:str,did:str,body:SnapshotRequest,who=Depends(identity)):
        return service.approve(pid,did,body.snapshot_hash,who['actor'],who['role'])

    @app.post('/api/projects/{pid}/decisions/{did}/release')
    def release(pid:str,did:str,body:ReleaseRequest,who=Depends(identity)):
        return service.release(pid,did,body.snapshot_hash,body.idempotency_key,who['actor'],who['role'])

    @app.get('/api/projects/{pid}/decisions/{did}/artifact')
    def artifact(pid:str,did:str,who=Depends(identity)):
        return service.get_artifact(pid,did)

    @app.post('/api/projects/{pid}/documents')
    async def upload(pid:str,snapshot_hash:str=Form(...),file:UploadFile=File(...),source_url:str|None=Form(None),who=Depends(identity)):
        require_role(who,{'engineer','inspector'})
        if source_url is not None:
            try:source_url=str(TypeAdapter(HttpUrl).validate_python(source_url))
            except ValidationError as exc:raise HTTPException(422,'Source URL must be an absolute HTTP or HTTPS URL.') from exc
        service.get(pid)
        content=await file.read(15*1024*1024+1)
        try:doc=await run_in_threadpool(parse_uploaded_document,file.filename or 'source.txt',content)
        except (ValueError,UnicodeError) as exc:raise HTTPException(422,str(exc)) from exc
        if source_url is not None:doc['source_url']=source_url
        result=service.add_document(pid,doc,snapshot_hash,who['actor'])
        # Preserve immutable original bytes by content hash, never the uploaded filename.
        destination=runtime/'objects'/doc['sha256'];destination.parent.mkdir(parents=True,exist_ok=True)
        if not destination.exists():destination.write_bytes(content)
        return {k:v for k,v in result.items() if k!='image_data_url'}

    @app.post('/api/projects/{pid}/documents/{docid}/extract')
    async def extract(pid:str,docid:str,body:ExtractRequest,who=Depends(identity)):
        require_role(who,{'engineer','inspector'})
        p=service.get(pid)
        if p['snapshot_hash']!=body.snapshot_hash:raise Conflict('Refresh the changed package before extraction.')
        doc=find(p['documents'],docid)
        if not p.get('equipment'):raise Conflict('Define the equipment scope before extraction.')
        scope={key:p[key] for key in ('name','customer','equipment')}
        if body.kind=='evidence':find(p['suppliers'],body.supplier_id)
        if not os.getenv('LLM_BASE_URL'):
            raise ModelUnavailable('Apertus endpoint is not configured. Set LLM_BASE_URL and LLM_NAME; synthetic examples are never substituted for inference.')
        if os.getenv('TEMPORAL_ADDRESS'):
            from .workflows import dispatch_extraction
            return await dispatch_extraction(dict(pid=pid,docid=docid,body=body.model_dump(),actor=who['actor'],scope=scope))
        result=await run_in_threadpool(Apertus().extract,doc,body.kind,scope=scope)
        if body.kind=='requirements':return service.add_candidates(pid,docid,result['data'],body.snapshot_hash,who['actor'],result['trace'])
        if body.kind=='supplier':
            batch=service.add_proposals(pid,docid,body.kind,result['data'],None,body.snapshot_hash,who['actor'],result['trace'])
            return batch['proposals'][0] if len(batch['proposals'])==1 else batch
        if not isinstance(result['data'],list) or len(result['data'])!=1:raise ModelUnavailable('Expected one evidence proposal.')
        return service.add_proposal(pid,docid,body.kind,result['data'][0],body.supplier_id,body.snapshot_hash,who['actor'],result['trace'])

    @app.post('/api/projects/{pid}/proposals/{proposal_id}/approve')
    def proposal(pid:str,proposal_id:str,body:ProposalApprovalRequest,who=Depends(identity)):
        return service.approve_proposal(pid,proposal_id,body.snapshot_hash,who['actor'],who['role'],body.family_coverage_confirmed,body.supersedes_evidence_id)

    @app.post('/api/projects/{pid}/proposals/{proposal_id}/correct-price')
    def correct_price(pid:str,proposal_id:str,body:SupplierPriceCorrectionRequest,who=Depends(identity)):
        return service.correct_supplier_price(pid,proposal_id,body.snapshot_hash,body.price_cents,body.currency,
            body.source_id,body.reason,who['actor'],who['role'])

    @app.post('/api/projects/{pid}/schedule')
    def schedule(pid:str,body:ScheduleRequest,who=Depends(identity)):
        return service.set_schedule(pid,body.snapshot_hash,body.required_delivery_week,body.source_id,who['actor'],who['role'])

    @app.get('/api/projects/{pid}/documents/{docid}/content')
    def document_content(pid:str,docid:str,who=Depends(identity)):
        import base64
        import binascii
        from urllib.parse import quote
        d=find(service.get(pid)['documents'],docid)
        source_hash=original_source_hash(d)
        media_type='application/octet-stream'
        headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','X-Source-SHA256':source_hash}
        try:
            if d.get('image_data_url'):
                try:
                    header,encoded=d['image_data_url'].split(',',1)
                    match=re.fullmatch(r'data:(image/(?:png|jpeg|webp|gif|bmp));base64',header)
                    if not match:raise ValueError('Invalid original image encoding.')
                    if len(encoded)>((MAX_ORIGINAL_BYTES+2)//3)*4:
                        raise PreviewProblem(413,'The stored original image exceeds the 15 MiB source limit.')
                    content=verify_original_bytes(base64.b64decode(encoded,validate=True),source_hash)
                    media_type=match.group(1)
                except (ValueError,binascii.Error,AttributeError,TypeError) as exc:
                    raise PreviewProblem(409,'The stored original image data is corrupt.') from exc
            else:
                content=read_original_bytes(runtime/'objects'/source_hash,source_hash)
                headers['Content-Disposition']="attachment; filename*=UTF-8''"+quote(d['name'])
        except PreviewProblem as exc:
            raise HTTPException(exc.status,str(exc)) from exc
        return Response(content,media_type=media_type,headers=headers)

    @app.get('/api/projects/{pid}/documents/{docid}/pages/{page_number}/preview')
    def document_page_preview(pid:str,docid:str,page_number:int=PathParameter(ge=1,le=10000),
                              max_dimension:int=Query(1800,ge=256,le=2400),who=Depends(identity)):
        doc=find(service.get(pid)['documents'],docid)
        if not doc['name'].lower().endswith('.pdf'):
            raise HTTPException(415,'Page previews are available for original PDF documents only.')
        source_hash=original_source_hash(doc)
        try:
            png,width,height=render_original_pdf_page(runtime/'objects'/source_hash,source_hash,page_number,max_dimension)
        except PreviewProblem as exc:
            raise HTTPException(exc.status,str(exc)) from exc
        return Response(png,media_type='image/png',headers={'Cache-Control':'private, no-store',
            'X-Content-Type-Options':'nosniff','X-Source-SHA256':source_hash,'X-Source-Page':str(page_number),
            'X-Preview-Width':str(width),'X-Preview-Height':str(height)})

    static=Path(__file__).parent.parent/'web'/'dist'
    if static.exists():app.mount('/',StaticFiles(directory=static,html=True),name='workbench')
    return app
