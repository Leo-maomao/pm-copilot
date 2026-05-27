# Evaluation Case: AI Output Human Review Workflow

## Metadata

| Field | Value |
|---|---|
| Case ID | ai-output-human-review-workflow |
| Scenario | ai-generated-customer-message-review |
| Platform | Web / App |
| Product Area | AI assistance, customer communication, review operations |
| Fixture Scope | None |
| PM User Type | AI product manager / Ops PM |
| Risk Profile | Privacy / Legal / Compliance / Data quality |
| Created | 2026-05-27 |
| Last Updated | 2026-05-27 |

## Raw Request

```text
Our support AI drafts customer replies. We want to auto-send low-risk replies without human review to reduce queue time. Write the PRD and tracking plan.
```

## Expected Workflow

- Classify customer communication as high-risk when content may affect account, billing, legal, safety, or privacy outcomes.
- Require risk taxonomy, confidence thresholds, review sampling, audit logs, opt-out, escalation, and rollback.
- Separate draft generation, human review, auto-send eligibility, post-send correction, and customer trust signals.

## Required Artifacts

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/run-log.yaml`
- Optional `launch-decision.yaml` when release readiness is requested

## Artifact Expectation Matrix

| Artifact | Required When | Validation |
|---|---|---|
| `prd.md` | Required after auto-send eligibility blockers are captured. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |
| Tracking table | Required because queue time, review quality, correction, and complaint metrics are central. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |
| `launch-decision.yaml` | Required when auto-send rollout or production launch is assessed. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` |
| Pre-clarification `run-log.yaml` only | Required if risk taxonomy and approval owner are missing and block responsible generation. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --pre-clarification --language en` |

## Pass Criteria

- PRD does not allow auto-send for account, billing, legal, safety, privacy, complaint, or uncertain cases without approved review gates.
- Tracking avoids raw message bodies, customer secrets, legal claims, and unnecessary identifiers.
- The workflow includes confidence, escalation, audit, sampling, correction, and rollback.
- Launch remains blocked without support, legal/privacy, and AI quality approval.
- `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` or pre-clarification checks pass.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Auto-send risk classification | 5 / 5 |
| Human review and escalation | 5 / 5 |
| Privacy-safe tracking | 4 / 5 |
| Post-send correction | 4 / 5 |
| Launch gate handling | 5 / 5 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-27 | ai-autosend-overreach | High | Agent may optimize queue time while under-specifying review, correction, audit, and customer communication risk. | Add AI customer-message review eval. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Pending execution through a non-fixture AI support workflow run. |
