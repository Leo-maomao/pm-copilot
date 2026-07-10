# Agent System References For 3.x

This note records external primary-source Agent patterns absorbed into PM Copilot.
It is not a generic reading list; every item maps to a durable PM Copilot capability.

## Sources Used

| Source | Primary Pattern | PM Copilot Absorption |
|---|---|---|
| OpenAI Agents SDK docs: https://openai.github.io/openai-agents-python/ | Agents, handoffs, guardrails, tracing, memory, and human-in-the-loop concepts are first-class runtime concerns. | Added Agent trace validation, `agent_strategy`, `decision_record`, `tool_plan`, `review_loop`, `memory_candidates`, and stricter final delivery contract. |
| Anthropic, Building Effective Agents: https://www.anthropic.com/engineering/building-effective-agents | Distinguishes workflows from agents and describes patterns such as prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer, and autonomy by task complexity. | Added goal-driven graph routing, task modes, effort budgets, delegation boundaries, PM usefulness review, and replanning triggers. |
| Anthropic, Multi-Agent Research System: https://www.anthropic.com/engineering/built-multi-agent-research-system | Lead agent decomposes broad research into subagents, then synthesizes evidence and manages coordination cost. | PM Orchestrator owns final product judgment, records delegation plan, and reconciles specialist outputs instead of pasting worker notes together. |
| LangGraph docs: https://docs.langchain.com/oss/python/langgraph/overview and https://docs.langchain.com/oss/python/langgraph/workflows-agents | Long-running graph execution benefits from state, persistence, human-in-the-loop, and explicit workflow/agent boundaries. | Added resume checkpoints, termination conditions, dynamic skip/merge/backtrack rules, and run-log validation. |
| Microsoft AutoGen AgentChat docs: https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/index.html | Multi-agent applications need explicit conversation patterns, memory, tools, and human feedback. | Strengthened `agents/agent-interface.md`, handoff payloads, memory candidates, and next-action categories. |
| OpenAI Agents SDK, Running Agents: https://openai.github.io/openai-agents-python/running_agents/ | The runtime loops over model output, tool or handoff execution, and another model turn until a final output or configured limit is reached. | Added a bounded Loop controller that turns runtime state into an explicit continue or stop decision. |
| Anthropic, Building Effective Agents: https://www.anthropic.com/engineering/building-effective-agents | Evaluator-optimizer works when evaluation criteria are clear and iterative refinement has measurable value. | Added `evaluator_optimizer`, PM usefulness evaluation, progress deltas, score movement, and no-progress termination. |
| LangGraph, Graph API and Interrupts: https://docs.langchain.com/oss/python/langgraph/graph-api and https://docs.langchain.com/oss/python/langgraph/interrupts | Cyclic graphs need explicit state and termination; interrupts persist state and require an external resume decision. | Kept workflow as the execution graph, added bounded Loop state, and made due human checkpoints stop before autonomous success. |
| AutoGen AgentChat, Termination: https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/termination.html | Termination conditions should be explicit, composable, and evaluated during execution rather than inferred from conversation length. | Added success, input, blocker, iteration/tool/time budget, no-progress, checkpoint, and failure stop decisions with regression fixtures. |

## Absorbed Design Principles

- Agentic behavior must be observable. PM Copilot validates trace fields instead of trusting prose claims.
- Workflows remain useful, but they are implementation paths. The product experience is goal framing, product judgment, and verified delivery.
- Delegation is a tool, not a default. PM Orchestrator decides when specialist work is useful and owns the final synthesis.
- Long runs need termination conditions. A run ends because it is complete, needs input, blocked, degraded, or failed, not because the state list ended.
- Historical runtime evidence matters. Self-iteration should scan local outputs for missing judgment, next actions, trace gaps, and validation gaps before changing rules.
- Registered tool capabilities `validation.agent_trace` and `analysis.agent_runs` make the absorbed patterns executable through PM Copilot tooling.
- A bounded Loop is a controller around the execution graph, not a requirement to repeat the entire workflow.
- Iteration budgets are ceilings. A run stops as soon as success, input, blocker, budget, no-progress, checkpoint, or failure evidence requires it.
- Progress is evidence-bearing: at least one artifact, evidence, decision, or validation delta plus score movement is required.
- The Loop contract is model-independent. Stronger models may make better judgments, but correctness comes from observable state, explicit limits, evaluator evidence, and machine validation rather than a model name.
