# TenderProof frontend - current live-only implementation

The current application is a real-data review workbench. All demonstration controls, role-header overrides, fabricated project banners, reset operations, canned corrections and canned amendments were removed after the user's live-data-only instruction. Earlier synthetic UI captures and demonstrations are superseded and are not evidence for this release.

## API and scope

- Project path: `/api/projects/default`.
- Authentication: server-issued bearer token in browser tab-session storage; the server maps identity, role and project authorization. The UI never sends `X-Demo-Role`.
- Project details: snapshot-bound `PATCH /api/projects/default` with name, customer and equipment scope. The UI requires all three fields before extraction, requirement/proposal approval or gate creation. Uploads can precede scope review.
- Server state only: requirements, suppliers, evidence, documents, assessments, costs, approvals and events are read from the API. There is no bundled project or inference fallback.

## Four workspaces and source inspection

Requirements provide search/status filters, explicit witness answers, snapshot-bound review and exact source/page references. Supplier comparison shows technical outcomes, commercial values supplied by the API and a sourced delivery milestone; an absent delay is displayed as not established. Acceptance shows evidence applicability, measurements, proposal review, explicit type-family coverage, same-supplier/same-kind supersession, role-bound approval gates, idempotent JSON release downloads and historical artifacts. History shows actual server events only.

Source inspection supports document upload, original authenticated download, image blob preview and real Apertus extraction by purpose/supplier. Long operations display elapsed seconds without claiming an invented completion percentage. Missing inference surfaces the actual backend error. Scope and configuration ambiguities remain human review issues.

Navy navigation, warm ivory documents and teal actions use restrained tables and linework. The source inspector stays available on desktop and stacks on narrow screens. Modals support focus/escape navigation; motions respect reduced-motion settings. External font service use has system fallbacks and is disclosed in the web README.

## Current verification

The frontend suite uses isolated controlled QA responses based on actual public Guam Power Authority GPA-070-25 / OP34276 metadata and numerical facts. It does not provide app data or claim model outputs. Coverage includes bearer-only requests, explicit witness/snapshot review, exact source/page, API failure without replacement data, mandatory scope, metadata PATCH, extraction purpose/supplier, historical immutable downloads, original-content errors, legitimate empty workspaces and mutation locking.

`npm test`: 30 tests passed. `npm run build`: TypeScript and Vite passed. Latest bundles: JS 282.70 kB / 86.13 kB gzip; CSS 42.77 kB / 9.96 kB gzip. A source scan found no demonstration-control, synthetic-banner or role-override strings in application TSX/types/CSS/README. No new live model result or deployed browser flow is claimed by this refactor. Backend schema/live authentication changes and any real Apertus evaluation must be verified by the parent integration work.

## Authentic research handoff

`docs/REAL_DATA_SOURCES.md` identifies the actual GPA-070-25 purchase order, incorporated E-004 Revision 10 specification, bid abstract and amendments. No actual matching FAT report or serial-number nameplate was established. Source copyright remains with the issuing parties; publicly downloadable originals are not relicensed as project-created data.

## Supplier batch review and documented costs

Supplier extraction now accepts the mapper's complete list of actual offers. The service saves the whole batch under one snapshot transaction, keeps distinct source references, rejects an invalid row without saving preceding rows, deduplicates identical rows, and makes Temporal persistence retries idempotent. Approval remains per proposal and requires an engineer. A single supplier retains the legacy object response; zero or multiple suppliers return `{proposals, trace}`. Evidence remains exactly one record. No technical facts or unknown identity/commercial fields are filled from another offer.

The extraction selector reads “Supplier bids / configurations” and the result states how many proposals require individual review. Unknown prices/currencies display “Not provided” rather than zero or an invented currency; unknown revisions and delivery baselines remain explicit. Commercial rows are “Documented unit price,” “Recorded expedite / rework,” and “Documented subtotal.” Default zero adjustments display “None documented”; undocumented costs remain unknown. This is not a full ownership-cost calculation.

Added regression coverage in `track_2b/tests/test_supplier_batches.py` (16 cases) for batches, source isolation, rollback, duplicates, empty extraction, separate authorization, durable retries, malformed lists and legacy HTTP shape. Added four Temporal timeout-boundary cases in `track_2b/tests/test_workflow_budget.py`. Final full Python suite: 92 passed. UI suite: 18 passed. TypeScript/Vite build passed. Earlier full runs overlapped the integration owner's test-first edits and failed pending telemetry/PDF cases; the final fresh run passed after those implementations were stable.

New Temporal requests capture a budget of four configured per-role HTTP timeouts plus 120 seconds outside workflow execution. Default: 1,320 seconds; allowed maximum: 3,720 seconds. Slow inference has one attempt; SQL persistence retains three idempotent attempts. Configure the same model timeout on API and worker. This code has not been replay-tested against pre-change in-flight workflow histories; deploy with drained/new extraction runs. No new actual live inference or Docker/browser capture is claimed here; parent integration owns that verification.

The independent source review is `docs/REAL_PACKAGE_REVIEW.md`; exact assistant-checked QA reference facts are in `track_2b/data/evaluation/gpa-source-facts.json`, separate from inference input. Original PDFs were rendered; hashes, page counts, arithmetic and cited parsed-span page numbers were verified. Handwritten bid uncertainties and missing FAT/serial/revision/approval evidence are preserved.

## Empty-package browser follow-up

Fixed the parent-observed real empty-package finding: zero requirements now says “Awaiting requirements,” including the comparison review status, and cannot imply review completion. Gate creation/approval/release controls require a nonempty set of approved requirements; historical record downloads remain accessible. This is a frontend guard in addition to the server's existing conditional assessment when no criteria exist. No backend changes were made for this follow-up.

The sidebar now uses the actual project name with its full title available by tooltip, instead of wrapping a long equipment scope there. The full scope remains visible in the workspace context and retained verbatim in Project details, whose scope field has a full-value tooltip. Two additional UI regressions cover the empty/release state and long-scope accessibility. Final scoped check: 18 UI tests passed and TypeScript/Vite build passed (JS `index-CfJ6oi9G.js`). Parent owns rebuilding deployed Docker assets and browser capture.


## Actual source-inspector follow-up

The exact Docling unavailable-image marker observed in the authentic 57-page tender is rendered as an explicitly labeled extraction notice: “Image content was not extracted. Inspect the original document.” Both document-library and cited-passage views distinguish it from quoted source text. The original span text, identifiers, page references and server data remain unchanged; authenticated original download stays available. This presentation does not claim that image content was extracted or reviewed.

The document metadata panel now shows the stored original `source_url` as an external link and `parsing.page_count` when those fields exist. It does not infer a URL or total page count from retained passages. Long source URLs wrap within the inspector. A regression reproduces the actual full-tender marker, source URL and 57-page metadata; another verifies that missing metadata is not invented.

Final scoped checks after this follow-up: **20 frontend tests passed**, TypeScript/Vite build passed. Assets: `index-D6v-Jk9U.js` (274.24 kB, 83.78 kB gzip) and `index-B2SGI0za.css` (40.64 kB, 9.51 kB gzip). Parent owns deployed rebuild/browser verification. No backend, database, parsed-source data or live inference was changed by this presentation fix.

The independent combined strict-parser evidence is [STRICT_SOURCE_PARSING.md](../../docs/STRICT_SOURCE_PARSING.md): four successful isolated offline reparses plus a separately verified successful actual API parse of the full 57-page tender. The failed isolated fifth attempt and Docker OOM/exit 137 remain recorded. The 95 attachment pages include duplicated source content; they are not 95 unique pages.


## Manual correction for real handwritten price OCR

Pending supplier proposals now expose **Correct price**. The engineer can review the existing source passage, download the original PDF, enter a decimal unit price and currency (USD/CHF/EUR or unknown), select a passage from that proposal's document and explain the source reading. The current model value is the starting draft; no QA reference value is preloaded into the application. Blank amount and currency remain explicit nulls. Known currency with unknown amount is supported.

Saving calls `POST /api/projects/default/proposals/{id}/correct-price` with the current snapshot, integer `price_cents` or null, currency or null, `source_id` and trimmed reason. Decimal parsing uses integer arithmetic, accepts at most two fractional digits and rejects negative, separator/exponent, excess-precision or unsafe-cent values. The source picker is limited to the proposal document. Save remains disabled without a source/reason; a draft locks that proposal's approval control. An API rejection preserves the draft and pending review.

The saved `original_data` and `price_corrections` are displayed as manual provenance, including before → after, actor, timestamp, source page, reason and source-inspector link. Known currency remains visible when the amount is unknown, and a known amount remains visible when currency is unknown. The same history appears beside the approved supplier's documented price. The UI performs **separate approval**, not an independent-reviewer identity check; server authorization and identity policy are unchanged. Correction does not imply compliance, acceptance, unit identity or a passing test.

Six UI regressions cover the sourced snapshot-bound request/separate approval, invalid and unknown amounts, exact 0.29-to-29-cent conversion, stale-snapshot draft preservation, approved-supplier provenance and mixed-null history readability. The numeric boundary test is QA arithmetic input, not a claimed source price. Final checks: **26 frontend tests passed**, TypeScript/Vite build passed. Assets: `index-DbkntFOd.js` (279.01 kB / 85.07 kB gzip), `index-DvAhsu3L.css` (41.78 kB / 9.76 kB gzip).

This frontend pass changed only App.tsx, App.test.tsx, types.ts, styles.css and this report. Backend correction support belongs to the backend owner. No original PDF, canonical parse, API database, actual proposal or model trace was mutated, and no new live inference/browser success is claimed. Parent owns independent frontend review and deployed application rebuild/verification.


## Read-only original PDF page preview

The source inspector now offers an explicit original-page preview beside each cited PDF passage and an initial page-one preview in the document library. Only the selected page is requested; source selection alone does not fetch a page, and no attachment-wide preview fetch occurs. The active panel supports page selection, fit-width / 2× zoom, opening the full PNG, accessible image text, loading status, explicit errors and user-triggered retry. Existing original download remains available. Requests carry the current bearer token. Switching pages, changing source context, changing identity, closing the inspector or unmounting aborts pending work and revokes the prior blob URL; late responses cannot resurrect closed previews.

The new API is `GET /api/projects/{pid}/documents/{docid}/pages/{page_number}/preview?max_dimension=1800`. It verifies membership and the document within that project, then reads the immutable original object by a validated SHA-256. The file must have a PDF name and signature and must match the stored hash. No text reconstruction is used for preview. Missing originals return 404; invalid type returns 415, bad page/corrupt PDF returns 422, hash mismatch returns 409 and PDF access busy returns 503. Input is limited to 15 MiB; dimensions are limited to 256–2400, and raster output to four million pixels. Page range is checked against the actual PDF, rather than inferred from source spans. PNG responses have private/no-store, nosniff and original hash/page headers. Bitmap, image, page and document handles are closed.

A shared application PDF lock covers API PDF ingestion and page rasterization in one process. The concurrency regression first reproduced simultaneous native entry, then verified that an active API parse prevents a preview from entering PDFium and returns an actionable busy error. Another verifies release after a failed parse without saving a document. The existing strict parse function is unchanged. This is a measured API boundary, not a production-hardening claim. The existing content-download handler was left unchanged; the preview path never uses its extracted-text fallback.

`track_2b/tests/test_pdf_page_preview.py`: **26 passed**, using software-generated blank PDFs and temporary QA databases only. Coverage includes requested-page geometry, authentication/project isolation, page/dimension/pixel/byte limits, missing/corrupt objects, hash integrity, concurrency and unchanged project/original state. Optional renderer tests use the document dependencies and skip when those dependencies are absent; the actual checked environment included them. Three new UI cases verify lazy/authenticated selected-page requests, zoom and URL cleanup, canceled late responses, and explicit missing-original failure with no image substitute.

The related nullable-configuration follow-up changes supplier/evidence frontend types to `string | null`. Supplier comparison and gate selection display **Configuration unknown**; evidence keeps its existing unknown display. A regression verifies the comparison and selection labels. No configuration is invented and no identity-editing feature was added.

Latest checked combined Python suite: **228 passed**. Latest frontend suite: **30 passed**. TypeScript/Vite production build passed: `index-CQJqGKmM.js` (282.70 kB / 86.13 kB gzip), `index-BEgCKw9W.css` (42.77 kB / 9.96 kB gzip). Parent's final `make check` remains authoritative as other backend fixes continue. This pass changed api.py, added page_preview.py and test_pdf_page_preview.py, and changed App.tsx, PdfPagePreview.tsx, App.test.tsx, types.ts, styles.css and this report. No integrations.py/service.py/models.py, deployment, submission, canonical source, QA reference or live project was edited. No actual live preview/browser success is claimed; parent owns the real-source calls and deployed visual verification.


## Original download integrity follow-up

The adjacent original-content endpoint's OCR-text fallback has now been removed. Missing originals return **404**, altered original bytes return **409** for a source-hash mismatch, and oversized originals return **413**. Filesystem objects are selected only after validating the stored SHA-256 as 64 lowercase hexadecimal characters. Download and preview share a bounded original-byte reader and hash verification. Valid download bytes and filenames remain unchanged. Valid inline raster-image originals retain their existing media behavior after strict base64 decoding and SHA verification; corrupt inline images return an explicit error. No missing object is replaced by extracted text under the original PDF filename.

Valid original responses now include private/no-store, nosniff and source-SHA headers. The earlier note that the download handler remained unchanged describes the previous preview pass and is superseded by this fix. `track_2b/tests/test_original_downloads.py` adds 13 software-only cases for absence, altered bytes, valid unchanged originals, path/hash isolation, byte limits, authentication and inline-image integrity. The original-download, preview and existing API checks passed **48 tests**. No live project, source original, canonical parse, frontend asset, model data or trace was changed; parent owns deployed verification and the independent reviewer owns the narrow source-integrity re-review.

Fresh combined Python check after this original-download delta: **252 passed**. The frontend was unchanged in this delta; subsequent cost-display work and final combined release verification remain with their assigned owners.
