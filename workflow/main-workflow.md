# Main Workflow

## Default Flow

```text
S0 Intake
-> S1 Context loading
-> S2 Discovery and clarification
-> S3 Clarification gate
-> S4 Optional research
-> S5 PRD drafting
-> S6 Metrics and tracking
-> S7 Flow and prototype
-> S8 Review
-> S9 Revision loop
-> S10 Final package
```

## State Definitions

| State | Owner | Entry Criteria | Exit Criteria |
|---|---|---|---|
| S0 Intake | PM Orchestrator | Task brief received | Request goal and artifact needs are identified |
| S1 Context loading | PM Orchestrator | Product context path is known | Relevant PM Copilot context and host project context are loaded |
| S2 Discovery and clarification | Discovery Agent | Request is ambiguous, incomplete, or needs project-fit validation | Critical questions, assumptions, and open decisions are captured |
| S3 Clarification gate | PM Orchestrator | Clarification questions exist or blocking assumptions are detected | User answers are applied, or the user explicitly accepts assumptions |
| S4 Optional research | Research Agent | External context is needed and tools are available | Source-backed research brief is produced or limitation is stated |
| S5 PRD drafting | Requirements Agent | Discovery output is usable | PRD contract is satisfied |
| S6 Metrics and tracking | Analytics Agent | PRD includes goals and user actions | KPI tree and tracking plan contracts are satisfied |
| S7 Flow and prototype | Prototype Agent | Core flow and platform are known | Mermaid flow and HTML prototype contracts are satisfied |
| S8 Review | Review Agent | Draft artifacts exist | Checklist, risks, and required fixes are produced |
| S9 Revision loop | PM Orchestrator | Review finds critical gaps | Artifacts are updated or gaps are accepted as open risks |
| S10 Final package | PM Orchestrator | Critical gaps are closed or accepted | Package summary and artifact index are complete |

## Human-in-the-Loop Checkpoints

Human confirmation is required before drafting downstream artifacts when:

- The product goal or target user is unclear.
- The current host project state is unknown and could change the proposed solution.
- Scope materially affects engineering effort, payment, privacy, legal, or compliance.
- The agent must choose between materially different product directions.
- Platform, affected module, primary user journey, or rollout surface is unclear.
- The tracking plan includes sensitive properties.
- Research sources are unavailable but competitor claims would affect the solution.
- The final package contains high-severity open risks.

If any must-answer question exists, stop after creating only:

- `examples/<run-id>/task-brief.md`
- `outputs/<run-id>/clarifying-questions.md`
- `outputs/<run-id>/assumptions.md`
- `outputs/<run-id>/run-log.yaml`

Do not create PRD, metrics, tracking, flow, prototype, review, or final package until the user answers or explicitly says to proceed with assumptions. User silence is not approval.

## Embedded Project Fit

When PM Copilot is used inside a host repository, the new requirement must fit the current product instead of assuming a greenfield product. Before S2 exits, capture:

- Existing product area or module likely affected.
- Relevant current behavior, routes, UI patterns, API contracts, data models, permission rules, and analytics conventions.
- Gaps between the user's requested change and the current implementation.
- Project constraints that should shape scope, rollout, migration, and acceptance criteria.

If the agent cannot determine the current product state from available files, ask for the missing context as must-answer questions.

## Run Folder Rules

Use `examples/<run-id>/` and `outputs/<run-id>/` for each requirement run. The run id is the scenario slug unless that folder already exists. For repeat or similar requirements, append a local timestamp such as `team-permissions-20260518-1430`.

Only update an existing run folder when the user explicitly names that folder or asks to revise the existing requirement.

## Language Rules

Use the user's language for conversation and generated artifacts. Chinese requests should produce Chinese PM outputs; English requests should produce English PM outputs. Keep file names, event names, and other machine-readable identifiers in ASCII.

## Skippable Steps

- Research can be skipped when the task does not need external evidence.
- Prototype can be reduced to a flow-only artifact when the request is purely backend, infra, or analytics.
- Tracking can be reduced when the task is a non-user-facing operational change, but the omission must be explained.

## Revision Rules

- Review findings with severity `Critical` or `High` must route back to the owning agent.
- Medium findings may be listed as review-time discussion points.
- Low findings may remain as optional improvements.

## Trace Format

```yaml
task_id:
current_state:
loaded_context:
agents_used:
skills_used:
tools_used:
artifacts_created:
assumptions:
open_questions:
human_confirmations:
guardrail_events:
review_result:
```
