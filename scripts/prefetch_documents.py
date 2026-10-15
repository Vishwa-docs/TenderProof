"""Prepare official parser assets before disabling runtime network access."""
import hashlib
import json
from pathlib import Path
import sys
from docling.utils.model_downloader import download_models

destination = Path(sys.argv[1] if len(sys.argv)>1 else '.runtime/docling')
download_models(destination, with_code_formula=False, with_picture_classifier=False)
manifest = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(destination.rglob('*')) if p.is_file() and '/.cache/' not in str(p)}
(destination/'asset-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(f'Prepared {len(manifest)} parser assets in {destination}')
