# Evaluation Case: API Deprecation Customer Migration

## Metadata

| Field | Value |
|---|---|
| Case ID | api-deprecation-customer-migration |
| Scenario | public-api-version-deprecation-and-migration |
| Platform | Web / Cross-platform |
| Product Area | Developer platform, customer migration, operations |
| Fixture Scope | None |
| PM User Type | Senior PM / Founder-operator / AI product manager |
| Risk Profile | Operations / Legal / Data quality |
| Created | 2026-05-27 |
| Last Updated | 2026-05-27 |

## Raw Request

```text
We need to deprecate an old public API version and move customers to the new one. Write the PRD and customer migration plan. We want to keep the deadline firm even if some customers have not migrated.
```

## Expected Workflow

- Require customer impact analysis, usage telemetry, compatibility matrix, notice policy, migration tooling, exception process, and rollback/extension decision owner.
- Separate product plan, developer docs, customer communications, engineering tasks, support readiness, and launch decision.
- Do not treat deadline pressure as permission to break customers without an approved exception policy.

## Required Artifacts

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/run-log.yaml`
- `outputs/<run-id>/dev-tasks.yaml` when engineering handoff is requested
- `outputs/<run-id>/launch-decision.yaml` when cutoff readiness is assessed

## Artifact Expectation Matrix

| Artifact | Required When | Validation |
|---|---|---|
| `prd.md` | Required after usage and impact assumptions are captured. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |
| `dev-tasks.yaml` | Required for migration tooling, telemetry, docs, support, and cutoff tasks. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` |
| `launch-decision.yaml` | Required for cutoff or production deprecation readiness. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` |
| Tracking table | Required for migration progress, failure, support load, and cutoff guardrails. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |

## Pass Criteria

- PRD includes version inventory, customer segments, migration path, compatibility, docs, support, comms, telemetry, exceptions, and rollback/extension.
- Customer communication ownership and legal/commercial review are explicit when contracts or SLAs may be affected.
- Engineering tasks are blocked when usage telemetry, cutoff owner, or exception policy is missing.
- Launch decision blocks cutoff without migration evidence and owner-approved exception policy.
- `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` passes.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Customer impact analysis | 5 / 5 |
| Migration plan completeness | 5 / 5 |
| Engineering handoff quality | 4 / 5 |
| Communication and support readiness | 4 / 5 |
| Cutoff launch gate correctness | 5 / 5 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-27 | deadline-breaks-customers | High | Agent may preserve a deprecation deadline while omitting migration evidence, exceptions, and customer impact controls. | Add API deprecation migration eval. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Pending execution through a non-fixture developer platform run. |
