# Agent Interface Contract

Every agent definition in this repository follows the same interface.

## Required Sections

- Purpose
- Responsibilities
- Inputs
- Outputs
- Completion Criteria
- Handoffs
- Failover, when applicable

## Output Rules

- Always distinguish facts, assumptions, and open questions.
- Never hide uncertainty.
- Return product judgment, not only files. Each agent should explain what it decided, why, what alternatives were rejected, and what should happen next.
- When an agent cannot complete a task, return the closest lower-fidelity artifact plus a limitation note.
- Preserve upstream decisions unless there is a clear contradiction.
- Use a stable output status on every handoff:
  - `complete`: the agent met its completion criteria.
  - `needs_input`: required human input blocks the next workflow state.
  - `blocked`: required context, approval, or tooling is missing and no lower-fidelity artifact is safe.
  - `degraded`: a lower-fidelity artifact was produced with an explicit limitation.
  - `failed`: the agent could not produce a usable output.
- Do not mark an output `complete` when required fields are unknown, validation placeholders remain, or the next agent would need to reverse-engineer missing context.
- Use stable machine codes in traces and localized human-facing wording in PRDs and UI deliverables.

## Runtime Protocol

Every agent response or internal handoff should be treated as an output envelope:

```yaml
agent:
status: complete # complete | needs_input | blocked | degraded | failed
confidence: "" # high | medium | low
facts:
assumptions:
open_questions:
decisions:
alternatives:
artifact_delta:
validation_delta:
risks:
next_actions:
action_closure:
handoff:
```

Rules:

- `facts` must cite the source path, user answer, or tool result when available.
- `assumptions` must include reason and risk. They are not facts.
- `open_questions` must use exactly one clarification classification from the workflow.
- `artifact_delta` must list files created, files changed, or explicitly state `none`.
- `validation_delta` must list commands run, skipped, or required later. Do not use vague placeholders.
- `decisions` must include evidence and tradeoffs for product-relevant choices.
- `alternatives` must note rejected paths when the choice affects scope, artifact mode, readiness, user experience, analytics, or launch.
- `next_actions` must identify the smallest useful follow-up for product, design, engineering, QA, analytics, launch, or memory.
- `action_closure` must turn the selected decision or blocker into an accountable critical path with owner, due phase, completion evidence, and status.
- Specialist agents may recommend readiness, but PM Orchestrator owns the final PRD, engineering handoff, and launch readiness fields.
- When two agents disagree, keep both positions visible and route the conflict to PM Orchestrator or Review Agent before final delivery.

## Mutation Boundaries

- PM Orchestrator owns final product judgment: task mode, autonomy level, selected path, rejected alternatives, final readiness labels, and final next actions.
- PM Orchestrator owns run id selection, workflow state, final readiness labels, and the final delivery check.
- Discovery owns clarification classification and current-state summary.
- Requirements owns PRD requirement content and acceptance criteria.
- Analytics owns metrics, event taxonomy status, event tables, and property dictionaries.
- UI Delivery owns flow/UI delivery fidelity, platform fit, interactions, states, and annotation mapping.
- Research owns source-backed facts, source limitations, and research confidence.
- Review owns findings, severity, required-before phase, and go/no-go recommendations.

An agent may not silently overwrite another agent's owned decision. It must record a proposed change, the reason, and the affected artifact or state.

## Exit Checklist

Before handoff, each agent checks:

- Required input sources are listed.
- Facts, assumptions, open questions, and decisions are separated.
- Output status matches the actual blocker state.
- Relevant artifact contract sections are either satisfied or explicitly limited.
- Readiness-impacting blockers name owner, required confirmation, and blocked phase.
- Product usefulness is explicit: the next reviewer can tell what decision the artifact supports and what work remains.
- Validation claims match commands actually run or skipped.
- No stale placeholders such as `pending`, `待执行`, `should run`, or `to be verified` remain in final delivery text.

## Handoff Payload

```yaml
from_agent:
to_agent:
status:
workflow_state:
task_goal:
inputs:
artifacts_available:
assumptions:
open_questions:
human_confirmation_required:
risks:
artifact_delta:
validation_delta:
decisions:
alternatives:
next_actions:
action_closure:
next_expected_output:
```
