# PM Copilot Entry

This is the canonical cross-platform entry for PM Copilot.

Use this file when an agent needs to run product manager work such as PRD, tracking plan, product requirements, UI delivery, prototype review, structured reference documents, document prototypes, competitor research, metrics, review, or PRD/UI-delivery generation.

## Context Source Rule

Do not assume the product context comes from a code repository. Classify every run as `repo-backed`, `document-backed`, or `brief-only`, then load context and apply the clarification gate according to that mode.

## Implemented Feature PRD Delivery

When the user has already implemented or changed a feature and asks PM Copilot to produce a PRD or delivery document from the current branch, use `implemented-feature-prd` mode.

In this mode the implementation is the primary evidence source. Inspect the current branch, diff, touched files, UI entry points, screenshots/assets, tests, analytics changes, and any existing docs before drafting. Reconstruct the product requirement from what the implementation actually does, then call out gaps, assumptions, and any behavior that cannot be proven from the branch. Do not invent hidden scope to make the PRD look complete.

The default deliverables are:

- Direct PM Copilot root: `outputs/<run-id>/prd.md`, optional `outputs/<run-id>/prd.html`, and `outputs/<run-id>/run-log.yaml`
- Embedded host repository: `pm-copilot/outputs/<run-id>/prd.md`, optional `pm-copilot/outputs/<run-id>/prd.html`, and `pm-copilot/outputs/<run-id>/run-log.yaml`

`prd.html` is a document rendering of the PRD, not a UI prototype. It should use a normal readable document layout with optional left table of contents and a single content area. Avoid decorative cards, module blocks, unusual background colors, gradients, or nested scroll containers. Tables must preserve all columns and wrap content readably. Mermaid diagrams must render as diagrams. Images or image placeholders must appear inline exactly where reviewers need them, including inside requirement/detail tables when that is the relevant position; do not move them into a separate image list. Real images should use local relative paths and support click-to-fullscreen or equivalent lightbox viewing. If the user will replace images manually, insert explicit inline placeholders at the intended location.

For implemented-feature PRDs, use `templates/implemented-feature-prd-template.md` as the default structure and render browser-readable delivery with `scripts/render_prd_html.py`. Missing screenshots must be marked only with the exact inline `占位图` block at the relevant requirement position. Recommend screenshot file names by content; when one object has multiple states, include the concrete state, for example `文件上传-上传中.png` and `文件上传-上传失败.png`, not `文件上传-状态.png`.

## Generalization Boundary

PM Copilot is a universal product-agent system for product managers across domains. Reference projects are fixtures for capability testing only. A borrowed host project may shape one run's `outputs/<run-id>/` evidence, but it must not become PM Copilot's target product, default scenario, example vocabulary, or permanent product context.

Keep host-specific names, local paths, APIs, domain nouns, data contracts, UI routes, and business assumptions out of generic docs, prompts, templates, tools, agents, skills, and workflow rules. When a host project exposes a weakness, extract the general capability failure and fix that layer: guardrail, workflow, validator, scorecard, skill, or agent contract.

## Activation

Activate PM Copilot when the user asks for work involving:

- PRD
- product requirements
- implemented feature to PRD or branch-to-PRD delivery
- requirement clarification
- product discovery, opportunity validation, or assumption mapping
- customer feedback, interview, support ticket, survey, or review synthesis
- user stories
- acceptance criteria
- metrics or KPI tree
- tracking plan or analytics events
- A/B test, experiment, beta rollout, fake-door test, or decision-metric design
- UI deliverable, prototype, or wireframe
- structured reference, document handoff, knowledge base, parameter table, rule reference, SOP/runbook, data dictionary, migration inventory, or browser-readable document prototype
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
- Chinese-language requests for requirements, tracking plans, UI deliverables, prototypes, competitor research, or review materials
- Chinese-language requests such as "我先写好功能，你还原 PRD/Markdown/HTML", "按当前分支生成 PRD", "把实现还原成需求文档", or equivalent delivery-document requests

The user should not need to remember the project name. If the task is clearly product-manager work, run this workflow.

## Default User Experience

The intended experience is:

```text
User: I need a PRD for checkout coupon optimization.
Agent: I will inspect the relevant product context, then clarify the key unknowns before generation.
Agent: <asks must-answer questions and stops if blocking unknowns exist>
Agent: <after answers or explicit permission to draft with risk, creates outputs/<run-id>/prd.md and the selected UI deliverable: source-backed preview/delta files by default when frontend source exists, source-extracted HTML when the UI was first rendered in the host project, or a compatibility prototype-<platform>.html only for standalone/no-source/fallback mode>
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

   When the requested delivery includes UI delivery, a UI prototype, a wireframe, or visual product review, also load these before S8 UI-delivery work starts:
   - `agents/prototype-agent.md`
   - `skills/multi-platform-prototype/SKILL.md`
   - `artifacts/prototype-contract.md`
   - `tools/prototype-tooling.md`

   When the request is a document-class handoff, such as a structured reference, parameter table, API capability catalog, vendor matrix, data dictionary, migration inventory, payment/risk rule reference, SOP/runbook, or browser-readable document prototype, also load:
   - `skills/knowledge-ops/SKILL.md`
   - `artifacts/structured-catalog-contract.md`
   - `templates/structured-catalog-template.md`
   - `templates/document-prototype-template.html` when HTML or browser-readable document review is requested

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
   - UI delivery and UI evidence: `skills/multi-platform-prototype/SKILL.md` (including screenshot/image-to-UI reconstruction), `skills/design-system-audit/SKILL.md`
   - Tool and capability governance: `skills/tool-vetting/SKILL.md`, `skills/sharingan/SKILL.md`, `skills/skill-cleaner/SKILL.md`

   Keep one canonical skill per capability type. When a new external skill or workflow overlaps an existing PM Copilot skill, use `skills/sharingan/SKILL.md` to merge the useful parts into the canonical skill instead of adding a duplicate sibling.

   Load `skills/sharingan/SKILL.md` when the user says "写轮眼" or "sharingan", or asks to copy, copy from, port, adapt, absorb, assimilate, internalize, or convert a third-party repo, document, prompt, workflow, template, script, tool, or example into PM Copilot capability.

   Load `skills/skill-cleaner/SKILL.md` when the user asks to audit, trim, clean, de-duplicate, or measure prompt-budget pressure for PM Copilot, Codex, plugin, or personal skill roots.

   Record the active UI Delivery Agent (`agents/prototype-agent.md`, legacy name) and `multi-platform-prototype` skill in `run-log.yaml`. A UI delivery/prototype-stage handoff with `skills_used: []` is incomplete unless UI delivery was explicitly omitted.

2. Match the user's language:
   - If the user writes in Chinese, use Chinese for user-facing replies and generated PM artifacts.
   - If the user writes in English, use English.
   - If the request mixes languages, use the dominant language unless the user asks otherwise.
   - Localize human-facing headings, table column labels, status labels, UI delivery annotations, button text, and review labels into the user's language.
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
   - Repository-location fallback: if the expected project or PM Copilot repository is not a git checkout in the current workspace, look for a same-name source folder under the local Desktop before giving up. If that folder exists, write the requested source/artifact changes there and state that the user must push from that folder; do not claim a remote repository push unless a real remote was found and pushed.
   - If no existing analytics taxonomy or event naming convention is found, say so explicitly. Treat generated tracking events as a proposed taxonomy, not as the product's existing standard.
   - Do not make the existing product adapt to an invented greenfield solution. Fit the requirement into the current product context unless the user explicitly asks for a redesign or greenfield exploration.
   - Do not treat PM Copilot's templates or eval cases as facts about the host product.

4. Infer a scenario slug and run id:
   - Use a short lowercase kebab-case name.
   - Example: `membership-renewal`, `checkout-coupon`, `team-permissions`.
   - For real user runs, use a dated ASCII run id in the form `<requirement-slug>-YYYY-MM-DD`, for example `checkout-coupon-2026-05-18`.
   - Keep the date at day precision. If the same dated run id already exists, append a numeric suffix such as `checkout-coupon-2026-05-18-2`; do not append minute-level timestamps unless the user explicitly requests that naming convention.
   - Reuse an existing output folder only when the user explicitly asks to update that requirement.
   - For real user runs, keep all generated run artifacts under `outputs/<run-id>/`. The repository does not ship example output folders.

5. Before the clarification gate:
   - Ask blocking questions in the conversation.
   - Create or update only `outputs/<run-id>/run-log.yaml` when a persistent trace is useful.
   - Do not create final delivery artifacts until the clarification gate passes.
   - Do not create separate `task-brief.md`, `clarifying-questions.md`, or `assumptions.md` by default. The original request, answered clarifications, and low-risk assumptions belong in `prd.md` after generation.
   - In `implemented-feature-prd` mode, do not ask for information that can be discovered from the current branch. Inspect the implementation first, then ask only for product intent, rollout, metric, launch, legal, or screenshot gaps that remain unprovable after inspection.

6. Enforce the clarification gate before generation:
   - The default target is a PRD and UI deliverable that can be used for product review and engineering handoff, not a speculative draft.
   - Ask blocking questions before creating downstream artifacts when missing information materially changes:
     - Product goal
     - Target user
     - Scope
     - Platform
     - Existing product fit, affected modules, or relevant historical product decisions
     - Metrics
     - Tracking
     - UI delivery direction
     - Payment, privacy, legal, compliance, security, or financial risk
   - If any must-answer question exists, ask it and stop before creating `prd.md` or UI deliverables. Record it in `run-log.yaml` only when a trace is being written.
   - If any item is classified as `must confirm before development or launch`, record whether it blocks engineering handoff, launch, or both. Ask before generating PRD/UI deliverables that claim the blocked readiness. Launch-only confirmations may remain open only when the PRD clearly marks launch status as blocked and the engineering handoff scope excludes the unconfirmed item.
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
   - Use `Research Agent` and `tools/research-tooling.md` when competitor, market, benchmark, pricing, policy, compliance, or comparable product behavior can materially shape scope, copy, metrics, or UI delivery direction.
   - If web research cannot run, record `external_research.status: skipped` or `degraded`, the exact limitation, and make product recommendations visibly assumption-based.
   - Record source title, URL, access date when available, observed fact, implication, and confidence in `run-log.yaml`.

8. After the clarification gate passes, create or update the product-manager delivery artifacts:
   - `outputs/<run-id>/prd.md` when the user asks for a product requirement, rollout, product decision, or feature change PRD
   - `outputs/<run-id>/prd.html` when the user asks for browser-readable, externally deliverable, or copy/share-friendly PRD output; this is a PRD document rendering, not a UI prototype
   - `outputs/<run-id>/catalog.md` or `outputs/<run-id>/reference.md` when the request is primarily a structured reference/document handoff such as a parameter table, capability catalog, rule reference, data dictionary, SOP/runbook, or migration inventory
   - `outputs/<run-id>/catalog.html`, `outputs/<run-id>/reference.html`, or a `document_prototype` HTML only when the user asks for HTML, a browser-readable structured document, or a richer document review view
   - UI deliverable reference:
     - source-backed preview/delta files recorded in `run-log.yaml` when frontend source exists
     - `outputs/<run-id>/prototype-<platform>.html` as a source-extracted handoff when the feature was first rendered in the host project and the selected region is then extracted into annotated standalone HTML
     - `outputs/<run-id>/prototype-<platform>.html` only for compatibility standalone/no-source/fallback mode when no source-derived extraction is in scope
     - `outputs/<run-id>/index.html` is allowed only as the offline entry file when the user explicitly asks for a portable/offline HTML folder; it follows the same compatibility or source-extracted HTML rules as `prototype-<platform>.html`
   - `outputs/<run-id>/run-log.yaml`
   - Optional exports only when useful or requested:
     - `outputs/<run-id>/tracking-plan.csv`
     - `outputs/<run-id>/user-flow.mmd`
   - Do not create `pm-package.md`, `task-brief.md`, `clarifying-questions.md`, `assumptions.md`, `metrics-tree.md`, `tracking-plan.md`, `user-flow.md`, `review-checklist.md`, or `final-package-summary.md` by default.
   - Avoid split Markdown handoff files unless the user explicitly asks for them or the request is a structured reference/document handoff.
   - For structured reference handoffs, follow `artifacts/structured-catalog-contract.md`: include source/review status, access date, owner, field dictionary, entity/field/rule structure when relevant, source facts, product decisions, attention points, change log, completeness check, and engineering handoff notes.
   - If the user explicitly says no PRD is needed, do not generate `prd.md`; record the PRD omission as not applicable in `run-log.yaml` and make the structured reference or document prototype the primary delivery.
   - Keep confirmed MVP scope, optional scope, and future scope separate. Do not place an unconfirmed optional capability in MVP requirements or acceptance criteria.
   - For existing-product changes, explicitly define entry point behavior, navigation visibility, permission or eligibility states, and fallback states so the UI deliverable, PRD, and engineering handoff agree.
   - For `implemented-feature-prd` mode, include a branch evidence map in `prd.md`: changed files or modules inspected, user-facing surfaces found, behavior inferred from code, screenshots/assets used, tests or validation found, unverified product intent, and implementation-to-requirement coverage. The PRD must be complete enough to review without manually searching the branch for missing behavior.
   - For `implemented-feature-prd` mode, use `templates/implemented-feature-prd-template.md`, keep generated artifacts under `outputs/<run-id>/` or embedded `pm-copilot/outputs/<run-id>/`, and generate `prd.html` with `scripts/render_prd_html.py` when HTML is requested.
   - For `implemented-feature-prd` mode, put real screenshots under `<run-folder>/assets/` and reference them inline. If a screenshot is missing, insert only the exact `占位图` block at that requirement position, including the recommended image file name and purpose; do not use the words outside that block.
   - For `implemented-feature-prd` mode, do not create a standalone image, figure, or screenshot list by default. Images and missing-image markers must travel with the requirement, flow step, table row, dialog, or state they explain.
   - For `implemented-feature-prd` mode, name state screenshots as `<screenshot-object>-<specific-state>`, for example `文件上传-上传中.png`; never recommend generic names such as `文件上传-状态.png` or `asset-upload-state.png`.
   - Validate implemented-feature PRD output with `python3 scripts/render_prd_html.py outputs/<run-id>` when HTML is needed and `python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>`. In embedded mode, use `python3 pm-copilot/scripts/render_prd_html.py pm-copilot/outputs/<run-id>` and `python3 pm-copilot/scripts/run_delivery_checks.py pm-copilot/outputs/<run-id> --language <zh|en>`.
   - Each specialist step must follow `agents/agent-interface.md`: record status, confidence, artifact delta, validation delta, risks, and next expected output. PM Orchestrator owns final readiness labels and resolves contradictions before delivery.

9. Continue with assumptions only when:
   - The user explicitly says to proceed as a draft without answers, or
   - The unknown is clearly low-impact and listed as `can draft with stated assumption`.
   - Items classified as `must confirm before development or launch` are not draft assumptions. If an unresolved item blocks engineering, status must be `Draft with confirmation risk`, not `Ready for engineering`, unless the user explicitly accepts that draft risk. If the item blocks launch only, engineering status may be ready only when the launch blocker is visible and excluded from engineering acceptance criteria.
   - Keep unanswered questions visible in `prd.md`.

10. Choose UI delivery platform and artifact mode:
   - Web for desktop admin, SaaS, dashboards, tables, complex forms.
   - H5 for mobile web, landing pages, campaigns, lightweight checkout.
   - App for native mobile product flows.
   - Mini Program for mini-program containers, authorization, booking, ordering, and lightweight forms.
   - Generate multiple UI deliverables only for true cross-platform requirements.
   - If an existing demo, screenshot, page, route, design system, or component implementation is available, adapt that current surface and show the delta for the new requirement. Do not create a new unrelated product shell.
   - Vocabulary rule: user words such as "prototype", "原型", "demo", "draft", or "only generate a prototype" describe review scope, not implementation method. PM Copilot's default UI deliverable is source-backed whenever source exists. Standalone HTML can be a compatibility artifact, or a source-extracted handoff after the UI has first been rendered in the host project; do not confuse either mode with freehand greenfield UI.
   - Source-code-first rule: in repo-backed UI-delivery work, frontend source presence is enough to require source-backed rendering. Do not infer the user wants freeform, greenfield, or hand-written standalone UI just because the request says "prototype", "draft", "quick", "only generate prototype", or omits exact-fidelity wording. Use freeform UI only when no frontend code/current surface is available, source rendering is concretely blocked, the raw request explicitly asks for standalone/portable HTML, or the raw request explicitly asks to redesign/rebuild/from-scratch/stop reusing the original design.
   - In repo-backed UI-delivery work, keep host production flows read-only by default, but treat a user request for exact online/source-code UI parity, or the mere availability of a renderable host frontend, as approval to create an isolated source-rendered preview route, Storybook story, demo entry, or preview-only screen. Read real frontend code, assets, data shapes, state rules, and screenshots, then choose the lowest-risk artifact mode that preserves the current UI.
   - Before drafting any repo-backed UI, build `host_frontend_inventory`: platform source kind, frontend entry files, route/page/screen files, component-library files, style token/global style files, icon/asset sources, data/mock sources, render command, and preview surface. When available, pass the user requirement or target surface as the inventory query so relevant files are ranked ahead of unrelated routes. Cover Web/H5, Mini Program/Taro/uni-app, React Native/Flutter/native App, and other host frontend stacks with their native page/component/style files. If the frontend source or render entry cannot be found and the user expects real-product UI, stop and ask for the host app path or runnable preview instead of inventing a shell.
   - Choose the UI artifact mode before drafting: use `source_delta_patch` as the default for any renderable repo-backed frontend, where the baseline is imported/rendered from original host source and only the new requirement is added in preview-only delta files. Use `code_preview_route` for Web/H5 routes, `storybook_or_demo` for component demos, `mini_program_preview` for Mini Program/Taro/uni-app pages, or `app_preview_screen` for React Native/Flutter/native App screens when those platform containers are a better fit. Use `source_extract_html` when the intended PM workflow is to first make the desired UI real in the current host repository, then extract only the target region into an annotated standalone `prototype-<platform>.html` or `index.html` for engineering handoff. The source implementation can be an isolated preview delta by default, or production-oriented host files when the user explicitly asks to implement the feature in the current repository first. This source-extracted HTML is a portable handoff derived from the running host UI; it requires source preview evidence, extraction selector(s), extracted asset/style handling, annotation layer, source-change scope, and validation of both the source preview and the extracted HTML. Use `self_contained_html_from_host_code` only when the user's raw request explicitly asks for a portable/standalone/HTML artifact without source implementation, explicitly asks to redesign/rebuild/from-scratch/stop reusing the original UI, or after source rendering is attempted and blocked by a concrete command, browser, simulator, dependency, or preview-surface failure. "Only generate a prototype" means review scope only; it does not authorize standalone HTML or greenfield UI. Production files being read-only is not a blocking reason because isolated preview files are allowed; if the user asks for actual implementation in the current repo, record that the host mutation policy is user-approved implementation work. In fallback mode, capture an existing UI screenshot baseline when possible, mark the parity claim as fidelity-limited, and do not call it exact. In source-rendered preview modes, add only isolated preview route/story/demo/page/screen files and record changed files in `isolated_ui_prototype`; do not touch production flows unless explicitly requested.
   - For document-class HTML, use `document_prototype` mode instead of a normal product-page UI prototype. A document prototype should render a structured reference as a readable review surface with navigation, sections, tables, hierarchical fields, source/review state, attention points, change log, and completeness check. It does not need product UI `annotation-marker` controls unless the artifact also represents a user-facing product UI.
   - Structure repo-backed UI deliverables as two layers: `baseline_import` imports or renders the original product page/screen/components/styles/assets from host source without rewriting them; `delta_patch` contains only the new feature, mock state, wrapper/story/page/screen composition, markers, explanation dialogs, backend simulation notes, and tracking/edge-case annotations. If the user explicitly asks to implement the feature in the current repo before extraction, record the implemented source files separately from preview-only delta files and treat the running implemented UI as the extraction source. Multi-turn conversations must continue from the same `delta_patch.next_delta_anchor` and append to `multi_turn_change_log`, not reconstruct the baseline.
   - A source-backed preview may require a local dev URL, but the handoff is incomplete if it gives only a localhost address. Always record the preview command, preview route/screen, and changed preview/delta files. If the user asks for the common PM handoff pattern "先在原项目代码里生成/调整，再单独提取这块成独立 HTML", keep the source-rendered implementation as the truth source and additionally generate a source-extracted `prototype-<platform>.html` or offline `index.html` with annotation markers. If the user explicitly asks for a direct HTML file and source-level parity is not required or is allowed to be limited, generate compatibility `prototype-<platform>.html`; otherwise explain that exact UI parity depends on the source-rendered entry.
   - If the user asks to send an offline prototype, produce a real interactive HTML artifact or source-backed package entry. Do not deliver a screenshot-only page as the prototype. Screenshots may be included as visual evidence only when the HTML still contains real DOM layout, live controls, state changes, and annotation interactions.
   - The baseline layer should not be redesigned or filled with UI-delivery-only explanatory copy. Delta markers and annotation controls must not resize, crop, recolor, or cover critical unchanged UI.
   - Do not modify existing production routes, pages, components, global styles, assets, package files, or backend code unless the user explicitly asks for production-oriented implementation. Isolated preview-only files are allowed for source-rendered UI delivery mode and must be recorded separately.
   - In repo-backed UI work, perform a source-rendering pass before any visual recreation: inspect the host app shell, global stylesheet or theme tokens, design-system/component-library files, affected route/page/component files, local assets/icons, and any screenshots or demos that show the current surface. Build a concrete source-to-demo component map before drafting the UI deliverable.
   - Reuse existing component structure, layout density, tokens, class names, copy tone, and interaction patterns. If exact fidelity matters, import or render the host components directly in an isolated preview so the real icons, fonts, components, CSS, platform chrome, and runtime states execute directly. A self-contained HTML artifact may inline CSS only after host rendering is unavailable or intentionally out of scope, and it must state the approximation.
   - Use production-quality UI copy in the product surface. Do not sprinkle visible labels such as "示例", "演示", "Demo", "Sample", "Prototype", "Not production code", or "不是生产代码" through the UI. Put delivery-boundary and draft/placeholder status in `run-log.yaml`, PRD notes, annotations, metadata attributes, or comments. Only show visible draft/placeholder labels inside product UI when the product requirement itself needs users to see unreviewed regulated/reference content.
   - Capture or record an existing UI visual baseline before writing the UI deliverable when possible. Use a running host app, existing preview route, Storybook/demo, or user-provided screenshot. If the host frontend is renderable and a standalone fallback is used, a missing baseline must have a concrete attempted-render/browser/setup failure or raw-request portable/standalone/HTML request; otherwise the UI deliverable is not complete.
   - After the style reuse pass, run a design calibration pass: choose visual density, layout variance, and motion intensity from the host product and scenario; avoid generic AI UI signatures that do not belong to the current surface.
   - Record `isolated_ui_prototype` in `run-log.yaml`, including host mutation policy, artifact mode, target surface, preview files changed when host-rendered, production or implementation files changed when user-approved, `baseline_import`, `delta_patch`, source-to-demo mapping, backend simulation method, parity claim, and limitations. For `source_extract_html`, also record `source_extract` with source preview URL/file, extraction selector(s), extraction command, extracted HTML path, source-region screenshot path, style capture method, asset handling, annotation layer, source-change scope, and extraction limitations.
   - Record `host_frontend_inventory` and `style_evidence` in `run-log.yaml`, including concrete source files/assets, reused components, reused tokens or class patterns, icon/asset sources, the intended new-requirement delta, and limitations. Record `source_to_demo_mapping` with non-empty `source` and `prototype_representation` entries so reviewers can audit which host component or screen each UI-delivery region came from. Add a hidden `style-source-summary` comment or `data-style-source` attribute in generated HTML so reviewers can trace the visual source.
   - Record `existing_ui_visual_baseline` in `run-log.yaml`: status, source, target page or component, screenshot paths when captured, comparison method, and limitation. If screenshots are available, use them as review evidence for unchanged regions; do not claim pixel-level parity unless a visual comparison actually ran.
   - If the existing frontend style source cannot be inspected and the user expects a product-specific UI deliverable, ask for the missing screenshot/demo/component reference or mark the UI Delivery Agent output `degraded`; do not mark the UI deliverable `complete`.
   - Use visible numbered annotation markers on the UI element being explained. Generate the default marker set from an editable annotation map/configuration block such as `annotationConfig.notes`; users should be able to add, remove, reorder, or edit notes in that block without rewriting the product surface. The default UI marker is a small red circular badge using `annotation-marker`, `data-annotation-id`, and `data-annotation-placement="top-right"`. Badge text must be plain digits such as `1`, `2`, and `3`, not circled numeral glyphs or nested badge content. Place markers at a safe top-right position that is not clipped by overflow and does not force component text to wrap. Marker visual style must not change after click. Clicking a marker opens a small local `annotation-dialog` popover beside that marker, clicking the same marker again closes it, and marker clicks must not open a full-screen/global modal.
   - Marker popovers must contain only the annotation body text. Do not render the marker number, annotation title/name, or a close button in the popover. Long text must wrap without horizontal scrolling.
   - Use a short draggable annotation floating control with only the label `注释` in Chinese outputs or `Notes` in English outputs. Clicking it hides the floating control and slides in a right-edge full-height `annotation-list` panel for the current page/state; closing the panel restores the floating control. The panel may show numbered entries and titles, must not shrink or reflow the product surface by reserving layout space, and must close when the user clicks outside the side panel.
   - For document prototypes, replace UI annotations with `attention_points`. These must identify meaningful document risks or decisions such as `source_gap`, `pm_override`, `conflict`, `engineering_must_read`, `launch_blocker`, `cost_or_quota_risk`, `security_or_compliance`, or `change_marker`, each with a concrete `target_ref`. Do not add generic notes just to satisfy an annotation count.
   - Do not use a row of reviewer state tabs as the main UI. Required states must be reached through realistic product controls, form submissions, permissions, retry actions, or loaded data. If a reviewer-only page/state switcher is still useful, make it a secondary fixed/collapsed control marked `data-reviewer-only="true"` outside the product layout; it must not replace real interactions or look like product navigation.
   - Before delivery, verify standalone UI HTML JavaScript parses when HTML is generated, all primary buttons visibly change real product state, annotation markers open body-only dialogs, the annotation toggle opens and closes the right-side current-state list panel, the page annotation panel number badges use matching plain digit text and centered badge styling, reviewer-only state switches stay fixed/collapsed if present, and compact labels such as tabs or segmented controls do not fold because of annotation placement.
   - Keep access states coherent. Logged-out, guest, or no-permission controls must not reveal signed-in-only account data, user IDs, account-management links, sync actions, logout actions, or privileged navigation when clicked.

11. Run tool preflight and validation after file changes when possible:
   - `python3 scripts/preflight_tools.py` before full-loop iteration, embedded host evaluation, or final delivery; use `--strict` for PM Copilot release validation.
   - `python3 scripts/inspect_host_frontend.py --host <host-repo> --query "<requirement or target surface>" --pretty` before repo-backed UI delivery when a host frontend exists; record the result under `host_frontend_inventory`.
   - `python3 scripts/preflight_integrations.py --tier recommended` when external tools or integration recommendations are in scope; add `--check-remote` when current source availability must be verified.
   - `python3 scripts/preflight_tools.py --check-network <url> --require-network --strict` when source-backed research is required.
   - `python3 scripts/validate_repo.py`
   - `python3 scripts/validate_outputs.py outputs/<run-id> --language zh` for Chinese generated runs, or `--language en` for English runs, when `prd.md` or UI deliverable artifacts exist.
   - The same output validation command applies when `catalog.md`, `reference.md`, `catalog.html`, `reference.html`, or document prototype HTML exists.
   - `python3 scripts/validate_outputs.py outputs/<run-id> --pre-clarification` when a run intentionally stops before generation with only `run-log.yaml`.
   - `python3 scripts/validate_prototype_visual.py outputs/<run-id>` for compatibility standalone HTML browser screenshot and visual diff validation. Without `--prototype`, the command validates every supported compatibility HTML file in the run folder. For source-backed UI preview files, run the host dev/preview/Storybook/simulator path, then run `python3 scripts/validate_ui_preview.py <preview-url-or-file> --run-folder outputs/<run-id>` when a browser URL or file target is available; otherwise record equivalent simulator evidence under `visual_validation`.
   - `python3 scripts/extract_ui_region.py --target <preview-url-or-file> --selector '<css-selector>' --output outputs/<run-id>/prototype-<platform>.html --run-folder outputs/<run-id>` when a source-rendered region must be extracted into an annotated standalone HTML handoff; then run both source preview validation and standalone HTML validation.
   - `python3 scripts/run_delivery_checks.py outputs/<run-id> --language zh` or `--language en` before final delivery or iteration scoring.
   - `python3 scripts/agent_improvement_scorecard.py` after self-iteration or benchmark runs to turn eval coverage, runtime evidence, validation status, and failures into prioritized improvement work.
   - If Playwright or browser tooling is unavailable, first run `python3 scripts/setup_visual_validation.py` or guide the user through the same setup. Skip visual validation only when setup fails, browser launch is forbidden, or the user declines installation; record the exact reason.
   - HTML checks with `tidy -errors -quiet -utf8` if available.
   - Record the exact command, result, and limitation in `run-log.yaml` and the PRD validation section using `artifacts/tool-result-contract.md`. Do not claim validation was executed if it was skipped, and do not say validation "should be run" after it has already run.
   - Use `tools/tool-registry.yaml` to decide whether a tool is required, optional, setup-required, or not applicable.
   - After validation commands finish, do a validation-finalization pass: replace any earlier placeholder such as `pending`, `待执行`, `should run`, or `to be verified` in both `prd.md` and `run-log.yaml` with the actual pass/fail/skipped result and the observed limitation.
   - When `prd.html` exists, validate that image paths resolve, images/placeholders are inline at the relevant PRD position, there is no separate screenshot list, requirement-detail tables keep all semantic columns visible, Mermaid diagrams are renderable, and the page reads as a normal document instead of a decorative UI prototype.
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
For product-manager tasks such as PRD, requirements, tracking plans, UI deliverables, prototypes, user flows, or competitor research, read `pm-copilot/PM_COPILOT.md` and follow it.
```

See `adapters/` for Codex, Claude Code, and Cursor examples.

When embedded, first identify the host project root and load only relevant host context before drafting. Typical sources include the host README, product docs, route definitions, API contracts, existing PRDs, analytics conventions, package metadata, and nearby UI or service modules. If there is no host project or the agent cannot determine the current product state, it must ask for available product documents or the minimum missing context before generating PRD/UI deliverables.

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
- Do not present standalone HTML compatibility artifacts as production code.
- Require human confirmation for payment, privacy, legal, compliance, financial, or security-sensitive decisions.
