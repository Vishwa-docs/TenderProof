"""Stdlib-only, resumable official-model downloader for the authorized GPU host.

Usage: python3 download_apertus_curl.py MANIFEST TOKEN_FILE DESTINATION
The token is passed to curl through stdin, never argv or log output.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import subprocess
import sys
from urllib.parse import quote

manifest_path, token_path, target = map(Path, sys.argv[1:])
manifest = json.loads(manifest_path.read_text())
token = token_path.read_text().strip()
if not token.startswith('hf_') or any(c in token for c in '\r\n"\\'):
    raise SystemExit('Invalid token file format.')
if manifest['repo'] != 'swiss-ai/Apertus-v1.5-8B' or manifest['revision'] != 'ef4bbc54d6fe658bc782280ff9f3b53a10a9758f':
    raise SystemExit('Manifest must identify the approved pinned official model.')
target.mkdir(parents=True, exist_ok=True)

def verified(path, item):
    if not path.is_file() or path.stat().st_size != item['bytes']:
        return False
    if not item['sha256']:
        return True
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(8 * 1024 * 1024):
            h.update(block)
    return h.hexdigest() == item['sha256']

def download(item):
    path = target / item['path']
    if not path.resolve().is_relative_to(target.resolve()):
        raise ValueError('Unsafe manifest path')
    path.parent.mkdir(parents=True, exist_ok=True)
    if verified(path, item):
        print('Already verified:', item['path'], flush=True)
        return
    partial = path.with_name(path.name + '.part')
    url = f"https://huggingface.co/{manifest['repo']}/resolve/{manifest['revision']}/{quote(item['path'])}"
    print('Downloading:', item['path'], item['bytes'], 'bytes', flush=True)
    result = subprocess.run([
        'curl', '--ipv4', '--fail', '--location', '--silent', '--show-error',
        '--connect-timeout', '30', '--retry', '8', '--retry-all-errors',
        '--retry-delay', '5', '--speed-limit', '1024', '--speed-time', '90',
        '--continue-at', '-', '--config', '-', '--output', str(partial), url,
    ], input=f'header = "Authorization: Bearer {token}"\n'.encode(), capture_output=True)
    if result.returncode:
        raise RuntimeError(f'curl download failed for {item["path"]}: exit {result.returncode}; partial file retained')
    if not verified(partial, item):
        raise RuntimeError(f'Integrity verification failed for {item["path"]}; partial file retained')
    partial.replace(path)
    print('Verified:', item['path'], flush=True)

try:
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(download, manifest['files']))
except Exception as exc:
    raise SystemExit(str(exc)) from None
(target / 'verified-download.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('All official model files downloaded and verified.', flush=True)
