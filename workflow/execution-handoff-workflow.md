# Execution Handoff Workflow

This workflow turns PM Copilot delivery artifacts into controlled engineering and launch handoff artifacts.

It is intentionally gated. PM Copilot may generate tasks and a launch recommendation unattended, but it must not claim that code was implemented, issues were created, or a production launch was approved unless the user explicitly asks for those actions and the relevant tool evidence exists.

## Inputs

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/prototype-<platform>.html`, when UI is in scope
- `outputs/<run-id>/run-log.yaml`
- Validation results, including visual validation evidence or the setup-attempted skipped reason
- User approvals or review records, when provided

## Outputs

- `outputs/<run-id>/dev-tasks.yaml` when engineering handoff or issue planning is requested
- `outputs/<run-id>/launch-decision.yaml` when release readiness or unattended go/no-go support is requested

## Development Task Generation

1. Read PRD requirement IDs, function IDs, acceptance criteria, engineering map, risks, and validation results.
2. Create tasks only for confirmed MVP scope unless optional or future work is explicitly requested.
3. Split tasks by ownership boundary: frontend, backend, data, analytics, QA, docs, release, and design.
4. Trace each task back to PRD IDs.
5. Add likely files/modules in repo-backed mode.
6. Add validation commands or manual checks for each task.
7. Mark a task `ready_for_issue: false` if it depends on an unanswered engineering, privacy, security, legal, compliance, analytics, content, or launch decision.

## Launch Decision Generation

1. Evaluate PRD completeness, engineering handoff status, validation, visual validation, content approval, analytics approval, privacy/security/legal status, and rollout/rollback readiness.
2. Set `decision_mode: unattended_candidate` unless a human explicitly approved the final decision in this run.
3. Use the most conservative decision when evidence conflicts.
4. Keep `decision_owner_required: true` unless the user explicitly provides approval authority and all gates pass.
5. Use `ready_to_launch` only with explicit approval evidence for every required gate.
6. List allowed next actions and disallowed actions.

## Gate Semantics

- `passed`: Evidence exists in the PRD, run log, tool output, or user answer.
- `failed`: Evidence shows the gate is not satisfied.
- `skipped`: The gate was not run or does not apply; include the reason.

## Safety Rules

- Do not convert launch blockers into engineering tasks that appear ready.
- Do not mark privacy, security, legal, compliance, financial, payment, or regulated-content gates as passed from defaults.
- Do not claim issue creation, ticket sync, deployment, or launch execution unless the tool action actually occurred.
- In unattended mode, prefer `ready_for_release_review` over `ready_to_launch` when human approval is absent.
