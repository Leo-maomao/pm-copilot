# Artifact Contracts

Every generated artifact must follow the relevant contract. Required decision fields must state `Unknown` or `Assumed` with a reason when evidence is incomplete. Conditional sections and optional blocks should be hidden when they do not apply instead of being preserved as empty or artificial `Not applicable` content.

Use the user's language for all human-facing artifact content, including headings, table column labels, status labels, notes, UI delivery annotations, and review labels. For analytics tables, localize reviewer-facing labels and keep machine field names such as `event_name` or `required_properties` visible in code formatting when implementation needs them. Keep file names, event names, property names, Mermaid node IDs, and other machine-readable identifiers in ASCII.

Readiness values, review severity labels, and review item statuses inside `prd.md` are human-facing and must be localized. Internal traces may keep stable English codes when useful, but Chinese PRDs should use Chinese statuses such as `可进入评审`, `框架范围可进入开发`, `发布前阻塞`, `高`, `中`, `低`, `未关闭`, or equivalent localized wording.

Repository templates are structure guides, not literal English copy. Translate template headings and labels when the requested output language is not English.

## Default Delivery

The default product-manager delivery contains only:

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/prd.html` for every PRD delivery
- a UI deliverable when a user-facing UI artifact is relevant:
  - `outputs/<run-id>/prototype-<platform>.html` for an evidence-based interactive review artifact
  - a UI flow or specification in `prd.md` when interactive HTML is not useful
  - `outputs/<run-id>/index.html` only as an offline folder entry when the user explicitly asks for portable/offline HTML handoff

When the user asks to turn an already implemented branch or current diff into a requirement delivery, PM Copilot must generate `outputs/<run-id>/prd.html` beside `prd.md`. This file is a browser-readable PRD document rendering, not a UI prototype and not a document-class structured catalog.

When the user asks primarily for a document-class handoff instead of a product requirement, such as a structured reference, parameter table, model matrix, API capability catalog, vendor table, data dictionary, payment or risk rule reference, SOP/runbook, or migration inventory, PM Copilot may generate `outputs/<run-id>/catalog.md` or `outputs/<run-id>/reference.md` as the primary delivery artifact. Generate `outputs/<run-id>/catalog.html`, `outputs/<run-id>/reference.html`, or a `document_prototype` HTML only when the user asks for HTML, browser-readable review, or richer document presentation. These files must follow `artifacts/structured-catalog-contract.md`.

For repo-backed UI work, source is read-only product evidence. The UI delivery reference is an evidence-based prototype, flow, or specification recorded in `run-log.yaml` and referenced from the PRD. It must distinguish current observed behavior from proposed behavior, name fidelity limitations, and identify the human owner who will implement the request. User words such as "prototype", "原型", "demo", or "only generate a prototype" describe review scope and never authorize host-source changes.

`outputs/<run-id>/run-log.yaml` is an internal trace artifact for debugging, regression, and auditability. It is not a PM-facing deliverable.

Generated run folders may also contain internal tool evidence under `outputs/<run-id>/tool-results/`, especially `delivery-check-report.json` from `scripts/run_delivery_checks.py`. These files are not PM-facing deliverables; they support auditability and regression scoring.

Do not create separate `task-brief.md`, `clarifying-questions.md`, `assumptions.md`, `pm-package.md`, `metrics-tree.md`, `tracking-plan.md`, `user-flow.md`, `review-checklist.md`, or `final-package-summary.md` by default. Create split files only when the user asks, an external workflow needs them, or a machine-readable export is useful.

When the user asks for engineering handoff, issue planning, unattended task planning, release readiness, or launch decision support, PM Copilot may additionally create:

- `outputs/<run-id>/dev-tasks.yaml`
- `outputs/<run-id>/launch-decision.yaml`

These are controlled handoff artifacts. They must follow `artifacts/dev-task-contract.md` and `artifacts/launch-decision-contract.md`.

The PRD contains only confirmed user problems, product behavior, user-facing flows, UI/interaction requirements, applicable new copy, and concise tracking requirements. Assumptions, unresolved questions, risks, validation results, technical evidence, and delivery-review findings belong in `run-log.yaml` or an explicitly requested handoff. Document-class requests keep source facts, product decisions, field dictionary, source status, review status, attention points, object-level changes, completeness checks, and engineering handoff notes in the structured reference artifact instead. If the user explicitly says no PRD is needed, do not create `prd.md`.

## Clarification Gate

Clarification output must not contradict itself. Do not mark one question as both blocking and assumed. Use distinct buckets:

- `must answer before generation`
- `can draft with stated assumption`
- `must confirm before development or launch`

If must-answer questions are unresolved, ask the user and stop before generating `prd.md` or UI deliverables. User silence is not approval.

Default readiness is `Ready for engineering` for the confirmed engineering scope. If engineering-blocking confirmations are missing, the agent must stop and ask. It may generate a draft only when the user explicitly requests a draft or accepts the risk, and the PRD status must reflect that downgrade. Launch readiness is a separate field; a PRD may be ready for engineering while launch remains blocked by content, legal, compliance, operational, or analytics approval.

## PRD

Required user-driven sections:

- H1 as one concise requirement sentence plus date, such as `# 优化团队权限设置体验 - 2026-06-29`
- `## 一、文档说明` with `文档信息` and `版本记录`
- `## 二、需求背景`
- `## 三、需求调研`, only when it materially shapes a requirement
- `## 四、需求清单`
- `## 五、需求详情`
- `## 六、多语言需求`, only when there is new or changed copy
- `## 七、埋点需求`, only when measurement is in scope

Keep the core PRD section numbers stable when optional research is omitted. Renumber only trailing optional sections: when localization is omitted but tracking remains, tracking is `## 六、埋点需求`.

Technical implementation sections must not appear in PRDs. Keep technical evidence in the run trace or a separately requested engineering handoff.

Required formatting:

- Use tables for document information, version records, research, requirement lists, requirement details, localization, and tracking when there are multiple items.
- In PRDs, use the requirement-detail subsection number, such as `5.1`, as the sole requirement identifier; do not add a duplicate `R1` label. In an in-place revision, compact remaining `5.x` IDs after deletion and update all references; the version record preserves historical change context.
- Use short paragraphs for background, research conclusions, and rationale.
- Avoid long undifferentiated unordered lists.
- Every requirement-list row identifies the matching detail number, target user, scenario, user problem or value, priority, and source status.
- Flow diagrams are optional and must sit immediately above the specific requirement-detail table they explain. `用户流程图` and `操作流程图` are distinct and may be used separately or together; when together, place them consecutively so the HTML delivery can render them side by side. Do not add fixed global flowchart subsections to every PRD.
- Remove optional diagrams, image blocks, API matrices, code evidence, or risk tables when they do not apply. Do not ship empty tables, angle-bracket placeholders, `TBD`, or `待补充`.
- Requirement details contain confirmed user-facing behavior only. Include normal flow, permissions, empty/loading/error feedback, recovery, and other user-visible boundaries in `需求详情`; do not add separate risk, pending-confirmation, acceptance-result, technical-test, or exception rows.
- Existing-product entry points, navigation visibility, permission or eligibility states, and fallback states are explicit when the feature adds or changes a surface.
- Frontend page, UI component, visual-state, or interactive-control requirements include the relevant interface specification inside the affected requirement detail: component/surface, layout/alignment, dimensions, spacing, typography, color/token, icon/image rules, states, responsive behavior, accessibility/focus behavior when relevant, and visual acceptance notes.
- Implemented-feature PRDs describe observed product behavior, confidence, and unverified product intent without exposing technical evidence.
- Implemented-feature PRDs keep screenshots and missing-image markers inline with the relevant requirement, table row, flow step, state, dialog, or evidence. Do not create a detached image list, figure list, or screenshot appendix by default.
- Screenshot evidence uses the smallest useful crop, but it must retain three layers of evidence: the target control or state, the locating page/section context, and any comparison context required to understand the behavior. Full-screen captures are reserved for page-level layout or relationship requirements.
- PRD screenshots are real local evidence by default. Omit the optional figure row when the image would not improve reviewability; use only the controlled inline `占位图：功能-状态.png` marker when an essential visual cannot be captured after all available recovery paths fail. Keep capture failures and rationale in internal evidence.
- Screenshot file names describe content. State screenshots use object plus concrete state, such as `资料卡片-加载中.png`, `资料卡片-加载失败.png`, or `设置弹窗-无权限.png`; generic names such as `资料卡片-状态.png` or `profile-card-state.png` are not acceptable.

Requirement details must be product-grade. For each functional item, include the relevant subset of:

- Requirement-detail number and requirement name
- User scenario
- Entry point or trigger
- Page or content requirements
- Business logic
- Interaction rules
- Data rules
- Permission or eligibility rules
- Edge and fallback states
- Tracking event links
- Acceptance criteria links

Minimum quality bar:

- A PM, designer, engineer, QA, and analytics reviewer can understand the requirement from `prd.md` plus the UI deliverable.
- User value is explicit in every requirement-list row and the corresponding detail.
- Research and reference findings explain why the product direction is shaped this way using source-backed competitor, benchmark, comparable feature, user research, public docs, or screenshots.
- Current-product findings from the host repository are product context, not a substitute for external product research. Describe only their user-visible product implications in the PRD; keep technical evidence in the run trace or a separately requested engineering handoff.
- Requirements are testable.
- Edge cases include error, empty, permission, payment, rollback, content-review, and launch-blocking cases where relevant.
- Product behavior in the PRD is confirmed and reviewable. Open questions, risks, and ownership stay in internal evidence or an explicitly requested handoff.
- Tool results follow `artifacts/tool-result-contract.md` and use capability IDs from `tools/tool-registry.yaml` where possible.
- Content source, review owner, review status, and disclaimer status are visible when the requirement includes reference, policy, medical, legal, financial, safety, or operational content. Unreviewed content is labeled as placeholder or draft and blocks launch.
- Delivery review findings, risks, validation, and technical evidence stay outside the PRD in internal evidence or an explicitly requested handoff.

## PRD HTML Document

Use `prd.html` when a PRD must be opened directly in a browser, delivered as a polished document package, or produced by the implemented-feature PRD workflow.

Required elements:

- Renders the same product requirement content as `prd.md`; it must not omit requirement rows, user-facing behavior, flow diagrams, tracking rows, or inline images/placeholders that appear in the Markdown.
- Uses a readable document layout with optional left table of contents and a normal content area. Do not create a card-heavy, module-heavy, marketing-style, or prototype-style page.
- Uses neutral document styling. Avoid unusual background colors, gradients, shadows, nested scrolling content containers, and mixed decorative modules.
- Preserves full table readability. Wide tables must keep all PRD semantic columns present and use wrapping, fixed layout, or horizontal overflow when needed.
- Renders Mermaid diagrams as diagrams. Final HTML must not leave raw Mermaid code blocks visible when Markdown contains Mermaid.
- Uses local relative paths or data URIs for images. Runtime scripts/styles needed for rendering should be local, except ordinary external reference links in document text.
- Places images and image placeholders inline at the relevant requirement, flow, or evidence position. If the Markdown has images inside table cells, the HTML must keep them inside the corresponding table cells.
- Real images support click-to-fullscreen or equivalent lightbox/dialog viewing.
- Does not create a detached screenshot/image list by default.
- Contains one visible top-level PRD title. The browser title should use page metadata such as `pagetitle`; the body should not duplicate the H1 or reserve a large blank column.

Minimum quality bar:

- A reviewer can read `prd.html` alone and understand the complete requirement without opening the Markdown or manually查漏补缺.
- The HTML document is portable with its local `assets/` folder when one is needed.
- The document is easy to scan and print/share as a PRD; it should not feel like a UI prototype.

## Tracking Plan

The tracking plan is a PRD section by default.

Required event table semantic columns. CSV exports must use the exact machine column names below; Markdown review tables may localize the visible label and include the machine name in code formatting.

- event_name
- description
- trigger
- platform
- actor
- required_properties
- optional_properties
- success_criteria
- validation_notes
- privacy_notes

Required property table semantic columns. CSV exports must use the exact machine column names below; Markdown review tables may localize the visible label and include the machine name in code formatting.

- property_name
- type
- required
- example
- description
- allowed_values
- privacy_level
- source

Minimum quality bar:

- Event names follow the configured taxonomy.
- If no configured taxonomy was found, the tracking plan is labeled as a proposed taxonomy and records the context source or absence of source.
- Each core user action has coverage or an explicit omission reason.
- Every property used by any event is defined once in the property dictionary.
- Sensitive properties are flagged and minimized.

## Flow Diagrams

Flow diagrams are PRD sections by default. Create `user-flow.mmd` only when a Mermaid source export is useful or requested.

Useful diagram types:

- Functional flow: system or feature-level logic, branches, and states.
- Operation flow: user-facing action path across pages or controls.

Minimum quality bar:

- Diagrams are standard Mermaid flowcharts when Markdown rendering is expected.
- The primary flow diagram is not a Markdown table or PNG image.
- Branch labels are meaningful.
- The flow matches the confirmed PRD scope.
- Notes explain only assumptions or edge cases that cannot fit cleanly in the diagram.

## Copy And Localization

Copy/i18n content is a PRD section by default when UI copy is added or changed.

Minimum quality bar:

- Newly added or changed UI copy appears as pure text that a product manager can copy into a localization request.
- The PRD also records usage scene, i18n key when known, and translation note when relevant.
- If no new copy is involved, the section says so explicitly instead of leaving reviewers to infer it.

## UI Deliverable

Required elements:

- Runs locally without build tooling when a portable HTML artifact is selected; source-rendered preview modes run through the host app's normal dev, preview, Storybook, simulator, or platform tooling.
- Simulates or uses the selected platform container.
- Matches existing product style when current screenshots, demos, routes, components, or design-system references are available.
- For repo-backed UI-delivery work, read real host frontend code and assets as evidence, keep the host read-only, and create an evidence-based prototype or specification under the run folder. This does not require the user to ask for exact UI parity.
- For repo-backed UI-delivery work, records `ui_delivery_trace` in `run-log.yaml`, including host mutation policy, artifact mode, target surface, preview files, `baseline_import`, `delta_patch`, source-to-demo mapping, backend simulation method, parity claim, and limitations.
- For repo-backed UI-delivery work, imports/renders `baseline_import` from original host source and puts only new feature behavior in `delta_patch`: preview composition, mock state, markers, explanation dialogs, interactions, backend notes, tracking notes, and edge-case notes.
- For repo-backed frontend products, records concrete `style_evidence` in `run-log.yaml`, includes source-to-demo mappings for reused host components, and includes `style-source-summary` or `data-style-source` in the HTML.
- For source-backed previews, records the preview command, preview route/screen/story, and changed preview/delta files; a localhost URL alone is not a complete UI deliverable reference.
- For portable HTML HTML, records boundary metadata/comments and the generated HTML path without adding visible "example/demo/not production" copy to the product UI.
- For repo-backed frontend products, records `existing_ui_visual_baseline` in `run-log.yaml`, including captured/provided screenshot evidence or an explicit skipped reason.
- For screenshot/image-to-UI work, records `image_reference_reconstruction` in `run-log.yaml`, including reference dimensions, intended viewport, visual inventory summary, asset handling, comparison method, mismatches fixed, and remaining fidelity limits.
- Includes key screens and states through realistic product controls or mocked data/API transitions, not just a reviewer state switcher.
- Includes interaction for the main path.
- States its fidelity level: `low`, `mid`, or `high`.
- Does not reserve a side annotation board by default. The product UI should keep its real layout width and height.
- Places compact numbered callouts at the top-right corner of the concrete UI component, state, or transition being explained, offset just outside the corner when needed to avoid covering content.
- Uses small red/white borderless `annotation-marker` badges with `data-annotation-id` and `data-annotation-placement="top-right"` on the UI surface. Marker badges and matching number badges inside marker dialogs and the right-side page annotation panel must show plain digits such as `1`, `2`, and `3`, not circled numeral glyphs or nested badge content, and must share the same rendered diameter, font size, font weight, line height, and centered digit alignment. Clicking a marker opens a local `annotation-dialog` popover beside that marker, clicking the same marker again closes it, and the marker's visual style does not change. Marker clicks must not open a full-screen/global modal. A short draggable `注释`/`Notes` floating control with `data-draggable="true"` opens a right-edge full-height `annotation-list` panel for the current page/state, hides while the panel is open, and reappears when it closes.

UI delivery annotations must cover the relevant subset of:

- Product design intent
- Logic rule
- Interaction behavior such as tap, hover, long-press, disabled, loading, error, and success
- Text length limit, truncation, and ellipsis behavior
- Content source and placeholder status
- Data source and refresh behavior
- Permission or eligibility behavior
- Tracking hook
- Engineering handoff note

Minimum quality bar:

- Standalone HTML requires no external assets; source-rendered previews may use verified host-project assets and dependencies through the host build path.
- Text fits in the layout.
- Callouts do not cover critical copy or controls.
- Annotation overlays must not change product layout, reserve persistent side space, or shrink the product viewport.
- Standalone HTML JavaScript parses when HTML is generated, and core buttons, product tabs, dialogs, annotation markers, and the annotation toggle produce visible state changes.
- Annotation markers are visible, unclipped, and do not force compact controls or tab labels to wrap.
- The product surface avoids visible `示例`, `演示`, `Demo`, `Sample`, `Prototype`, `Not production code`, or `不是生产代码` labels unless the requirement explicitly needs visible draft status. Delivery boundaries belong in metadata, comments, run logs, PRD notes, or annotations.
- The UI deliverable shows real screens, state changes, validation, empty states, errors, permissions, and success feedback where relevant.
- When existing product UI exists, the UI deliverable adapts the existing surface and highlights the new requirement delta instead of inventing an unrelated product surface.
- When host frontend code exists, the UI deliverable reuses the current app shell, component-library structure, tokens, spacing density, and copy tone rather than introducing a separate visual system, unless the raw request explicitly asks to redesign/rebuild/from-scratch/stop reusing the original UI.
- When source-level fidelity is requested or exact icons/components/native platform chrome matter, uses a source-rendered preview mode when available; otherwise the artifact explicitly states standalone-HTML fidelity limitations.
- Repo-backed UI-delivery-only work never mutates existing production routes, pages, components, styles, assets, package files, or backend code. It records observed evidence, proposed behavior, fidelity limits, and the human implementation owner.
- Delta markers and annotation controls do not resize, crop, recolor, or cover critical unchanged baseline UI.
- Backend-dependent behavior is represented through mock data, states, and annotations rather than implying backend implementation exists.
- For long pages, multi-state flows, and modals, preserve the product's real scrolling behavior. Do not clip modal contents or force the whole product into a fixed-height frame unless the host product does that.
- When existing screenshots or a runnable host app are available, unchanged regions are compared or reviewed against that visual baseline; without baseline evidence, the artifact must not claim pixel-level parity.
- When the target UI is supplied as an image, high, exact, 1:1, or pixel-level fidelity requires exact-size screenshot comparison evidence. Otherwise the PRD/run log must mark the UI deliverable fidelity-limited and list the verification gap.
- Browser screenshot validation covers at least one primary desktop or default viewport and one constrained/mobile viewport when the platform has responsive behavior. Visual diff baselines are required for regression suites and optional for first-run exploratory artifacts.

## Engineering and Launch Handoff

`dev-tasks.yaml` and `launch-decision.yaml` are optional controlled handoff artifacts.

Minimum quality bar:

- Development tasks trace to PRD requirement-detail IDs and, when present, acceptance IDs from the requested handoff.
- Blocked tasks are not marked issue-ready.
- Launch decisions separate evidence-backed gates from missing approvals.
- Unattended launch decisions cannot mark `ready_to_launch` unless explicit human approval evidence is present.
- Allowed and disallowed next actions are explicit.

## Document Prototype

Use a document prototype when the requested HTML is a browser-readable document or reference surface rather than a user-facing product page. It may use `prototype-web.html` when that is the selected HTML delivery path, but it must declare:

```html
<meta name="pm-copilot-artifact" content="document_prototype">
```

Required elements:

- Self-contained HTML with no external scripts, fonts, stylesheets, images, or CDNs.
- Document navigation, stable anchors, source/review status, structured tables, hierarchical fields or grouped rules when relevant, and responsive reading behavior.
- `attention_points` rendered as semantic badges, inline markers, risk summaries, change highlights, or filters. Traditional UI `annotation-marker` controls are optional and should not be used as filler.
- Attention points must use typed values such as `source_gap`, `pm_override`, `conflict`, `engineering_must_read`, `launch_blocker`, `cost_or_quota_risk`, `security_or_compliance`, or `change_marker`, and must target a concrete object, field, rule, or decision.
- Markdown, HTML, and run-log summaries must come from the same structured reference data or be checked for consistency before delivery.
- Presentation-only edits must not change structured source facts, product decisions, enums, defaults, limits, or rules.

Minimum quality bar:

- Reviewers can navigate the document quickly and see what is confirmed, uncertain, changed, blocked, or important for engineering.
- Generic notes that do not change reviewer behavior are not counted as valid attention points.
- Object-level patching preserves unrelated entities across multi-turn calibration.
- Document prototype validation should check document semantics, source/review state, attention points, and script parsing; it should not require product UI annotation controls.

## Structured References

Use `catalog.md`, `reference.md`, `catalog.html`, `reference.html`, or document prototype HTML for document-class knowledge handoffs: model integration matrices, API capability catalogs, vendor comparison tables, parameter dictionaries, migration inventories, data dictionaries, feature-flag lists, payment/risk rules, SOPs/runbooks, or other structured reference artifacts.

Minimum quality bar:

- The catalog declares `artifact_type: structured_catalog`.
- Every row has stable `item_id`, `display_name`, `source_status`, `review_status`, `owner`, `access_date`, and `implementation_notes`.
- Model catalogs include provider, model ID, version/release, modalities, context window, required/optional parameters, rate limits, pricing source, and deprecation status.
- Fast-changing facts are source-backed or explicitly marked draft/blocked.
- HTML catalogs are self-contained and do not load external scripts, fonts, stylesheets, images, or CDNs.
- Structured references distinguish extracted `source_facts` from final `product_decisions`.
- Document attention points are typed, useful, and target concrete objects, fields, rules, or decisions.
- Multi-turn calibration is object-level and records `change_log`, conflicts, protected objects, and presentation-only edits.

## Optional Exports

Split PRD, split tracking Markdown, split user-flow Markdown, review checklist files, `pm-package.md`, and `final-package-summary.md` must not be generated by default. Create a separate file only when the user explicitly asks for it or an external tool requires a machine-readable export such as CSV, Mermaid source, structured catalog Markdown/HTML, development task YAML, launch decision YAML, or visual review artifacts.
