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
- Metrics tree
- Tracking plan
- User flow
- Prototype
- Review checklist
- Final package

## Required Artifacts

- `outputs/<run-id>/task-brief.md`
- `outputs/<run-id>/clarifying-questions.md`
- `outputs/<run-id>/assumptions.md`
- `outputs/<run-id>/pm-package.md`
- `outputs/<run-id>/prototype-<platform>.html`
- Optional exports such as `tracking-plan.csv` or `user-flow.mmd` when useful

## Known Risks

- 

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

## Pass Criteria

- The agent asks or records high-impact clarification questions.
- The agent stops before downstream generation when must-answer questions remain open.
- The agent stops before `Ready for engineering` when pre-development or pre-launch confirmations remain open, unless the user explicitly asks for a draft with confirmation risk.
- All required artifacts are generated after the clarification gate passes.
- Assumptions are explicit.
- Tracking plan avoids forbidden sensitive properties.
- Prototype matches selected platform.
- Review checklist catches remaining blockers.

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pass / Fail / Partial |
| Notes |  |
