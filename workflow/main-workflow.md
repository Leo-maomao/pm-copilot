# Main Workflow

PM Copilot 3.0 uses this file as an execution graph, not as a fixed linear workflow.
The default path is still S0-S12, but PM Orchestrator may skip, merge, repeat, or backtrack states according to `agents/agent-operating-model.md`.
Every skip, merge, backtrack, and rejected route must be recorded in `run-log.yaml`.

## Agentic Execution Graph

Default graph:

```text
S0 Intake
-> S1 Tool preflight
-> S2 Context loading
-> S2b Implemented feature evidence scan
-> S3 Discovery and clarification
-> S4 Clarification gate
-> S5 External product research
-> S6 PRD drafting
-> S6b Structured reference drafting
-> S7 Metrics and tracking
-> S8 Flow and UI delivery
-> S8b Document prototype delivery
-> S9 Review
-> S10 Revision loop
-> S11 Delivery Orchestrator
-> S12 Execution Handoff
```

Dynamic graph rules:

- Start with Observe, Frame, Decide, Act, Verify, Learn from `agents/agent-operating-model.md`.
- Classify `task_mode` before state selection: `prd_delivery`, `implemented_feature_prd`, `ui_delivery`, `tracking_plan`, `launch_readiness`, `dev_handoff`, `structured_reference`, `product_review`, `self_improvement`, or `mixed_delivery`.
- Select `autonomy_level`: `clarify-first`, `draft-with-risk`, `full-loop`, or `self-iteration`.
- Select `effort_budget`: `fast-pass`, `standard-loop`, `deep-agentic`, `research-intensive`, or `release/self-iteration`.
- Record `delegation_plan` when specialist work is split across agents, workers, or independent tool passes.
- Record `termination_condition` before final delivery so completion is based on PM usefulness and evidence, not state count.
- Use S0-S12 as the safe default when the task spans PRD, UI delivery, review, and validation.
- Skip states that are irrelevant to the selected task mode. Example: `tracking_plan` can skip S8 UI delivery when no user-facing UI is in scope.
- Merge states when a lightweight task would otherwise create ceremony. Example: `launch_readiness` may merge S9 Review, S11 Delivery Orchestrator, and S12 Execution Handoff.
- Backtrack when evidence, user answers, tools, review, or validation contradict an earlier decision.
- Replan when a High/Critical review finding appears, context source changes, tool output fails, artifacts conflict, or the user changes the goal.

## State Definitions

| State | Owner | Entry Criteria | Exit Criteria |
|---|---|---|---|
| S0 Intake | PM Orchestrator | Task brief received | Goal, task mode, autonomy level, success criteria, and requested artifacts are identified |
| S1 Tool preflight | PM Orchestrator | Full-loop, self-iteration, embedded, UI, final delivery, or external integration work is expected | Available, setup-required, unavailable, skipped, and not_applicable tools are recorded |
| S2 Context loading | PM Orchestrator | Product context source is unknown or needs discovery | `repo-backed`, `document-backed`, or `brief-only` mode is selected and relevant product context is loaded |
| S2b Implemented feature evidence scan | PM Orchestrator + Requirements Agent | User asks to restore PRD/HTML from an already implemented branch or current diff | Changed files, UI surfaces, behavior evidence, screenshots/assets, tests, validation, and unverified intent are recorded |
| S3 Discovery and clarification | Discovery Agent | Request is ambiguous, incomplete, risky, or needs current-product-fit validation | Critical questions, assumptions, open decisions, and confidence are captured |
| S4 Clarification gate | PM Orchestrator | Blocking questions or readiness confirmations exist | User answers are applied, or the output is downgraded to a draft with visible assumption or confirmation risk |
| S5 External product research | Research Agent | Product solution, copy, metrics, UI direction, policy, pricing, or comparable feature evidence can improve the decision | Source-backed research is produced, or the limitation and confidence impact are recorded |
| S6 PRD drafting | Requirements Agent | PRD is in scope and discovery output is usable | `prd.md` satisfies `artifacts/prd-contract.md` |
| S6b Structured reference drafting | Knowledge Ops Agent | User asks for structured reference, parameter table, model/API/vendor matrix, rule reference, data dictionary, SOP/runbook, or migration inventory | `catalog.md`, `reference.md`, requested HTML, or document prototype satisfies `artifacts/structured-catalog-contract.md` |
| S7 Metrics and tracking | Analytics Agent | Goals, user actions, or launch decisions need measurable evidence | Metrics and tracking are complete inside `prd.md` or `tracking-plan.csv` when requested |
| S8 Flow and UI delivery | UI Delivery Agent (`agents/prototype-agent.md`, legacy name) | User-facing UI, flow, surface fit, visual parity, or interaction states are in scope | Flow/UI delivery contract is satisfied and validation route is known |
| S8b Document prototype delivery | UI Delivery Agent + Knowledge Ops Agent | User asks for browser-readable reference/document review surface | Document prototype declares `pm-copilot-artifact=document_prototype` and renders source/review status, structured data, and typed `attention_points` |
| S9 Review | Review Agent | Draft artifacts exist or a review-only request is active | PM usefulness review, structured review findings, risks, blockers, alternatives, and required fixes are recorded |
| S10 Revision loop | PM Orchestrator | Review, validation, or user feedback finds material gaps | Artifacts are updated, or gaps are accepted as visible residual risk |
| S11 Delivery Orchestrator | PM Orchestrator | Artifacts are ready for final check or a release/eval run needs evidence | `scripts/run_delivery_checks.py` passes, or failures are fixed/recorded with impact |
| S12 Execution Handoff | PM Orchestrator | User asks for issue planning, development handoff, release readiness, or go/no-go support | `dev-tasks.yaml` and/or `launch-decision.yaml` preserve blockers, approvals, rollout, rollback, and validation gaps |

## Task Mode Routing

| Task Mode | Typical Path | Notes |
|---|---|---|
| `prd_delivery` | S0-S5-S6-S7-S8-S9-S11 | Default feature requirement delivery. |
| `implemented_feature_prd` | S0-S2-S2b-S3-S6-S9-S11 | Implementation is evidence; `prd.html` is required and rendered with `render_prd_html.py`. |
| `ui_delivery` | S0-S2-S3-S8-S9-S11 | Use source-backed preview/delta when frontend source exists; compatibility HTML is fallback or explicit portable scope. |
| `tracking_plan` | S0-S2-S3-S7-S9-S11 | Metrics and event taxonomy are primary; UI states are included only when they affect triggers. |
| `launch_readiness` | S0-S2-S9-S11-S12 | Readiness, risk, owner, rollback, and approval evidence are primary. |
| `dev_handoff` | S0-S2-S6/S8-S9-S12 | Converts confirmed scope into issue-ready work without hiding open blockers. |
| `structured_reference` | S0-S2-S6b-S8b-S9-S11 | PRD is not forced when the user asks for a reference/document handoff. |
| `product_review` | S0-S2-S9-S10-S11 | Review existing artifacts or implementation; no new PRD unless explicitly requested. |
| `self_improvement` | S0-S1-S2-S9-S10-S11 | Improve PM Copilot itself with release metadata and optimization-cycle evidence. |
| `mixed_delivery` | S0-S12 as needed | Use the smallest graph that covers all requested outcomes. |

## Agent State And Handoff Discipline

All specialist work follows `agents/agent-interface.md`.
PM Orchestrator records each transition in `run-log.yaml` with:

- Agent name, owner state, task mode, and autonomy level.
- Effort budget, delegation plan, resume checkpoint, and termination condition when they affect the path.
- Input evidence used and confidence.
- Product judgment, decisions made, rejected alternatives, and next expected output.
- Output status: `complete`, `needs_input`, `blocked`, `degraded`, or `failed`.
- Artifact delta: files created, changed, omitted, or unchanged.
- Validation delta: commands run, skipped, required later, or not applicable.
- Readiness impact: PRD, engineering handoff status, launch status, or none.

State transitions are append-only for audit purposes.
If a later agent changes an earlier decision, record the superseding decision, evidence, affected artifact, and reason instead of deleting the earlier state.

Document-class revision loops must use object-level patching.
Updating one entity, field group, rule, or SOP step must not rewrite unrelated objects.
Presentation-only requests must not change structured source facts, product decisions, defaults, enums, limits, or rules.

PM Orchestrator is the only owner of final readiness labels.
Specialist agents may recommend readiness, blockers, and fixes, but final `prd_status`, `engineering_handoff_status`, and `launch_status` must be reconciled after Review Agent and delivery checks.

## Resume And Idempotency

When continuing an existing run:

- Load the latest `outputs/<run-id>/run-log.yaml` before editing artifacts.
- Continue from the last reliable workflow state.
- Do not create a new run id unless the user asks for a new iteration or the existing folder is clearly a different requirement.
- Do not duplicate optional exports that already exist unless the new output supersedes them and the reason is recorded.
- Preserve prior blockers until they are answered, accepted as draft risk, or moved out of current scope.

If a run log is missing or malformed, continue only after recording the limitation and reconstructing the minimum safe state from existing artifacts and current user input.

## Conflict Resolution

If agent outputs contradict each other:

1. Prefer current user instruction and current product evidence over memory or older artifacts.
2. Prefer validated tool output over unvalidated prose when they describe the same artifact state.
3. Keep launch-sensitive, security-sensitive, privacy-sensitive, payment-sensitive, financial, legal, and regulated-content uncertainty open unless explicit approval evidence exists.
4. Route unresolved contradictions to Review Agent before final delivery.
5. Record the final resolution in `run-log.yaml` and in the PRD readiness or risk section when it affects reviewers.

## Tool Preflight

Use `tools/tool-registry.yaml` as the source of tool capability truth.
Run preflight before full-loop iteration, embedded host evaluation, UI delivery validation, external integration work, release validation, or any final delivery that claims tool-backed evidence:

```bash
python3 scripts/preflight_tools.py
```

Use `--strict` for PM Copilot release validation or other runs where missing required tooling must stop delivery.
If external research is required, include `--check-network <url> --require-network --strict`.

Record the result under `tool_preflight` in `run-log.yaml`.
If a required tool is `setup_required`, `unavailable`, or `skipped` under strict preflight, run or guide the setup command before deciding to skip the dependent check.

## External Integration Vetting

External MCP servers, SaaS APIs, OAuth tools, automation connectors, paid UI generators, analytics platforms, databases, CRM/support systems, and advertising tools require a separate vetting pass before PM Copilot depends on them.

Use Integration Governance Agent with `skills/tool-vetting/SKILL.md`, `tools/external-tooling.md`, and `tools/external-tool-catalog.json`.
Run:

```bash
python3 scripts/preflight_integrations.py --tier recommended
```

Add `--check-remote` when current source availability is part of the decision.
Add `--require-ready` only when selected integrations must be configured before the run can continue; candidate and hold tools are not ready for required use.

Record the result under `external_integrations` in `run-log.yaml`.
Missing API keys, OAuth consent, paid accounts, workspace permissions, or production-data credentials are `setup_required` or `blocked`.
Default to read-only scopes for analytics, databases, CRM, support, project-management, ads, and workspace data.
Write operations require explicit user approval for the concrete action.

## Human-in-the-Loop Checkpoints

Human confirmation is required before drafting downstream artifacts when:

- The product goal or target user is unclear.
- The current product state is unknown and could change the proposed solution.
- Scope materially affects engineering effort, payment, privacy, legal, compliance, security, financial, or operational risk.
- The agent must choose between materially different product directions.
- Platform, affected module, primary user journey, or rollout surface is unclear.
- The tracking plan includes sensitive properties.
- Research sources are unavailable but competitor claims would affect the solution.
- The PRD/UI-delivery output contains high-severity open risks.
- An item is marked `must confirm before development or launch` and the requested output is expected to claim the readiness that item blocks.

If any must-answer question exists, ask the user and stop before creating `prd.md` or UI deliverables.
Create or update only `outputs/<run-id>/run-log.yaml` when a persistent trace is useful.
User silence is not approval.

## External Product Research

For PRD deliveries, S5 is expected by default when product solution, copy, metrics, UI delivery direction, policy, pricing, or comparable feature evidence can materially improve the decision.
Repository files are current-state context, not external product research.
Do not fill the PRD research section only with host implementation facts.

Use Research Agent to look for relevant competitors, benchmark products, comparable feature patterns, public docs, help center pages, product screenshots/articles, or official policy/pricing sources.
Record source title, URL, access date when available, observed fact, product implication, limitation, and confidence.
If browsing is unavailable or the user explicitly says not to research, record `external_research.status: skipped` or `degraded`, the reason, and the impact on recommendation confidence.

## Document-Class Delivery

Use document-class delivery when the user primarily needs structured knowledge rather than a product feature spec.
Examples include parameter references, API or vendor capability catalogs, payment/risk rules, data dictionaries, SOPs, runbooks, migration inventories, and browser-readable document summaries.

Classify the delivery before drafting:

- `structured_reference`: structured facts, fields, rules, decisions, attention points, and handoff notes are the primary artifact.
- `document_prototype`: HTML prototype is a document/reference review surface.
- `mixed_delivery`: PRD plus structured reference or document prototype are both needed.

If the user explicitly says no PRD is needed, do not generate `prd.md`.
Record PRD as not applicable in the run log and make the structured reference or document prototype the primary delivery.

For document-class artifacts, maintain one structured source of truth before rendering.
Separate extracted `source_facts` from final `product_decisions`, preserve hierarchy and conditional rules, record `attention_points`, and run a completeness check before delivery.

## Implemented-Feature PRD Delivery

Use this mode when the feature has already been implemented or changed in the current branch and the user asks PM Copilot to restore, reverse-engineer, or package the requirement into Markdown and HTML.

Classification:

- `implemented_feature_prd`: PRD is reconstructed from current branch evidence; `prd.html` is required.
- `implemented_feature_prd_html`: legacy alias for older run logs; keep accepting it, but do not treat it as the only mode that requires `prd.html`.
- `implemented_feature_prd_review`: existing PRD/HTML is being corrected against the implementation.

Before S3 clarification, run S2b:

- Inspect branch status and diff using normal source-control tools.
- Read changed files and nearby product context, including UI entry points, menus, dialogs, feature flags, permissions, data operations, analytics, copy, i18n, and tests when present.
- Inspect screenshots/assets supplied by the user.
- If images are not ready, define inline placeholder positions in the PRD instead of creating a detached image list.
- Record evidence in `run-log.yaml` under `implemented_feature_prd`: branch name when available, diff summary, files inspected, behavior evidence, UI surfaces, screenshots or placeholders, validation evidence, and unverified product intent.
- Ask only for facts that cannot be recovered from implementation evidence and that affect product intent, rollout, launch approval, metrics, legal/privacy/compliance, or screenshot replacement.

Drafting rules:

- Treat implementation evidence as current-product truth, but distinguish observed behavior from product intent.
- Reconstruct background, goals, scope, entry points, interaction flow, business logic, data rules, permissions, edge cases, tracking, acceptance criteria, and risks.
- Include an implementation-to-requirement coverage map.
- If implementation reveals behavior that seems incomplete, inconsistent, or not product-approved, record it as a risk or open confirmation.

HTML rendering rules:

- Generate `outputs/<run-id>/prd.html` for implemented-feature PRD delivery even when the user only asks for Markdown.
- `prd.html` is a document rendering of `prd.md`, not a product UI prototype.
- Use neutral document styling. Avoid unusual background colors, gradients, decorative cards, nested scroll containers, or marketing/prototype visual style.
- Preserve full table readability and render Mermaid diagrams through local assets.
- Put images and image placeholders inline at the exact relevant PRD position, including table cells when the image explains that row.
- Local image paths must resolve inside the run folder or its `assets/` subfolder.

## UI Visual Validation

When compatibility HTML UI deliverables are generated, run:

```bash
python3 scripts/validate_prototype_visual.py outputs/<run-id>
```

For source-backed UI previews, run the host dev/preview/Storybook/simulator path.
When a browser preview URL or local preview file exists, run:

```bash
python3 scripts/validate_ui_preview.py <preview-url-or-file> --run-folder outputs/<run-id>
```

If Playwright or browser tooling is missing, first run or guide:

```bash
python3 scripts/setup_visual_validation.py
```

Only record `visual_validation.status: skipped` after setup fails, browser launch is forbidden, or the user declines installation.

## Delivery Orchestrator

Before final delivery, prefer:

```bash
python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>
```

The Delivery Orchestrator verifies that PRD, structured reference, UI deliverable, readiness, structured review findings, validation results, and trace evidence are consistent.
When the run is pre-clarification only, use the script's pre-clarification mode and do not create downstream artifacts.

## Execution Handoff

When the user requests engineering handoff, issue planning, release readiness, rollout, rollback, or launch decision support, generate:

- `dev-tasks.yaml` only when implementation tasks are useful and source requirements are clear enough.
- `launch-decision.yaml` only when launch status, blockers, owner approvals, validation evidence, and rollback plan matter.

Do not hide unresolved blockers in handoff files.
The PM Orchestrator must keep PRD status, engineering handoff status, and launch status separate.

## Practice-Driven Self-Iteration

Use `self_improvement` mode when a real PM Copilot delivery reveals a workflow defect and the user asks to improve PM Copilot itself.

Self-iteration flow:

1. Load the completed run artifacts, user corrections, validation reports, and relevant source files before changing PM Copilot.
2. Classify each issue with `docs/failure-taxonomy.md` and rewrite host-specific symptoms as reusable product-agent failures.
3. Choose the smallest durable fix surface: validator/tool, artifact contract, template, skill, workflow, guardrail, agent interface, docs.
4. If the issue can be detected mechanically, update a validator. Prompt-only fixes are not enough for repeatable failures.
5. Add or update an eval case for high-severity, repeated, or cross-surface failures.
6. Update an optimization-cycle note with source run, generalized failure, fix surface, validation, version, and sync targets.
7. Bump `VERSION`, update `CHANGELOG.md`, run release validation, and sync embedded copies when requested.

Self-iteration is complete only when the generic PM Copilot repository validates and the user-facing failure would be prevented by rules or caught by tooling in a future run.

## Generalization Boundary

PM Copilot serves product managers across industries and product types.
Reference projects are fixtures for capability testing only.
Self-iteration may use real host projects to create pressure, but durable instructions must remain general.
Do not promote a host project's terminology, domain, local path, backend contract, route name, analytics vocabulary, visual style, or user journey into generic PM Copilot instructions.

Allowed host-specific locations:

- `outputs/<run-id>/` runtime evidence for that run.
- `evals/` fixture-scoped regression cases that explicitly describe themselves as fixtures.

Disallowed generic locations:

- `PM_COPILOT.md`
- `README*.md`
- `workflow/`
- `prompts/`
- `agents/`
- `skills/`
- `templates/`
- `tools/`
- `artifacts/`
- `guardrails/`
- `docs/`
- `context/*.example.yaml`

## Clarification Semantics

Avoid contradictory clarification output.
A single unknown must belong to exactly one bucket:

- `must answer before generation`: blocks PRD, metrics, tracking, flow, UI delivery, review, and delivery check.
- `can draft with stated assumption`: can be assumed for a draft PRD/UI deliverable, but the assumption must be visible and reviewable.
- `must confirm before development or launch`: blocks the readiness phase it applies to. Each item must state whether it blocks engineering handoff, launch, or both.

If the user asks to proceed with assumptions while must-answer or engineering-blocking confirmation questions remain, downgrade PRD status to `Draft with assumption risk` or `Draft with confirmation risk`.
Do not call it development-ready.
If only launch-blocking confirmations remain, the PRD may be engineering-ready only when launch status is explicitly blocked and engineering acceptance criteria exclude the unconfirmed launch item.

## Readiness Model

Every final delivery must carry three related but separate readiness fields:

- PRD status: whether the delivery is blocked, a draft, ready for review, or ready for engineering.
- Engineering handoff status: whether engineering can build the confirmed scope now, and which decisions block implementation.
- Launch status: whether shipped behavior, content source, copy, compliance, analytics, and operational process are approved for release.

Do not use one `Ready` label to hide a blocked phase.
A framework can be ready for engineering while content, legal copy, or operational approval blocks launch; the PRD must say both facts.
