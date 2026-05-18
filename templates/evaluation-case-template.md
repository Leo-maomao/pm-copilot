# Evaluation Case: <Scenario Name>

## Metadata

| Field | Value |
|---|---|
| Case ID |  |
| Scenario |  |
| Platform | Web / H5 / App / Mini Program / Cross-platform |
| Product Area |  |
| Created |  |
| Last Updated |  |

## Raw Request

```text
Paste the original realistic product request here.
```

## Context Files

- `context/product-context.local.yaml`

## Expected Workflow

- Discovery and clarification
- PRD
- Metrics and tracking sections inside PRD
- Flow diagrams inside PRD, when useful
- Prototype
- Delivery check

## Required Artifacts

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/prototype-<platform>.html`
- `outputs/<run-id>/run-log.yaml` when trace is useful
- Optional exports such as `tracking-plan.csv` or `user-flow.mmd` when useful

## Known Risks

- 

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Delivery | 20 / 28 |
| PRD | 31 / 40 |
| Metrics and tracking | 21 / 28 |
| Prototype | 24 / 32 |
| Delivery review inside PRD | 15 / 20 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|

## Pass Criteria

- The agent asks or records high-impact clarification questions.
- The agent stops before downstream generation when must-answer questions remain open.
- The agent stops before `Ready for engineering` when engineering-blocking confirmations remain open, unless the user explicitly asks for a draft with confirmation risk.
- PRD status, engineering handoff status, and launch status are recorded separately.
- Launch-only blockers do not get hidden behind `Ready for engineering`; they remain visible with owner and required confirmation.
- `prd.md` and prototype are generated after the clarification gate passes.
- Assumptions are explicit.
- Confirmed MVP scope is separated from optional, conditional, and future scope.
- Surface entry, navigation visibility, permission or eligibility states, and fallback behavior are explicit for existing-product changes.
- Reference or regulated content records source status, review owner, review status, disclaimer status, and launch impact.
- Tracking plan avoids forbidden sensitive properties.
- Tracking plan marks proposed taxonomy when no existing analytics convention was loaded.
- Prototype matches selected platform.
- PRD and prototype agree on scope, logic, interactions, tracking, and blockers.
- Review findings include artifact, evidence, owner, required-before phase, and status, or an explicit no-finding summary.
- Validation results are concrete and consistent between PRD and run log.

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pass / Fail / Partial |
| Notes |  |
