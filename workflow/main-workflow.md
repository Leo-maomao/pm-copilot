# Main Workflow

## Default Flow

```text
S0 Intake
-> S1 Tool preflight
-> S2 Context loading
-> S2b Implemented feature evidence scan (when current branch already contains the feature)
-> S3 Discovery and clarification
-> S4 Clarification gate
-> S5 External product research
-> S6 PRD drafting
-> S7 Metrics and tracking
-> S8 Flow and UI delivery
-> S9 Review
-> S10 Revision loop
-> S11 Delivery check
-> S12 Optional execution handoff
```

## State Definitions

| State | Owner | Entry Criteria | Exit Criteria |
|---|---|---|---|
| S0 Intake | PM Orchestrator | Task brief received | Request goal and artifact needs are identified |
| S1 Tool preflight | PM Orchestrator | Full-loop, embedded, final delivery, or external integration work is expected | Available, setup-required, and unavailable tools are recorded |
| S2 Context loading | PM Orchestrator | Product context source is known or needs discovery | Relevant PM Copilot context and available product context are loaded |
| S2b Implemented feature evidence scan | PM Orchestrator + Requirements Agent | User asks to generate PRD/HTML from an already implemented branch or current diff | Changed files, UI surfaces, behavior evidence, screenshots/assets, tests, validation, and unverified intent are recorded |
| S3 Discovery and clarification | Discovery Agent | Request is ambiguous, incomplete, or needs current-product-fit validation | Critical questions, assumptions, and open decisions are captured |
| S4 Clarification gate | PM Orchestrator | Clarification questions exist or blocking assumptions are detected | User answers are applied, or the user explicitly asks for a draft with assumption or confirmation risk |
| S5 External product research | Research Agent | PRD solution shaping needs competitor, benchmark, comparable feature, market, policy, pricing, or source-backed context | Source-backed research brief is produced or limitation is stated |
| S6 PRD drafting | Requirements Agent | Discovery output is usable | `prd.md` contract is satisfied |
| S6b Structured reference drafting | Knowledge Ops Agent | User asks for document-class handoff, structured reference, parameter table, model/API/vendor matrix, rule reference, data dictionary, SOP/runbook, or migration inventory | `catalog.md`, `reference.md`, requested HTML, or document prototype satisfies `artifacts/structured-catalog-contract.md` |
| S7 Metrics and tracking | Analytics Agent | PRD includes goals and user actions | Metrics and tracking sections are complete inside `prd.md` |
| S8 Flow and UI delivery | UI Delivery Agent (`agents/prototype-agent.md`, legacy name) | Core flow and platform are known | Flow sections are complete inside `prd.md`; UI delivery contract is satisfied |
| S8b Document prototype delivery | UI Delivery Agent + Knowledge Ops Agent | User asks for HTML/prototype where the content is a document/reference review surface | Document prototype declares `pm-copilot-artifact=document_prototype`, renders structured reference data, and uses typed `attention_points` instead of required product UI annotations |
| S9 Review | Review Agent | Draft PRD and UI deliverable exist | Risks, blockers, and required fixes are reflected in PRD status and validation sections |
| S10 Revision loop | PM Orchestrator | Review finds critical gaps | Artifacts are updated or gaps are accepted as open risks |
| S11 Delivery check | PM Orchestrator | Critical gaps are closed or accepted | `run_delivery_checks.py` passes or failures are fixed/recorded |
| S12 Optional execution handoff | PM Orchestrator | User asks for development tasks, issue planning, release readiness, or launch decision support | `dev-tasks.yaml` and/or `launch-decision.yaml` are generated with blockers and approvals preserved |

## Agent State And Handoff Discipline

All specialist work follows `agents/agent-interface.md`. PM Orchestrator records each agent transition in `run-log.yaml` with:

- Agent name and owner state.
- Input evidence used.
- Output status: `complete`, `needs_input`, `blocked`, `degraded`, or `failed`.
- Artifact delta: files created, files changed, or `none`.
- Validation delta: commands run, skipped, required later, or `none`.
- Readiness impact: PRD, engineering handoff, launch, or `none`.
- Next expected output or human confirmation.

State transitions are append-only for audit purposes. If a later agent changes an earlier decision, record the superseding decision, evidence, and affected artifact rather than deleting the earlier state.

Document-class revision loops must use object-level patching. Updating one entity, field group, rule, or SOP step must not rewrite unrelated objects. Presentation-only requests must not change structured source facts, product decisions, defaults, enums, limits, or rules.

PM Orchestrator is the only owner of final readiness labels. Specialist agents may recommend readiness, blockers, and fixes, but final `prd_status`, `engineering_handoff_status`, and `launch_status` must be reconciled after Review Agent and delivery checks.

## Resume And Idempotency

When continuing an existing run:

- Load the latest `outputs/<run-id>/run-log.yaml` before editing artifacts.
- Continue from the last reliable workflow state.
- Do not create a new run id unless the user asks for a new iteration or the existing folder is clearly a different requirement.
- Do not duplicate optional exports that already exist unless the new output supersedes them and the reason is recorded.
- Preserve prior blockers until they are answered, explicitly accepted as draft risk, or moved out of current scope.

If a run log is missing or malformed, continue only after recording the limitation and reconstructing the minimum safe state from existing artifacts and current user input.

## Conflict Resolution

If agent outputs contradict each other:

1. Prefer current user instruction and current product evidence over memory or older artifacts.
2. Prefer validated tool output over unvalidated prose when they describe the same artifact state.
3. Keep launch-sensitive, security-sensitive, privacy-sensitive, payment-sensitive, financial, legal, and regulated-content uncertainty open unless explicit approval evidence exists.
4. Route unresolved contradictions to Review Agent before final delivery.
5. Record the final resolution in `run-log.yaml` and the PRD readiness or risk section when it affects reviewers.

## Tool Preflight

Use `tools/tool-registry.yaml` as the source of tool capability truth. Run preflight before full-loop iteration, embedded host evaluation, final delivery, or PM Copilot release validation:

```bash
python3 scripts/preflight_tools.py
```

Use `--strict` for PM Copilot release validation or other runs where missing required tooling must stop delivery. If external research is required, include `--check-network <url> --require-network --strict`.

Record the result under `tool_preflight` in `run-log.yaml`. If a required tool is `setup_required`, `unavailable`, or `skipped` under strict preflight, run or guide the setup command before deciding to skip the dependent check.

## External Integration Vetting

External MCP servers, SaaS APIs, OAuth tools, automation connectors, paid UI generators, analytics platforms, databases, CRM/support systems, and advertising tools require a separate vetting pass before PM Copilot depends on them.

Use Integration Governance Agent with `skills/tool-vetting/SKILL.md`, `tools/external-tooling.md`, and `tools/external-tool-catalog.json`. Run:

```bash
python3 scripts/preflight_integrations.py --tier recommended
```

Add `--check-remote` when current source availability is part of the decision. Add `--require-ready` only when the selected integrations must be configured before the run can continue; candidate and hold tools are not ready for required use.

Record the result under `external_integrations` in `run-log.yaml`. Missing API keys, OAuth consent, paid accounts, workspace permissions, or production-data credentials are `setup_required` or `blocked`; they must not be treated as available merely because the tool exists. Default to read-only scopes for analytics, databases, CRM, support, project-management, ads, and workspace data. Write operations require explicit user approval for the concrete action.

## Human-in-the-Loop Checkpoints

Human confirmation is required before drafting downstream artifacts when:

- The product goal or target user is unclear.
- The current product state is unknown and could change the proposed solution.
- Scope materially affects engineering effort, payment, privacy, legal, or compliance.
- The agent must choose between materially different product directions.
- Platform, affected module, primary user journey, or rollout surface is unclear.
- The tracking plan includes sensitive properties.
- Research sources are unavailable but competitor claims would affect the solution.
- The PRD/UI-delivery output contains high-severity open risks.
- An item is marked `must confirm before development or launch` and the requested output is expected to claim the readiness that item blocks.

If any must-answer question exists, ask the user and stop before creating `prd.md` or UI deliverables. Create or update only `outputs/<run-id>/run-log.yaml` when a persistent trace is useful.

Do not create PRD, metrics, tracking, flow, UI-delivery, review, or delivery artifacts until the user answers or explicitly says to proceed with assumptions. User silence is not approval.

## External Product Research

For PRD deliveries, S5 is expected by default when a product solution, feature design, copy, metrics, or UI delivery direction can benefit from competitor or comparable-product evidence. Repository files are current-state context, not external product research. Do not fill the PRD "research/reference findings" section only with host implementation facts.

Use Research Agent to look for relevant competitors, benchmark products, comparable feature patterns, public docs, help center pages, product screenshots/articles, or official policy/pricing sources. When the requested feature changes a common product flow, the research must include same-flow competitor or comparable-product evidence, not only general policy, security, or implementation references. Record source-backed findings and product implications. If browsing is unavailable or the user explicitly says not to research, record `external_research.status: skipped` or `degraded`, the reason, and the impact on recommendation confidence.

Current host files still matter, but they belong in current-state facts, background, product-fit decisions, or the engineering implementation map. Keep external research and repository context separate so reviewers can tell which product decisions are market-informed and which are implementation constraints.

## Document-Class Delivery

Use document-class delivery when the user primarily needs structured knowledge rather than a product feature spec. Examples include parameter references, API or vendor capability catalogs, payment/risk rules, data dictionaries, SOPs, runbooks, migration inventories, and browser-readable document summaries.

Classify the delivery before drafting:

- `product_requirement`: PRD and normal UI delivery are in scope.
- `structured_reference`: structured facts, fields, rules, decisions, attention points, and handoff notes are the primary artifact.
- `document_prototype`: HTML prototype is a document/reference review surface.
- `mixed_delivery`: PRD plus structured reference or document prototype are both needed.

If the user explicitly says no PRD is needed, do not generate `prd.md`. Record PRD as not applicable in the run log and make the structured reference or document prototype the primary delivery.

For document-class artifacts, maintain one structured source of truth before rendering. Separate extracted `source_facts` from final `product_decisions`, preserve hierarchy and conditional rules, record `attention_points`, and run a completeness check before delivery.

## Implemented-Feature PRD Delivery

Use this mode when the feature has already been implemented or changed in the current branch and the user asks PM Copilot to restore, reverse-engineer, or package the requirement into Markdown and HTML.

Classification:

- `implemented_feature_prd`: PRD is reconstructed from current branch evidence.
- `implemented_feature_prd_html`: PRD plus browser-readable `prd.html` are requested.
- `implemented_feature_prd_review`: existing PRD/HTML is being corrected against the implementation.

Before S3 clarification, run S2b:

- Inspect branch status and diff using the host environment's normal source-control tools.
- Read changed files and nearby product context, including UI entry points, menus, dialogs, feature flags, permissions, data operations, analytics, copy, i18n, and tests when present.
- Inspect existing screenshots/assets supplied by the user. If images are not ready, define inline placeholder positions in the PRD instead of creating a detached image list.
- Record evidence in `run-log.yaml` under `implemented_feature_prd`: branch name when available, diff summary, files inspected, behavior evidence, UI surfaces, screenshots or placeholders, validation evidence, and unverified product intent.
- Ask only for facts that cannot be recovered from implementation evidence and that affect product intent, rollout, launch approval, metrics, legal/privacy/compliance, or screenshot replacement.

Drafting rules:

- Treat implementation evidence as current-product truth, but distinguish observed behavior from product intent.
- Reconstruct complete product requirements: background, goals, scope, entry points, interaction flow, business logic, data rules, permissions, edge cases, tracking, acceptance criteria, and risks.
- Include an implementation-to-requirement coverage map so reviewers can see which code evidence supports each requirement and which behavior remains unverified.
- If implementation reveals behavior that seems incomplete, inconsistent, or not product-approved, record it as a risk or open confirmation instead of smoothing it over.
- Do not require the user to manually查漏补缺. If a behavior is visible in the branch, include it in the PRD; if it cannot be verified, mark the gap explicitly with owner and impact.

HTML rendering rules:

- Generate `outputs/<run-id>/prd.html` when the user asks for HTML, browser-readable output, or externally deliverable documents.
- `prd.html` is a document rendering of `prd.md`, not a product UI prototype. It may have a left table of contents, but the right side is the normal document content area; do not wrap content in decorative cards, nested scrolling containers, or mixed module/text blocks.
- Use neutral document styling. Avoid unusual background colors, gradients, shadows, card-heavy sections, or a marketing/prototype visual style.
- Preserve full table readability. Wide requirement tables must keep all semantic columns present and use wrapping or horizontal overflow without hiding the acceptance column or other rightmost fields.
- Render Mermaid diagrams as diagrams in HTML. Do not leave raw Mermaid code blocks visible in final HTML.
- Put images and image placeholders inline at the exact relevant PRD position, including table cells when the image explains that row. Do not add a separate screenshot/image list.
- Local image paths must resolve inside the run folder or its `assets/` subfolder. Real images should support click-to-fullscreen or equivalent lightbox viewing.

## Evaluation And Default-Option Mode

When the user explicitly asks PM Copilot to run iterative evaluation, self-iteration, benchmark loops, or to choose recommended options automatically, do not stop the loop for clarification questions. Instead:

- Select the most conservative recommended option that fits the current product context.
- Preserve the Generalization Boundary: any borrowed host project is a fixture for this run only, not a PM Copilot product default or reusable domain assumption.
- Record the chosen option and rationale in `run-log.yaml`.
- Generate the full `prd.md`, UI deliverable, and `run-log.yaml` for that round.
- Keep unresolved launch or engineering confirmations visible in readiness and risks.
- Downgrade readiness when a default option creates assumption or confirmation risk.
- Never use default-option mode to approve payment, privacy, legal, compliance, security, financial, or regulated-content launch decisions.

## Generalization Boundary

PM Copilot serves product managers across industries and product types. Self-iteration may use real host projects to create pressure, but the durable output of that pressure must be a general capability improvement. Do not promote a host project's terminology, domain, local path, backend contract, route name, analytics vocabulary, visual style, or user journey into generic PM Copilot instructions.

Allowed host-specific locations:

- `outputs/<run-id>/` runtime evidence for that run.
- `evals/` fixture-scoped regression cases that explicitly describe themselves as fixtures.

Disallowed host-specific locations:

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

When a host run finds a defect, rewrite the finding as a general rule. For example, "a source-backed preview can be polluted by authenticated background requests or development overlays" is reusable; the host project's product name, route name, and business nouns are not.

## Clarification Semantics

Avoid contradictory clarification output. A single unknown must belong to exactly one bucket:

- `Must answer before generation`: blocks PRD, metrics, tracking, flow, UI delivery, review, and delivery check.
- `Can draft with stated assumption`: can be assumed for a draft PRD/UI deliverable, but the assumption must be visible and reviewable.
- `Must confirm before development or launch`: blocks the readiness phase it applies to. Each item must state whether it blocks engineering handoff, launch, or both.

If the user asks to proceed with assumptions while must-answer or engineering-blocking confirmation questions remain, downgrade PRD status to `Draft with assumption risk` or `Draft with confirmation risk`. Do not call it development-ready. If only launch-blocking confirmations remain, the PRD may be engineering-ready only when launch status is explicitly blocked and the engineering acceptance criteria exclude the unconfirmed launch item.

Conditional risks should follow the chosen scope. If the generated scope explicitly excludes the behavior that creates a risk, record the risk as a non-goal, future-scope blocker, or guardrail instead of leaving it as an unresolved current-launch confirmation. If the scope includes the behavior or is ambiguous, keep the confirmation open.

## Readiness Model

Every final PRD must carry three related but separate readiness fields:

- PRD status: whether the delivery is blocked, a draft, ready for review, or ready for engineering.
- Engineering handoff status: whether engineering can build the confirmed scope now, and which decisions block implementation.
- Launch status: whether the shipped behavior, content, copy, compliance, analytics, and operational process are approved for release.

Do not use one `Ready` label to hide a blocked phase. A framework can be ready for engineering while content, legal copy, or operational approval blocks launch; the PRD must say both facts.

## Scope Integrity

After user answers are applied, separate product decisions into:

- Confirmed MVP scope: requirements and acceptance criteria may be written here.
- Optional or conditional scope: describe as a decision still needed; do not include it in MVP acceptance criteria.
- Future scope: useful direction that is not part of the current delivery.
- Explicit non-goals: behaviors that should not be built without a new requirement pass.

If the user says a capability is possible, desirable, or "if needed" but does not confirm it for MVP, treat it as optional or future scope. Do not turn it into a must-build requirement.

For content-heavy features, separate the product framework from the content payload. Requirements may cover the content container, states, permissions, and maintenance flow while launch remains blocked on source, review owner, review status, or disclaimer confirmation.

## Current Product Fit

The new requirement must fit the current product instead of assuming a greenfield product, unless the user explicitly asks for a greenfield exploration.

Current product context can come from a host software repository, historical PRDs, specs, product docs, screenshots, analytics exports, support tickets, meeting notes, or direct user answers. A software repository is useful but not required.

Before S3 exits, capture:

- Existing product area or module likely affected.
- Relevant current behavior, user journeys, UI patterns, API contracts, data models, permission rules, analytics conventions, or documented historical decisions.
- Entry points, navigation visibility, permission or eligibility states, and fallback behavior for users who cannot access the new surface.
- Gaps between the user's requested change and the current product context.
- Project constraints that should shape scope, rollout, migration, and acceptance criteria.

If no analytics convention or event taxonomy is found, record that as a current-state fact. S7 may still produce a tracking proposal, but it must be labeled as proposed and must not claim to follow an existing taxonomy.

If the agent cannot determine the current product state from available repositories, documents, or user answers, ask for the missing context as must-answer questions.

## UI Delivery Context Gate

Before S8 exits for any UI delivery, PM Orchestrator must confirm that `agents/prototype-agent.md`, `skills/multi-platform-prototype/SKILL.md`, `artifacts/prototype-contract.md`, and `tools/prototype-tooling.md` were applied and recorded in `run-log.yaml`. The file names keep the legacy "prototype" label for compatibility; the active definition is UI delivery.

For repo-backed UI-delivery work, S8 must preserve the host production code boundary by default. The agent should read real frontend code, assets, data shapes, state rules, and screenshots, then generate a source-backed preview/delta that imports or renders the current product surface with only the requested feature delta. Do not modify production routes, pages, components, global styles, assets, package files, or backend code unless the user explicitly requests production-oriented implementation. If the user does ask to implement the UI in the current repository first and then hand off a 1:1 artifact, record the changed implementation files and extract from the running implemented UI rather than hand-recreating the result.

S8 repo-backed UI output must be evaluated as two layers. `baseline_import` imports or renders the original product UI from host source; `delta_patch` contains the requested new feature, visible markers, explanation dialogs, interactions, backend simulation notes, and tracking or edge-case annotations. UI-delivery markers and controls must not degrade the baseline layer.

Repo-backed S8 is not complete until the run log contains `isolated_ui_prototype` with host mutation policy, artifact mode, target surface, source-to-demo mapping, backend simulation method, parity claim, changed preview files or user-approved implementation files, and limitations. Backend-dependent behavior can be represented with mock data and annotations, but the UI deliverable must not imply that backend implementation exists unless implementation work was explicitly requested and verified.

For repo-backed UI delivery, S8 is not complete until the run log contains `style_evidence` with source files, reused components, reused tokens or class patterns, UI delta, and limitations. Compatibility HTML must include a traceable `style-source-summary` comment or `data-style-source` attribute. If existing frontend code, screenshots, or demos are available but style evidence is missing, route the work back to UI Delivery Agent instead of accepting a polished-looking greenfield artifact.

Repo-backed S8 should also record `existing_ui_visual_baseline`. Prefer captured screenshots from a running host app, preview route, Storybook/demo, or user-provided screenshots. If the host app cannot be started or no screenshot source exists, record `status: skipped`, the exact limitation, and the expected impact on visual parity. Do not claim the UI deliverable is pixel-identical to the existing UI unless a visual comparison actually ran.

The style reuse pass should inspect the smallest relevant host files: app shell or root layout, global stylesheet or theme config, design-system components, affected routes/pages, and nearby feature components. A compatibility HTML artifact may emulate inspected host patterns only when standalone fallback is allowed; if renderable frontend source exists, source-backed preview/delta is the default and hand recreation is not complete.

## Run Folder Rules

Use `outputs/<run-id>/` as the single generated-artifact folder for each real requirement run. The run id uses an English kebab-case requirement slug plus day-precision date, for example `team-permissions-2026-05-18`. For same-day collisions, append a numeric suffix such as `team-permissions-2026-05-18-2`.

Only update an existing run folder when the user explicitly names that folder or asks to revise the existing requirement.

The repository does not ship example output folders. `outputs/` is generated at runtime by real user runs and should not be treated as product context.

If PM Copilot or the host project is expected to be a repository but the current workspace does not contain the matching git checkout, look for a same-name source folder under the local Desktop. Writing source or artifact changes there is allowed when the folder exists, but the final handoff must say that no repository push occurred and that the user can push from that local folder.

## Delivery Rules

Default delivery should optimize for reviewability, not file count.

- Create `outputs/<run-id>/prd.md` as the primary product-manager handoff artifact when PRD is in scope.
- For document-class reference handoffs, create `outputs/<run-id>/catalog.md` or `outputs/<run-id>/reference.md` as the primary artifact instead of forcing the request into a PRD. Generate `catalog.html`, `reference.html`, or a `document_prototype` HTML only when the user asks for HTML or a browser-readable document.
- For implemented-feature PRD delivery, create `outputs/<run-id>/prd.md` and, when requested, `outputs/<run-id>/prd.html`. This HTML is a document rendering and should not be named `prototype-<platform>.html`.
- For implemented-feature PRD delivery, use `templates/implemented-feature-prd-template.md`, and in embedded mode write to `pm-copilot/outputs/<run-id>/` rather than the host root. Generate or refresh the HTML document with `scripts/render_prd_html.py`.
- For implemented-feature PRD delivery, keep screenshots and missing-image markers inline with the related requirement, table row, flow step, state, dialog, or evidence. Missing screenshots in Chinese PRDs use the exact `占位图` block only, with a recommended file name such as `文件上传-上传中.png`; real screenshots live under `<run-folder>/assets/`.
- For implemented-feature PRD delivery, screenshot names describe content and concrete state. Use object plus specific state, such as `文件上传-上传中.png` or `文件上传-上传失败.png`; do not use generic names such as `文件上传-状态.png`.
- For implemented-feature PRD delivery, screenshot coverage is by independent changed page, window, panel, or dialog. Do not split micro-states when a single screenshot captures the full window or panel.
- For implemented-feature PRD delivery, functional flow diagrams must be Mermaid `flowchart` blocks, not tables or PNGs. Copy/i18n sections must include newly added or changed UI copy as pure text, or explicitly state no new copy exists.
- Create or record a UI deliverable when a user-facing UI artifact is relevant: source-backed preview/delta files by default when frontend source exists, `outputs/<run-id>/prototype-<platform>.html` for source-extracted HTML or compatibility standalone/no-source/fallback mode, and `outputs/<run-id>/index.html` as the offline folder entry when the user explicitly asks for a portable/offline handoff. If the user asks to implement the UI in the current repo before handoff, run the host implementation or approved preview first, then extract the finished region as the portable artifact instead of hand-recreating it.
- Create `outputs/<run-id>/run-log.yaml` as an internal trace when useful.
- Keep source or export files only when they are useful for analytics import, Mermaid rendering, external review workflow, or user-requested iteration.
- `prd.md` must include version history, requirement input and confirmation record, background, research/reference findings, goals/metrics, scope, requirement list, requirement details, flow diagrams when useful, tracking plan, UI delivery reference, risks/open confirmations, acceptance criteria, and validation results.
- Do not create separate `task-brief.md`, `clarifying-questions.md`, `assumptions.md`, `pm-package.md`, `metrics-tree.md`, `tracking-plan.md`, `user-flow.md`, `review-checklist.md`, or `final-package-summary.md` by default.
- Avoid making the user open many small Markdown files to understand one requirement.

Structured reference delivery must keep source facts, product decisions, attention points, and implementation notes separate. For model, API, payment, risk, data, or SOP references, fast-changing values such as model IDs, parameters, limits, pricing, region availability, SDK support, rules, and deprecation status must be current-source-backed or explicitly marked draft/blocked with an owner.

## UI Visual Validation

For compatibility HTML UI deliverables, run browser-based visual validation:

- `python3 scripts/validate_prototype_visual.py outputs/<run-id>`
- Add `--baseline-dir <path>` for regression suites.
- Add `--update-baseline` only when intentionally establishing a new baseline.

Without `--prototype`, the visual validator checks every supported compatibility HTML file in the run folder. For source-backed UI previews, run the host app's dev/preview/Storybook/simulator path, then run `python3 scripts/validate_ui_preview.py <preview-url-or-file> --run-folder outputs/<run-id>` when a browser URL or local preview file exists; otherwise record equivalent simulator evidence. Record UI deliverable file names or preview surfaces, screenshots, visual report path, nonblank checks, diff status, and limitations in `run-log.yaml`. If Playwright or browser installation is unavailable, first run `python3 scripts/setup_visual_validation.py` or guide the user through setup. Record the check as skipped only after setup fails, browser launch is not permitted in the environment, or the user declines installation.

## Delivery Orchestrator

Before final delivery or iteration scoring, run the orchestrator:

```bash
python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>
```

The orchestrator records a machine-readable report under `outputs/<run-id>/tool-results/delivery-check-report.json`. If the orchestrator cannot run, run the individual validation commands and record why.

## Execution Handoff

When the user asks PM Copilot to turn requirements into development tasks, issue-ready work, release readiness, or a launch decision:

- Follow `workflow/execution-handoff-workflow.md`.
- Create `outputs/<run-id>/dev-tasks.yaml` for engineering handoff when requested.
- Create `outputs/<run-id>/launch-decision.yaml` for release readiness or go/no-go support when requested.
- In unattended mode, keep `decision_mode: unattended_candidate` and do not use `ready_to_launch` unless explicit human approval evidence exists for all required gates.
- Keep blockers and required approvals visible; do not convert launch blockers into ready implementation tasks.

## Language Rules

Use the user's language for conversation and generated artifacts. Chinese requests should produce Chinese headings, table labels, statuses, narrative text, UI delivery notes, and review labels; English requests should produce English equivalents. For analytics tables, localize reviewer-facing labels and keep machine field names such as `event_name` or `required_properties` visible in code formatting when implementation needs them. Keep file names, event names, property names, Mermaid node IDs, and other machine-readable identifiers in ASCII.

Repository templates are structural examples, not literal copy. Translate headings and labels before writing user-facing artifacts.

## Skippable Steps

- Research can be skipped when the task does not need external evidence.
- UI delivery can be omitted when the request is purely backend, infra, or analytics.
- Tracking can be reduced when the task is a non-user-facing operational change, but the omission must be explained in the PRD.

## Revision Rules

- Review findings with severity `Critical` or `High` must route back to the owning agent.
- Medium findings may be listed as review-time discussion points.
- Low findings may remain as optional improvements.
- Review findings must include artifact, evidence, owner, required-before phase, and status. A review that reports no Critical or High issues must still record the checks performed and any Medium or Low residual risks.

## Trace Format

Use `templates/agent-run-log-template.yaml` as the canonical trace shape.

Minimum trace requirements:

- Record `context.source_mode` as `repo-backed`, `document-backed`, or `brief-only`.
- In repo-backed mode, record host files inspected and current-state facts used for product-fit decisions.
- Record `workflow.clarification_gate.required`, `status`, `stopped_before_generation`, and `assumption_risk_accepted`.
- Classify every unresolved question as exactly one of `must answer before generation`, `can draft with stated assumption`, or `must confirm before development or launch`.
- Record numeric review scores when a quality rubric exists.
- If S6-S11 artifacts are generated while unresolved must-answer questions or `must confirm before development or launch` blockers remain, record the user's explicit draft-risk acceptance as evidence and downgrade PRD readiness.
- Record tool preflight, validation commands actually run, their results, and any skipped validation with the reason. The PRD and run log must use the same validation status.
- Record PRD, engineering handoff, and launch readiness separately, including blockers for each phase.
- Record content source and review status when the feature includes reference, policy, medical, legal, financial, safety, or operational content.
- Record structured review findings or an explicit no-finding review summary with evidence of the checks performed.
