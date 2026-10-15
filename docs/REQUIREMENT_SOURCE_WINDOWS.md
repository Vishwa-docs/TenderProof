# Complete-source requirement windows

Added 15 October 2026 after discovery of the full 57-page GPA-070-25 invitation package. The earlier 100,000-character extraction guard could not accept its 122,962 embedded-text characters. The full original remains stored unchanged; windowing is only an inference-input strategy.

## Contract and bounds

`plan_extraction` deterministically covers every ordered original source span exactly once. IDs, page numbers and text are preserved; aliases map reversibly to the original IDs. Empty span text is retained. Invalid text, duplicate IDs or invalid page numbers reject the plan before a model call.

Requirement windows allow at most 48,000 source characters and 56,000 characters of compact serialized span payload. Consecutive spans belonging to the same page stay together whenever that page fits. An oversized page is split only between spans. An individual span that cannot fit is rejected explicitly; it is never truncated, selected away or silently split. The plan rejects more than 12 windows. These character limits reserve space for schema, interpretation, audit proposals and output within the intended model context; they are not an exact tokenizer-based guarantee for arbitrary languages or content.

A document fitting one window still uses one sequence of the existing four roles. Larger requirement documents run document interpreter, obligation mapper, evidence analyst and adversarial challenger for each window. Every request includes the selected equipment scope, original document identity/hash, total span/character counts, window index/count/pages and window source hash. Model instructions explicitly avoid claims of global completeness or consistency from local window context.

Supplier and evidence extraction retain their existing complete-document single-pass limit of 100,000 source characters. Larger input rejects explicitly. No supplier or evidence source is selected away to make it fit.

## Validation, aggregation and persistence

Each window's schema and citations are validated against that window's actual source IDs. A citation to an unseen span from a different window is rejected even if it exists elsewhere in the same document. All four roles must succeed in every window before any result is returned for persistence.

Requirement rows are deduplicated only when every validated field except `source_ids` is exactly equal. Their citations are unioned in first-seen order. Conflicting values, conditions or other field differences remain separate candidates. If merging would exceed the schema's 30-citation bound, separate rows are retained instead of losing references. This is not semantic reconciliation or a global consistency proof.

The direct API and Temporal persistence activity save the aggregate once using the existing transactional `add_candidates` path. Every candidate remains pending human review. A later-window failure yields no partial candidate save or snapshot update. The existing operation key keeps a repeated persistence activity idempotent.

## Durable plan, deadline and trace

Temporal dispatch reads the exact source snapshot, computes the plan and stores it in the workflow request. Inference recomputes the plan and rejects a mismatch before making calls. The captured activity deadline is:

`window_count × 4 × LLM_TIMEOUT_SECONDS + 120 seconds`

With the permitted 1–900-second per-call setting and maximum 12 windows, the inference deadline is at most 43,320 seconds. Inference has one activity attempt; persistence retains its separate short retry policy. Three windows at the default 300 seconds require 3,720 inference seconds; four require 4,920 seconds.

The existing UI waits synchronously; no polling or invented progress was added. After starting or attaching to a durable workflow, the API waits for its result for at most the planned inference budget plus 240 seconds, allowing time for the three short persistence attempts. This is at most 43,560 seconds. If that wait expires, the API returns a 503 containing the workflow ID and stops waiting; it does not call Temporal cancellation or termination. The workflow remains persisted and can finish. Refreshing the project can reveal its pending results; retrying the same unchanged extraction attaches to the same workflow. A 43,620-second gateway read allowance provides another 60 seconds beyond the maximum API result wait. Gateway configuration is deployment-owned. Connection/setup failures occur before this result-wait bound; local direct development mode has HTTP per-call timeouts but no durable workflow recovery.

The trace records original document SHA-256, the canonical hash of all original `[id, page, exact_text]` tuples, total spans/characters, all-source coverage, the actual window plan, planned call count/budget, workflow budget when applicable, and each window's offsets/pages/span count/hash, source map, role calls, issues and candidate count. Existing private per-call HTTP archives continue to contain actual requests/responses when enabled. Traces remain evidence of input coverage and observed calls, not proof that the model extracted every obligation correctly.

## Verification and limits

A read-only planner check used the actual complete local file `.runtime/sources/gpa-07025-full-ifb-amendment-i.pdf`, SHA-256 `a101432f314d0839c3d114779f42b03e7b08766476a78eb817074ea7d1f01d10`. PDFium returned 57 pages and 122,962 embedded-text characters. Representing each page as a native-text span produced three windows:

| Window | Original pages | Embedded-text characters |
| --- | --- | ---: |
| 1 | 1–40 | 45,272 |
| 2 | 41–51 | 41,887 |
| 3 | 52–57 | 35,803 |

This check made no model calls, did not run Docling/OCR and did not ingest or approve records. Actual Docling/OCR output may contain more text and require a different window count; the deployed planner computes that count from the stored spans.

Software regressions cover exact ordered span/character preservation in every role, empty spans, page-aware splits, oversized spans, more than 12 windows, malformed spans, duplicate IDs, invalid later windows, citations outside a window, safe exact deduplication, preservation of conflicting values, all-or-nothing API persistence, one pending atomic SQL batch with idempotent retries, and exact Temporal plan/deadline capture. HTTP responses in these regressions are controlled QA, never an Apertus evaluation.

Cross-window references and conflicts, extraction completeness, OCR correctness and unencoded narrative obligations still require human engineering review. Every original source remains available for that review. No general physical-equipment compliance or global independent proof is claimed.

Final verification: `make check` passed with **120 backend tests in 9.48 seconds**, **18 frontend tests in 4.64 seconds**, and the TypeScript/Vite production build in **1.51 seconds**. After adding the planned-budget trace fields, the backend suite was rerun: **120 passed in 9.26 seconds**. `git diff --check` and Python syntax compilation passed. No actual model inference, application-data mutation or Compose change was performed.

After adding the bounded API result wait, the final fresh backend run passed **121 tests in 8.39 seconds**, including a timeout case that verifies the started workflow is not cancelled or terminated and its ID is returned for recovery. The current deployment-owned files were read back with gateway `proxy_read_timeout 43620s` and model-relay `proxy_read_timeout 960s`; this review did not mutate those files or restart containers.
