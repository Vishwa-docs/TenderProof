# Final review fix report

Implemented 15 October 2026 against `docs/FINAL_CODE_REVIEW.md`. No commit was made. No Compose service, runtime application data, stored original, approval, decision or release was changed by this fix pass.

## FR-01 — report conditions: resolved

`domain.assess_evidence` now treats report-level conditions as constraints on every measurement. A measurement inherits any report condition it does not repeat. A different measurement-level value for the same key makes the report `conflicting`; it cannot override or erase the report condition. The resulting effective conditions must still match the approved criterion exactly. Missing conditions or an additional unmatched condition keep applicability `unknown`. Assessment does not mutate the stored report.

The original conflict reproduction was observed returning `supported`; the regression now requires `conflicting` and confirms the shipment gate raises `Conflict`. Separate cases cover inherited conditions, measurement-only conditions, consistent repeated conditions, incompatible report conditions, missing conditions, and extra scope.

The isolated QA fixture was corrected: cooling and loss temperature belong to its separate explicit measurements, as its constructed source states, and are no longer mislabeled as conditions applying globally to every measurement. No product or real source record was altered.

## FR-02 — partial PDF conversion: resolved

`integrations.parse_document` now retains Docling's `ConversionResult` and checks the installed `ConversionStatus.SUCCESS` enum before reading source items. `PARTIAL_SUCCESS`, `FAILURE`, `SKIPPED`, conversion errors even with a success status, and incomplete input/result/document page sets are rejected before persistence. Conversion is requested with `raises_on_error=False` so the adapter can return a controlled, bounded failure containing the actual status and page error information. The existing upload handler maps `ValueError` to HTTP 422.

At most five error summaries are used, error messages are limited to 160 characters each, control characters are normalized, and the total diagnostic detail is bounded. Successful documents retain `docling_status`, `docling_errors`, `converted_pages`, actual total page count, native-text supplement accounting, `pages_with_source_spans`, `pages_without_source_spans`, and `visual_review_required`.

Regressions use the installed Docling enum and controlled converter results; they do not run OCR or simulate Apertus. Partial/failure/skipped cases were observed being accepted with the status check bypassed, then rejected with the fix. Tests also cover status/error inconsistency, a missing page, and successful conversion metadata where one converted page has no extracted text. Blank/no-text page metadata is explicit and does not certify OCR or document interpretation completeness.

## Prototype and coverage wording

The gate area says **“Prototype release · ERP simulator”** and **“Checks cover reviewed encoded numeric requirements; unencoded obligations require engineering review.”** Requirement review and the new-gate dialog repeat the relevant scope boundary. The completion label now says “Encoded review complete.” No new approval flow or permission step was added.

`Service.release` retains `simulator=true` and its immutable packet now also states the encoded-numeric coverage limit, the need for engineering review of unencoded obligations, and that it does not certify physical equipment compliance. The existing idempotent release test checks that this wording survives in the exported packet.

## Scoped file changes

| File | Change |
| --- | --- |
| `track_2b/src/tenderproof/domain.py` | Inherit report conditions, reject conflicting overrides, preserve conservative matching |
| `track_2b/src/tenderproof/integrations.py` | Validate conversion status/errors/page coverage; retain success metadata |
| `track_2b/src/tenderproof/service.py` | Narrow exported-packet meaning clarification only |
| `track_2b/src/web/src/App.tsx` | Gate, requirement-review and completion wording |
| `track_2b/tests/support/fixtures.py` | Correct only the constructed report's condition scope |
| `track_2b/tests/test_domain.py` | Condition inheritance/conflict/missing-scope and shipment-block regressions |
| `track_2b/tests/test_pdf_conversion.py` | Five Docling boundary regressions; requires optional document dependencies |
| `track_2b/tests/test_service.py` | Exported scope boundary assertion |
| `track_2b/src/web/src/App.test.tsx` | Visible prototype/coverage boundary and completion-label assertions |

## Final verification

One final `make check` completed successfully after the fixes:

- Backend: **105 passed in 7.04 seconds**, no skips in this installed-document environment.
- Frontend: **18 passed**, Vitest duration **4.01 seconds**.
- Production build: TypeScript check and Vite build passed; **1,579 modules**, build **1.31 seconds**.
- `git diff --check`: clean.

These are software correctness checks using isolated QA inputs. No model-performance evaluation or new real inference was performed. Both reported defects are resolved in the reviewed code; no additional unresolved defect was identified in this scoped pass.

The four real PDFs were already ingested before the stricter conversion-result check existed. This fix does not retroactively assert their conversion statuses. Revalidation of those complete originals using the updated parser and deployment of the new code remain parent-owned. Existing page-span coverage and successful native-text preservation are narrower evidence than a retained successful Docling conversion result. No claim that all physical criteria or omitted narrative obligations are covered is made.
