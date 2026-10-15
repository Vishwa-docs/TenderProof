.PHONY: run stop setup setup-access sources ingest documents dev test build check
run: setup-access
	docker compose up --build -d
	@echo "TenderProof: http://localhost:8001"
stop:
	docker compose down
setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.lock.txt
	cd track_2b/src/web && npm ci
setup-access:
	@test -x .venv/bin/python || python3 -m venv .venv
	@.venv/bin/python -c 'import dotenv' 2>/dev/null || .venv/bin/pip install python-dotenv==1.2.4
	.venv/bin/python scripts/bootstrap_local.py
sources:
	.venv/bin/python scripts/fetch_sources.py
ingest: sources
	.venv/bin/python scripts/ingest_sources.py
documents:
	.venv/bin/pip install -r requirements-documents.lock.txt
	.venv/bin/python scripts/prefetch_documents.py .runtime/docling
dev: setup-access
	DOCLING_ARTIFACTS_PATH="$(CURDIR)/.runtime/docling" HF_HUB_OFFLINE=1 PYTHONPATH=track_2b/src .venv/bin/python -m uvicorn tenderproof.api:create_app --factory --env-file .env --host 127.0.0.1 --port 8000
test:
	.venv/bin/python -m pytest -q
	cd track_2b/src/web && npm test
build:
	cd track_2b/src/web && npm run build
check: test build
