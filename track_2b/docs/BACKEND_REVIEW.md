# TenderProof backend review

Review date: 2026-10-15. Scope: `domain.py`, `models.py`, `service.py`, `api.py`, `integrations.py`, fixtures, and existing tests. Specification: `docs/superpowers/plans/tenderproof.md` and `track_2b/docs/PROGRESS.md`. Workflows, MCP, deployment, and frontend were being implemented concurrently and are outside this review.

## Complete-source requirement window verification

Following discovery of the 57-page source, bounded requirement extraction now plans every ordered source span into page-aware windows without truncation. Every window runs all four roles, citations are constrained to the actual window, and persistence receives one fully validated pending aggregate only after all windows succeed. Exact duplicate rows may merge citations; conflicting rows stay separate. Temporal captures and verifies the same plan and budgets four calls per window. The prior single-window path and bounded supplier/evidence behavior remain supported.

Fresh verification: `make check` passed **120 backend tests, 18 frontend tests and the production UI build**; the last backend run after the bounded API result wait passed **121 tests in 8.39 seconds**. Behavioral checks include late-window failure with no SQL/snapshot change, complete ordered source preservation including empty spans, oversized/invalid-plan rejection before calls, cross-window citation rejection, conservative deduplication and one atomic idempotent pending batch. See `docs/REQUIREMENT_SOURCE_WINDOWS.md` for exact contract, native-text planning evidence and limitations. No real model evaluation or live deployment mutation was performed.

## Consolidated final-review fixes

The subsequent independent review identified two additional defects: report-level conditions were ignored, and partial Docling conversion status was discarded. Both are now repaired and regression-tested. Report conditions constrain every measurement; local conflicts block applicability and shipment. PDF conversion accepts only successful, error-free, complete page coverage and retains actual parsing/coverage metadata. UI approvals and exported simulator packets now state that checks cover reviewed encoded numeric requirements and that unencoded obligations still require engineering review.

Final `make check`: **105 backend tests passed in 7.04 seconds; 18 frontend tests passed in 4.01 seconds; TypeScript/Vite production build passed in 1.31 seconds**. `git diff --check` was clean. See `docs/FINAL_REVIEW_FIXES.md` for the scoped changes, reproductions and remaining live-source revalidation boundary. These later findings supersede the earlier scoped statement that no unresolved defect had been found at that time. No Compose or runtime application data was changed by the fixes.

## Later scoped integration review

Fresh command `.venv/bin/python -m pytest -q`: **92 passed in 2.76 seconds**, exit 0. Integration-only command: **23 passed in 0.24 seconds**. This supersedes earlier software test counts, not the historical deployment/model evidence limits.

Added and verified compact alias restoration for root and nested citations; selected scope and complete source-span text across all four role requests; distinct basic/alternate supplier rows, empty applicable-offer results and whole-batch rejection for invented citations. Supplier-list support retained the older single-supplier response. Evidence still requires one record.

Per-call traces now record provider response ID/model, bounded numerical usage, elapsed time and hashes of actual request/response bodies and assistant content. Optional private UUID archives contain exact credential-free HTTP bodies and are published by an atomic directory rename. Invalid returned content is retained for investigation before abstention. Timeout defaults to 300 seconds per call and accepts only 1–900; workflow orchestration captures the four-call budget outside deterministic execution. Transport tests are constructed software QA, never real-model quality measurements.

The actual OP34276 PDF exposed missing embedded-text lines/list labels during Docling layout reconstruction. The new native-text supplement preserves those original lines with page pins and explicit parser-origin metadata. All embedded lines on the nine actual pages were verified retained, and the supplement ran inside the offline Docker image. See `docs/PDF_SOURCE_FIDELITY.md` for exact counts and limits. OCR correctness and semantic table interpretation still require visual review; this is not a general completeness guarantee.

No new unresolved defect was identified in this scoped pass. Final Compose rebuild, real inference and final live source ingestion remain parent-owned deployment verification.

## Live-only migration verification

After the user's real-data-only instruction, the backend was changed to create only an empty live project with ID `default`. Authored sample data was removed from the application package and moved to `track_2b/tests/support` for isolated software regression tests. Demo mutation routes and role-header authentication were removed. All API tests now use server-owned bearer principals.

The current fresh command `.venv/bin/python -m pytest -q` completed with **57 passed in 2.86 seconds**, exit code 0. `git diff --check` was clean. This count supersedes the earlier test count below. Constructed regression inputs and mock transports remain software QA only; they are not real-model performance evidence.

The API now requires an engineer-defined equipment scope before extraction/approval, passes that scope to both direct and Temporal extraction, and prevents changing it after claims exist. It does not claim general multi-equipment validation. Optional HTTP(S) source URLs are retained as provenance without being fetched by the server. Missing price, currency, delivery, revision, serial, and family values remain null; missing commercial inputs prevent a feasible purchase recommendation, and missing required identity prevents supported test applicability.

The parent task owns the clean live database, actual-document intake, final container rebuild, and real Apertus verification. No claim that those external checks are complete is made here. Operational smoke scripts now read existing live state only and cannot seed records, approve decisions, or launch a mock model.

## Earlier re-review verdict

**All nine initial backend findings are resolved in the reviewed implementation.** The final fresh command `.venv/bin/python -m pytest -q` completed with **45 passed in 3.03 seconds**, exit code 0, with no warnings in that run. The initial findings and reproducers are retained below as a historical audit record; they are not open defects.

The bounded backend meets the reviewed specification for human-reviewed interpretation, source-bound evidence, typed applicability, guarded purchase/shipment decisions, immutable artifacts, and conservative change invalidation. No unresolved correctness/security defect remains from this review. This is not a claim that deployed PostgreSQL, Temporal, or a real Apertus endpoint has been exercised by this reviewer.

The reviewer was subsequently authorized to repair `domain.py`, narrow fixture/correction provenance code, and backend tests. Pending/rejected criteria and unsupported FAT claims were each observed failing before the implementation repair, then observed passing. Parent-owned repairs were independently checked through tests and code inspection.

| Finding | Final repair and verification |
| --- | --- |
| BR-01 | Issued artifacts persist in a separate immutable table and are read independently of current decisions. Regression confirms identical retrieval after demo reset and service restart. |
| BR-02 | Live projects start with an unknown delivery milestone. The authenticated live integration test confirms release is blocked, inspector milestone editing is forbidden, and engineer approval of an existing source span permits the release workflow. |
| BR-03 | Inspector approval can explicitly supersede prior evidence for the same supplier and kind. Regression rejects an engineer and a cross-supplier replacement, preserves the old report, and confirms corrected evidence permits shipment preparation. |
| BR-04 | Model schema still forbids self-approved family coverage. API tests confirm an explicit inspector confirmation is required for supported type coverage, and an engineer cannot perform that inspector operation. Blank family identity remains unknown. |
| BR-05 | Measurement pins refer to FAT passages. Fixtures and corrections omit the unstated ONAF measurements; a regression also checks correction of older stored evidence that contains that erroneous extra measurement. |
| BR-06 | Maximum-rating witness answers now match the actual upper-bound operator; existing minimum-rating witness behavior is retained. |
| BR-07 | Invalid decimal values become schema failures; null model content and malformed audit values produce controlled `ModelUnavailable` results. Four malformed-envelope/audit tests were observed failing before the parent repair and passing afterward. |
| BR-08 | Evidence assessment preserves actual criterion review state. Separate pending/rejected regressions initially returned supported, and now return unknown without altering the criteria. The existing type-report test now uses genuinely approved criteria. |
| BR-09 | Authenticated original-document retrieval exposes the immutable image. Tests verify exact bytes, image media type, `nosniff`, and rejection of unauthenticated/wrong-project requests. |

The new `test_live_flow.py` exercises a complete authenticated live-mode path using the real model schema validator, HTTP handlers, SQL persistence and release gates, with **only the external model HTTP transport mocked**. It covers source upload, engineering requirement review, supplier review, inspector evidence review, source-linked schedule approval, both release gates with separate required roles, and immutable artifact retrieval after a later schedule change invalidates the decisions. This is reproducible integration evidence, not actual Apertus inference.

No authentication bypass or release without the configured two approval roles was found in the reviewed code. The global release guard blocks pending requirements and stale content snapshots. Solver consistency checks correctly prevent contradictory guarantees from proving compliance.

## Initial baseline verification

- `.venv/bin/python -m pytest -q`: **22 passed**, one upstream Starlette/httpx deprecation warning.
- Direct service/domain reproducers for reset artifact loss, inherited live deadline, unavailable type approval, missing family identity, wrong witness answer, pending-criterion evidence assessments, and evidence correction.
- Mock HTTP model response containing a malformed quantity reproduced an uncaught `decimal.InvalidOperation`.
- An authenticated **live-mode API** flow succeeded with explicitly mocked Apertus extraction output: upload → requirement proposal and engineering review → supplier proposal and engineering approval → routine evidence proposal and inspector approval → purchase and shipment decisions → two distinct role approvals → simulator artifacts. This verifies API integration, not real Apertus inference. No external model call, PostgreSQL execution, Temporal worker execution, or external release was claimed.

## Initial findings — all resolved on re-review

### BR-01 — P1: resetting the demo permanently deletes an issued artifact

**Location:** `service.py::Service.release`, `Service.reset`, `Service._mutate`; `api.py::artifact`.

Release stores the only copy of the artifact inside the current package's decision. Snapshots are inserted only when engineering content changes; creating, approving, and releasing a decision do not change that content hash. Reset clears the entire decisions list. Consequently an immediately reset release has neither a current artifact nor an artifact in historical snapshot storage, and its previously valid artifact URL becomes unavailable.

**Reproducer:** approve the three demo requirements; prepare Helvetic purchase; approve as distinct engineer/commercial actors; release; call `reset` before any further content mutation; inspect `packages` and every `package_snapshots.state`.

**Observed:** current decision count `0`; historical snapshot count `4`; total persisted artifacts `0`.

**Required behavior:** issued artifacts remain immutable and retrievable independently of resetting or changing current package state. An append-only artifact record keyed by project/decision is appropriate; retrieval must not depend on finding the decision in the current package.

### BR-02 — P1: live decisions silently use the synthetic delivery deadline

**Location:** `service.py::Service.__init__`; `fixtures.py::demo_package`; `domain.py::compare_options`.

The live package is initialized from `demo_package()` and clears documents, requirements, suppliers, and evidence, but retains `required_delivery_week=24`. No live source supports that number and no current API operation configures it. Every imported supplier is therefore evaluated against a synthetic commercial constraint, despite the live empty-project presentation.

**Reproducer:** `Service('sqlite:///.../live.db', mode='live').get('demo')['required_delivery_week']` returns `24` with an empty documents list. A supplier delivering week 30 is treated as delayed even if the actual customer source permits week 40; a week-24 supplier can pass even if the actual deadline is week 20.

**Required behavior:** a live delivery milestone must be an explicitly reviewed, source-bound input. An unknown milestone must remain unknown and block the relevant release until configured; it must not inherit a fixture default.

### BR-03 — P2: ordinary evidence correction cannot unblock shipment

**Location:** `service.py::Service.approve_proposal`, `Service._gate`, `Service.correct_demo`.

The normal extraction/proposal workflow can add a corrected FAT but cannot mark the old report superseded. `_gate` rejects any active contradictory report. The only operation that supersedes evidence is `correct_demo`, which is intentionally unavailable in live mode. A live project that admits one wrong-revision report cannot recover through its ordinary API.

**Reproducer:** approve the demo requirements; upload a corrected revision-B Helvetic report; add and inspector-approve it through `add_proposal`/`approve_proposal`, with all measurement refs pinned to the uploaded report; request shipment. This is the same normal evidence path used in live mode.

**Observed:** Helvetic evidence statuses become `['contradicted', 'supported']`; shipment still raises `Applicable acceptance evidence is missing, contradictory or for the wrong equipment revision.`

**Required behavior:** an inspector should be able to explicitly replace an identified prior report for the same supplier, retaining its historical record and invalidating affected approvals. Do not silently ignore arbitrary contradictory evidence.

### BR-04 — P2: type-report approval has no reachable workflow; missing family can pass the domain check

**Location:** `models.py::Evidence.approved_family_coverage`; `service.py::Service.approve_proposal`; `domain.py::assess_evidence`.

`Evidence.approved_family_coverage` is correctly restricted to `Literal[False]` for model output, but no human operation can change it. Approving a type-report proposal leaves it false forever, so type evidence can never become applicable through the API. Conversely, directly supplying the approval flag to the domain function allows absent family identity to pass when both report and supplier have `family=''`.

**Reproducer:** validate a type report with `approved_family_coverage=True`: Pydantic rejects it; validate/approve with false: assessment remains unknown. Independently, use matching configuration/revision, empty family on both records, and `approved_family_coverage=True`: `assess_evidence` returns `supported`.

**Required behavior:** keep model output unable to self-approve coverage; add an explicit attributable human family-coverage review, with the role required by the engineering-review policy. Require nonempty, matching family identity before coverage approval can produce support.

### BR-05 — P2: FAT measurement provenance points to supplier guarantees

**Location:** `fixtures.py::demo_package` evidence construction; `service.py::Service.correct_demo`.

Each demo evidence record assigns `measurements=s['facts']`, so measurements cite the supplier offer, not the FAT. The corrected report copies those same measurements and changes only the evidence-level source IDs. It can establish shipment applicability while the supporting measurement pins still point to commercial guarantee text. The synthetic designation does not make the source-binding demonstration accurate.

**Reproducer:** inspect corrected Helvetic evidence's `measurements[*].source_ids` after `correct_demo`. They remain `helvetic-offer:2`/`helvetic-offer:3`, while evidence-level source IDs refer to `fat-helvetic-b`.

**Required behavior:** each measurement must pin to the actual test-result span, and corrected measurements must cite the corrected report. The test record also does not state every copied supplier fact, such as the ONAF rating; omit claims that are not in that report. Existing source references are necessary but do not alone demonstrate that a span supports a measurement.

### BR-06 — P2: the witness generator gives the wrong answer for a maximum rating

**Location:** `domain.py::witness_for`; `service.py::Service.review`.

The witness generator assumes every ONAN rated-power requirement is a minimum and always sets `expected=False`. The schema also admits `operator='le'`. For a maximum of 25 MVA ONAN, the generated 20-MVA-without-fans example satisfies the encoded requirement, but the review endpoint requires the engineer to answer false.

**Reproducer:** copy the demo rated-power requirement and set `operator='le'`; `witness_for` asks whether 20 MVA without fans and 25 MVA with fans satisfies it, with expected false. `assess_requirement` on a 20 MVA ONAN supplier returns `supported` for the same requirement.

**Required behavior:** generate a witness only for supported operator/property combinations, or derive its expected answer by evaluating the actual encoded requirement. Do not force an incorrect human answer to complete approval.

### BR-07 — P2: malformed model quantities escape the abstention boundary

**Location:** `models.py::Fact.finite`; `integrations.py::Apertus.extract` and `Apertus._call`.

`Decimal(v)` raises `decimal.InvalidOperation` for text such as `garbage`. Pydantic does not convert this exception into `ValidationError`, and the extraction handler does not catch it. A model can therefore return a valid JSON envelope with an invalid decimal string and cause an unhandled HTTP 500 rather than the specified structured unavailable/abstention response. No claims were saved in the reproducer, so this is an error-handling/availability defect rather than an approval bypass.

**Reproducer:** make the mocked obligation-mapper response contain a candidate with `value='garbage'` and otherwise valid fields/source references; call `Apertus.extract`.

**Observed:** `InvalidOperation`, not `ModelUnavailable`. `Fact.model_validate(...)` reproduces the same exception directly.

**Required behavior:** translate decimal parse errors into ordinary schema validation failures. Validate the entire model response envelope and audit structure so null/wrong-type output cannot similarly escape as `TypeError`.

### BR-08 — P2: evidence assessment silently approves unreviewed criteria

**Location:** `domain.py::assess_evidence`, specifically the call to `assess_requirement({**r, 'status':'approved'}, measured)`.

Evidence assessment replaces every requirement's actual review state with approved. A matching report therefore appears supported even while all criteria are pending, and the same occurs for rejected interpretations. Purchase/shipment creation is still protected by `compare_options`, so this is a false assessment shown to the reviewer rather than a release bypass.

**Reproducer:** start from the untouched demo, change the Helvetic evidence revision to B, and call `assess_evidence` with the three pending requirements.

**Observed:** requirement states are `['pending', 'pending', 'pending']`, evidence result is `supported`.

**Required behavior:** preserve the actual review states; criteria that are not approved must not yield a supported acceptance judgment.

### BR-09 — P2: uploaded image sources cannot be retrieved for human inspection

**Location:** `integrations.py::parse_document`; `api.py::upload` and `api.py::project`.

Image parsing creates a single placeholder-text span and preserves the actual image as `image_data_url`. Both upload and project responses strip that field. Original bytes are written to private runtime object storage, but the reviewed API has no authenticated document-content endpoint. After a reload, the workbench can show only the placeholder, despite requiring human review of visual model proposals.

**Reproducer:** upload a PNG/JPEG; inspect the successful upload response and subsequent project response. Neither contains image bytes or a usable source-content URL; the only span says visual engineering review is required.

**Required behavior:** expose the immutable original through an authenticated, project-scoped source endpoint or equivalent authorized preview. Verify that the UI can display it before claiming image-based review is complete.

## Scope limits and specification gaps

- The milestone comparison and full-package invalidation are explicitly approved MVP rulings. A general CPM engine, selective incremental recomputation, real ERP publication, and the twenty-extension roadmap are not required fixes for this review.
- Only source-ID membership is mechanically checked for model proposals. This cannot prove that a cited passage actually entails a value. Human review remains essential; the current architecture appropriately requires it before extracted requirements/suppliers/evidence enter release decisions.
- The existing suite covers the authored demo well but does not prove PostgreSQL locking, durable Temporal execution, PDF parsing with installed Docling resources, or real Apertus endpoint behavior. These are verification gaps, not evidence of defects by themselves.
- The extraction instruction omits obligations that cannot be faithfully encoded. The UI/report must describe the bounded encoded scope and avoid claiming whole-document completeness. This review does not require support for arbitrary unmodeled obligations.

## Remaining verification limits

No reviewed finding remains open. Actual deployed model quality, PostgreSQL transaction behavior, durable Temporal worker behavior, and PDF/OCR behavior depend on their real runtime prerequisites and are not established by this review's SQLite and mocked-transport results. The parent task owns those deployment checks. The twenty-extension roadmap, general CPM scheduling, selective incremental recomputation, and external ERP publication remain outside the approved launch scope.
