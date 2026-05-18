# Main Workflow

## Default Flow

```text
S0 Intake
-> S1 Context loading
-> S2 Discovery and clarification
-> S3 Assumption confirmation
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
| S1 Context loading | PM Orchestrator | Product context path is known | Relevant context is loaded and irrelevant context is ignored |
| S2 Discovery and clarification | Discovery Agent | Request is ambiguous or incomplete | Critical questions, assumptions, and open decisions are captured |
| S3 Assumption confirmation | PM Orchestrator | Clarification questions exist | User answers are applied or assumptions are explicitly accepted |
| S4 Optional research | Research Agent | External context is needed and tools are available | Source-backed research brief is produced or limitation is stated |
| S5 PRD drafting | Requirements Agent | Discovery output is usable | PRD contract is satisfied |
| S6 Metrics and tracking | Analytics Agent | PRD includes goals and user actions | KPI tree and tracking plan contracts are satisfied |
| S7 Flow and prototype | Prototype Agent | Core flow and platform are known | Mermaid flow and HTML prototype contracts are satisfied |
| S8 Review | Review Agent | Draft artifacts exist | Checklist, risks, and required fixes are produced |
| S9 Revision loop | PM Orchestrator | Review finds critical gaps | Artifacts are updated or gaps are accepted as open risks |
| S10 Final package | PM Orchestrator | Critical gaps are closed or accepted | Package summary and artifact index are complete |

## Human-in-the-Loop Checkpoints

Human confirmation is required when:

- The product goal or target user is unclear.
- Scope materially affects engineering effort, payment, privacy, legal, or compliance.
- The agent must choose between materially different product directions.
- The tracking plan includes sensitive properties.
- Research sources are unavailable but competitor claims would affect the solution.
- The final package contains high-severity open risks.

If the user does not answer, the agent may continue only with explicit assumptions and a visible risk note.

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
