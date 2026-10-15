# Independent supplier price-correction review

Reviewed 15 October 2026 against `docs/PRICE_CORRECTION_REVIEW.md` and the current backend implementation. **No actionable correctness or authorization issue was identified within the reviewed backend change.** This is a scoped pass, not a whole-application security or engineering certification.

## Scope and assessment

- **Authorization and target:** the API retains bearer/project-membership checks; `Service.correct_supplier_price` independently requires the engineer role. Only pending supplier proposals qualify. Approved suppliers and evidence proposals are rejected. The actor comes from the server-owned identity.
- **Snapshot and source binding:** correction executes through the existing locked `_mutate` transaction and checks the current snapshot. The chosen span is found inside the proposal's exact document; an unrelated document's span cannot qualify by sharing an ID prefix. The audit entry captures the document, span and page.
- **Money and unknowns:** both commercial fields are mandatory in the request. Cents are strict integers in `[0, 10^14]` or null, so booleans, strings and fractional values do not become money. Currency is restricted to USD/CHF/EUR or null. Amount and currency can independently remain unknown; existing comparison and gate logic keeps either case conditional after separate approval. Reason/source bounds and forbidden extra fields are enforced.
- **Preserved model evidence:** only `data.price_cents` and `data.currency` change. First-correction `original_data` is copied once; subsequent corrections preserve it, prior audit entries, facts, and the inference trace. Each appended entry records actor/time/source/reason and before/after values. Correction does not create a supplier, approve the proposal, or release a decision.
- **Atomic invalidation and retained history:** proposal changes and correction history are included in the content snapshot. Audit recording, snapshot/version update, decision invalidation and package storage share the existing transaction. Failed validation/stale requests leave state unchanged. Existing snapshots and issued artifacts retain their prior contents. Separate proposal approval copies correction provenance into the supplier; exported simulator packets include that supplier and the preserved proposal trace.

Principal code reviewed: `models.py:76–80`, `service.py:236–261` and `270–298`, `api.py:134–137`, plus existing identity, transaction, comparison and immutable-packet code used by the new path.

## Verification and limits

Fresh focused command:

```text
.venv/bin/python -m pytest -q track_2b/tests/test_price_corrections.py
26 passed in 1.50s
```

Read every focused regression: authentication/project roles, stale snapshots, exact document membership, required fields and numeric bounds, independent null values, raw-data/trace preservation, repeated corrections, audit hashes, prior snapshot retention, separate approval, conservative invalidation, and exported provenance. The implementer's reported 153-test backend result was not rerun.

These tests use temporary isolated SQLite databases and explicitly constructed software-QA records. No live database, original source, model response, container, or production implementation was modified by this reviewer. Live PostgreSQL concurrency and the correctness of the three actual handwritten-price readings were not independently exercised. A valid source link records the review location; it does not prove that a human reading or OCR output is correct.

The frontend correction controls were still in progress and are **outside this verdict**. UI currency/amount entry, displayed provenance, and independent correction-versus-approval behavior require their own scoped check after that work is ready. This review does not certify physical equipment compliance or authorize an actual purchase; release remains an ERP simulator action.

## Frontend follow-up — 15 October 2026

**No actionable issue was identified in the completed correction UI change.** This follow-up extends the backend verdict above to the correction form, formatting/parsing helpers, proposal/supplier provenance types and rendering, shared mutation/source-download paths, and six new UI regressions. The earlier frontend exclusion is superseded for this scope.

- Correction controls render only with pending supplier proposals. The UI does not infer a role from a client-controlled value: the existing authenticated endpoint remains authoritative for engineer-only correction and project membership. The form expressly identifies this as an engineer's source-review action.
- `decimalCents` parses nonnegative decimal input with at most two fractional digits using `BigInt`, then converts only a safe integer to the JSON number. It does not multiply a floating-point decimal. Blank amount and blank currency become explicit independent nulls; known currency/unknown amount and known amount/unknown currency remain legible in correction history. The API still enforces its narrower `10^14`-cent maximum; values outside the server contract receive validation errors rather than being saved.
- The source selector and its validity check use only the proposal's `document_id`. Source inspection uses the chosen span, and original download uses that same document through the bearer-authenticated content endpoint. Saving requires a selected source and nonblank bounded reason; no corrected amount or source-reading claim is prefilled from QA reference data.
- Saving sends a snapshot-bound `correct-price` request only. The affected proposal's approval control is disabled while its draft is open. Successful save closes the form but leaves a separate approval action; a rejected request, including HTTP 409, retains the draft and surfaces the server error. No correction path invokes approval or release automatically.
- History is explicitly labeled manual, distinguishes original model price from before/after human edits, and displays actor, timestamp, source page, reason and source link. Approved supplier price cells retain the same provenance display. The UI neither rewrites the original source nor presents the manual value as a new inference result.

Principal frontend code inspected: `App.tsx:114–136`, `538–749`, `812–900`, and `1612–1619`; shared request/mutation and original-download helpers; and `types.ts` proposal/supplier/correction fields.

Fresh focused UI command from `track_2b/src/web`:

```text
npm test -- -t 'manual price|decimal|correction draft|corrected amount'
6 passed | 20 skipped (26), duration 7.64s
```

The six selected regressions cover sourced save/separate approval, invalid/blank amounts, exact 0.29-to-29-cent conversion, HTTP 409 draft preservation, approved-supplier history, and mixed-null history. The implementer's full 26-test run and TypeScript/Vite build were not repeated. No implementation, deployed bundle, container, live API record or source was changed; browser/deployment verification and the accuracy of actual handwritten readings remain parent-owned.
