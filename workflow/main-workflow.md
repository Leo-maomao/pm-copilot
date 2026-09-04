# Agent Execution Graph

PM Copilot uses a dynamic execution graph governed by `agents/agent-operating-model.md`. Dynamic routing never permits a required gate to be skipped.

For `prd_delivery` and `implemented_feature_prd`, the required sequence is: requirement proposal -> discussion -> clarification -> explicit user confirmation -> complete contracted artifacts -> independent stage review -> final validation. The PM Orchestrator may select optional specialists and mode-specific artifacts within that sequence, records the chosen path, and uses the bounded Agent Loop to decide whether another evidence-producing pass is justified. Repeating a node without an evidence, artifact, decision, validation, or readiness delta is `no_progress`.

The runtime records `task_mode`, `autonomy_level`, `effort_budget`, `delegation_plan`, and `termination_condition`; the graph itself does not duplicate those contracts.

## Graph Nodes

| Node | Owner | Use When | Completion Evidence |
|---|---|---|---|
| Goal framing | PM Orchestrator | Every task | Goal, task mode, autonomy level, success criteria, effort budget, and requested artifacts are explicit |
| Tool preflight | PM Orchestrator | Tools, repository access, research, UI rendering, validation, or release work are needed | Required capabilities and fallbacks are recorded |
| Context acquisition | PM Orchestrator | Product truth must be loaded from a repository, documents, screenshots, or brief | Context mode, source files, facts, gaps, and confidence are recorded |
| Implementation evidence | PM Orchestrator + Requirements Agent | The task concerns an already implemented feature | Changed files, visible behavior, tests, assets, and unverified intent are separated |
| Discovery | Discovery Agent | Ambiguity, risk, or missing product judgment can change the answer | Blocking questions, assumptions, alternatives, and confidence are explicit |
| Human decision | PM Orchestrator | A product, legal, launch, scope, or approval checkpoint is required | The Agent stops until the decision is recorded |
| External research | Research Agent | Current external evidence can materially change product judgment | Sources, synthesis, limitations, and confidence impact are recorded |
| Requirements delivery | Requirements Agent | PRD or requirement definition is in scope | `prd.md` satisfies `artifacts/prd-contract.md` |
| Structured knowledge | Requirements Agent | A catalog, reference, SOP, matrix, rule set, or document prototype is in scope | The requested structured artifact satisfies its contract |
| Measurement design | Analytics Agent | Goals, behavior, launch, or experiment decisions need measurable evidence | Metrics and tracking are defined and validated |
| UI delivery | UI Delivery Agent | User-facing flow, interaction, visual handoff, or screenshot reconstruction is in scope | Source-rendered, source-extracted, or portable UI artifact and visual evidence satisfy the UI contract |
| Product review | Review Agent | Product usefulness, consistency, risk, or readiness must be evaluated | Findings, severity, required fixes, accepted risks, and recommendation are explicit |
| Delivery validation | PM Orchestrator | A final artifact or run folder is claimed | Repository, output, trace, Loop, HTML, and visual checks applicable to the run pass |
| Execution handoff | PM Orchestrator | Engineering, QA, analytics, or launch must act next | Accountable action closure, owners, due phases, completion evidence, and readiness are explicit |
| Learning | PM Orchestrator | Durable facts, preferences, decisions, or system defects were discovered | Memory candidates or optimization evidence are recorded without silently storing sensitive data |

## Routing Rules

- Start from the user goal, not from a predefined node order.
- Use `task_mode`, `autonomy_level`, and `effort_budget` to select optional work only after preserving every mandatory stage for that mode.
- Skip only artifacts and specialist nodes that are genuinely irrelevant to the selected contract. Never skip requirement discussion, clarification, explicit confirmation, contracted delivery, independent review, or final validation for a PRD path.
- Run independent research, analytics, UI inspection, or specialist review in parallel when their outputs do not block one another.
- Replan when evidence conflicts, the user changes the goal, a tool fails, artifacts disagree, or Review Agent finds High/Critical issues.
- Stop on success, required input, blocker, budget, no progress, due human checkpoint, or failure.
- Do not claim completion because a graph path ended. Completion requires PM usefulness, artifact acceptance, validation evidence, and accountable next action. A non-zero `run_delivery_checks.py` result blocks final-delivery claims; a required visual placeholder remains deliverable only when its explicit manual completion notice and replacement instruction pass validation.

## Stage Transition Gate

A stage may advance only when its named acceptance evidence is present and an
independent reviewer or deterministic validator has accepted it. For ambiguous
production requests, an Intake Agent's `complete` result is provisional: the
Clarification Review Agent must independently confirm that every
branch-changing unknown is answered, deliberately assumed with user consent,
or assigned to a later named confirmation owner. For delivery artifacts, the
Stage Quality Review Agent checks the artifact before its immediate consumer
starts. Failure, a reviewer outage, exhausted repair budget, or consecutive
no-progress is a stop at the current stage, never permission to bypass it.

## Common Subgraphs

`prd_delivery`:

```text
Goal framing -> Context acquisition -> Requirement discussion -> Clarification
-> Explicit user confirmation -> Requirements delivery -> Independent stage review
-> Measurement design when needed -> Product review -> Delivery validation
-> Execution handoff
```

`implemented_feature_prd`:

```text
Goal framing -> Context acquisition -> Implementation evidence
-> Requirement discussion -> Clarification -> Explicit user confirmation
-> Requirements delivery -> Independent stage review -> Product review
-> Delivery validation
```

`ui_delivery`:

```text
Goal framing -> Tool preflight -> Context acquisition -> Discovery when needed
-> Requirement discussion -> Clarification -> Explicit user confirmation
-> UI delivery -> Independent stage review -> Product review -> Delivery validation
```

`launch_readiness`:

```text
Goal framing -> Context acquisition -> Measurement design
-> Product review -> Human decision when required -> Execution handoff
```

`self_improvement`:

```text
Goal framing -> Runtime evidence analysis -> Generalize defect
-> Change contracts, tools, or prompts -> Add regression coverage
-> Delivery validation -> Learning
```

## Loop Integration

The execution graph defines where work can move. `loop_policy`, `loop_state`, `iteration_trace`, and `scripts/evaluate_agent_loop.py` determine whether another pass is justified.

## Adaptive Model Routing

Evaluation controllers select one model for each Agent call from the active,
verified runtime. An explicit operator `--model` override applies to every
Agent stage and is recorded as an override. Without an override, bounded
single-artifact discussion, confirmation, and trace stages use the available
standard model; primary PRD, launch, development-handoff, UI, and skill
deliveries use the highest-judgment model. Independent stage reviews always
use the highest-judgment model. Deterministic rendering and validation do not
call a model.

For ordinary single-Agent work, prefer the ready local CLI for the active
model family. A Seawork-backed Codex session alone is not a reason to launch a
Seawork Agent: its daemon, control plane, background watchers, and stream
bridge add failure and latency modes that do not improve a normal artifact or
review stage. Use Seawork only when the task actually needs its detached
multi-Agent scheduler/verifier contract, an operator explicitly requires it,
or the selected model is unavailable through the matching direct CLI. Record
the capability that justified that external route. When its control plane is
unhealthy, do not repeatedly retry it; use the verified matching direct CLI
where safe and retain the fallback provenance.

A validator-identified artifact repair may escalate from the standard model to
the highest-judgment model once. It must record the failure category, upgrade
source, and selection reason. Repeating the same model after no progress is
prohibited; the controller stops at the current stage with attributable
evidence for manual handling. Every `agent_calls` record includes the selected
model and `stage_model_selection` evidence, so adaptive routing cannot create
a second authoritative output branch.

For eligible `full-loop` and `self-iteration` work, first decompose the goal under the First-Principles Execution Rule in `agents/agent-operating-model.md`, then generate a bounded role plan with `python3 scripts/plan_agent_delegation.py --request '<user request>'`. If the plan contains two or more independent evidence workers and a multi-Agent runtime is ready, dispatch it with `python3 scripts/run_agent_delegation.py --request '<user request>' --task-mode '<mode>' --cwd '<project-workspace>' --ledger '<run-folder>/tool-results/agent-task-ledger.json' --execute`; planning without this dispatch is a direct-path decision and must be recorded with its reason. Route completed specialist outputs to Review Agent for challenge. Resolve material disagreement through the canonical Conflict-Resolution Gate in `agents/agent-operating-model.md`; the evaluator maps its recorded status to reconciliation, a human-input stop, or a blocked stop. Next, inspect local authenticated runtimes with `python3 scripts/agent_runtime.py discover --json`. The controller selects the user's active host runtime and model rather than a fixed default. When that session is Seawork-backed, invoke `scripts/agent_runtime.py loop` for a bounded worker/verifier cycle and retain its active agent model; if the Seawork daemon is unavailable, use the ready CLI matching the active model family for a single-worker fallback. Record the selected provider/model and worker result in `delegation_plan` and `iteration_trace`, then run `scripts/evaluate_agent_loop.py` before another iteration. Detected IDE or CLI tools without a registered headless contract are not execution fallbacks.

Review Agent evaluates progress and usefulness. PM Orchestrator owns the final continue or stop decision. Loop budgets are ceilings, not targets.

For an implemented-feature PRD with a `required_placeholder`, visual recovery is part of the success criteria, not a post-delivery note. A result such as an empty Chrome DevTools target list marks only Chrome DevTools as `not_available`; it must not suppress existing-preview discovery, project-runtime activation, test-state recovery, Playwright, or Computer Use. In the same pass, continue through every remaining independent recovery route that is runnable; do not close a pass after one path is unavailable. Retain local evidence for every route. The loop may stop successfully only after a real figure is captured or the full capability chain has recorded its terminal outcomes; otherwise `scripts/evaluate_agent_loop.py` continues the run when budget remains and rejects a success stop when it does not.

## Required Commands

```bash
python3 scripts/preflight_tools.py --json
python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>
```

For PM Copilot repository changes:

```bash
python3 scripts/validate_repo.py
python3 scripts/test_agent_loop.py
python3 scripts/agent_improvement_scorecard.py
python3 scripts/validate_agent_task_ledger.py outputs/<run-id>/tool-results/agent-task-ledger.json
```
