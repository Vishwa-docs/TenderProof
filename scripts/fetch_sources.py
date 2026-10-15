"""Fetch complete primary-source documents; record hashes, never invent missing records."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess

root=Path(__file__).resolve().parents[1]
catalog=json.loads((root/'track_2b/data/sources.json').read_text())
destination=root/'.runtime/sources';destination.mkdir(parents=True,exist_ok=True)
def fetch(source):
    target=destination/source['filename']
    if not target.exists():
        temporary=target.with_suffix('.download')
        subprocess.run(['curl','--fail','--location','--silent','--show-error','--max-time','90',
                        '--max-filesize',str(15*1024*1024),source['url'],'--output',str(temporary)],check=True)
        content=temporary.read_bytes()
        if len(content)>15*1024*1024 or not content.startswith(b'%PDF'):
            raise ValueError(f"Invalid or oversized PDF: {source['id']}")
        temporary.replace(target)
    content=target.read_bytes()
    if not content.startswith(b'%PDF'):raise ValueError(f"Not a PDF: {target.name}")
    sha=hashlib.sha256(content).hexdigest()
    if source.get('expected_sha256') and sha!=source['expected_sha256']:
        raise ValueError(f"Source changed: {source['id']}; review the new document before updating the pinned catalog.")
    return {**source,'sha256':sha,'bytes':len(content),
            'verified_at':datetime.now(timezone.utc).isoformat(),'owner':source.get('publisher','Guam Power Authority'),
            'redistribution_permission':'not established','local_path':str(target.relative_to(root))}
with ThreadPoolExecutor(max_workers=4) as pool:
    manifest=list(pool.map(fetch,catalog['sources']))
(destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(f'Fetched {len(manifest)} complete source PDFs into .runtime/sources; originals excluded from publication.')
