"""Download and verify a pinned official model; never print credentials or URLs."""
from pathlib import Path
import hashlib
import json
import os
import time

# HTTP range downloads provide resumable progress on networks where Xet retries.
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
os.environ.setdefault('HF_HUB_DOWNLOAD_TIMEOUT', '60')
from dotenv import dotenv_values
from huggingface_hub import HfApi, snapshot_download

root = Path(__file__).resolve().parents[1]
repo = 'swiss-ai/Apertus-v1.5-8B'
revision = 'ef4bbc54d6fe658bc782280ff9f3b53a10a9758f'
destination = root / '.runtime/models/Apertus-v1.5-8B'
token = os.environ.get('HF_TOKEN') or dotenv_values(root / '.env').get('HF_TOKEN')
if not token:
    raise SystemExit('Set HF_TOKEN in the private .env file before downloading.')
print(f'Downloading {repo} revision {revision}', flush=True)
for attempt in range(4):
    try:
        snapshot_download(repo, revision=revision, token=token,
                          local_dir=destination, max_workers=2)
        break
    except Exception as exc:
        print(f'Download attempt {attempt + 1}: {type(exc).__name__}; partial files retained.', flush=True)
        if attempt == 3:
            raise SystemExit('Download incomplete. Re-run to resume.') from None
        time.sleep(5 * (attempt + 1))

metadata = HfApi(token=token).model_info(repo, revision=revision, files_metadata=True)
files = []
for entry in metadata.siblings:
    path = destination / entry.rfilename
    if not path.is_file() or path.stat().st_size != entry.size:
        raise SystemExit(f'Incomplete model file: {entry.rfilename}')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    actual = digest.hexdigest()
    if entry.lfs and actual != entry.lfs.sha256:
        raise SystemExit(f'Integrity verification failed: {entry.rfilename}')
    files.append({'path': entry.rfilename, 'bytes': entry.size, 'sha256': actual})
(root / '.runtime/apertus-model.json').write_text(json.dumps({
    'repository': repo, 'revision': revision, 'status': 'downloaded_and_verified',
    'files': files,
}, indent=2) + '\n')
print(f'Verified {len(files)} complete official model files.', flush=True)
