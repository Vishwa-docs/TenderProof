# Requirement source-window review

Independent scoped review, 15 October 2026. Contract: `docs/REQUIREMENT_SOURCE_WINDOWS.md`. Scope: `integrations.py` planning/window execution/aggregation, `workflows.py` plan/deadline/result waiting, their API persistence boundary, and targeted regressions. Previously accepted FR-01/FR-02 fixes were not reopened. No application data, containers, or production code was changed by this review.

## Findings

### RW-01 — P2: completed unchanged extractions restart instead of reattaching

**Location:** `track_2b/src/tenderproof/workflows.py:68–69`.

`Client.start_workflow` omits `id_reuse_policy`. The installed Temporal SDK defaults it to `ALLOW_DUPLICATE` for closed workflows; the existing exception branch therefore attaches only when a start is rejected, such as an already-running workflow. Consider a completed extraction returning no candidates, or only already-persisted candidates: its content snapshot remains unchanged. Retrying that exact request starts another run with the same workflow ID and executes all model windows again. Persistence then finds the existing `completed_operations` key and returns the earlier cached result. The retry can spend up to the entire multi-window inference budget while discarding the new inference, contrary to the documented completed-result recovery behavior.

**Evidence:** inspected the actual installed SDK default and its documentation in `temporalio/client/_client.py` (`start_workflow`, default `WorkflowIDReusePolicy.ALLOW_DUPLICATE`; closed-workflow policy description). `Service._mutate` deduplicates the persistence operation, not the preceding model calls. `add_candidates` with zero additions changes events but not the content snapshot.

**Correction boundary:** reject reuse of successfully completed executions so the existing handle can return their result, while retaining an intentional retry path for failed executions after an endpoint/configuration problem is repaired without source changes. `ALLOW_DUPLICATE_FAILED_ONLY` matches that distinction; blanket `REJECT_DUPLICATE` would also freeze failed-run recovery unless another explicit recovery mechanism is added. Cover both completed-result reattachment and failed-run recovery in the regression.

### RW-02 — P3: compact span payload can exceed its limit by one character

**Location:** `track_2b/src/tenderproof/integrations.py:41–46`.

The cost sum includes each compact span row plus one separator character, but a complete nonempty JSON array is one character longer than that sum because it also needs its outer brackets. A single span consisting of 27,994 quotation marks has 27,994 source characters and a computed row cost of exactly 56,000, so the planner accepts it. The actual compact serialized `source_spans` array is 56,001 characters, violating the explicit 56,000-character bound.

**Observed reproduction:** direct pure planner/JSON calculation returned `planner_row_cost=56000`, `actual_compact_span_payload=56001`, and one accepted window. No model call or persistence occurred. Account for the outer array when testing both individual spans and accumulated windows, and add an exact-boundary payload regression. This is a strict-bound error, not observed source loss or an approval bypass.

## Verification

- Fresh targeted command: `.venv/bin/python -m pytest -q track_2b/tests/test_requirement_windows.py track_2b/tests/test_workflow_budget.py` — **20 passed in 0.98 seconds**. Full suites/build were not rerun; the implementer's reported 121 backend tests and 18 frontend tests/build are separate evidence.
- Read the planner ranges, source hashes/global aliases, all four per-window calls, window-local source-ID validation, exact-field deduplication, and the single final persistence call. No additional source omission, cross-window citation acceptance, or partial-save defect was identified in those paths.
- Additional isolated HTTP-transport QA exercised citation overflow with 62 original citations across three windows: all 12 role calls completed, all 62 citations remained, and output rows contained 30, 30, and 2 citations. No semantic merging or lost source reference occurred.
- Additional controlled-handle QA used a real `asyncio.wait_for` deadline rather than a handle that immediately raises timeout. Only the local result waiter was cancelled; neither workflow cancellation nor termination was invoked, and the error included the workflow ID. Installed `WorkflowHandle.result` code was also inspected: it waits on history events and has no implicit workflow-cancel operation.
- Plan mismatch is checked before calls; dispatch captures the deterministic plan and its window-derived timeout; inference has one attempt and persistence remains separately retryable. API timeout leaves durable work available for recovery. The deployment-owned gateway allowance is 43,620 seconds against the maximum 43,560-second API result wait; intake timeout is 1,800 seconds.

These checks are software QA and code inspection only. They did not run actual Apertus, start a live Temporal workflow, reparse or upload the 57-page document, or establish live PostgreSQL/worker behavior. Complete source-span transmission is not proof of complete or correct obligation extraction, cross-window consistency, expert coverage, or physical equipment compliance. Missing actual acceptance evidence remains unknown and release remains an ERP simulator action.

## Scoped correction re-review — 15 October 2026

**RW-01 and RW-02 are resolved in the inspected implementation. No new actionable issue was identified in these corrections.** The findings above are retained as the initial review record.

- **RW-01:** `workflows.py:72–74` now explicitly uses `WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY` and attaches when Temporal reports an existing execution. Successfully completed unchanged extractions no longer restart inference, while a deliberate request after a failed run can start a replacement without changing source data. The failed execution's history remains available; inference activity automatic retries remain disabled. Reviewed the regressions for completed empty requirement/supplier results and explicit failed-run recovery.
- **RW-02:** `integrations.py:41–76` now includes the outer array in individual-span and accumulated-window size checks, recomputes actual compact payload length defensively, and records `source_payload_characters`. `_call` uses matching compact JSON serialization. The original quotation-mark reproducer is now rejected before inference. Reviewed the exact 56,000-character transport test across all four roles, the rejected 56,001-character individual span, and a two-span 56,001-character payload that splits while preserving all content.

Fresh reviewer verification: `.venv/bin/python -m pytest -q track_2b/tests/test_requirement_windows.py track_2b/tests/test_workflow_budget.py` — **26 passed in 1.19 seconds**. A separate pure planner invocation confirmed rejection of the original 56,001-character reproducer. The implementer's reported 127-test backend run and wider 50-test focused run were not repeated. These remain isolated software checks; no live workflow, application record, container, source upload, or production code was mutated during this re-review.
