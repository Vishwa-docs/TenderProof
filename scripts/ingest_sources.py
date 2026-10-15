"""Upload complete authentic sources, leaving every engineering claim unapproved."""
from pathlib import Path
import json
import os
import httpx

root=Path(__file__).resolve().parents[1]
catalog=json.loads((root/'track_2b/data/sources.json').read_text())
manifest=json.loads((root/'.runtime/sources/manifest.json').read_text())
token=os.getenv('TENDERPROOF_API_TOKEN') or (root/'.runtime/operator_token').read_text().strip()
with httpx.Client(base_url=os.getenv('TENDERPROOF_API_URL','http://127.0.0.1:8001'),
                  headers={'Authorization':'Bearer '+token},timeout=1800,trust_env=False) as client:
    def project():
        r=client.get('/api/projects/default');r.raise_for_status();return r.json()
    p=project()
    if not p['equipment']:
        r=client.patch('/api/projects/default',json={'snapshot_hash':p['snapshot_hash'],
            'name':'GPA-070-25 · OP34276 · Item 2','customer':'Guam Power Authority','equipment':catalog['scope']})
        r.raise_for_status()
    for source in manifest:
        p=project()
        if any(d['sha256']==source['sha256'] for d in p['documents']):
            print('Already present:',source['filename'],flush=True);continue
        path=root/source['local_path']
        print('Parsing complete document:',source['filename'],flush=True)
        with path.open('rb') as stream:
            r=client.post('/api/projects/default/documents',data={'snapshot_hash':p['snapshot_hash'],'source_url':source['url']},
                          files={'file':(source['filename'],stream,'application/pdf')})
        r.raise_for_status();d=r.json()
        print(f"Stored {d['name']}: {len(d['spans'])} source spans",flush=True)
    p=project()
    (root/'.runtime/real-source-intake.json').write_text(json.dumps({'project_id':p['id'],'snapshot_hash':p['snapshot_hash'],
        'documents':[{'id':d['id'],'name':d['name'],'sha256':d['sha256'],'source_url':d.get('source_url'),
                      'pages':sorted({s['page'] for s in d['spans']}),'spans':len(d['spans'])} for d in p['documents']]},indent=2))
print('Intake complete. No requirements, proposals, purchases or acceptance decisions were approved.')
