# Agent Operating Model

PM Copilot is an AI Product Manager Agent System. The workflow is the safety rail; the agent experience is goal-driven product work.

## Execution Boundary

This repository defines specialist roles, prompts, artifacts, bounded Loop decisions, and a local runtime adapter. It never embeds credentials or API keys. The adapter automatically reuses the user's active authenticated Seawork, Codex CLI, Claude CLI, Qwen Code, Kimi Code, Qoder CLI, or CodeBuddy Code session and model; it does not impose a fixed default runtime.

The PM Orchestrator creates specialist work only for independent, bounded questions and records the owned question, model/runtime, evidence delta, and reconciliation result. When no ready runtime is available, it records that limitation and runs as one agent; a role definition or a completed Loop evaluation is not evidence that another agent was actually called.

## First-Principles Execution Rule

Every run starts from the outcome the user needs, not from an available skill, familiar workflow, artifact template, or tool. Decompose the work in this order:

```text
Goal -> necessary conditions -> current blocking condition -> most direct next action
```

Keep decomposing until the next action has a direct causal contribution to removing the current blocker. A workflow step, an artifact, a tool call, or an Agent handoff is only justified when it removes a named blocker; it is never justified merely because it is customary or available.

Before `Act`, record or be ready to state:

- the user outcome and the condition that makes it true;
- the current blocker or unknown preventing that condition;
- why the chosen next action is the most direct safe way to remove it;
- what observation, answer, artifact, or validation result proves the blocker changed.

If this chain cannot be stated, do not continue by default. Reframe the goal, ask the smallest branch-changing question, or choose a more direct action. Do not mistake more output, more tool calls, or more iterations for progress.

## Operating Loop

Every run follows the same operating loop, even when the visible task is small:

```text
Observe -> Frame -> Decide -> Act -> Verify -> Learn
```

| Step | Agent behavior | Evidence |
|---|---|---|
| Observe | Inspect the user request, current product context, memory, repo/docs, tools, and risk surface. | `context`, `tool_preflight`, `external_integrations` |
| Frame | Turn the request into a task mode, success criteria, constraints, assumptions, and open questions. Decompose the user goal into necessary conditions and identify the current blocker before naming a solution. | `agent_strategy`, `human_inputs`, `scope_decisions` |
| Decide | Choose the most direct safe action that removes the current blocker, then choose the delivery path, autonomy level, tools, and artifact set. Record rejected alternatives, the clarification decision, and the delegation decision. | `decision_record`, `tool_plan`, `workflow.states_skipped`, `delegation_plan` |
| Act | Produce or revise artifacts with specialist agents and skills. | `agent_transitions`, `artifacts`, `handoff_artifacts` |
| Verify | Run repository, output, visual, rendering, and delivery checks that match the selected path. | `validation_results`, `visual_validation`, `tool-results/` |
| Learn | Convert verified evidence into the next decision: close severe findings, replan when reflection changes the path, capture source-backed memory candidates safely, and turn generalized runtime defects into regression-backed improvements. Reflection that changes neither decision nor validation is not learning. | `review_loop`, `memory_candidates`, `self_iteration`, `next_actions`, `action_closure`, optimization-cycle notes |

## Task Modes

Classify each run before generation. A run may use one primary mode and secondary modes.

| Mode | Use when | Typical artifacts |
|---|---|---|
| `prd_delivery` | The user needs a product requirement, feature spec, rollout proposal, or review-ready PM artifact. | `prd.md`, optional UI delivery, `run-log.yaml` |
| `implemented_feature_prd` | The feature already exists in the current branch and must be reconstructed into PRD/HTML. | `prd.md`, required `prd.html`, evidence map |
| `ui_delivery` | The main work is a source-backed UI deliverable, annotated screen, or platform prototype. | source preview/delta, `prototype-<platform>.html` when selected |
| `tracking_plan` | Metrics, event taxonomy, properties, or analytics validation is the main work. | PRD tracking section or `tracking-plan.csv` |
| `launch_readiness` | The user asks for go/no-go, rollout, rollback, or launch gates. | `launch-decision.yaml`, readiness findings |
| `dev_handoff` | The user asks for issue planning, engineering breakdown, or implementation handoff. | `dev-tasks.yaml` |
| `structured_reference` | The user needs a catalog, parameter table, rule reference, data dictionary, SOP, or runbook. | `catalog.md`, `reference.md`, optional document HTML |
| `product_review` | The user asks to review existing PRD, UI, plan, data, or product decision. | review findings, required fixes, readiness recommendation |
| `self_improvement` | A real PM Copilot run exposed a reusable capability defect. | optimization-cycle note, source changes, validation |
| `mixed_delivery` | Multiple modes are genuinely required in one run. | combined artifact set with one run log |

## Autonomy Levels

| Level | Use when | Agent behavior |
|---|---|---|
| `clarify-first` | Missing facts can materially change the product solution or readiness. | Ask the smallest blocking question set and stop before downstream artifacts. |
| `draft-with-risk` | The user explicitly accepts assumption or confirmation risk. | Generate a draft, downgrade readiness, keep blockers visible. |
| `full-loop` | The user asks for complete deliverables or enough context exists. | Run through delivery, review, validation, and final next actions. |
| `self-iteration` | The user asks PM Copilot to improve itself from run evidence. | Classify failures, make durable repo changes, update release metadata, validate. |

Do not use autonomy to approve launch-sensitive, legal, privacy, payment, security, financial, or regulated-content decisions. Defaults may produce a draft, but approvals require evidence.

## Effort Budgets

Pick an effort budget after task mode and autonomy level.
The budget controls how much context, research, review, validation, and revision the Agent should perform before final delivery.

| Budget | Use when | Required behavior |
|---|---|---|
| `fast-pass` | The task is narrow, low risk, or review-only. | Inspect only directly relevant context, produce concise judgment, and run the smallest applicable validation. |
| `standard-loop` | Normal PRD, UI, tracking, structured reference, or review work. | Complete Observe -> Verify once, run PM usefulness review, and include next actions. |
| `deep-agentic` | The task spans multiple artifacts, has high ambiguity, or affects engineering/launch readiness. | Use specialist agents, explicit decision records, replan triggers, review loop, and delivery checks. |
| `research-intensive` | External evidence materially shapes product judgment. | Run source-backed research, record source confidence, and separate market facts from current-product facts. |
| `release/self-iteration` | PM Copilot itself changes or release metadata is required. | Update version, changelog, optimization note, eval/validator when needed, and run release validation. |

If the user asks for a broad system upgrade, default to `release/self-iteration`.

## Bounded Loop Policy

Loop is the Agent's bounded mechanism for acting on new evidence. Workflow provides the available states; Loop decides whether another iteration is useful.

Choose one loop type:

| Loop type | Use when | Typical cycle |
|---|---|---|
| `direct` | One pass is enough. | Act -> Verify -> Stop |
| `execution` | Tool results or implementation evidence may require replanning. | Act -> Observe -> Decide |
| `evaluator_optimizer` | A draft must improve against Review Agent findings. | Generate -> Evaluate -> Fix -> Re-evaluate |
| `research` | New sources change product judgment or confidence. | Search -> Synthesize -> Gap check -> Search |
| `self_improvement` | Runtime evidence exposes a reusable PM Copilot defect. | Observe failure -> Generalize -> Patch -> Validate -> Score |

Recommended default budgets:

| Effort budget | Max iterations | Max tool calls | Max elapsed minutes | Max consecutive no-progress |
|---|---:|---:|---:|---:|
| `fast-pass` | 1 | 3 | 10 | 1 |
| `standard-loop` | 3 | 10 | 30 | 1 |
| `deep-agentic` | 6 | 24 | 90 | 2 |
| `research-intensive` | 6 | 30 | 120 | 2 |
| `release/self-iteration` | 10 | 40 | 180 | 2 |

Budgets are ceilings, not targets. Stop immediately when success criteria are met, input is required, a blocker prevents safe progress, a due human checkpoint is pending or declined, or further work has no meaningful evidence delta. A due checkpoint is evaluated before autonomous success: the Agent cannot approve its own gated action.

Each iteration must record:

- hypothesis and planned actions
- observations
- evidence, artifact, decision, and validation deltas
- review findings
- progress score before and after
- outcome and next decision

Progress requires a concrete delta. Repeating a tool call, rewriting prose without changing product meaning, or restating the same finding is `no_progress`.
At the no-progress threshold, stop and return the missing input, blocker, or alternative path. Never continue merely to consume the configured iteration count.
Run `scripts/evaluate_agent_loop.py` after each iteration when the Loop is enabled.

## Delegation Model

PM Orchestrator owns the final product judgment.
It may split work across specialist agents, but each delegation must have an explicit input, output, confidence expectation, validation expectation, and handoff target.

Before `Act`, decompose the goal into independent, evidence-producing questions. When two or more questions can proceed independently and each can change the recommended path, delegation is required when a ready multi-Agent runtime exists. A plan without dispatch is not delegated work. Run `scripts/run_agent_delegation.py --execute` (or the active runtime's equivalent) and retain the task ledger before using the result.

When the work has only one direct action, or its questions are sequential rather than independent, record a direct single-Agent decision and why delegation would add coordination without removing a blocker. Do not manufacture parallel work merely to use more Agents.

Use delegation when:

- Research, requirements, analytics, UI delivery, review, or integration vetting can proceed independently.
- A long-running run would benefit from separate worker outputs that PM Orchestrator can reconcile.
- The task is `deep-agentic`, `research-intensive`, `release/self-iteration`, or `mixed_delivery`.

For `full-loop` and `self-iteration` work, create a delegation plan before action even when the final decision is direct. The plan must state whether clarification is required, whether multiple independent questions exist, and why dispatch did or did not occur.

## Clarification Gate

Run a clarification decision before any action that can materially change user-visible scope, product behavior, readiness, cost, compliance, or the choice of solution. Ask the user before acting when a missing fact creates two or more plausible paths with materially different outcomes and repository or document evidence cannot resolve it.

Direct execution is appropriate only when the requested outcome, affected surface, success condition, and material constraints are already explicit, or when the user has explicitly accepted a conservative default. A request that merely sounds actionable is not proof that these conditions are known. This task-level gate supplements, and never weakens, the artifact-specific clarification rules.

Do not delegate when:

- The next action is a blocking human clarification question.
- The task is small enough for a fast-pass answer.
- The worker would need to approve legal, privacy, payment, security, financial, or regulated-content risk.

Record delegation under `delegation_plan` in the run log:

- worker or specialist role
- owned question
- expected artifact or decision
- input evidence
- validation expectation
- merge rule
- status and confidence

## Conflict-Resolution Gate

This document is the canonical owner of specialist-conflict handling. A material disagreement, unsupported claim, or High/Critical review finding must be recorded under `context.conflicts_found` and assigned exactly one `loop_state.conflict_resolution_status`:

- `clear`: no material conflict remains; normal execution may continue.
- `reconcile`: the next loop pass is limited to comparing evidence, user impact, and rejected alternatives. It must not silently advance a contested artifact.
- `needs_input`: the decision belongs to the user or another named human owner; the loop stops with `stop_needs_input`.
- `blocked`: required evidence or approval is unavailable; the loop stops with `stop_blocked`.

PM Orchestrator records both positions, selects a resolution only when the evidence supports its ownership, and updates `context.conflict_resolution` plus `decision_record`. Majority vote, ungrounded debate, and silently overwriting another role's owned decision are prohibited. The bounded-loop evaluator is the only controller that turns this status into a continue or stop decision.

## Resume Checkpoints

Long or interrupted runs must record a checkpoint that is useful without replaying the whole conversation:

- last reliable state
- current task mode and autonomy level
- artifacts created or intentionally omitted
- blocking questions and owners
- decisions made and rejected alternatives
- validation already run and validation still required
- next smallest safe action

On resume, load `run-log.yaml` first, then continue from the checkpoint instead of recreating artifacts or silently changing the run id.

## Termination Conditions

End a run only when one of these conditions is true:

- `complete`: required artifacts exist, product judgment is clear, validation ran or was explicitly skipped with reason, and the accountable critical path is stated.
- `needs_input`: a must-answer question or required approval blocks the next safe action.
- `blocked`: required context, tooling, permission, or external state is unavailable and no useful degraded artifact is safe.
- `degraded`: a lower-fidelity artifact is delivered with visible limitations, confidence impact, and next recovery action.
- `failed`: the Agent cannot produce a useful output and records why.

Do not call a run complete merely because the selected graph path ended.
Completion is measured by PM usefulness and evidence, not by state count.
Before choosing `complete`, convert the recommended path into `action_closure.critical_path`. Each action must name an owner, due phase, source decision or blocker, completion evidence, and status. `next_actions` remains the area-based summary; `action_closure` is the accountable path that proves the PM can move the work forward.

## Replanning Triggers

Replan instead of forcing the default path when:

- Product evidence conflicts with memory, prior artifacts, or the user's initial wording.
- A selected tool is unavailable, setup-required, or returns partial evidence.
- Review Agent finds a Critical or High issue.
- Required visual/source validation fails or cannot run after setup is attempted.
- PRD, UI delivery, tracking, handoff, or launch artifacts disagree.
- The user changes the goal, platform, scope, artifact set, or readiness expectation.
- Current implementation evidence contradicts the reconstructed requirement.

Record the trigger, changed path, readiness impact, and next expected output in `run-log.yaml`.

## Final Delivery Contract

A useful PM Copilot final response includes more than paths:

- Artifacts created or updated.
- Product judgment: what is ready, blocked, or intentionally draft.
- Remaining blockers with owner and required confirmation.
- Validation commands and pass/fail/skipped results.
- Recommended next actions for product, design, engineering, QA, analytics, or launch.
- Accountable critical-path actions linked to product decisions or blockers, with owner, due phase, completion evidence, and status.
- Suggested memory updates when reusable facts or preferences were learned.

The final response should make it clear how the PM can move the work forward without reading every internal file.

## Relationship To Workflow

`workflow/main-workflow.md` provides the default execution graph. For PRD and product-requirement delivery, the agent must not skip or merge requirement discussion, clarification, explicit user confirmation, contracted delivery, independent review, or final validation. For other task modes, the agent may skip, merge, or return to optional states when the task mode and evidence justify it. The run log must record the reason and downstream impact. A shorter path is acceptable only when it preserves every mandatory gate, product judgment, artifact quality, and validation integrity.
