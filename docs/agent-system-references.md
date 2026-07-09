# Agent System References For 3.0

This note records external primary-source Agent patterns absorbed into PM Copilot 3.0.
It is not a generic reading list; every item maps to a durable PM Copilot capability.

## Sources Used

| Source | Primary Pattern | PM Copilot Absorption |
|---|---|---|
| OpenAI Agents SDK docs: https://openai.github.io/openai-agents-python/ | Agents, handoffs, guardrails, tracing, memory, and human-in-the-loop concepts are first-class runtime concerns. | Added Agent trace validation, `agent_strategy`, `decision_record`, `tool_plan`, `review_loop`, `memory_candidates`, and stricter final delivery contract. |
| Anthropic, Building Effective Agents: https://www.anthropic.com/engineering/building-effective-agents | Distinguishes workflows from agents and describes patterns such as prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer, and autonomy by task complexity. | Reframed S0-S12 as an execution graph and added task modes, effort budgets, delegation model, PM usefulness review, and replanning triggers. |
| Anthropic, Multi-Agent Research System: https://www.anthropic.com/engineering/built-multi-agent-research-system | Lead agent decomposes broad research into subagents, then synthesizes evidence and manages coordination cost. | PM Orchestrator owns final product judgment, records delegation plan, and reconciles specialist outputs instead of pasting worker notes together. |
| LangGraph docs: https://docs.langchain.com/oss/python/langgraph/overview and https://docs.langchain.com/oss/python/langgraph/workflows-agents | Long-running graph execution benefits from state, persistence, human-in-the-loop, and explicit workflow/agent boundaries. | Added resume checkpoints, termination conditions, dynamic skip/merge/backtrack rules, and run-log validation. |
| Microsoft AutoGen AgentChat docs: https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/index.html | Multi-agent applications need explicit conversation patterns, memory, tools, and human feedback. | Strengthened `agents/agent-interface.md`, handoff payloads, memory candidates, and next-action categories. |

## Absorbed Design Principles

- Agentic behavior must be observable. PM Copilot 3.0 validates trace fields instead of trusting prose claims.
- Workflows remain useful, but they are implementation paths. The product experience is goal framing, product judgment, and verified delivery.
- Delegation is a tool, not a default. PM Orchestrator decides when specialist work is useful and owns the final synthesis.
- Long runs need termination conditions. A run ends because it is complete, needs input, blocked, degraded, or failed, not because the state list ended.
- Historical runtime evidence matters. Self-iteration should scan local outputs for missing judgment, next actions, trace gaps, and validation gaps before changing rules.
- Registered tool capabilities `validation.agent_trace` and `analysis.agent_runs` make the absorbed patterns executable through PM Copilot tooling.
