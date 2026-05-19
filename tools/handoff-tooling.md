# Handoff Tooling

Handoff tools turn a reviewed requirement into controlled engineering planning artifacts. They do not create issues or claim implementation by themselves.

## Development Task Export

Create `outputs/<run-id>/dev-tasks.yaml` when the user asks for:

- engineering handoff
- issue planning
- development tasks
- implementation breakdown

The file must follow `artifacts/dev-task-contract.md`.

## Required Evidence

Each task should include:

- source PRD requirement IDs
- likely ownership boundary
- likely files/modules in repo-backed mode
- acceptance criteria
- validation commands or manual checks
- unresolved blockers
- `ready_for_issue`

## Safety Rules

- Do not mark a task `ready_for_issue: true` when it depends on unresolved product, privacy, security, legal, compliance, analytics, content, or launch decisions.
- Do not claim Jira/GitHub issue creation unless the issue tool was actually called and recorded.
