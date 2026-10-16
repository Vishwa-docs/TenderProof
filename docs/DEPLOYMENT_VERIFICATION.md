# Current deployment verification — 15 October 2026

The 16 October workbench build passes **380 Python tests, 51 frontend tests, TypeScript and Vite**. `make run` rebuilt the application. Authenticated API calls and current JS/CSS asset hashes match the build. Forward migration preserved all original content and events; an app/worker restart preserved version 13 and snapshot `fec4b6ba125c296f9564f2e475ef6e441b1ee93a55a7ccbc2df826b2a2620ba6`.

The current real case contains five documents, 35 pending requirements and four pending offers. All five extraction runs have unresolved assurance conditions. There are no approvals, acceptance evidence or releases. Genuine Apertus inference completed before the model endpoint was stopped and borrowed workloads restored. See [final verification](../track_2b/submission/VERIFICATION.md) and [real model execution](REAL_MODEL_INTEGRATION.md).

The gateway now refreshes its app upstream through Docker DNS, fixing an observed 502 after the app container changed. The inspected API and served assets were reachable after that fix.

## Historical checkpoints

Everything below describes earlier checkpoints. Old pending-inference statements, test counts, assets and snapshot IDs are historical, not the current submission state.

# Deployment verification — authentic sources

Recorded 15 October 2026. These are observed software and source-ingestion checks. They do not establish model accuracy, engineering certification, production availability or shipment acceptance.

## Current application

The live application at `http://127.0.0.1:8001` contains GPA-070-25 / OP34276 item 2, with five complete authentic PDFs. It contains no seeded business examples. The selected equipment is three 750 kVA transformers; the separate 300 kVA order line is excluded from the scope.

At this checkpoint, requirements and decisions are empty because actual Apertus inference has not yet completed. The model endpoint is explicitly unconfigured. The interface and API report that condition; neither substitutes an example response.

## Reproducible build and software checks

- `docker compose build app` completed from the public Dockerfile, including prefetched offline Docling assets. Its observed image record is `sha256:5b2809e7953c77bc01586a45ad91b70d6df3cbb08911dd791d67345dd2448a17 arm64 7362148091`. The first build downloads substantial dependencies; later builds reuse them.
- `.venv/bin/python -m pytest -q`: **127 passed in 9.53 seconds**. Log: `.runtime/backend-final.log`.
- `npm test`: **20 passed in 4.53 seconds**. Log: `.runtime/frontend-latest.log`. This includes the final source-inspector presentation checks.
- `npm run build`: successful production bundle. Log: `.runtime/frontend-build-final.log`.
- Independent review resolved the complete-source windowing findings: completed workflows reuse results, explicit retries after failed workflows may create a replacement, and the exact compact source-payload limit includes JSON brackets. See [review](REQUIREMENT_WINDOWS_REVIEW.md).

Regression tests use isolated constructed software inputs. Their pass rate is not a real-model or engineering-performance result. `make run` completed with exit code 0. The resulting image is `sha256:7d005d4ccbcdb4552a9fb7fad91d943682b0e48ab42dd4dbbeedaa4c0cad8808` (arm64, 7,362,150,484 bytes). At 2026-10-15 09:54:44 UTC, all six containers were running, app/PostgreSQL/Temporal were healthy, and the gateway served `index-D6v-Jk9U.js` and `index-B2SGI0za.css`. The complete five-source project remained identical after this rebuild. Evidence: `.runtime/make-run-verification.log`, `.runtime/make-run-live-verification.json`, `.runtime/make-run-project-verification.json`.

## Actual source ingestion and persistence

Five PDFs, totaling 95 attachment pages with overlapping specification and amendment content, are stored with their exact original bytes, URLs and SHA-256 hashes. Their parsed output contains 2,136 source spans. The complete 57-page IFB has 1,214 spans and 233,182 characters, with strict Docling SUCCESS, zero reported conversion errors, and converted/source-span page coverage 1–57.

The first four stored records predate the parser's retained status fields; their strict revalidation is recorded separately. See [source parsing verification](STRICT_SOURCE_PARSING.md) for the four isolated checks, the integrated fifth check, OCR limits and the terminated parallel verification attempt. No full-parsing or image-authenticity claim is inferred from an absence of missing embedded lines.

After restarting PostgreSQL, Temporal, app, worker and gateway without deleting volumes, the complete project JSON was identical. All five original downloads retained their expected hashes. The snapshot before and after was:

`cdd3f564c90af98af33cd105510521297b4f0e19dbba7351d508b3044d13a73e`

Evidence: `.runtime/real-project-five-before-restart.json`, `.runtime/real-source-restart-verification.json`, `.runtime/source-restart.log`. No completed live inference workflow existed at that point, so this is not evidence of live-inference recovery.

## Read-only MCP and tested network boundary

The actual MCP SDK initialized the stdio server using protocol `2025-11-25`, listed `read_package`, `read_document_revision`, and `prepare_purchase_draft`, and successfully read the authentic project using its server-configured bearer principal. Only `read_package` was invoked. No approval, draft or release was created. Evidence: `.runtime/live-mcp-verification.json`.

Docker reports the application's `sovereign` network as internal. Both app and worker reached PostgreSQL on port 5432 and Temporal on port 7233. Direct connection attempts to `1.1.1.1:443` and `8.8.8.8:53` failed with OSError. Evidence: `.runtime/live-network-verification.json`.

These measured routes are not a comprehensive exfiltration assessment. The fixed model relay accepts only model-list and chat-completion paths and publishes no host port. Actual authenticated model connectivity and its final network boundary remain to be verified after the GPU server is available.

## Model and submission status

The supported Swiss AI vLLM image is downloaded and verified as `ghcr.io/swiss-ai/vllm_apertus_1.5_release@sha256:d85533f251c8272218ae2e519510836376e5a335b44f2204f193018e37753bc6`. Its CLI was inspected successfully in an ephemeral container without loading weights or stopping other workloads. Official Apertus weights are still downloading to the authorized GPU machine. The two pre-existing GPU workloads have not been stopped. No paid cloud endpoint has been provisioned. Hugging Face credits were still USD 0.00 on the latest account check.

Real inference traces, source-reviewed proposals, completed Temporal workflow recovery, final captures and rendered report/deck/video remain pending. The report and artifact generators enforce that distinction. Earlier synthetic-based operational records and outputs are withdrawn into ignored private archival storage and are not submission evidence.

## Audited price-correction deployment checkpoint

The price-correction change passed its focused independent review in [review](PRICE_CORRECTION_INDEPENDENT_REVIEW.md). Root `make run` completed again with exit code 0; observed image `sha256:96abd41b45f170ca57e9a76aab7a9881674e69b07f139e66f77a79ee0eef3a36`, arm64, 7,362,159,538 bytes. At 2026-10-15 10:21:05 UTC the gateway served `index-DbkntFOd.js` and `index-DvAhsu3L.css`; all six services were running and app, PostgreSQL and Temporal were healthy. The complete five-document project JSON was unchanged. No correction has been applied to a live model proposal yet because actual inference remains pending. Evidence: `.runtime/make-run-price-correction.log`, `.runtime/price-correction-deployment-verification.json`.

## Original-page preview checkpoint — 2026-10-15 10:47 UTC

Root `make run` completed with exit0 from public sources. Actual HTTP serves `index-CQJqGKmM.js` and `index-BEgCKw9W.css`. Authenticated previews of bid-abstract page3 and complete-tender page57 returned PNGs with matching original SHA/page headers, bounded dimensions and private/no-store caching; unauthenticated requests returned401. The five-document project is byte-for-byte JSON equivalent to its earlier saved state, including snapshot `cdd3f564c90af98af33cd105510521297b4f0e19dbba7351d508b3044d13a73e`. Actual inline page selection and zoom were inspected in the browser and captured. The automation browser blocked separate blob-tab navigation; the existing inline viewer worked. Evidence: `.runtime/original-preview-deployment-verification.json`. Apertus remained unconfigured; no extraction result is claimed. The subsequent original-download integrity fix is not included in this deployed checkpoint.

## Final reviewed application checkpoint — 2026-10-15 11:00 UTC

Root `make check` passed267Python tests in13.21seconds,33frontend tests in9.01seconds, and TypeScript/Vite. Root `make run` completed exit0. Actual HTTP serves `index-AxrPa7ge.js`/`index-BEgCKw9W.css`; image `sha256:a12d2a639cbfab92e07537a0ec11dfe2d038be378f36f72bfc5679012c900b94` is arm64,7,362,172,069bytes. All six Compose services are running. All five original download responses match their recorded SHA256 and include private/no-store and sourceSHA headers. Full project JSON remains identical to the earlier saved authentic-source state: revision7, no requirements/proposals/suppliers/evidence/decisions. Source/render handling, nullable configuration and unknown ancillary costs are included in this build. Evidence: `.runtime/reviewed-final-deployment-verification.json`, `.runtime/final-make-check.log`, `.runtime/make-run-reviewed-final.log`. Apertus is not configured at this checkpoint; no inference/release outcome is asserted.
