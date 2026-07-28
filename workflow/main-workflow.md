# Agent Execution Graph

PM Copilot uses a dynamic execution graph governed by `agents/agent-operating-model.md`. There is no numbered state sequence and no mandatory full-path traversal.

The PM Orchestrator selects only the nodes required to satisfy the goal, records the chosen path, and uses the bounded Agent Loop to decide whether another evidence-producing pass is justified. Repeating a node without an evidence, artifact, decision, validation, or readiness delta is `no_progress`.

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
- Use `task_mode`, `autonomy_level`, and `effort_budget` to select the smallest sufficient subgraph.
- Skip irrelevant nodes without ceremonial log entries. Record only selected, rejected, revisited, or materially skipped paths that affect the decision.
- Run independent research, analytics, UI inspection, or specialist review in parallel when their outputs do not block one another.
- Replan when evidence conflicts, the user changes the goal, a tool fails, artifacts disagree, or Review Agent finds High/Critical issues.
- Stop on success, required input, blocker, budget, no progress, due human checkpoint, or failure.
- Do not claim completion because a graph path ended. Completion requires PM usefulness, artifact acceptance, validation evidence, and accountable next action.

## Common Subgraphs

`prd_delivery`:

```text
Goal framing -> Context acquisition -> Discovery -> Requirements delivery
-> Measurement design when needed -> Product review -> Delivery validation
-> Execution handoff
```

`implemented_feature_prd`:

```text
Goal framing -> Context acquisition -> Implementation evidence
-> Requirements delivery -> Product review -> Delivery validation
```

`ui_delivery`:

```text
Goal framing -> Tool preflight -> Context acquisition -> Discovery when needed
-> UI delivery -> Product review -> Delivery validation
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

For eligible `full-loop` and `self-iteration` work, first generate a bounded role plan with `python3 scripts/plan_agent_delegation.py --request '<user request>'`. Dispatch only the selected independent evidence tasks, then route their outputs to Review Agent for challenge. Material disagreement, unsupported claims, and High/Critical findings trigger evidence comparison and PM Orchestrator arbitration; they do not trigger an unbounded vote or debate. Next, inspect local authenticated runtimes with `python3 scripts/agent_runtime.py discover --json`. The controller selects the user's active host runtime and model rather than a fixed default. When that session is Seawork-backed, invoke `scripts/agent_runtime.py loop` for a bounded worker/verifier cycle and retain its active agent model; if the Seawork daemon is unavailable, use the ready CLI matching the active model family for a single-worker fallback. Record the selected provider/model and worker result in `delegation_plan` and `iteration_trace`, then run `scripts/evaluate_agent_loop.py` before another iteration. Detected IDE or CLI tools without a registered headless contract are not execution fallbacks.

Review Agent evaluates progress and usefulness. PM Orchestrator owns the final continue or stop decision. Loop budgets are ceilings, not targets.

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
```
