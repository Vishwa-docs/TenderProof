# Unknown configuration independent review

Reviewed 2026-10-15. Scope: nullable supplier/evidence configuration, extraction validation, release eligibility, preservation through approvals and exports, and the focused regressions. Only isolated software-QA data was used; no live database, network, model, or host operation was performed.

## Finding

**UC-01 — P2: null configurations can receive an affirmative type-family coverage approval.** `Service.approve_proposal` checks configuration and revision equality but not their presence before setting `approved_family_coverage=True` (`track_2b/src/tenderproof/service.py:280–283`). With the newly nullable schemas, a supplier and type report can both have `configuration=None`; their equality passes this guard when family and revision match. An inspector's explicit coverage confirmation then persists an affirmative coverage flag despite the API's requirement for a matching, nonempty configuration.

Confirmed through the public service methods in a temporary SQLite database: approve a supplier proposal with null configuration, add a type report with null configuration and matching family/revision, then approve it with `family_coverage_confirmed=True`. The resulting evidence has `configuration: null` and `approved_family_coverage: true`. Its applicability correctly remains `unknown`, so **this is an incorrect coverage-approval/audit state, not a purchase or shipment release bypass**. Require present, matching configuration and revision on both supplier and report before accepting explicit family coverage confirmation; retain ordinary approval for assessment without that confirmation.

Status: **resolved in scoped re-review on 2026-10-15.** The corrected guard (`track_2b/src/tenderproof/service.py:280–284`) requires nonempty and matching family, configuration, and revision on both sides before setting coverage. Independently inspected the seven added regression cases and ran `.venv/bin/python -m pytest -q track_2b/tests/test_unknown_configuration.py track_2b/tests/test_review_regressions.py track_2b/tests/test_api.py`: **43 passed in 2.96s**. Missing configuration/revision on the supplier, report, or both now rejects confirmation atomically, leaving the full package, audit and snapshot unchanged. Ordinary approval without coverage confirmation preserves unknown applicability; known matching identity still permits supported coverage. No unresolved finding remains in this scope.

## Verified behavior

- `Supplier.configuration` and `Evidence.configuration` accept omitted/explicit null values, and retain nonempty 1–120-character validation for present strings. The mapper's instruction to preserve unknown identity as null now agrees with both JSON schemas. No configuration label or identity is synthesized by the adapter.
- An otherwise feasible offer becomes conditional when configuration is missing. Contradicted/conflicting offers remain rejected, and known configurations retain their previous comparison behavior. Both decision creation and subsequent gate checks use this comparison. Evidence applicability also abstains when either configuration is missing.
- Controlled HTTP adapter tests preserve null in validated proposals and original archived model responses. The service regression preserves it through pending and approved supplier records and an immutable ERP-simulator packet for a different eligible supplier. Proposal approval does not grant release eligibility.
- Independently ran `.venv/bin/python -m pytest -q track_2b/tests/test_unknown_configuration.py track_2b/tests/test_domain.py track_2b/tests/test_service.py`: **47 passed in 1.42s**. The separate isolated UC-01 reproduction exposed the approval boundary not covered by those tests.

## Frontend null handling

After the frontend implementer confirmed this subset was stable, inspected `types.ts` (`Supplier.configuration` and `Evidence.configuration` are `string | null`) and the corresponding `App.tsx` render paths. Supplier comparison and gate selection display “Configuration unknown” for null; evidence retains its existing missing-value em dash. These are presentation fallbacks and do not replace the null stored in the proposal or supplier. Independently ran `npm test -- -t 'missing supplier configuration'` in `track_2b/src/web`: **1 passed, 29 skipped**, duration **1.25s**. No additional finding in this subset.

The source-preview feature is outside this review. Test results establish software behavior only, not model-extraction accuracy or physical equipment assurance.
