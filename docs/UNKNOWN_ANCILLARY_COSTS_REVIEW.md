# Unknown ancillary amounts

`Supplier.expedite_cents` and `Supplier.rework_cents` now accept bounded integer cents or `null`, defaulting to `null` when omitted. This aligns the generated extraction schema with the existing instruction to preserve unknown commercial values. An explicitly supplied zero remains zero. No extraction prompt or real source record was changed.

The comparison's existing `total_cents` field is a **documented subtotal**, not a full-cost estimate. A known base price is added to whichever ancillary amounts are known. If the base price is unknown, the subtotal remains `null`; it never presents an ancillary-only sum as the offer price. Unknown expedite or rework amounts are named in the open conditions and make an otherwise feasible offer conditional. Both purchase and shipment gates therefore remain blocked. Technical rejection remains a rejection.

The interface displays `Unknown` for absent ancillary amounts and a formatted currency amount for an explicit zero. Unknown values remain null through validated model responses, pending proposals, supplier approval and immutable package exports. Approving a supplier proposal does not resolve missing commercial information or grant a release.

Validation uses isolated software tests only. The new regression file covers absent/null values, existing numeric bounds, zero and nonzero amounts, raw response archives, known-component arithmetic, blocked gates, approval persistence and export. The existing constructed successful-release test now explicitly states its zero ancillary amounts in both its test document and controlled response, rather than relying on implicit defaults. Real PDFs, source catalogs, runtime data and model evaluations are unchanged.

Focused checks: **61 Python tests passed in 0.82s** across ancillary-cost, domain and integration tests; **4 ancillary display tests passed**.

Full `make check`: **267 Python tests passed in 12.64s**, **33 UI tests passed** (9.10s command duration), and the TypeScript/Vite production build passed (Vite build 1.43s). Independent scoped review has been requested.
