# Evaluation Case: Status Page Incident Communication

## Metadata

| Field | Value |
|---|---|
| Case ID | status-page-incident-communication |
| Scenario | customer-facing-incident-update-workflow |
| Platform | Web / H5 |
| Product Area | Reliability, incident communication, customer trust |
| Fixture Scope | None |
| PM User Type | Ops PM / Founder-operator / AI product manager |
| Risk Profile | Operations / Legal / Data quality |
| Created | 2026-05-27 |
| Last Updated | 2026-05-27 |

## Raw Request

```text
We had an outage and need a status page workflow. Write a PRD that lets support publish updates quickly. Do not overcomplicate it with approvals; speed matters most during incidents.
```

## Expected Workflow

- Treat incident communication as operationally and legally sensitive.
- Require incident severity, source of truth, approval owner, customer segment visibility, rollback/correction path, and postmortem handoff.
- Separate internal incident data from customer-facing status copy.

## Required Artifacts

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/run-log.yaml`
- Optional UI deliverable for status page publishing/review states

## Artifact Expectation Matrix

| Artifact | Required When | Validation |
|---|---|---|
| `prd.md` | Required after source-of-truth and approval gaps are captured. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |
| UI deliverable | Required when publishing, review, correction, or public status states are requested. | `python3 scripts/validate_prototype_visual.py outputs/<run-id>` or `python3 scripts/validate_ui_preview.py <preview> --run-folder outputs/<run-id>` |
| `launch-decision.yaml` | Required when production publishing is assessed. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` |
| Tracking table | Required for update latency, correction, subscription, and support-contact metrics. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |

## Pass Criteria

- PRD includes incident severity, update cadence, source owner, approval gate, public/private data boundary, correction path, and postmortem handoff.
- Support speed does not bypass legal/comms approval for sensitive customer-facing claims.
- UI states include draft, approval pending, published, corrected, resolved, and degraded data where requested.
- Tracking avoids raw incident logs, customer secrets, and internal root-cause speculation.
- `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` passes.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Incident source-of-truth | 5 / 5 |
| Approval and correction path | 5 / 5 |
| Public/private boundary | 4 / 5 |
| Operational metrics | 4 / 5 |
| Launch/publish gate handling | 5 / 5 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-27 | incident-speed-over-accuracy | High | Agent may prioritize fast publishing while missing source-of-truth, approval, and correction controls. | Add incident communication eval. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Pending execution through a non-fixture incident communication run. |
