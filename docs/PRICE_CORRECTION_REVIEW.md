# Audited supplier price correction

An engineer can correct the price and currency of a **pending supplier proposal** after inspecting its original source. This is a human review action; it is not a change to the document, extracted text, raw inference trace, or model evaluation result.

`POST /api/projects/{pid}/proposals/{proposal_id}/correct-price` accepts:

```json
{
  "snapshot_hash": "<current package SHA-256>",
  "price_cents": null,
  "currency": null,
  "source_id": "<existing span in this proposal's document>",
  "reason": "<explanation of the original-source review>"
}
```

Both commercial fields must be explicit. `price_cents` is an integer from 0 through 100000000000000, or null; booleans, strings and fractional values are rejected. Currency is USD, CHF, EUR, or null. Amount and currency may independently remain unknown. The reason must contain 1–2000 characters after trimming. The server records the selected source's document and page; the source must belong to the proposal's exact document, not merely share an ID prefix.

The source link records where the reviewer looked. It does not automatically prove that a handwritten amount was read correctly. Reviewers must inspect the original document when extracted text is unreliable. This action changes only the top-level commercial price and currency; original model facts remain unchanged and still require review.

The response is the updated proposal. Its `original_data` captures the complete proposal data before the first correction and remains unchanged through later corrections. Its `price_corrections` list is ordered oldest first; each entry contains `id`, `at`, `actor`, `document_id`, `source_id`, `page`, `reason`, `before`, and `after`. The last two objects contain the price and currency. The inference `trace` is unchanged. Project JSON exposes this information.

Each correction changes the package snapshot, emits `supplier_price_corrected` audit information, and invokes the existing conservative decision invalidation. Earlier stored snapshots remain unchanged. The proposal stays pending; an engineer must separately call the existing approval action. The correction itself grants no approval. Existing purchase release approval rules remain in force. Approved or non-supplier proposals cannot be corrected through this endpoint.

On subsequent approval, the supplier retains `proposal_id`, `original_data`, and `price_corrections`. Exported simulator decision packets therefore contain the manual provenance alongside the preserved proposal trace. A missing amount or currency remains conditional even after proposal approval and prevents a purchase decision.

## Verification

`track_2b/tests/test_price_corrections.py` contains isolated software QA cases for authentication, project membership, role restrictions, stale snapshots, exact document membership, request bounds, null handling, raw-data/trace preservation, repeated corrections, audit integrity, immutable prior snapshots, independent approval, decision invalidation, and exported provenance. Constructed test records are never application data or model-performance evidence.

Focused command:

```text
.venv/bin/python -m pytest track_2b/tests/test_price_corrections.py track_2b/tests/test_supplier_batches.py track_2b/tests/test_service.py track_2b/tests/test_api.py -q
58 passed in 3.15s
```

Full backend check: `.venv/bin/python -m pytest -q` — **153 passed in 10.42s**. No live database, source records, model calls, or running services were modified for this change.
