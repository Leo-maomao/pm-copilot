# Evaluation Case: Offline Sync Conflict Resolution

## Metadata

| Field | Value |
|---|---|
| Case ID | offline-sync-conflict-resolution |
| Scenario | field-ops-offline-edit-sync-conflicts |
| Platform | App / H5 |
| Product Area | Field operations, offline-first workflow, data reliability |
| Fixture Scope | None |
| PM User Type | Ops PM / Senior PM |
| Risk Profile | Operations / Data quality / Security |
| Created | 2026-05-27 |
| Last Updated | 2026-05-27 |

## Raw Request

```text
Field workers lose connectivity and need to edit records offline. Make a PRD for offline editing and sync. Keep it simple; conflicts are rare, so we can handle them later.
```

## Expected Workflow

- Treat offline conflict, idempotency, queue ownership, permission drift, and partial sync as core requirements rather than edge polish.
- Specify local queue, server version, merge policy, retry, cancellation, audit, conflict UI, and data-loss prevention.
- Block launch without backend contract, QA matrix, and operational support owner.

## Required Artifacts

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/run-log.yaml`
- UI deliverable when conflict or offline UI states are requested

## Artifact Expectation Matrix

| Artifact | Required When | Validation |
|---|---|---|
| `prd.md` | Required after offline data classes and conflict rules are captured. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |
| UI deliverable | Required when offline queue, conflict review, retry, or sync status UI is in scope. | `python3 scripts/validate_prototype_visual.py outputs/<run-id>` or `python3 scripts/validate_ui_preview.py <preview> --run-folder outputs/<run-id>` |
| `dev-tasks.yaml` | Required when implementation planning is requested. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` |
| Tracking table | Required for sync success, conflict, retry, and data-loss guardrails. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |

## Pass Criteria

- PRD covers offline create/edit/delete, sync queue, idempotency key, conflict detection, merge policy, permission drift, partial failure, and audit.
- UI states include offline, syncing, conflict, retry, stale permission, and success where UI is requested.
- Tracking records counts and categories, not raw record contents.
- Launch remains blocked without backend contract, QA matrix, and support playbook.
- `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` passes.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Conflict model | 5 / 5 |
| Idempotency and retry | 5 / 5 |
| UI state coverage | 4 / 5 |
| Data-loss prevention | 5 / 5 |
| Validation evidence | 4 / 5 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-27 | offline-edge-dismissal | High | Agent may accept "conflicts are rare" and omit core offline failure modes. | Add offline sync regression requiring conflict and idempotency coverage. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Pending execution through a non-fixture offline workflow run. |
