# PM Copilot

<p align="center"><a href="README.md">简体中文</a> | <strong>English</strong></p>

<a id="english"></a>

PM Copilot is an out-of-the-box AI Product Manager Agent System.
Current version: `6.2.4`.
It turns ambiguous goals, existing code, product documents, screenshots, research signals, or already implemented features into deliverables a PM can use to drive review, design alignment, engineering handoff, tracking, launch decisions, and learning.

It is not a template library or a fixed-step pipeline.
The execution graph provides safety boundaries; the user-facing experience is an AI PM that understands the goal, gathers evidence, makes product judgments, creates artifacts, verifies the result, and proposes memory candidates for future runs.

中文简介：PM Copilot 是面向产品经理的开源 AI Product Manager Agent System，支持 PRD、UI 交付、埋点方案、研发交接、上线判断、已实现功能反向 PRD、结构化参考和自我迭代。

## What It Does

- Clarifies requirements: goal, user, scope, platform, risk, and must-answer questions.
- Delivers PRDs: `prd.md` with background, goals, research, requirements, tracking, acceptance, risks, and readiness.
- Routes every PRD request through the production controller: discuss and clarify first, wait for explicit confirmation, and revise one canonical requirement folder in place without `-2` or `-3` copies.
- Renders PRD HTML: `scripts/render_prd_html.py` creates browser-readable `prd.html` for external review.
- Delivers UI: reviewable annotated prototypes, flows, and specifications grounded in existing source, screenshots, and design-system evidence without modifying host source code. Embedded projects use `outputs/<run-id>/`; globally installed runtimes use `pm-copilot-outputs/<run-id>/` at the project root.
- Routes each task through `indexes/runtime-routing.yaml` so only the smallest relevant active workflow, contract, skill, and memory records are loaded.
- Designs metrics and tracking: events, properties, triggers, privacy notes, and validation.
- Supports engineering handoff: optional `dev-tasks.yaml` with dependencies, acceptance, blockers, and issue-ready slices.
- Supports launch decisions: optional `launch-decision.yaml` with readiness, blockers, owners, rollback, and approval gaps.
- Reconstructs implemented features: inspects branch diff, code, screenshots/assets, and validation evidence, then creates `prd.md` plus required `prd.html`.
- Creates structured references: parameter tables, capability matrices, rule references, data dictionaries, SOPs/runbooks, and document prototypes with source/review status and attention points.
- Improves itself: converts real project failures into reusable updates to agents, workflow, skills, artifacts, tools, validators, and evals.

PM Copilot supports three context modes: `repo-backed`, `document-backed`, and `brief-only`.
The agent chooses the context mode, task mode, and autonomy level before drafting.

## Language Support

PM Copilot treats English and Chinese as first-class user-facing languages.
Generated PM artifacts, UI delivery labels, annotations, review findings, readiness statuses, and validation notes should follow the user's language with the same delivery scope and quality bar.
File names, event names, property names, requirement IDs, Mermaid node IDs, anchors, and other machine-readable identifiers stay ASCII for portability.

## Quick Start

For direct agent usage, see `docs/direct-use.md`.
For embedded project usage, see `docs/embedded-use.md`.
For practical PM scenarios, see `docs/use-cases.md`.
For autonomy choices, see `docs/agent-modes.md`.
For artifact value examples, see `docs/output-gallery.md`.

Use natural product goals instead of internal state names:

```text
We want to improve the H5 membership auto-renewal experience. Users say renewal reminders are unclear, the cancellation entry is hard to find, and support tickets are increasing.

Please identify missing critical information first. If enough context is available, create the PRD, H5 UI deliverable, tracking plan, and launch decision recommendation.
```

For an already implemented feature:

```text
The feature is already implemented on the current branch. Please inspect the branch diff, relevant code, screenshots/assets, and validation evidence, then reconstruct the implementation into a complete PRD Markdown file and generate a deliverable prd.html.

When a figure is needed, capture a real accessible surface: use Playwright for previews first, then an authenticated browser or system UI for a state that automation cannot reach. Save the real image under `assets/` and reference it inline. Omit the figure row when the image would not improve reviewability. When it is necessary but every trusted capture path fails, use the controlled fallback `占位图：功能-状态.png` and record the manual replacement location in the run log.
```

Name screenshots by content.
When one object has multiple states, use object plus concrete state, such as `资料卡片-加载中.png` and `资料卡片-加载失败.png`; do not use `资料卡片-状态.png`.
Cover every independent changed page, window, panel, or dialog, but do not split micro-states when one screenshot captures the complete window or panel. Avoid both irrelevant full-page captures and crops that hide the locating context.

## Two Practical Demos

Paste either request into an agent-enabled workspace.
PM Copilot should classify context mode, task mode, and autonomy level first; ask blocking questions when required; then generate artifacts and validation evidence when enough information is available.
For high-risk or evidence-poor requests, stopping at `stop_needs_input` or a human checkpoint is a valid result; the Agent should not continue merely to produce more files.

### Demo 1: Team Permission Management In An Existing Project

This verifies that PM Copilot reads code and product evidence before forming the permission model, interaction boundaries, and engineering handoff judgment instead of applying a generic permissions template.

![Team permission management demo screenshot](docs/assets/readme-demo-team-permissions.png)

```text
We need team permission management in the admin console.

Please inspect the existing routes, role model, member management page, permission checks, analytics conventions, and component patterns first.
Do a small amount of external comparable-product research, but do not treat repository files as competitor research.
If important information is missing, ask me before generation.
If enough information is available, create the PRD, a Web UI deliverable, and issue-ready engineering tasks.
```

A useful run should produce:

| Artifact | What to look for |
|---|---|
| `prd.md` | The first screen states the recommended permission approach, confidence, MVP/non-goals, key security blocker, and next checkpoint; details cover invites, role changes, permission blocking, audit, and recovery states |
| Web UI deliverable | Evidence-based annotated prototype or UI specification with observed/proposed behavior and fidelity notes |
| `dev-tasks.yaml` | Issue-ready engineering tasks, dependencies, acceptance criteria, test notes, likely host files, and blocking confirmations |
| `run-log.yaml` | Agent selection of `mixed_delivery` and autonomy level, source evidence, product decisions, Loop progress and stop reason, next actions, accountable critical path, and memory candidates |

### Demo 2: Membership Auto-Renewal Optimization Without A Code Repository

This verifies that PM Copilot does not mechanically produce every artifact for a payment and consumer-rights scenario: it stops with `stop_needs_input` when evidence is insufficient and proceeds only when the gates are satisfied.

![Membership auto-renewal demo screenshot](docs/assets/readme-demo-membership-renewal.png)

```text
We want to improve the H5 membership auto-renewal experience. Users say renewal reminders are unclear, the cancellation entry is hard to find, and support tickets are increasing.

The business goal is to reduce renewal-related complaints without materially hurting membership retention.
If you need current billing rules, reminder timing, cancellation paths, support scripts, legal requirements, or metric definitions, ask me first.
When enough information is available, create the PRD, H5 UI deliverable, tracking plan, and launch decision recommendation.
```

A useful run should produce:

| Artifact | What to look for |
|---|---|
| `prd.md` | The first screen states the recommendation, confidence, blockers, and separate PRD/engineering/launch statuses; details cover reminders, cancellation, payment, support, legal risks, and non-goals |
| `prototype-h5.html` | `portable_html` UI deliverable for no-code/document-backed starts, covering membership center entry, renewal reminder, auto-renewal management, cancellation confirmation, result receipt, logged-out/no-membership/API-failure states |
| Tracking table inside the PRD | Events such as `renewal_notice_view`, `renewal_manage_open`, `renewal_cancel_submit`, `renewal_cancel_result`, plus privacy notes |
| `launch-decision.yaml` | Engineering-ready scope, launch blockers, legal/payment/support owners, rollback recommendation, and missing human approvals |
| `run-log.yaml` | Clarifying questions, assumptions, external research, per-iteration evidence delta, Loop stop reason, access-state visual validation, tool results, and unresolved gates |

## Agent Operating Model

PM Copilot is defined in `agents/agent-operating-model.md`:

```text
Observe -> Frame -> Decide -> Act -> Verify -> Learn
```

Task modes:

| Mode | Use |
|---|---|
| `prd_delivery` | Create a complete PRD from goals and context |
| `implemented_feature_prd` | Reconstruct PRD and HTML from an implemented branch |
| `ui_delivery` | Deliver source-first UI, source-extracted HTML, or portable HTML |
| `tracking_plan` | Create metrics and analytics tracking |
| `launch_readiness` | Judge launch blockers, owners, rollback, and approvals |
| `dev_handoff` | Create development tasks and handoff information |
| `structured_reference` | Create a structured reference, rule table, SOP, or document prototype |
| `product_review` | Review an existing PRD, UI, implementation, or launch plan |
| `self_improvement` | Improve PM Copilot from real failures |
| `mixed_delivery` | Combine multiple product-manager outcomes |

Autonomy levels:

- `clarify-first`: default; ask before generation when critical context is missing.
- `draft-with-risk`: create a visible-risk draft when the user explicitly asks to proceed.
- `full-loop`: inspect context, create, review, validate, and recommend next actions.
- `self-iteration`: update PM Copilot itself with version, changelog, eval, and validation.

For complex work, PM Copilot also chooses an effort budget and records delegation plan, resume checkpoint, and termination condition.
That makes long runs explain why they continue, why they stop, and which specialist outputs were accepted or rejected instead of only showing workflow state.
A full delivery converts the recommendation into `action_closure`: every critical action needs an owner, due phase, source decision or blocker, completion evidence, and status instead of a generic "align later" follow-up.
Complex work uses a bounded Agent Loop. Every iteration must record an evidence, artifact, decision, or validation delta and is limited by iteration, tool-call, elapsed-time, and consecutive no-progress budgets. `evaluate_agent_loop.py` decides continue or stop. This is a model-independent runtime contract.

## Use Inside An Existing Project

Expected setup:

```text
host-repo/
|-- AGENTS.md or CLAUDE.md or .cursor/rules/
|-- src/
`-- pm-copilot/
    `-- PM_COPILOT.md
```

Copy or clone this repository into the host project as `pm-copilot/`, then install an adapter in the host repository root:

```bash
cd host-repo/pm-copilot
python3 scripts/install_adapter.py --host .. --tool all
```

The adapter is required for reliable embedded use.
Simply placing the `pm-copilot/` folder inside another project does not guarantee that Codex, Claude Code, Cursor, or another agent will automatically discover nested instructions.
If a user writes `@pm-copilot` in the host repository, the adapter should resolve it to the local `pm-copilot/PM_COPILOT.md`, not to an external tool call.

## Repository Structure

```text
PM_COPILOT.md  Cross-platform Agent front door
agents/        Agent responsibilities, interface, and operating model
workflow/      Execution graph, context loading, delivery checks, and handoff flow
artifacts/     PRD, UI, trace, structured reference, tool result, and handoff contracts
skills/        Reusable product-management capabilities
tools/         Tool registry, tool-use protocol, and validation notes
prompts/       Prompt assembly, memory, clarification, and generation rules
context/       Product memory, user preferences, decisions, and example context
guardrails/    Safety, privacy, source, assumption, and failover rules
templates/     Artifact and run-log templates
docs/          User, maintainer, use-case, mode, and migration docs
scripts/       Local validation, rendering, extraction, adapter, and scorecard scripts
adapters/      Host-project adapters for Codex, Claude Code, Cursor
```

## Validation And Tools

Common commands:

```bash
python3 scripts/preflight_tools.py
python3 scripts/validate_outputs.py outputs/<run-id>
python3 scripts/run_delivery_checks.py outputs/<run-id> --language en
python3 scripts/validate_agent_trace.py outputs/<run-id>
python3 scripts/analyze_agent_run_evidence.py --json
python3 scripts/setup_visual_validation.py
python3 scripts/validate_prototype_visual.py outputs/<run-id>
python3 scripts/validate_ui_preview.py <preview-url-or-file> --run-folder outputs/<run-id>
python3 scripts/render_prd_html.py outputs/<run-id>
python3 scripts/agent_improvement_scorecard.py
python3 scripts/validate_repo.py
```

`tools/tool-registry.yaml` is the source of tool capability truth.
Tool results should follow `artifacts/tool-result-contract.md` where possible.
Use `validate_prototype_visual.py` for portable HTML UI deliverables.
Use the host project's preview route for source-backed UI, and run `validate_ui_preview.py` when a URL or file target is available.

## Memory

PM Copilot uses local file memory to make repeated work more useful:

- `context/product-memory.local.yaml` for stable product facts
- `context/user-preferences.local.yaml` for the user's working style
- `context/decision-log.local.yaml` for durable product decisions
- `outputs/<run-id>/run-log.yaml` for one-run traces

The repository ships `.example.yaml` schemas only.
`.local.yaml` memory files are ignored by Git and should stay private.
Current user instructions and current product context always override memory.

## Platform Neutrality

PM Copilot is not tied to a specific agent framework.
It is composed of portable Markdown contracts, scripts, and templates that can work in Codex, Claude Code, Cursor, or internal agent platforms.
Agents define responsibilities, skills provide methods, workflow provides the execution graph, artifacts define acceptance, tools provide validation, and guardrails constrain high-risk behavior.

## Maintainer Entry Points

- `docs/release-checklist.md`: release checks
- `docs/optimization-playbook.md`: system improvement method
- `docs/self-improvement-system.md`: self-improvement system
- `docs/practice-self-iteration.md`: converting real feedback into generic capability
- `docs/versioning.md`: versioning policy
