# Final code review

Reviewed 15 October 2026 against `docs/superpowers/plans/tenderproof.md`, the current SDD ledger, `.superpowers/sdd/tenderproof-engineering/final-review.diff`, and current application source. This independent review changed no application code or live data.

## Findings

### FR-01 — P1: conflicting report conditions can support shipment

**Location:** `track_2b/src/tenderproof/domain.py:95–100`; shipment consumption at `track_2b/src/tenderproof/service.py:125–127`.

`Evidence.conditions` is accepted by the schema and displayed to the reviewer, but `assess_evidence` never reads it. It evaluates only each measurement's conditions. A routine report with matching configuration/revision/serial, report-level `temperature_c=85`, and a load-loss measurement labeled `temperature_c=75` therefore supports a requirement at 75°C. The shipment gate accepts that report despite its internally conflicting operating conditions.

**Observed reproduction:** using the existing constructed QA fixture entirely in memory, approve its criteria, match the report revision, and change only the report-level temperature to 85. `Evidence.model_validate` succeeds, `assess_evidence` returns `supported`, and `Service._gate(..., 'shipment')` returns without error. No model, database, runtime source, or release artifact was involved.

**Required correction:** define and enforce the relationship between report-level and measurement-level conditions. An explicit conflict must produce `conflicting` or `unknown`, never support; applicable report conditions must not silently disappear from the assessment.

### FR-02 — P2: partial PDF conversion is silently treated as complete input

**Location:** `track_2b/src/tenderproof/integrations.py:125–133`.

`converter.convert(path).document` discards the conversion status and errors. The installed Docling implementation explicitly permits `PARTIAL_SUCCESS` even with its default `raises_on_error=True`; a failed page backend can produce that status. The native-text supplement cannot recover content that exists only in a scanned image. Consequently a multi-page PDF with a failed scanned page can be ingested and passed to all four extraction roles with the failed page's clauses absent and no specific conversion-failure warning. The reported total page count does not establish successful extraction of those pages.

**Evidence:** inspected the installed Docling `document_converter.py:773–775` acceptance of partial success and `pipeline/base_pipeline.py:468–479` page-failure handling. This is a reachable error path established by code inspection, not an observed failure of the four GPA PDFs.

**Required correction:** retain and check the conversion result before accepting its document. Reject incomplete conversion or persist explicit page-level failure/coverage information and prevent it from being represented as fully parsed extraction input. Generic visual-review language does not identify a known failed page.

## Coverage and limits

- Read the typed schemas, numerical/evidence rules, source parsing and Apertus adapter, API authorization, transactional snapshot/approval/artifact storage, supplier-batch handling, Temporal activities/dispatch, MCP surface, and relevant workbench flows and regression tests.
- No additional server authentication/project-membership bypass, atomic supplier-batch defect, approval-role bypass, or mutable released-artifact path was identified in those inspected paths. This is not a comprehensive security certification.
- Existing reported results of 92 backend tests and 16 frontend tests/build were not rerun. The one focused reproduction above is software QA only and does not establish model quality or actual evidence applicability.
- No live Apertus inference, real supplier/evidence extraction, current PostgreSQL locking test, or current Temporal worker execution was performed by this reviewer. Persistence activity retries are guarded by a project-scoped operation key in the same SQL transaction; that code inspection does not establish live retry/failover behavior.
- The actual full GPA documents remain the only intended runtime sources. Missing equipment-specific FAT, serial number, and drawing revision must remain unknown. Neither finding supplies those missing facts or authorizes a live release.
- The completeness boundary is narrower than the original documents: `Candidate` encodes numeric facts, `Apertus.extract` explicitly omits obligations it cannot encode, and gates inspect only stored requirements. Approving every visible candidate does not establish extraction completeness, review of omitted narrative obligations, expert certification, or physical equipment assurance. This is an explicit scope limit, not a request to add an unapproved general engineering rules engine. Gate wording and exported packets must preserve that boundary; release remains an ERP simulator action only.
- The workbench agent's concurrent empty-state/layout adjustment and root-owned deployment/model provisioning were outside this review's changes.

## Scoped re-review verdict — 15 October 2026

**FR-01 and FR-02 are resolved in the inspected fix implementation. No new actionable defect was identified within these fixes.** The findings above remain the historical initial review. This re-review covers `docs/FINAL_REVIEW_FIXES.md`, the changed evidence-condition logic, PDF conversion-status/page-coverage boundary, exported-packet wording, workbench labels, and their targeted regression code.

- **FR-01:** `domain.py:95–103` now rejects contradictory values for the same condition key before assessing measurements. It merges report conditions into each measurement without modifying the original report; absent or extra unmatched conditions remain conservative under exact matching. The regression explicitly checks the original 85°C/75°C conflict and that the shipment gate raises `Conflict`. Additional cases cover inheritance, matching repeated conditions, missing conditions, and extra scope. The historical QA fixture correction changes only its constructed condition scope, not any actual source or runtime evidence.
- **FR-02:** `_checked_pdf_conversion` now requires `ConversionStatus.SUCCESS`, no conversion errors, and complete matching input/result/document page sets. `parse_document` invokes it before extracting source items and also checks the original PDF page count after native-text supplementation. Partial status cannot be silently accepted through Docling's default behavior. Verified the installed **Docling 2.139.0** schema directly: `ConversionResult` exposes the inspected status/errors/pages/document/input fields and `ErrorItem` exposes category/page number/message. Diagnostic output is bounded. Controlled boundary regressions cover partial/failure/skipped states, success with errors, missing pages, and explicit successful no-text-page metadata.
- **Scope labels:** requirement review, the gate area, and the new-gate dialog explicitly distinguish reviewed encoded numeric requirements from unencoded obligations. The gate UI identifies the ERP simulator before release. The immutable packet retains `simulator=true` and states that it does not certify physical equipment compliance. The relevant UI and packet regressions assert these boundaries.

The implementer reports a fresh **105 backend tests, 18 frontend tests, and production build passing** in `docs/FINAL_REVIEW_FIXES.md`; this reviewer inspected the regression code and did not rerun those suites. This verdict is code review, not new live inference, OCR-performance evidence, deployed verification, or engineering approval. Existing GPA ingestion predates the stricter conversion checks and requires parent-owned revalidation; successful page counts alone do not retroactively prove successful Docling conversion. Missing actual FAT/serial/drawing-revision evidence must still keep shipment blocked.

The separate in-progress requirement-windowing change prompted by the 122k-character source document is **outside this verdict**. No new windowing code, timing budget, or full-document inference behavior is approved by this scoped re-review.
