# Evaluation Case: B2B Permission Audit Handoff

## Metadata

| Field | Value |
|---|---|
| Case ID | b2b-permission-audit-handoff |
| Scenario | workspace-role-bulk-permission-change |
| Platform | Web |
| Product Area | B2B SaaS administration and audit controls |
| Fixture Scope | None |
| PM User Type | Senior PM / Ops PM |
| Risk Profile | Security / Compliance / Operations |
| Created | 2026-05-27 |
| Last Updated | 2026-05-27 |

## Raw Request

```text
Our B2B workspace admins need to bulk update member roles before an enterprise audit. Please write the PRD and make it ready for engineering. We must avoid permission leaks, keep audit evidence, and have a rollback plan.
```

## Expected Workflow

- Classify the scenario as non-fixture, brief-only, security/compliance-sensitive B2B admin work.
- Generate a PRD with explicit permission matrix, audit, dry-run, preview, confirmation, partial failure, and rollback requirements.
- Generate `dev-tasks.yaml` with backend, frontend, audit, analytics, QA, and release tasks.
- Generate `launch-decision.yaml` that blocks launch until security/compliance approval and rollback ownership are confirmed.
- Run delivery checks.

## Pass Criteria

- `prd.md`, `run-log.yaml`, `dev-tasks.yaml`, and `launch-decision.yaml` exist.
- PRD separates PRD status, engineering handoff status, and launch status.
- Engineering tasks include source requirements, acceptance criteria, validation commands, owner roles, blockers, and `ready_for_issue`.
- Launch decision does not mark `ready_to_launch` without human confirmation.
- Audit log, least privilege, idempotency, dry-run preview, partial failure, rollback, and security approval are visible.
- `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` passes.

## Artifact Expectation Matrix

| Artifact | Required When | Validation |
|---|---|---|
| `prd.md` | Always required after the user asks for a PRD and engineering readiness. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |
| `run-log.yaml` | Always required to preserve blockers, approvals, and validation evidence. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |
| `dev-tasks.yaml` | Required because the user asks to make the package ready for engineering. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` |
| `launch-decision.yaml` | Required because permission changes, audit evidence, and rollback create launch gates. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` |
| UI deliverable | Not required unless the user separately asks for admin UI design. | Explicit not-applicable evidence in `run-log.yaml`. |

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Security and permission modeling | 5 / 5 |
| Engineering handoff quality | 5 / 5 |
| Launch gate correctness | 5 / 5 |
| Rollback and audit readiness | 4 / 5 |
| Validation evidence | 4 / 5 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-27 | handoff-artifact-gap | High | PM output can be reviewable while engineering tasks and launch gates remain too vague for execution. | Require dev-tasks and launch-decision artifacts for security-sensitive handoff scenarios. |

## Latest Result

| Field | Value |
|---|---|
| Run ID | b2b-permission-audit-handoff-20260527-1120 |
| Status | Passed |
| Notes | Non-fixture handoff run generated PRD, run-log, dev tasks, and launch decision. `python3 scripts/run_delivery_checks.py outputs/b2b-permission-audit-handoff-20260527-1120 --language en` passed. Launch remains blocked pending security/compliance approval. |
