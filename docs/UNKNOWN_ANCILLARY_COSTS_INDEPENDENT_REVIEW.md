# Nullable ancillary costs independent review

Reviewed 2026-10-15. Scope: `Supplier.expedite_cents` / `rework_cents`, comparison arithmetic and eligibility, the corresponding UI types/rendering, new ancillary regressions, and the two-line constructed successful-flow test adjustment. No application data, runtime, source document, model trace, or deployment was changed.

**Verdict: no actionable finding identified in this scoped delta.**

- Both schema fields now default to null and accept explicit null; present integer amounts retain the nonnegative, bounded-cent constraints. Explicit zero remains zero. The actual adapter includes this schema in the mapper instruction and validates responses through it, preserving null/zero in proposals and original response archives.
- With a known base price, the documented subtotal adds only known ancillary components. An unknown base leaves the subtotal null. Missing expedite/rework values are named in the open conditions and downgrade a feasible offer to conditional; existing technical rejection is retained. The common gate check requires feasibility at decision creation, approval and release, so proposal approval cannot bypass unresolved costs for purchase or shipment.
- Service approval copies the nullable fields unchanged. The focused persistence test preserves them in pending proposals, approved suppliers and an immutable ERP-simulator snapshot issued for a separate eligible supplier, while blocking a decision for the unresolved offer without changing package state.
- UI types accept `number | null`; the two render paths use null checks, displaying “Unknown” for absence and a formatted amount for explicit zero. The subtotal remains labeled as documented amounts rather than a full-cost estimate.
- The existing successful-flow test now states zero expedite and rework amounts in both its constructed test source and controlled model response. This removes reliance on the old implicit defaults without modifying real sources or weakening that test's release/schedule checks.

Independent focused verification:

- `.venv/bin/python -m pytest -q track_2b/tests/test_unknown_ancillary_costs.py track_2b/tests/test_domain.py track_2b/tests/test_live_flow.py`: **39 passed in 1.33s**.
- In `track_2b/src/web`, `npm test -- -t 'ancillary'`: **4 passed, 29 skipped**, duration **1.38s**.

No whole-suite rerun or broader review was needed. These isolated software tests do not establish the correctness of any live model extraction or modify previously stored records; the root agent owns deployment and actual-source verification.
