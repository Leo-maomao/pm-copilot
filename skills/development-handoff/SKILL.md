---
name: development-handoff
description: Use when turning a PRD and prototype package into development tasks, issue-ready implementation slices, QA checks, and a controlled launch decision recommendation.
---

# Development Handoff

## Goal

Transform a review-ready PM Copilot package into engineering tasks and a launch decision-support artifact without hiding blockers or approvals.

## Workflow

1. Load `prd.md`, `run-log.yaml`, the prototype, and validation results.
2. Confirm the PRD status, engineering handoff status, launch status, and open review findings before generating tasks.
3. Follow `artifacts/dev-task-contract.md` for `dev-tasks.yaml`.
4. Follow `artifacts/launch-decision-contract.md` for `launch-decision.yaml`.
5. Split tasks by clear ownership: frontend, backend, data, analytics, QA, docs, release, and design.
6. Trace every task to requirement IDs, function IDs, or acceptance criteria IDs.
7. Include likely files/modules when repo-backed context is available.
8. Include dependencies, validation commands, migration or data-backfill notes, rollout notes, and rollback notes when relevant.
9. Mark blocked tasks explicitly instead of turning open decisions into ready work.
10. Do not create ready implementation work for optional or future scope unless the user requested it and the task is labeled future or blocked.
11. Evaluate launch gates conservatively.
12. In unattended mode, generate a recommendation or gate result only. Do not claim human approval.

## Output

- `outputs/<run-id>/dev-tasks.yaml`
- `outputs/<run-id>/launch-decision.yaml` when launch or release readiness is requested
- Blocked work summary when unresolved confirmations remain
- Optional issue text only when the user asks for issue creation or a platform-specific export

## Quality Bar

- A developer can create implementation issues directly from ready tasks.
- QA can see validation commands or manual checks per task.
- Launch-sensitive blockers remain blockers.
- Task IDs are stable and source requirements remain traceable after issue export.
- `ready_to_launch` is only used when explicit approval evidence exists for every gate.
- Unattended output remains a decision-support package, not an execution claim.
