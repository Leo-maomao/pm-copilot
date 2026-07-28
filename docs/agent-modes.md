# Agent Modes

PM Copilot separates task mode from autonomy level.
Task mode describes the PM job.
Autonomy level describes how far the Agent should go before stopping.

## Task Modes

| Mode | Use When | Typical Output |
|---|---|---|
| `prd_delivery` | A new or changed feature needs a product requirement | `prd.md`, UI delivery, run log |
| `implemented_feature_prd` | The feature already exists in the branch and needs reverse PRD/HTML | `prd.md`, `prd.html`, implementation evidence |
| `ui_delivery` | The main value is UI surface, interaction, or visual handoff | Evidence-based prototype, UI specification, or existing UI extract |
| `tracking_plan` | Metrics and analytics are the primary need | Tracking table or `tracking-plan.csv` |
| `launch_readiness` | The PM needs go/no-go support | Findings, blockers, `launch-decision.yaml` |
| `dev_handoff` | Confirmed scope must become engineering work | `dev-tasks.yaml` |
| `structured_reference` | The user needs reference/document structure rather than a PRD | `catalog.md`, `reference.md`, or document prototype |
| `product_review` | Existing artifacts or implementation need critique | Review findings and required fixes |
| `self_improvement` | PM Copilot itself needs durable improvement | Repo changes, eval/validator, version and changelog |
| `mixed_delivery` | The request spans several PM outcomes | Smallest graph covering the requested outcomes |

## Autonomy Levels

### `clarify-first`

Default for normal PM work.
The Agent asks before generation when missing information would change the product decision, scope, platform, tracking, UI direction, or high-risk readiness.

Stops when:

- A must-answer question remains open.
- The current product context cannot be established.
- Launch-sensitive risk would be hidden by drafting.

### `draft-with-risk`

Use when the user explicitly asks to proceed with assumptions.
The Agent may draft, but must downgrade readiness and make assumption or confirmation risk visible.

Defaults forward when:

- The unknown is low risk.
- The assumption can be clearly stated.
- The artifact is a draft, not engineering-ready or launch-ready.

### `full-loop`

Use when the user expects end-to-end delivery.
The Agent observes context, frames scope, decides route, acts, verifies, reviews, revises when needed, and returns next actions.
The Loop is bounded by iteration, tool-call, elapsed-time, and no-progress budgets. Every additional iteration must produce a concrete delta and pass the Loop decision check.

Continues by default when:

- Missing information is non-blocking.
- Tools are available or alternatives can produce credible evidence.
- Review findings can be fixed within the current run.

Degrades when:

- A tool fails after setup or fallback attempts.
- External research cannot run.
- UI visual validation is blocked by environment limitations.

### Delegated Execution

PM Copilot includes a local runtime adapter for already authenticated command-line agents. It does not require users to add an API key or copy credentials into a PM Copilot configuration file. Run `python3 scripts/agent_runtime.py discover --json` to identify the active host runtime and model; automatic execution uses that session rather than a fixed runtime preference. Supported headless runtimes include Seawork, Codex CLI, Claude CLI, Qwen Code, Kimi Code, Qoder CLI, and CodeBuddy Code. A Seawork-backed session can run detached workers, structured output, and verifier loops; the other supported CLIs run direct single-worker work.

When the host exposes agent delegation, `full-loop` and `self-iteration` runs must use it for two or more independent evidence, review, or validation tasks when delegation improves speed or quality. The PM Orchestrator records the selected model/runtime, each specialist's owned question, and the reconciliation result in `delegation_plan` and `agent_transitions`.

When no ready runtime can create a specialist, the run remains single-agent and records `delegation_plan: unavailable` with the capability limitation. A detected IDE or unregistered CLI does not count as delegated execution. It must not claim multi-agent collaboration merely because the execution graph or Loop evaluator is present.

For a qualifying request, PM Copilot uses `scripts/plan_agent_delegation.py` to select at most three independent evidence roles, then `scripts/run_agent_delegation.py` to dispatch them and run Review Agent after their outputs exist. `collaboration_protocol` records a targeted challenge only for a material conflict, unsupported claim, or High/Critical finding; PM Orchestrator performs the evidence-based arbitration or asks one minimal human question.

### `self-iteration`

Use when the task is to improve PM Copilot itself.
The Agent must generalize the failure, update durable repo surfaces, add or update regression coverage when useful, bump version, update `CHANGELOG.md`, add an optimization-cycle note, and run validation.

Stops only when:

- The failure cannot be reproduced or generalized from available evidence.
- Required release metadata or validation cannot be produced.
- The user changes the improvement target.
- The configured budget or no-progress threshold is reached.

## Final Delivery Expectations

Every full delivery should include:

- Produced artifacts or changed files
- Product judgment and confidence when a decision was made
- Blockers and unresolved confirmations
- Validation commands and results
- Next actions
- Accountable critical-path actions with owner, due phase, completion evidence, and decision or blocker linkage
- Memory candidates when durable learning was found
