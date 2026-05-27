# Evaluation Case: Membership Auto-Renewal Optimization

## Metadata

| Field | Value |
|---|---|
| Case ID | eval-001 |
| Scenario | membership-auto-renewal |
| Platform | H5 |
| Product Area | Subscription retention |
| Fixture Scope | None |
| PM User Type | Growth PM |
| Risk Profile | Payment / Legal |
| Created | 2026-05-18 |
| Last Updated | 2026-05-26 |

## Raw Request

```text
We want to optimize membership auto-renewal because renewal conversion looks lower than expected. Please create a PRD and clickable annotated UI deliverable.
```

## Context Files

- `context/product-context.example.yaml`

## Expected Workflow

- Discovery and clarification
- PRD
- Metrics and tracking sections inside PRD
- Flow diagrams inside PRD
- H5 UI deliverable
- Delivery review inside `prd.md`

## Required Artifacts

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/prototype-h5.html` as compatibility HTML because this brief-only case has no frontend source
- `outputs/<run-id>/run-log.yaml` when a persistent trace is useful
- Optional split source or export files only when useful

## Known Risks

- Legal copy for billing, cancellation, and refund policy must not be invented as final.
- Raw payment details must not appear in tracking properties.
- The flow must not hide cancellation access.
- Baseline renewal metrics are unknown and should remain open.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Delivery | 23 / 32 |
| PRD | 31 / 40 |
| Metrics and tracking | 21 / 28 |
| UI delivery | 24 / 32 |
| Delivery review inside PRD | 15 / 20 |

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
- H5 UI deliverable is local, clickable, annotated, and records compatibility-HTML boundary metadata when delivered as compatibility HTML without placing visible not-production labels in the product surface.
- Delivery review findings block launch until legal copy, baseline metrics, and payment failure categories are confirmed.
- PRD status is not `Ready for engineering` while required engineering-blocking billing or payment confirmations remain unresolved.
- PRD status, engineering handoff status, and launch status are separate.
- `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` passes for final artifacts.

## Latest Result

| Field | Value |
|---|---|
| Run ID | membership-auto-renewal-20260526-1804 |
| Status | Passed |
| Notes | Non-fixture brief-only run generated PRD, run-log, and compatibility H5 UI delivery. `python3 scripts/run_delivery_checks.py outputs/membership-auto-renewal-20260526-1804 --language en` passed with visual evidence. Engineering and launch blockers remain visible for legal copy, subscription/payment contract, and analytics taxonomy confirmation. |
