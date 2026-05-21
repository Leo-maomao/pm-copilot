# PM Copilot Entry

This is the canonical cross-platform entry for PM Copilot.

Use this file when an agent needs to run product manager work such as PRD, tracking plan, product requirements, prototype, competitor research, metrics, review, or PRD/prototype delivery generation.

## Context Source Rule

Do not assume the product context comes from a code repository. Classify every run as `repo-backed`, `document-backed`, or `brief-only`, then load context and apply the clarification gate according to that mode.

## Activation

Activate PM Copilot when the user asks for work involving:

- PRD
- product requirements
- requirement clarification
- product discovery, opportunity validation, or assumption mapping
- customer feedback, interview, support ticket, survey, or review synthesis
- user stories
- acceptance criteria
- metrics or KPI tree
- tracking plan or analytics events
- A/B test, experiment, beta rollout, fake-door test, or decision-metric design
- prototype or wireframe
- user flow
- competitor research
- competitive teardown, battlecard, pricing comparison, or positioning analysis
- operating metrics, funnel, retention, conversion, support-signal, or dashboard analysis
- roadmap, release note, stakeholder update, or customer announcement
- knowledge-base, SOP, runbook, or internal process documentation
- business process mapping, handoff analysis, cycle-time analysis, or operations bottleneck review
- design system, UI audit, visual consistency, or design-token review
- product review checklist
- product launch review
- development handoff, issue planning, launch decision support, or go/no-go review
- external MCP/API/SaaS tool selection, integration planning, or automation setup for PM workflows
- Chinese-language requests for requirements, tracking plans, prototypes, competitor research, or review materials

The user should not need to remember the project name. If the task is clearly product-manager work, run this workflow.

## Default User Experience

The intended experience is:

```text
User: I need a PRD for checkout coupon optimization.
Agent: I will inspect the relevant product context, then clarify the key unknowns before generation.
Agent: <asks must-answer questions and stops if blocking unknowns exist>
Agent: <after answers or explicit permission to draft with risk, creates outputs/<run-id>/prd.md and outputs/<run-id>/prototype-<platform>.html>
```

The user should not need to manually copy templates or create folders. Do that for them.

## Required Behavior

1. Read these files first:
   - `README.md`
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

   When the requested delivery includes a UI prototype, also load these before S8 prototype work starts:
   - `agents/prototype-agent.md`
   - `skills/multi-platform-prototype/SKILL.md`
   - `artifacts/prototype-contract.md`
   - `tools/prototype-tooling.md`

   When the request mentions external tools, MCP servers, SaaS APIs, workspace connectors, analytics platforms, databases, CRM/support systems, advertising platforms, automation tools, paid design-generation services, or operational data analysis, also load:
   - `agents/integration-governance-agent.md`
   - `skills/tool-vetting/SKILL.md`
   - `tools/external-tooling.md`
   - `tools/external-tool-catalog.json`

   When the request includes product or operations data analysis, also load:
   - `skills/product-ops-analysis/SKILL.md`
   - `agents/analytics-agent.md`

   Apply task skills only when their trigger matches the request:
   - Intake and scope: `skills/requirement-intake/SKILL.md`, `skills/opportunity-discovery/SKILL.md`, `skills/feedback-synthesis/SKILL.md`, `skills/process-mapping/SKILL.md`, `skills/knowledge-ops/SKILL.md`, `skills/scope-edge-cases/SKILL.md`
   - PRD and delivery: `skills/prd-writing/SKILL.md`, `skills/user-stories/SKILL.md`, `skills/user-flow/SKILL.md`, `skills/acceptance-criteria/SKILL.md`, `skills/review-checklist/SKILL.md`, `skills/artifact-packaging/SKILL.md`, `skills/development-handoff/SKILL.md`
   - Metrics and data: `skills/metrics-tree/SKILL.md`, `skills/tracking-plan/SKILL.md`, `skills/experiment-design/SKILL.md`, `skills/product-ops-analysis/SKILL.md`
   - Research and communication: `skills/competitor-research/SKILL.md`, `skills/roadmap-communication/SKILL.md`
   - Prototype and UI evidence: `skills/multi-platform-prototype/SKILL.md`, `skills/design-system-audit/SKILL.md`
   - Tool and capability governance: `skills/tool-vetting/SKILL.md`, `skills/sharingan/SKILL.md`

   Keep one canonical skill per capability type. When a new external skill or workflow overlaps an existing PM Copilot skill, use `skills/sharingan/SKILL.md` to merge the useful parts into the canonical skill instead of adding a duplicate sibling.

   Load `skills/sharingan/SKILL.md` when the user says "写轮眼" or "sharingan", or asks to copy, copy from, port, adapt, absorb, assimilate, internalize, or convert a third-party repo, document, prompt, workflow, template, script, tool, or example into PM Copilot capability.

   Record the active Prototype Agent and `multi-platform-prototype` skill in `run-log.yaml`. A prototype delivery with `skills_used: []` is incomplete unless the prototype was explicitly omitted.

2. Match the user's language:
   - If the user writes in Chinese, use Chinese for user-facing replies and generated PM artifacts.
   - If the user writes in English, use English.
   - If the request mixes languages, use the dominant language unless the user asks otherwise.
   - Localize human-facing headings, table column labels, status labels, prototype annotations, button text, and review labels into the user's language.
   - Localize readiness status values and review severity/status labels in user-facing artifacts. Machine-readable trace values may keep stable English codes, but PRD tables should not show raw labels such as `Ready for review`, `Blocked before launch`, `High`, `Medium`, or `Open` when the user requested Chinese.
   - Do not copy English headings from repository templates into Chinese deliverables.
   - For analytics tables, localize reviewer-facing labels and keep machine field names such as `event_name` or `required_properties` visible in code formatting when implementation needs them.
   - Keep file names and machine-readable identifiers in ASCII kebab-case or snake_case.

3. Load memory and product context from the best available source:
   - Load local memory files when present:
     - `context/product-memory.local.yaml`
     - `context/user-preferences.local.yaml`
     - `context/decision-log.local.yaml`
   - Use memory to reduce repeated questions and match the user's working style.
   - Do not use memory as authority over current user instructions, current host repository facts, current user-provided documents, or guardrails.
   - If memory conflicts with current context in a way that affects scope, readiness, privacy, payment, legal, compliance, security, analytics, or launch risk, state the conflict and ask or choose the higher-priority current source.
   - If reusable product facts, user preferences, or durable decisions are learned during a run, suggest memory updates at the end. Do not silently store sensitive memory.
   - Prefer `context/product-context.local.yaml` if it exists.
   - Otherwise use `context/product-context.example.yaml`.
   - If using the example context, tell the user it is a generic placeholder and ask only for missing context that materially affects the task.
   - Repo-backed mode: if PM Copilot is embedded in a software repository, inspect the host project's relevant current state before proposing a new requirement. Existing product behavior, routes, data models, UI patterns, APIs, permissions, analytics conventions, and docs are constraints for the new requirement.
   - Document-backed mode: if there is no software repository but the user provides historical PRDs, specs, research notes, product docs, meeting notes, screenshots, support tickets, analytics exports, or other product documents, treat those documents as the current product context.
   - Brief-only mode: if neither a repository nor product documents are available, proceed only after clarifying the minimum context needed for the requested artifact. Use explicit assumptions for low-risk unknowns.
   - If no existing analytics taxonomy or event naming convention is found, say so explicitly. Treat generated tracking events as a proposed taxonomy, not as the product's existing standard.
   - Do not make the existing product adapt to an invented greenfield solution. Fit the requirement into the current product context unless the user explicitly asks for a redesign or greenfield exploration.
   - Do not treat PM Copilot's templates or eval cases as facts about the host product.

4. Infer a scenario slug and run id:
   - Use a short lowercase kebab-case name.
   - Example: `membership-renewal`, `checkout-coupon`, `team-permissions`.
   - Use the slug as the run id when no matching output folder exists and the slug does not collide with a curated example scenario.
   - If `outputs/<slug>/` already exists, create a unique run id by appending the local timestamp, for example `checkout-coupon-20260518-1430`.
   - Reuse an existing output folder only when the user explicitly asks to update that requirement.
   - For real user runs, keep all generated run artifacts under `outputs/<run-id>/`. The repository does not ship example output folders.

5. Before the clarification gate:
   - Ask blocking questions in the conversation.
   - Create or update only `outputs/<run-id>/run-log.yaml` when a persistent trace is useful.
   - Do not create final delivery artifacts until the clarification gate passes.
   - Do not create separate `task-brief.md`, `clarifying-questions.md`, or `assumptions.md` by default. The original request, answered clarifications, and low-risk assumptions belong in `prd.md` after generation.

6. Enforce the clarification gate before generation:
   - The default target is a PRD and prototype that can be used for product review and engineering handoff, not a speculative draft.
   - Ask blocking questions before creating downstream artifacts when missing information materially changes:
     - Product goal
     - Target user
     - Scope
     - Platform
     - Existing product fit, affected modules, or relevant historical product decisions
     - Metrics
     - Tracking
     - Prototype direction
     - Payment, privacy, legal, compliance, security, or financial risk
   - If any must-answer question exists, ask it and stop before creating `prd.md` or prototype HTML. Record it in `run-log.yaml` only when a trace is being written.
   - If any item is classified as `must confirm before development or launch`, record whether it blocks engineering handoff, launch, or both. Ask before generating PRD/prototype deliverables that claim the blocked readiness. Launch-only confirmations may remain open only when the PRD clearly marks launch status as blocked and the engineering handoff scope excludes the unconfirmed item.
   - Do not treat user silence as approval to continue.
   - If the user explicitly requests an evaluation loop or instructs the agent to choose recommended options automatically, choose conservative defaults for the loop, record them as defaulted answers, and still generate the full artifacts required by that evaluation round. Keep launch, compliance, privacy, legal, payment, security, financial, and regulated-content confirmations unresolved unless the user explicitly approves them.
   - Do not label the same unknown as both `must answer before generation` and `can draft with stated assumption`.
   - Use three distinct buckets: `must answer before generation`, `can draft with stated assumption`, and `must confirm before development or launch`.
   - Do not keep a conditional risk as an unresolved confirmation when the generated scope explicitly excludes the triggering behavior. Record it as a non-goal or guardrail instead. Example: if the MVP does not save health data, health-data retention review is a future-scope blocker, not a current launch blocker.
   - For reference, policy, medical, legal, financial, safety, or operational content, record content source, review owner, review status, and disclaimer status. Unreviewed or placeholder content must be labeled as such and must block launch, even when the surrounding product framework is ready for engineering.

7. Run external product research for PRD solution shaping unless the user explicitly says to skip it or tooling/network access is unavailable:
   - The PRD's research/reference section should include source-backed competitor, benchmark, or comparable feature research that helps choose a better product solution.
   - When the requirement changes a common product flow, research the same flow in direct competitors or comparable products. Capture entry points, required inputs, primary and fallback paths, platform differences, constraints, and the implication for the proposed solution.
   - Repository files are current-product context, not competitor or feature research. Put implementation facts in background, current-state context, or the engineering implementation map; do not use repo file reading as the only content under "调研与参考结论".
   - Use `Research Agent` and `tools/research-tooling.md` when competitor, market, benchmark, pricing, policy, compliance, or comparable product behavior can materially shape scope, copy, metrics, or prototype direction.
   - If web research cannot run, record `external_research.status: skipped` or `degraded`, the exact limitation, and make product recommendations visibly assumption-based.
   - Record source title, URL, access date when available, observed fact, implication, and confidence in `run-log.yaml`.

8. After the clarification gate passes, create or update the product-manager delivery artifacts:
   - `outputs/<run-id>/prd.md`
   - `outputs/<run-id>/prototype-<platform>.html`
   - `outputs/<run-id>/run-log.yaml`
   - Optional exports only when useful or requested:
     - `outputs/<run-id>/tracking-plan.csv`
     - `outputs/<run-id>/user-flow.mmd`
   - Do not create `pm-package.md`, `task-brief.md`, `clarifying-questions.md`, `assumptions.md`, `metrics-tree.md`, `tracking-plan.md`, `user-flow.md`, `review-checklist.md`, or `final-package-summary.md` by default.
   - Avoid split Markdown handoff files unless the user explicitly asks for them.
   - Keep confirmed MVP scope, optional scope, and future scope separate. Do not place an unconfirmed optional capability in MVP requirements or acceptance criteria.
   - For existing-product changes, explicitly define entry point behavior, navigation visibility, permission or eligibility states, and fallback states so the prototype, PRD, and engineering handoff agree.
   - Each specialist step must follow `agents/agent-interface.md`: record status, confidence, artifact delta, validation delta, risks, and next expected output. PM Orchestrator owns final readiness labels and resolves contradictions before delivery.

9. Continue with assumptions only when:
   - The user explicitly says to proceed as a draft without answers, or
   - The unknown is clearly low-impact and listed as `can draft with stated assumption`.
   - Items classified as `must confirm before development or launch` are not draft assumptions. If an unresolved item blocks engineering, status must be `Draft with confirmation risk`, not `Ready for engineering`, unless the user explicitly accepts that draft risk. If the item blocks launch only, engineering status may be ready only when the launch blocker is visible and excluded from engineering acceptance criteria.
   - Keep unanswered questions visible in `prd.md`.

10. Choose prototype platform:
   - Web for desktop admin, SaaS, dashboards, tables, complex forms.
   - H5 for mobile web, landing pages, campaigns, lightweight checkout.
   - App for native mobile product flows.
   - Mini Program for mini-program containers, authorization, booking, ordering, and lightweight forms.
   - Generate multiple prototypes only for true cross-platform requirements.
   - If an existing demo, screenshot, page, route, design system, or component implementation is available, adapt that current surface and show the delta for the new requirement. Do not create a new unrelated product shell.
   - Source-code-first rule: in repo-backed prototype-only UI work, frontend source presence is enough to require source-backed rendering. Do not infer the user wants freeform, greenfield, or hand-written standalone UI just because the request says "prototype", "draft", "quick", "only generate prototype", or omits exact-fidelity wording. Use freeform UI only when no frontend code/current surface is available, source rendering is concretely blocked, the raw request explicitly asks for standalone/portable HTML, or the raw request explicitly asks to redesign/rebuild/from-scratch/stop reusing the original design.
   - In repo-backed prototype-only UI work, keep host production flows read-only by default, but treat a user request for exact online/source-code UI parity, or the mere availability of a renderable host frontend, as approval to create an isolated source-rendered preview route, Storybook story, demo entry, or preview-only screen. Read real frontend code, assets, data shapes, state rules, and screenshots, then choose the lowest-risk artifact mode that preserves the current UI.
   - Before drafting any repo-backed UI, build `host_frontend_inventory`: platform source kind, frontend entry files, route/page/screen files, component-library files, style token/global style files, icon/asset sources, data/mock sources, render command, and preview surface. When available, pass the user requirement or target surface as the inventory query so relevant files are ranked ahead of unrelated routes. Cover Web/H5, Mini Program/Taro/uni-app, React Native/Flutter/native App, and other host frontend stacks with their native page/component/style files. If the frontend source or render entry cannot be found and the user expects real-product UI, stop and ask for the host app path or runnable preview instead of inventing a shell.
   - Choose the prototype artifact mode before drafting: use `source_delta_patch` as the default for any renderable repo-backed frontend, where the baseline is imported/rendered from original host source and only the new requirement is added in preview-only delta files. Use `code_preview_route` for Web/H5 routes, `storybook_or_demo` for component demos, `mini_program_preview` for Mini Program/Taro/uni-app pages, or `app_preview_screen` for React Native/Flutter/native App screens when those platform containers are a better fit. Use `self_contained_html_from_host_code` only when the user's raw request explicitly asks for a portable/standalone/HTML artifact, explicitly asks to redesign/rebuild/from-scratch/stop reusing the original UI, or after source rendering is attempted and blocked by a concrete command, browser, simulator, dependency, or preview-surface failure. "Only generate a prototype" means prototype scope only; it does not authorize standalone HTML or greenfield UI. Production files being read-only is not a blocking reason because isolated preview files are allowed. In fallback mode, capture an existing UI screenshot baseline when possible, mark the parity claim as fidelity-limited, and do not call it exact. In source-rendered modes, add only isolated preview route/story/demo/page/screen files and record changed files in `isolated_ui_prototype`; do not touch production flows unless explicitly requested.
   - Structure repo-backed UI prototypes as two layers: `baseline_import` imports or renders the original product page/screen/components/styles/assets from host source without rewriting them; `delta_patch` contains only the new feature, mock state, wrapper/story/page/screen composition, markers, explanation dialogs, backend simulation notes, and tracking/edge-case annotations. Multi-turn conversations must continue from the same `delta_patch.next_delta_anchor` and append to `multi_turn_change_log`, not reconstruct the baseline.
   - The baseline layer should not be redesigned or filled with prototype-only explanatory copy. Delta markers and annotation controls must not resize, crop, recolor, or cover critical unchanged UI.
   - Do not modify existing production routes, pages, components, global styles, assets, package files, or backend code unless the user explicitly asks for production-oriented implementation. Isolated preview-only files are allowed for source-rendered prototype mode and must be recorded separately.
   - In repo-backed UI work, perform a source-rendering pass before any visual recreation: inspect the host app shell, global stylesheet or theme tokens, design-system/component-library files, affected route/page/component files, local assets/icons, and any screenshots or demos that show the current surface. Build a concrete source-to-demo component map before drafting the prototype.
   - Reuse existing component structure, layout density, tokens, class names, copy tone, and interaction patterns. If exact fidelity matters, import or render the host components directly in an isolated preview so the real icons, fonts, components, CSS, platform chrome, and runtime states execute directly. A self-contained HTML prototype may inline CSS only after host rendering is unavailable or intentionally out of scope, and it must state the approximation.
   - Capture or record an existing UI visual baseline before writing the prototype when possible. Use a running host app, existing preview route, Storybook/demo, or user-provided screenshot. If the host frontend is renderable and a standalone fallback is used, a missing baseline must have a concrete attempted-render/browser/setup failure or raw-request portable/standalone/HTML request; otherwise the prototype is not complete.
   - After the style reuse pass, run a design calibration pass: choose visual density, layout variance, and motion intensity from the host product and scenario; avoid generic AI UI signatures that do not belong to the current surface.
   - Record `isolated_ui_prototype` in `run-log.yaml`, including host mutation policy, artifact mode, target surface, preview files changed when host-rendered, `baseline_import`, `delta_patch`, source-to-demo mapping, backend simulation method, parity claim, and limitations.
   - Record `host_frontend_inventory` and `style_evidence` in `run-log.yaml`, including concrete source files/assets, reused components, reused tokens or class patterns, icon/asset sources, the intended new-requirement delta, and limitations. Record `source_to_demo_mapping` with non-empty `source` and `prototype_representation` entries so reviewers can audit which host component or screen each prototype region came from. Add a hidden `style-source-summary` comment or `data-style-source` attribute in generated HTML so reviewers can trace the visual source.
   - Record `existing_ui_visual_baseline` in `run-log.yaml`: status, source, target page or component, screenshot paths when captured, comparison method, and limitation. If screenshots are available, use them as review evidence for unchanged regions; do not claim pixel-level parity unless a visual comparison actually ran.
   - If the existing frontend style source cannot be inspected and the user expects a product-specific prototype, ask for the missing screenshot/demo/component reference or mark the Prototype Agent output `degraded`; do not mark the prototype `complete`.
   - Use visible numbered annotation markers on the UI element being explained. The default UI marker is a small red circular badge using `annotation-marker`, `data-annotation-id`, and `data-annotation-placement="top-right"`; markers and the matching number badges inside marker dialogs and the right-side page annotation panel must share the same red background, white text, no border line, rendered diameter, font size, font weight, line height, and centered digit alignment. Badge text must be plain digits such as `1`, `2`, and `3`, not circled numeral glyphs or nested badge content. Number badges should reuse one shared badge style or CSS variables and must not inherit larger heading or list typography. Place markers at a safe top-right position that is not clipped by overflow and does not force component text to wrap. Marker visual style must not change after click. Clicking a marker opens a small local `annotation-dialog` popover beside that marker, clicking the same marker again closes it, and marker clicks must not open a full-screen/global modal.
   - Use a short draggable annotation floating control with only the label `注释` in Chinese outputs or `Notes` in English outputs. Clicking it hides the floating control and slides in a right-edge full-height `annotation-list` panel for the current page/state; closing the panel restores the floating control. The panel must not shrink, reflow, or cover the product surface by reserving layout space.
   - If the prototype needs page/state switching controls, keep them in a stable fixed position outside the product layout, not embedded as abrupt content in the host surface.
   - Before delivery, verify prototype JavaScript parses, all primary buttons visibly change state, annotation markers open dialogs, the annotation toggle opens and closes the right-side current-state list panel, every marker dialog and page annotation panel number badge uses matching plain digit text plus the same rendered size, font sizing, and centered alignment as the UI marker, state switches stay fixed, and compact labels such as tabs or segmented controls do not fold because of annotation placement.
   - Keep access states coherent. Logged-out, guest, or no-permission controls must not reveal signed-in-only account data, user IDs, account-management links, sync actions, logout actions, or privileged navigation when clicked.

11. Run tool preflight and validation after file changes when possible:
   - `python3 scripts/preflight_tools.py` before full-loop iteration, embedded host evaluation, or final delivery; use `--strict` for PM Copilot release validation.
   - `python3 scripts/inspect_host_frontend.py --host <host-repo> --query "<requirement or target surface>" --pretty` before repo-backed UI prototyping when a host frontend exists; record the result under `host_frontend_inventory`.
   - `python3 scripts/preflight_integrations.py --tier recommended` when external tools or integration recommendations are in scope; add `--check-remote` when current source availability must be verified.
   - `python3 scripts/preflight_tools.py --check-network <url> --require-network --strict` when source-backed research is required.
   - `python3 scripts/validate_repo.py`
   - `python3 scripts/validate_outputs.py outputs/<run-id> --language zh` for Chinese generated runs, or `--language en` for English runs, when `prd.md` or prototype artifacts exist.
   - `python3 scripts/validate_outputs.py outputs/<run-id> --pre-clarification` when a run intentionally stops before generation with only `run-log.yaml`.
   - `python3 scripts/validate_prototype_visual.py outputs/<run-id>` for UI prototype browser screenshot and visual diff validation. Without `--prototype`, the command validates every supported prototype file in the run folder.
   - `python3 scripts/run_delivery_checks.py outputs/<run-id> --language zh` or `--language en` before final delivery or iteration scoring.
   - If Playwright or browser tooling is unavailable, first run `python3 scripts/setup_visual_validation.py` or guide the user through the same setup. Skip visual validation only when setup fails, browser launch is forbidden, or the user declines installation; record the exact reason.
   - HTML checks with `tidy -errors -quiet -utf8` if available.
   - Record the exact command, result, and limitation in `run-log.yaml` and the PRD validation section using `artifacts/tool-result-contract.md`. Do not claim validation was executed if it was skipped, and do not say validation "should be run" after it has already run.
   - Use `tools/tool-registry.yaml` to decide whether a tool is required, optional, setup-required, or not applicable.
   - After validation commands finish, do a validation-finalization pass: replace any earlier placeholder such as `pending`, `待执行`, `should run`, or `to be verified` in both `prd.md` and `run-log.yaml` with the actual pass/fail/skipped result and the observed limitation.
   - On resumed runs, load `outputs/<run-id>/run-log.yaml` first, continue from `workflow.last_reliable_state`, and keep prior blockers visible until answered, explicitly accepted as draft risk, or moved out of current scope.

12. Create execution handoff artifacts when requested:
   - For development tasks, issue planning, or engineering handoff, follow `workflow/execution-handoff-workflow.md` and create `outputs/<run-id>/dev-tasks.yaml`.
   - For release readiness, launch decision support, or go/no-go checks, create `outputs/<run-id>/launch-decision.yaml`.
   - These artifacts may be generated unattended as `unattended_candidate`, but they must preserve blockers and required approvals. Do not mark `ready_to_launch` unless explicit human approval evidence exists for every required gate.

13. Suggest memory updates after a run when useful:
   - Stable product facts belong in `context/product-memory.local.yaml`.
   - User working preferences belong in `context/user-preferences.local.yaml`.
   - Durable decisions and rejected options belong in `context/decision-log.local.yaml`.
   - One-off task details stay in `outputs/<run-id>/run-log.yaml`.
   - Ask before writing sensitive, strategic, legal, financial, customer, partner, or private data.

## Embedded Repository Mode

If PM Copilot is stored inside another software repository, do not assume nested tool-specific instruction files are loaded by every tool.

Instead, the host repository should contain a tiny adapter instruction that says:

```text
For product-manager tasks such as PRD, requirements, tracking plans, prototypes, user flows, or competitor research, read `pm-copilot/PM_COPILOT.md` and follow it.
```

See `adapters/` for Codex, Claude Code, and Cursor examples.

When embedded, first identify the host project root and load only relevant host context before drafting. Typical sources include the host README, product docs, route definitions, API contracts, existing PRDs, analytics conventions, package metadata, and nearby UI or service modules. If there is no host project or the agent cannot determine the current product state, it must ask for available product documents or the minimum missing context before generating PRD/prototype deliverables.

## Output Style

Keep user-facing progress concise. Do not restate the entire workflow unless the user asks.

Final response should include:

- Scenario name
- Output folder
- Key artifacts created
- Open questions or launch blockers
- Validation result

## Guardrails

- Do not fabricate competitor sources.
- Do not claim a tool was used if it was not.
- Do not collect forbidden sensitive tracking properties.
- Do not hide assumptions.
- Do not present HTML prototypes as production code.
- Require human confirmation for payment, privacy, legal, compliance, financial, or security-sensitive decisions.
