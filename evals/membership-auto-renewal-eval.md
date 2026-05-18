# Evaluation Case: Membership Auto-Renewal Optimization

## Metadata

| Field | Value |
|---|---|
| Case ID | eval-001 |
| Scenario | membership-auto-renewal |
| Platform | H5 |
| Product Area | Subscription retention |
| Created | 2026-05-18 |
| Last Updated | 2026-05-18 |

## Raw Request

```text
We want to optimize membership auto-renewal because renewal conversion looks lower than expected. Please create a PRD and related review materials.
```

## Context Files

- `context/product-context.example.yaml`

## Expected Workflow

- Discovery and clarification
- PRD
- Metrics tree
- Tracking plan
- User flow
- H5 prototype
- Review checklist
- Final package

## Required Artifacts

- `outputs/membership-auto-renewal/clarifying-questions.md`
- `outputs/membership-auto-renewal/assumptions.md`
- `outputs/membership-auto-renewal/prd.md`
- `outputs/membership-auto-renewal/metrics-tree.md`
- `outputs/membership-auto-renewal/tracking-plan.csv`
- `outputs/membership-auto-renewal/user-flow.mmd`
- `outputs/membership-auto-renewal/prototype-h5.html`
- `outputs/membership-auto-renewal/review-checklist.md`
- `outputs/membership-auto-renewal/final-package-summary.md`

## Known Risks

- Legal copy for billing, cancellation, and refund policy must not be invented as final.
- Raw payment details must not appear in tracking properties.
- The flow must not hide cancellation access.
- Baseline renewal metrics are unknown and should remain open.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Package | 14 / 20 |
| PRD | 18 / 24 |
| Metrics and tracking | 15 / 20 |
| Prototype | 14 / 20 |
| Review checklist | 12 / 16 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
|  |  |  |  |  |

## Pass Criteria

- Clarifying questions ask for baseline metrics, legal copy, payment failure categories, channels, and region/payment scope.
- PRD includes visible cancellation and policy access.
- Tracking plan avoids raw payment data.
- H5 prototype is local, low fidelity, and interactive.
- Review checklist blocks launch until legal copy, baseline metrics, and payment failure categories are confirmed.

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pass |
| Notes | Initial curated output passes repository structure validation. |
