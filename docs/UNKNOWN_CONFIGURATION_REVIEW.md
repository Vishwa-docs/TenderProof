# Unknown equipment configuration

The extraction instructions require unknown identity fields to remain null. Previously, the supplier and evidence schemas required a nonempty configuration string, so a faithful null response failed validation. Simply relaxing that schema would also have made an otherwise complete supplier offer eligible for purchase without identifying its equipment configuration.

The scoped fix changes two schema fields and one comparison guard:

- `Supplier.configuration` and `Evidence.configuration` accept explicit null or omission, defaulting to null. Present values retain their 1–120-character bounds; whitespace-only or overlong strings remain invalid.
- A supplier with unknown configuration cannot become feasible. An otherwise feasible comparison becomes conditional and explains that a source-supported configuration is required before release. Existing contradictory offers remain rejected.
- Evidence assessment already returns unknown when either selected-equipment or report configuration is missing. That behavior remains in place.

The adapter now preserves a faithful null without synthesizing a model name or equipment identity. Raw response traces retain the original content. Pending proposals and subsequently approved supplier records retain null. Proposal approval does not make such an offer eligible for purchase or shipment. A decision packet for a different eligible supplier can retain the unknown offer in its package snapshot without treating it as eligible.

This does not introduce an equipment-identity editing flow or alter approval roles. It does not infer supplier configurations from an awarded supplier, another bid, or model knowledge. No API or frontend implementation was changed in this scoped fix.

The initial scoped fix added 17 isolated software regression cases covering nullable/default schema behavior, present-value bounds, actual adapter validation with controlled HTTP responses, preserved response archives, acceptance/shipment abstention, purchase blocking, and preservation through proposal approval and package export. Known-configuration behavior is checked alongside missing configurations. These tests are not model-performance measurements and do not seed application data.

Focused verification:

```text
.venv/bin/python -m pytest track_2b/tests/test_unknown_configuration.py track_2b/tests/test_integrations.py track_2b/tests/test_domain.py track_2b/tests/test_service.py -q
70 passed in 2.36s
```

Full local suite after the initial change and independently reviewed lifecycle fix, before the UC-01 follow-up below: `.venv/bin/python -m pytest -q` — **219 passed in 16.54s**. No application data, model inference, or remote services were changed by these checks.

## UC-01: explicit type-family coverage must have known identity

Independent review found that equality alone accepted two missing configurations or revisions when an inspector requested `family_coverage_confirmed=true`. This incorrectly stored the coverage flag, although evidence assessment still remained unknown and release gates stayed blocked.

`Service.approve_proposal` now requires a type report plus nonempty, equal family, configuration **and revision on both the supplier and report** before recording explicit family coverage. Failure occurs before any evidence, proposal status, audit or package snapshot mutation. Null fields remain valid: the inspector may approve the report without confirming family coverage, and its applicability remains unknown. No new approval role or frontend/API flow was introduced.

Seven additional isolated regressions cover supplier-only, report-only and both-sided null configuration/revision, atomic rejection, subsequent approval without coverage, and known matching identity success. The test file now contains 24 cases. Both-sided null configuration and revision failed before this correction.

Focused recheck:

```text
.venv/bin/python -m pytest track_2b/tests/test_unknown_configuration.py track_2b/tests/test_review_regressions.py track_2b/tests/test_api.py -q
43 passed in 2.70s
```
