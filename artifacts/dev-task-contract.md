# Development Task Contract

Use this contract when PM Copilot turns a review-ready PRD into implementation tasks.

`dev-tasks.yaml` is a machine-readable engineering handoff artifact. It is optional by default and should be generated when the user asks for development handoff, unattended task planning, issue creation, or implementation planning after PRD review.

## Required Fields

```yaml
run_id: ""
source_prd: "prd.md"
handoff_status: "" # ready | blocked | draft
generation_mode: "" # human_confirmed | unattended_candidate
blocking_summary: []
assumptions: []
tasks:
  - id: "" # T1
    title: ""
    type: "" # frontend | backend | data | analytics | qa | docs | release | design
    priority: "" # P0 | P1 | P2
    owner_role: ""
    source_requirements: [] # R/F/AC IDs from PRD
    description: ""
    affected_surfaces: []
    likely_files: []
    dependencies: []
    acceptance_criteria: []
    validation_commands: []
    risks: []
    blocked_by: []
    ready_for_issue: false
release_notes:
  user_visible_change: ""
  migration_or_rollout_note: ""
  rollback_note: ""
```

## Rules

- Tasks must trace back to PRD requirement IDs, function IDs, or acceptance criteria IDs.
- Do not create implementation tasks for optional or future scope unless the task is explicitly marked blocked or future.
- If engineering-blocking confirmations remain open, `handoff_status` must be `blocked` or `draft`, and each affected task must list `blocked_by`.
- A task is `ready_for_issue: true` only when it has source requirements, acceptance criteria, dependencies, likely surface/files, validation commands, and no unresolved blocker.
- Validation commands should prefer `scripts/run_delivery_checks.py` for full package checks and more specific project commands for implementation-level checks.
- Separate frontend, backend, data, analytics, QA, docs, and release tasks instead of mixing them into one vague item.
- For repo-backed runs, include likely files or modules from the host repository. If files are unknown, state the missing context in `blocked_by`.
- For privacy, payment, security, legal, compliance, financial, or regulated-content work, create explicit review or approval tasks and do not mark launch-sensitive tasks as ready without approval evidence.

## Quality Bar

- Engineering can create issues from the tasks without rereading the entire PRD.
- QA can see which validation command or manual check belongs to each task.
- Blocked work is clearly separated from ready work.
- The artifact does not imply that implementation has started or that code has been changed.
