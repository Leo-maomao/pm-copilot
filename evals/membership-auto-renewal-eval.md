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
- `outputs/membership-auto-renewal/pm-package.md`
- `outputs/membership-auto-renewal/prototype-h5.html`
- Optional split source or export files only when useful

## Known Risks

- Legal copy for billing, cancellation, and refund policy must not be invented as final.
- Raw payment details must not appear in tracking properties.
- The flow must not hide cancellation access.
- Baseline renewal metrics are unknown and should remain open.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Package | 17 / 24 |
| PRD | 21 / 28 |
| Metrics and tracking | 18 / 24 |
| Prototype | 21 / 28 |
| Review checklist | 12 / 16 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
|  |  |  |  |  |

## Pass Criteria

- Clarifying questions ask for baseline metrics, legal copy, payment failure categories, channels, and region/payment scope.
- PRD includes visible cancellation and policy access.
- Tracking plan avoids raw payment data.
- Tracking plan uses complete event and property tables.
- User flow renders as a standard Mermaid flowchart.
- H5 prototype is local, clickable, annotated, and clearly not production code.
- Review checklist blocks launch until legal copy, baseline metrics, and payment failure categories are confirmed.
- Package status is not `Ready for engineering` while required billing or payment confirmations remain unresolved.

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Needs rerun against consolidated package and confirmation-risk readiness rules. |
