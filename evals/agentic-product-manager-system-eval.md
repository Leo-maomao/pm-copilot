# Evaluation Case: Agentic Product Manager System

## Metadata

| Field | Value |
|---|---|
| Case ID | agentic-product-manager-system |
| Scenario | Mixed PM delivery that requires goal framing, task-mode selection, product judgment, artifact creation, review, validation, next actions, and memory candidates |
| Platform | Cross-platform |
| Product Area | Product operations and launch readiness |
| Created | 2026-07-09 |
| Last Updated | 2026-07-09 |
| Fixture Scope | Public generic |
| PM User Type | AI product manager |
| Risk Profile | Operations / Data quality |

## Fixture Isolation Terms

- `<none>`

## Raw Request

```text
We are preparing a customer-facing change that adds bulk notification scheduling for account admins. I need the PM work, not just a template: inspect any available context, choose the right delivery mode, draft the PRD, include the tracking plan, review whether the scope is useful for engineering and launch, and tell me the next actions and what should be remembered for future notification work.
```

## Context Files

- `context/product-context.example.yaml`
- Optional host repository or user-provided notification docs when available

## Expected Workflow

- The agent classifies task mode as `mixed_delivery` or a justified combination of `prd_delivery`, `tracking_plan`, `launch_readiness`, and `dev_handoff`.
- The agent classifies autonomy level as `full-loop` unless must-answer information blocks generation.
- The agent records success criteria, selected path, skipped path, rejected alternatives, and replan triggers.
- The agent asks blocking questions if target user, product goal, notification channels, privacy/compliance, or launch constraints are materially unknown.
- When drafting is allowed, the agent creates PRD content that includes goals, scope, notification timing, recipient eligibility, abuse/fatigue controls, tracking, launch blockers, and review findings.
- The agent runs PM usefulness review before final delivery.
- The agent returns next actions and memory candidates.
- The agent runs `run_delivery_checks.py` or records why only pre-clarification validation applies.

## Required Artifacts

- `outputs/<run-id>/prd.md` after clarification gates pass
- UI deliverable reference only if user-facing scheduling UI is in scope
- `outputs/<run-id>/run-log.yaml`
- Optional `dev-tasks.yaml` or `launch-decision.yaml` when the run claims engineering handoff or launch readiness

## Artifact Expectation Matrix

| Artifact | Required When | Validation |
|---|---|---|
| `prd.md` | Clarification gate passes or user accepts draft risk. | `python3 scripts/validate_outputs.py outputs/<run-id>` |
| UI deliverable reference | Scheduling UI, preview, or interaction states are in scope. | `python3 scripts/validate_ui_preview.py <preview> --run-folder outputs/<run-id>` or `python3 scripts/validate_prototype_visual.py outputs/<run-id>` |
| `run-log.yaml` | Always for this eval. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` |
| `dev-tasks.yaml` | Engineering handoff is claimed. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` |
| `launch-decision.yaml` | Launch readiness or go/no-go support is claimed. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` |

## Agentic Expectation Matrix

| Field | Required Evidence |
|---|---|
| `task_mode` | Explicitly recorded in run log or final summary. |
| `autonomy_level` | Explicitly recorded as `full-loop`, `clarify-first`, or justified alternative. |
| Product judgment | Recommended path, confidence, blockers, and rejected alternatives are visible. |
| Review loop | PM usefulness review checks whether the artifacts help engineering and launch work. |
| Next actions | Concrete PM follow-ups with owner or phase. |
| Memory candidates | Durable notification facts or preferences are proposed, or explicitly marked none. |

## Known Risks

- The agent mechanically follows S0-S12 without stating why the path fits the goal.
- The output is format-complete but not useful for PM decision making.
- Launch, privacy, abuse, fatigue, or data-quality blockers are hidden behind a generic ready label.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Delivery | 23 / 32 |
| PRD | 31 / 40 |
| Metrics and tracking | 21 / 28 |
| UI delivery | 24 / 32 when UI is in scope |
| Delivery review inside PRD | 15 / 20 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-07-09 | agentic-trace-missing | High | The system could generate artifacts without recording task mode, autonomy, product judgment, next actions, or memory candidates. | Added 3.0 operating model, run-log fields, and validator checks. |

## Pass Criteria

- The agent selects and explains task mode and autonomy level.
- The agent does not present the workflow as the main user value.
- Must-answer questions stop generation unless the user accepts draft risk.
- PRD status, engineering handoff status, and launch status are recorded separately.
- Product judgment includes recommended path, confidence, blockers, and alternatives.
- Tracking plan includes event names, trigger timing, privacy notes, and validation suggestions.
- Review findings include PM usefulness, artifact, evidence, owner, required-before phase, and status.
- Validation results cite `validate_outputs.py`, `run_delivery_checks.py`, `validate_prototype_visual.py`, `validate_ui_preview.py`, or pre-clarification status as applicable.
- Next actions are concrete enough for the PM to continue.
- Memory candidates are proposed or explicitly marked none.

## Latest Result

| Field | Value |
|---|---|
| Run ID | pending |
| Status | Pending |
| Notes | Added as part of PM Copilot 3.0 Agent System upgrade. |
