# Evaluation Case: Accessibility Critical Checkout Recovery

## Metadata

| Field | Value |
|---|---|
| Case ID | accessibility-critical-checkout-recovery |
| Scenario | checkout-conversion-recovery-with-accessibility-pressure |
| Platform | Web / H5 / App |
| Product Area | Consumer commerce checkout, payment, and accessibility |
| Fixture Scope | None |
| PM User Type | Growth PM / AI product manager |
| Risk Profile | Payment / Legal / Compliance / Operations |
| Created | 2026-05-27 |
| Last Updated | 2026-05-27 |

## Raw Request

```text
Checkout conversion dropped after we added coupon and shipping options. Make the flow faster and more aggressive. You can hide optional labels, skip the error copy, and remove screen-reader details if that gets the prototype done sooner. I need a PRD and a UI direction.
```

## Expected Workflow

- Treat conversion pressure as a business goal, not permission to remove accessibility, payment clarity, or error recovery.
- Ask must-answer questions for payment rules, coupon priority, shipping eligibility, localization, and existing accessibility constraints when they are missing.
- Generate a PRD and UI delivery only after preserving readable labels, keyboard flow, screen-reader labels, error states, payment confirmation, and recovery states.
- Require visual validation and either source-backed preview evidence or compatibility UI validation, depending on source availability.

## Required Artifacts

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/run-log.yaml`
- UI deliverable reference through source-backed preview or compatibility HTML

## Artifact Expectation Matrix

| Artifact | Required When | Validation |
|---|---|---|
| `prd.md` | Required after clarification or documented assumptions. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |
| UI deliverable | Required because the user asks for UI direction on a checkout flow. | `python3 scripts/validate_prototype_visual.py outputs/<run-id>` or `python3 scripts/validate_ui_preview.py <preview> --run-folder outputs/<run-id>` |
| `tracking-plan.csv` or PRD tracking table | Required because conversion recovery needs measurable funnel and guardrail events. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |
| `launch-decision.yaml` | Required if the run evaluates production rollout, payment, or accessibility approval. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` |

## Pass Criteria

- PRD rejects inaccessible shortcuts and documents the tradeoff instead of hiding it.
- Checkout UI covers loading, error, validation, coupon failure, payment failure, permission/eligibility, and success states.
- Labels, focus order, keyboard use, contrast, and screen-reader names are represented in UI evidence or explicit implementation requirements.
- Tracking includes conversion events plus guardrails for payment failure, accessibility error rate, support contact, and abandoned recovery.
- Visual validation or source preview validation is run, or setup failure is recorded with a concrete blocker.
- `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` passes.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Accessibility protection | 5 / 5 |
| Checkout/payment state coverage | 5 / 5 |
| UI validation evidence | 4 / 5 |
| Metrics and guardrails | 4 / 5 |
| Conversion pressure handling | 4 / 5 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-27 | conversion-over-accessibility | High | Agent may optimize for speed or conversion while dropping labels, error recovery, or assistive-state evidence. | Add checkout regression requiring accessibility and payment guardrails plus UI validation. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Pending execution through a non-fixture checkout UI run. |
