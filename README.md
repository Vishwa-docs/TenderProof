# TenderProof

TenderProof is SwissChivers' Hack Apertus Track 2B prototype for reviewing transformer procurement evidence. It preserves source documents, asks Apertus to propose scoped engineering claims, and uses explicit human review plus deterministic checks before purchase or shipment decisions. Unknown measurements, identity fields and delivery baselines stay unknown.

The application starts with an **empty `default` project**. It has no seeded business records, role-switching shortcut, or simulated model fallback. The included source catalog links actual Guam Power Authority procurement PDFs; the originals are fetched separately. Isolated regression fixtures under `track_2b/tests/` verify software behavior and are not model evaluations.

## Recorded submission result

Apertus v1.5 8B completed five source-kind runs on four authentic PDFs, including the complete 57-page tender. The case contains 35 pending requirements and four pending offers, with mixed extraction quality. An audited PO unit-price correction preserves the raw output. All results remain pending; missing FAT and unresolved extraction conditions block release. The GPU endpoint was stopped after recording and borrowed workloads restored.

[Speaking slides](track_2b/submission/output/TenderProof_Slides.html) · [Exact video script](demo.md) · [Judge quickstart](docs/JUDGE_QUICKSTART.md) · [Six-page report](track_2b/SwissChivers_Report.pdf) · [Submission verification](track_2b/submission/VERIFICATION.md)

## Run with Docker

Requirements: Docker with Compose, Python 3.11 or newer, and network access for the initial image/package/model-artifact downloads. The image includes Docling and prefetched parser/OCR assets; the first build is substantial. An actual Apertus inference service is required for extraction, but source review can start without it.

```sh
cp .env.example .env
make setup-access
# Configure LLM_BASE_URL, LLM_NAME and LLM_API_KEY in .env for your actual endpoint.
make run
```

Open [http://localhost:8001](http://localhost:8001). Sign in using the private token in `.runtime/operator_token`. Setup generates a database password and an engineer principal restricted to `default`; it creates no procurement data. Preserve `.env` and Docker volumes between runs. `make stop` stops the stack without removing its named volumes.

`LLM_BASE_URL` must include `/v1` and be reachable by the app and worker. `LLM_NAME` defaults to `swiss-ai/Apertus-v1.5-8B`; the server must actually run the configured Apertus model. An empty endpoint causes a clear unavailable response, never substitute output. The checked-in model relay targets a separately configured host tunnel at port 18102; it does not provision a model. See [model access and deployment](track_2b/docs/MODEL_ACCESS.md) before using it.

`LLM_TIMEOUT_SECONDS` defaults to 300 per role (allowed range 1–900). Successful extraction traces record provider response IDs, reported usage counters and content hashes. Optional `APERTUS_TRACE_DIR` stores exact request/response bodies in private UUID directories for investigation, including invalid returned content. These archives contain source text; keep them in ignored local storage. Authorization headers are not archived.

Large requirement documents use complete, page-aware source windows of at most 48,000 text characters, with all four roles run per window. Every original span is retained; valid candidates are saved together after all windows complete; invalid rows and failed structured audits are retained as explicit blocking assurance conditions. Cross-window interpretation and unencoded obligations still require human review. See [window bounds, trace coverage and workflow deadlines](docs/REQUIREMENT_SOURCE_WINDOWS.md).

Compose runs PostgreSQL, a persistent Temporal development server, an API/worker pair, and a loopback-only gateway. App and worker use an internal Docker network. Any model relay or externally hosted inference changes the data boundary and must be described with the actual hosting location. This prototype is not a production deployment or a demonstrated air-gapped installation.

## Review real sources

Set the project name, customer and exact equipment scope before extracting claims. Upload complete originals in the workbench, then inspect source pins and proposals. The model cannot grant approval. Purchase release requires engineer and commercial approval; shipment release requires inspector and commercial approval. Additional authorized identities must be configured by the operator in `TENDERPROOF_PRINCIPALS_JSON`; the initial engineer token cannot perform every role.

To fetch and upload the five cataloged GPA-070-25 PDFs to a running local instance:

```sh
make setup
make ingest
```

This uses `.runtime/operator_token`, targets `http://127.0.0.1:8001`, and sets the scope to OP34276 item 2, the 750 kVA transformer, excluding the separate 300 kVA item. It stores full originals with source URL and SHA-256, leaving all claims unapproved. Override `TENDERPROOF_API_URL` and `TENDERPROOF_API_TOKEN` when needed. Downloads and receipts stay under ignored `.runtime/`.

The source set includes an order, specification, bid abstract and amendments. It does **not** establish a unit-specific FAT result or serial-number match. Drawing-approval-relative delivery terms do not establish a project-relative deadline. See [source provenance and limitations](docs/REAL_DATA_SOURCES.md) and [data licensing](track_2b/data/README.md).

## Local development and verification

For a local API with SQLite and direct extraction, rather than the Compose PostgreSQL/Temporal deployment:

```sh
make setup
make documents
make build
make dev
```

`make dev` loads `.env`, uses `.runtime/docling` with offline model lookup, and serves the built workbench at [http://localhost:8000](http://localhost:8000). Prefetch assets with `make documents` while network access is available. Leave `DATABASE_URL` and `TEMPORAL_ADDRESS` unset for local SQLite/direct mode; a Docker-internal model URL must be changed to an endpoint reachable from the host. Frontend builds require Node.js 22 and npm.

```sh
make check
```

This runs backend and frontend regression tests and builds the UI. These are software checks, not claims about Apertus accuracy. Read [deployment verification](docs/DEPLOYMENT_VERIFICATION.md) for measured checks and their limits. The read-only scripts `scripts/container_smoke.py` and `scripts/temporal_smoke.py` inspect an existing deployment without seeding business data.

## Repository and submission

- [Track 2B challenge and mandatory files](track_2b/README.md)
- [Technical report](track_2b/technical_report.md)
- [Verified submission requirements](track_2b/docs/SUBMISSION_REQUIREMENTS.md)
- [Verified hackathon precedents, market evidence and reused foundations](docs/PRIOR_ART_AND_MARKET.md)
- Backend: `track_2b/src/tenderproof/`; frontend: `track_2b/src/web/`
- Runtime credentials, original third-party PDFs, local databases and model caches are excluded from version control and the Docker build context.

The selected `track_2b/` directory is preserved; unrelated template tracks are removed as required by the [official template](https://github.com/HackApertus/project-template).

## Licences and attribution

Copyright 2026 SwissChivers. Team-authored code is [Apache-2.0](LICENSE); team-authored documentation and non-code outputs are [CC-BY-4.0](LICENSES/CC-BY-4.0.txt); the team's source-catalog metadata is [CDLA-Permissive-2.0](LICENSES/CDLA-Permissive-2.0.txt). See [the scope and third-party notices](NOTICE.md). Original procurement PDFs, upstream template material, dependencies and model assets retain their own rights and notices. This repository grants no new rights in third-party PDFs and does not distribute model weights.
