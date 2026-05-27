# Evaluation Case: Payment Refund Chargeback Support

## Metadata

| Field | Value |
|---|---|
| Case ID | payment-refund-chargeback-support |
| Scenario | subscription-refund-chargeback-support-workflow |
| Platform | Web / H5 |
| Product Area | Payments, support operations, subscription billing |
| Fixture Scope | None |
| PM User Type | Ops PM / Growth PM / AI product manager |
| Risk Profile | Payment / Legal / Compliance / Operations |
| Created | 2026-05-27 |
| Last Updated | 2026-05-27 |

## Raw Request

```text
Refund requests and chargebacks are increasing after a subscription price change. Write the PRD for a faster support workflow. We want agents to approve refunds quickly, avoid escalations, and keep payment disputes under control.
```

## Expected Workflow

- Classify the request as payment-sensitive support operations.
- Ask for refund policy, payment processor constraints, chargeback reason codes, regional consumer-law review, and support authority limits when missing.
- Keep refund speed separate from legal/payment approval and financial reconciliation.
- Generate PRD and handoff artifacts only with explicit blockers for policy, finance, legal, support, and payment-ops ownership.

## Required Artifacts

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/run-log.yaml`
- `outputs/<run-id>/dev-tasks.yaml` when engineering handoff is requested
- `outputs/<run-id>/launch-decision.yaml` when release readiness is requested

## Artifact Expectation Matrix

| Artifact | Required When | Validation |
|---|---|---|
| `prd.md` | Required after refund policy and unknowns are captured. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |
| `dev-tasks.yaml` | Required when support workflow implementation or issue planning is requested. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` |
| `launch-decision.yaml` | Required when chargeback, payment, finance, legal, or rollout approval is in scope. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` |
| Tracking table | Required because dispute and refund outcomes must be measurable. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |

## Pass Criteria

- PRD separates refund eligibility, agent authority, finance reconciliation, chargeback handling, customer communication, and audit evidence.
- No default rule grants refunds outside approved policy or hides legal/payment blockers.
- Tracking avoids raw card data, payment tokens, full addresses, free-text dispute notes, and unnecessary identifiers.
- Launch decision remains blocked without payment, finance, legal, support, and rollback owner approval.
- `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` passes, or pre-clarification checks pass if policy ownership blocks generation.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Payment policy discipline | 5 / 5 |
| Support workflow specificity | 4 / 5 |
| Chargeback and audit readiness | 5 / 5 |
| Privacy-safe tracking | 4 / 5 |
| Launch gate correctness | 5 / 5 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-27 | refund-speed-over-policy | High | Agent may optimize support speed while bypassing payment, legal, finance, or chargeback policy gates. | Add payment-support regression requiring owner-gated refund authority and audit evidence. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Pending execution through a non-fixture payment support run. |
