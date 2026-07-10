# Evaluation Case: Accountable Action Closure

## Metadata

| Field | Value |
|---|---|
| Case ID | accountable-action-closure |
| Scenario | A persuasive PM recommendation must become an accountable execution path rather than generic next steps |
| Platform | Cross-platform |
| Product Area | Product decision and execution readiness |
| Created | 2026-07-10 |
| Last Updated | 2026-07-10 |
| Fixture Scope | Public generic |
| PM User Type | Senior PM |
| Risk Profile | Operations / Data quality |

## Fixture Isolation Terms

- `<none>`

## Raw Request

```text
Review the proposed launch plan, choose the recommended path, and finish the PM work. Do not just tell me to align with engineering later. Tell me exactly what must happen next, who owns it, when it is required, what decision or blocker it resolves, and what evidence proves it is complete.
```

## Context Files

- `context/product-context.example.yaml`
- Optional user-provided launch plan or host repository evidence

## Expected Workflow

- Select `product_review`, `launch_readiness`, or justified `mixed_delivery` mode.
- Record a decision with a stable decision id and evidence.
- Preserve engineering and launch blockers with stable blocker ids when present.
- Run PM usefulness review and reject generic unowned next steps.
- Produce `next_actions` as an area summary and `action_closure.critical_path` as the accountable execution path.
- Align action status with `termination_condition`: blocked and needs-input runs expose matching critical-path status.

## Required Artifacts

- `outputs/<run-id>/run-log.yaml`
- `outputs/<run-id>/prd.md` or review findings when the clarification gate permits generation
- Optional `launch-decision.yaml` when launch readiness is claimed

## Artifact Expectation Matrix

| Artifact | Required When | Validation |
|---|---|---|
| `run-log.yaml` | Always | `python3 scripts/validate_agent_trace.py outputs/<run-id>` |
| `prd.md` or review findings | Product decision evidence is available | `python3 scripts/validate_outputs.py outputs/<run-id>` |
| `launch-decision.yaml` | Launch readiness is claimed | `python3 scripts/run_delivery_checks.py outputs/<run-id>` |

## Agentic Expectation Matrix

| Field | Expected Behavior |
|---|---|
| Product judgment | Records the recommended path, `high|medium|low` confidence, evidence, and alternatives. |
| Decision ids | Every product-relevant decision used by action closure has a stable id. |
| Blocker ids | Every blocker referenced by action closure exists in readiness evidence. |
| Next actions | Summarizes follow-up work by functional area. |
| Action closure | Every critical action has owner, due phase, source decision or blocker id, completion evidence, and status. |
| Termination alignment | `blocked` and `needs_input` termination states have matching critical-path action status. |

## Known Risks

- The Agent sounds decisive but leaves ownership implicit.
- The response says "align", "confirm", or "follow up" without completion evidence.
- The action list cannot be traced to a decision or blocker.
- The run claims completion while unresolved blocker actions remain hidden.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Delivery | 23 / 32 |
| PRD | 31 / 40 when PRD is in scope |
| Metrics and tracking | 21 / 28 when tracking is in scope |
| UI delivery | 24 / 32 when UI is in scope |
| Delivery review inside PRD | 15 / 20 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-07-10 | persuasive-but-unowned | High | The Agent produced persuasive recommendations but no accountable owner or completion evidence. | Add `action_closure` contract and strict trace validation. |

## Pass Criteria

- The selected recommendation is linked to at least one stable decision id.
- Every critical-path action names an owner and allowed due phase.
- Every critical-path action defines observable completion evidence.
- Every action references an existing decision or blocker id.
- Duplicate or empty action ids fail validation.
- Blocked or needs-input termination states expose a matching blocked or needs-input action.
- `python3 scripts/validate_agent_trace.py outputs/<run-id>` passes.

## Latest Result

| Field | Value |
|---|---|
| Run ID | pending |
| Status | Pending |
| Notes | Added for PM Copilot.1 accountable action-closure regression coverage. |
