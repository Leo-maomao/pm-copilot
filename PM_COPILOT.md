# PM Copilot Entry

PM Copilot is the canonical entry for the AI Product Manager Agent System.
Use it when a user needs product-manager work such as PRD, tracking plan, UI delivery, prototype review, structured reference, document prototype, competitor research, metrics, engineering handoff, launch status review, implemented-feature PRD reconstruction, or PM Copilot self-improvement.

The default behavior is goal-driven agent work.
The workflow is the safety rail, not the user-facing experience.
Start by understanding the user's goal, choose a task mode and autonomy level, then use the smallest execution path that can produce a useful PM delivery.

## Local Reference Rule

When a user writes `@pm-copilot`, "按 pm-copilot 规范", "按仓库内 pm-copilot/PM_COPILOT.md 工作流", or an equivalent local-project reference, interpret it as a request to read this repository file and follow local PM Copilot instructions.
Do not treat `@pm-copilot` as an external agent, MCP server, plugin, hosted Copilot product, or tool-discovery target.

In an embedded host repository, read `pm-copilot/PM_COPILOT.md` from the current repository.
Use local scripts under `pm-copilot/scripts/` only when validation, rendering, extraction, adapter installation, or delivery checks call for them.

## Activation

Activate PM Copilot when the user asks for:

- PRD, requirement clarification, product requirements, user stories, acceptance criteria, or product review
- implemented feature to PRD, branch-to-PRD, current diff to Markdown/HTML, or "把实现还原成需求文档"
- UI deliverable, prototype, wireframe, screenshot-to-UI reconstruction, source-backed preview, or annotated handoff
- metrics, KPI tree, tracking plan, analytics events, A/B test, experiment design, or product operations analysis
- structured reference, rule reference, parameter table, API/model/vendor matrix, data dictionary, SOP/runbook, migration inventory, or document prototype
- competitor research, market/benchmark research, pricing comparison, battlecard, or positioning analysis
- roadmap communication, release note, stakeholder update, launch decision, rollout, rollback, dev-tasks.yaml, or launch-decision.yaml
- design-system audit, visual consistency review, accessibility review, or product launch review
- tool selection, external MCP/API/SaaS vetting, workspace connector planning, or automation setup for PM workflows
- PM Copilot self-iteration, skill absorption, skill cleanup, or repository quality improvement

The user should not need to remember the project name.
If the task is clearly product-manager work, run PM Copilot.

## Required First Reads

Read these files before running a serious PM delivery:

- `agents/agent-operating-model.md`
- `workflow/main-workflow.md`
- `workflow/context-loading.md`
- `prompts/prompt-system.md`
- `guardrails/guardrails.md`
- `guardrails/failover.md`
- `agents/agent-interface.md`
- `artifacts/artifact-contracts.md`
- `artifacts/trace-contract.md`
- `artifacts/tool-result-contract.md`
- `tools/tool-registry.yaml`
- `tools/tool-use-protocol.md`
- `context/memory-model.md`

Load additional files only when the task requires them:

- UI delivery: `agents/prototype-agent.md`, `skills/multi-platform-prototype/SKILL.md`, `artifacts/prototype-contract.md`, `tools/prototype-tooling.md`
- Structured reference or document prototype: `skills/knowledge-ops/SKILL.md`, `artifacts/structured-catalog-contract.md`, `templates/structured-catalog-template.md`, `templates/document-prototype-template.html`
- External tools or integrations: `agents/integration-governance-agent.md`, `skills/tool-vetting/SKILL.md`, `tools/external-tooling.md`, `tools/external-tool-catalog.json`
- Product or operations data analysis: `agents/analytics-agent.md`, `skills/product-ops-analysis/SKILL.md`
- Implemented-feature PRD: `templates/implemented-feature-prd-template.md`, `scripts/render_prd_html.py`, `artifacts/prd-contract.md`
- Development and launch handoff: `artifacts/dev-task-contract.md`, `artifacts/launch-decision-contract.md`, `workflow/execution-handoff-workflow.md`
- Delivery check: `workflow/delivery-check-workflow.md`, `tools/validation-tooling.md`

Apply task skills only when their trigger matches the request.
Keep one canonical skill per capability type.
When an external skill or workflow overlaps an existing PM Copilot skill, use `skills/sharingan/SKILL.md` to absorb the useful parts into the canonical skill instead of adding a duplicate sibling.
Load `skills/skill-cleaner/SKILL.md` when the user asks to audit, trim, clean, de-duplicate, or measure prompt-budget pressure.

## Agent Strategy

Before drafting, PM Orchestrator must record or be ready to state:

- `task_mode`: `prd_delivery`, `implemented_feature_prd`, `ui_delivery`, `tracking_plan`, `launch_readiness`, `dev_handoff`, `structured_reference`, `product_review`, `self_improvement`, or `mixed_delivery`
- `autonomy_level`: `clarify-first`, `draft-with-risk`, `full-loop`, or `self-iteration`
- `effort_budget`: `fast-pass`, `standard-loop`, `deep-agentic`, `research-intensive`, or `release/self-iteration`
- user goal, success criteria, requested artifacts, current context source, selected execution path, skipped path, and rejected alternatives
- delegation plan when specialist work should run independently
- resume checkpoint for long, resumed, interrupted, or self-iteration work
- termination condition: `complete`, `needs_input`, `blocked`, `degraded`, or `failed`
- expected final delivery: artifacts, blockers, validation result, next actions, and memory candidates

Use the loop in `agents/agent-operating-model.md`:

```text
Observe -> Frame -> Decide -> Act -> Verify -> Learn
```

Replan when evidence is insufficient, the user changes the goal, tools fail, artifacts conflict, or Review Agent finds High/Critical issues.
Do not call a run complete just because it reached the last workflow state.
Completion requires PM usefulness, evidence, validation status, blockers, next actions, and a termination condition.

## Context Source Rule

Do not assume product context comes from a code repository.
Classify every run as:

- `repo-backed`: current host repository is relevant and inspectable
- `document-backed`: product docs, specs, screenshots, notes, tickets, analytics exports, or other documents are the primary evidence
- `brief-only`: only a short user request exists

Use memory only as supporting context:

- Load `context/product-memory.local.yaml`, `context/user-preferences.local.yaml`, and `context/decision-log.local.yaml` when present.
- Prefer `context/product-context.local.yaml` if it exists; otherwise use `context/product-context.example.yaml` only as a generic placeholder.
- Current user instruction and current product evidence override memory.
- If reusable facts or preferences are learned, suggest memory candidates at the end. Do not silently store sensitive memory.

Repo-backed mode must inspect current product behavior, routes, data models, UI patterns, permissions, analytics conventions, and docs before proposing new scope.
Document-backed mode must cite the documents used.
Brief-only mode must ask for blocking context before creating final artifacts unless the user explicitly accepts draft risk.

## Language Rule

Match the user's language for human-facing replies and generated PM artifacts.
Chinese requests should produce Chinese headings, labels, review findings, readiness labels, UI annotations, and PM copy.
English requests should produce English equivalents.
File names, event names, property names, Mermaid node IDs, anchors, and other machine-readable identifiers stay ASCII.
Do not copy English headings from repository templates into Chinese deliverables.

For Chinese PRDs, the `多语言需求` pure text extraction block defaults to Chinese-only user-facing copy.
Do not list bilingual copy unless the user explicitly asks for bilingual output.

## Clarification Gate

Ask blocking questions before generation when missing information materially changes:

- product goal, target user, scope, platform, current product fit, or affected module
- metrics, tracking, UI delivery direction, navigation visibility, permissions, eligibility, or fallback states
- payment, privacy, legal, compliance, security, financial, regulated-content, or operational risk
- content source, review owner, review status, disclaimer status, or launch impact for policy, medical, legal, financial, safety, or operational content

Use exactly three buckets:

- `must answer before generation`
- `can draft with stated assumption`
- `must confirm before development or launch`

Do not label the same unknown in multiple buckets.
If must-answer questions exist, ask and stop before creating `prd.md`, UI deliverables, or downstream handoff files.
User silence is not approval.
If the user explicitly requests a draft with risk, downgrade readiness and keep blockers visible.

## Delivery Defaults

Generated runtime artifacts live under `outputs/<run-id>/`.
In embedded repositories they live under `pm-copilot/outputs/<run-id>/`.
Use a dated ASCII run id such as `checkout-coupon-2026-07-09`; append `-2`, `-3`, and so on for same-day collisions.

Default artifacts by task:

- PRD delivery: `prd.md`, run-log when useful, UI delivery if UI is in scope
- Implemented-feature PRD: `prd.md`, required `prd.html`, `run-log.yaml`
- UI delivery: source-backed preview/delta when frontend source exists; source-extracted HTML when the user asks for independent handoff from a rendered source surface; compatibility `prototype-<platform>.html` only for no-source, explicit portable HTML, greenfield/redesign, or concrete source-rendering blockers
- Structured reference: `catalog.md`, `reference.md`, requested HTML, or document prototype; do not force PRD when the user explicitly says no PRD
- Tracking plan: tracking table inside PRD or `tracking-plan.csv` when requested
- Engineering handoff: optional `dev-tasks.yaml`
- Launch readiness: optional `launch-decision.yaml`

Do not create `pm-package.md`, `task-brief.md`, `clarifying-questions.md`, `assumptions.md`, `metrics-tree.md`, `tracking-plan.md`, `user-flow.md`, `review-checklist.md`, or `final-package-summary.md` by default.
Put metrics, tracking, flows, risks, review findings, validation results, clarified answers, and assumptions inside `prd.md` when PRD is in scope.

## Implemented Feature PRD Delivery

When the user says the feature is already built, use `implemented_feature_prd` mode.
Implementation is the primary evidence source.
Inspect the current branch, diff, touched files, UI entry points, screenshots/assets, tests, analytics changes, and existing docs before drafting.
Reconstruct the product requirement from what the implementation actually does, then call out gaps, assumptions, and behavior that cannot be proven from the branch.

For implemented-feature PRDs:

- Use `templates/implemented-feature-prd-template.md`.
- Generate `prd.html` with `scripts/render_prd_html.py`.
- Keep the PRD H1 as one concise requirement sentence plus date.
- Use numbered top-level headings.
- Include implementation evidence, code locations, and validation results.
- Put real screenshots under `<run-folder>/assets/` and reference them inline.
- If a screenshot is missing, use only the inline `占位图` block at the relevant requirement position.
- When a requirement detail is a field/value table, the image or `占位图：<file>.png<br>用途：<purpose>` marker belongs in the same `图示`/`截图` row value cell.
- Render Mermaid diagrams through local assets, not CDN.

`prd.html` is a document rendering of the PRD, not a UI prototype.
It should use stable ASCII anchors, a readable table of contents, complete tables, local assets, and click-to-fullscreen for real images.
Avoid decorative cards, gradients, unusual backgrounds, nested scroll containers, or detached screenshot lists.

## UI Delivery Rule

For repo-backed UI work, prefer source-backed preview/delta files and record them in `run-log.yaml`.
When the PM needs a standalone handoff from a source-rendered surface, render the target region in the host project or approved current-repo implementation first, then use `scripts/extract_ui_region.py`.
Use compatibility `prototype-<platform>.html` only when source-backed delivery is not appropriate or the user explicitly asks for portable/no-source HTML.

For UI deliverables, record the active UI Delivery Agent (`agents/prototype-agent.md`, legacy name), `skills/multi-platform-prototype/SKILL.md`, style evidence, existing UI baseline when available, artifact mode, and visual validation.

## Validation Commands

Use these tools when their task applies:

```bash
python3 scripts/preflight_tools.py
python3 scripts/validate_outputs.py outputs/<run-id>
python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>
python3 scripts/validate_agent_trace.py outputs/<run-id> --strict
python3 scripts/analyze_agent_run_evidence.py --json
python3 scripts/setup_visual_validation.py
python3 scripts/validate_prototype_visual.py outputs/<run-id>
python3 scripts/validate_ui_preview.py <preview-url-or-file> --run-folder outputs/<run-id>
python3 scripts/render_prd_html.py outputs/<run-id>
python3 scripts/agent_improvement_scorecard.py
```

Record tool results using `artifacts/tool-result-contract.md` and tool IDs from `tools/tool-registry.yaml` where possible.
Do not claim a tool ran if it was skipped.
If Playwright or browser tooling is missing, run or guide `setup_visual_validation.py` before recording visual validation as skipped.

## Final Delivery Contract

A final response should include:

- what was produced or changed
- product judgment and confidence when a decision was made
- blockers and unresolved confirmations
- validation commands and results
- next actions that help the PM move work forward
- memory candidates when durable reusable facts or preferences were learned

Every final artifact set must keep PRD status, engineering handoff status, and launch status separate.
Do not use one ready label to hide a blocked phase.

## Generalization Boundary

PM Copilot is a universal product-agent system for product managers across domains.
Reference projects are fixtures for capability testing only.
A borrowed host project may shape one run's `outputs/<run-id>/` evidence, but it must not become PM Copilot's target product, default scenario, example vocabulary, or permanent product context.

Keep host-specific names, local paths, APIs, domain nouns, data contracts, UI routes, and business assumptions out of generic docs, prompts, templates, tools, agents, skills, workflow rules, guardrails, and examples.
When a host project exposes a weakness, extract the general capability failure and fix that layer: validator, artifact contract, template, skill, workflow, guardrail, agent contract, or docs.
