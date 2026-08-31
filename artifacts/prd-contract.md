# PRD Contract

## Purpose

A PM Copilot PRD is a user-driven product document. It explains what identified users need, why they need it, and what experience and business rules the product must provide. It is not an engineering design, implementation plan, or technical solution document.

Every requirement must be traceable from a user, user scenario, or user-confirmed business problem in `需求清单` to a matching item in `需求详情`.

## Evidence and Writing Reliability

Write only product facts that are user-confirmed, directly observed, or supported by cited research. Before drafting, clean the input into facts, decisions, unknowns, and discarded description; do not copy instructional prose, template notes, process logs, or technical evidence into the PRD.

When a product rule is proposed rather than confirmed, obtain a user decision before generation when it would change scope, user rights, pricing, compliance, or a core flow. Do not create a `待确认` item, risk field, or acceptance-result field in the PRD to paper over missing decisions. Do not silently fill gaps with model assumptions, inferred user intent, invented limits, fabricated research, or guessed existing behavior.

## Implemented-Feature Evidence Boundary

For an implemented-feature PRD, code, local test data, screenshots, and rendered states prove only that a candidate behavior exists; they do not alone prove release intent. Before using a candidate entry, control, state, copy, or figure, classify it as one of:

- `confirmed production behavior`: supported by user-confirmed launch intent, an explicit product decision, or trustworthy product evidence; it can enter the PRD.
- `development-only scaffolding`: local self-test, demo, screenshot staging, debugging, mock or fixture data, temporary entry, or explanatory text used only to build, test, or present the feature; record it under `context.context_excluded` when useful, but do not include it in the PRD title, requirement list, requirement details, visible copy, tracking, or figures.
- `unresolved intent`: do not include it in the PRD; ask for confirmation when omitting it would leave material production behavior unclear.

User-confirmed launch goals and explicit product decisions override observed implementation. A demo can evidence a confirmed production behavior, but the PRD describes only the intended production experience, never the demo setup or convenience text.

## Canonical Structure For New PRDs

Use these top-level sections and titles in order only when creating a new PRD:

```text
## 一、文档说明
## 二、需求背景
## 三、需求调研                 # optional
## 四、需求清单
## 五、需求详情
## 六、多语言需求               # optional
## 七、埋点需求                 # optional
```

`需求调研` is included only when user research, competitive research, analytics, interviews, or other evidence materially shapes a requirement. `多语言需求` and `埋点需求` are included only when they contain real content. Keep the core section headings stable even when optional sections are omitted; when `多语言需求` is omitted but `埋点需求` is present, it is `## 六、埋点需求`.

When a new PRD references or migrates content from another PRD, use the current new-PRD template for its document structure. The source PRD is evidence for confirmed requirement content, terminology, assets, and requested migration boundaries only. Never infer or state that the new document adopts the source PRD's chapters, field labels, numbering, or legacy media layout without explicit user direction.

## In-Place Revision Scope

When the user identifies an existing PRD, that PRD is the sole structural source of truth. Preserve its chapter order, headings, field labels, numbering, and all unaffected content. Do not describe another or older PRD as the correct template, and do not apply the new-PRD template to an existing PRD unless the user explicitly requests a structural rewrite.

For a layout-only request, such as pairing screenshots with their corresponding logic, modify only the affected `需求详情` cell and its rendered HTML. Do not add, remove, reorder, or rename chapters, requirement rows, detail fields, version records, research, localization, tracking, or flow diagrams. Renumber requirements only when the user explicitly deletes or merges requirements; then update every affected reference and preserve the version history.

The H1 is a concise requirement sentence plus date, for example:

```markdown
# 支持团队项目协作 - 2026-07-28
```

Do not center the title on the word `PRD`.

## 一、文档说明

This section starts with two required subsections:

1. `文档信息`: requirement source, target users, affected product surface, document owner/status, and current revision summary.
2. `版本记录`: version, date, change summary, and owner for every material product-requirement revision.

Keep document administration compact. It must not replace the user problem, requirement list, or requirement details.

`需求来源` must name the user input, observed problem, research, or confirmed business decision that initiated this document. `目标用户` names a concrete role or segment, not a generic audience. `影响范围` names the affected user-facing surface and excludes unrelated surfaces. `文档状态` states review readiness rather than a document operation. Do not fill any cell with template instructions, generic filler, or model guesses.

Do not add a version entry for rendering, formatting, screenshot capture, synchronization, validation, model invocation, or another document-only operation. `首次创建` is valid for the initial version; later entries must name the changed user problem, product behavior, scope, rule, or user-visible copy.

## 二、需求背景

State the user problem before proposing product behavior. Include the relevant subset of:

- target users and their role or segment
- current user journey, problem, and impact
- business context and expected user or business result
- confirmed scope boundary
- current-product evidence, clearly labeled as observed behavior rather than product truth

Do not put repository files, technical architecture, or implementation options in this section.

Write the background as a short causal chain: **who** encounters **what current problem** in **which scenario**, causing **what user or business impact**, and why the proposed scope is worth addressing now. Do not repeat the requirement table, promise an outcome without a user problem, or turn a solution preference into background.

## 三、需求调研（可选）

Use this section only for evidence that changes the product decision. For each finding, state its source, date or confidence, insight, and affected requirement IDs. Do not manufacture research or present implementation observations as external research.

Each finding must answer “what should change in this PRD because of this evidence?” If it does not alter priority, target user, flow, rule, wording, measurement, or scope, omit it. Keep source facts separate from the resulting product judgment.

## 四、需求清单

`需求清单` is mandatory and is the user-to-requirement index. Use the matching detail subsection number, such as `5.1`, as the sole requirement identifier; contain one row per coherent user need.

Each row must include:

- detail subsection number and concise requirement name
- target user or role
- user scenario, problem, or trigger
- user value or expected outcome
- requirement summary
- priority and confirmation/source status

Do not list technical tasks, APIs, code components, data tables, or implementation phases as requirements. A requirement with no identifiable user, scenario, or user value is incomplete and must be clarified before it is treated as an MVP requirement.

Use one row for one independently reviewable user outcome. Name the outcome rather than a screen, button, or internal task. The summary states the user-visible behavior and boundary; it does not repeat the title or hide rules behind words such as “优化”“支持”“完善”.

Requirement granularity is defined by a user outcome that needs a distinct product decision, not by a page, dialog, control, field, copy string, validation, or visual state. Changes within the same page, dialog, or flow stay in one requirement when they share the target user, primary entry, decision context, completion outcome, and release boundary; group the main flow, rules and states, and design and interaction details inside its matching detail table. Create another requirement only when its user outcome, target population or permission, entry, completion outcome, priority, or independently selectable release boundary differs. Visual coverage records states separately but never creates or requires a requirement row.

## 五、需求详情

`需求详情` is the behavioral source of truth. In a new standard PRD, create one numbered subsection for every requirement-list row, such as `### 5.1 团队项目入口`. Do not add a second identifier such as `R1`. In an in-place revision, retain the existing detail-table structure unless the user explicitly requests a structural change.

Each detail starts from the affected user and uses the smallest applicable set of merged fields:

- `用户与场景`: target user, user story, scenario, problem, and value
- `需求入口`: visible entry point, trigger, eligibility, and navigation context
- `需求详情`: main flow, business rules, permissions, normal and exception states, empty/loading/error feedback, recovery, degradation, and other user-visible boundaries
- `设计与交互`: information hierarchy, visible controls, interaction, accessibility, and feedback
- `需求详情` may contain repeated `prd-detail-media` blocks when a screenshot clarifies a state. In Markdown pipe tables, each source marker uses the exact inline syntax `[[prd-detail-media src="./assets/功能-状态.png" alt="功能-状态" copy="对应状态、规则和反馈"]]`; never put a block-level `<div>` in a table cell. After Pandoc output, the renderer expands every marker into `<div class="prd-detail-media-block"><div class="prd-detail-media"><img src="./assets/功能-状态.png" alt="功能-状态" /></div><div class="prd-detail-copy">对应状态、规则和反馈</div></div>`. Each block keeps the screenshot and its corresponding status, rule, or feedback in the same cell; the outer requirement table remains one table and one `需求详情` cell. The renderer fixes the image column width across all blocks, preserves image proportions, and switches to stacked layout only on narrow screens or paged output. A standalone Markdown image, `<img>`, or `prd-detail-media-block` source HTML directly in `需求详情` is invalid.

`用户与场景`、`需求入口`、`需求详情`、`设计与交互` are required for every detail. For an implemented-feature PRD, record one visual-coverage decision for every independently reviewable production user-facing page, panel, dialog, or decisive state retained in the PRD: `real_figure`, `required_placeholder`, or `not_required`. A production user-facing surface that materially affects review must not silently omit this decision.

The detail table may use only `用户与场景`、`需求入口`、`需求详情`, and `设计与交互`. Put boundaries, permissions, exceptions, recovery, state constraints, and every inline figure block in `需求详情` or `设计与交互`; never add standalone rows such as `边界规则`、`状态规则`、`异常规则`、`图示`, or other ad hoc field names. Visible image captions are omitted when the adjacent requirement text already identifies the state; keep alt text and controlled filenames for accessibility and traceability.

Use `real_figure` when a trusted rendered surface is available. Use `required_placeholder` only after a capability-based recovery chain: discover an existing preview, reuse or activate the project runtime through its actual project configuration, recover the needed test state, then attempt Playwright, Chrome DevTools, and Computer Use. The protocol never assumes a fixed port. Each non-skipped capability and capture attempt records its actual action, evidence, and a non-empty local result under `tool-results/`. A required placeholder does not downgrade or block PRD delivery: keep it inline, set `文档状态` to `可评审（图示待人工补全）`, and create one explicit manual replacement instruction for each missing figure in the run log. Record one coverage item per independently reviewable production state; never bundle several states into one placeholder name. A coverage item does not define a PRD requirement and must not cause a requirement to split. Use `not_required` only for a non-visual requirement or a declared non-essential visual state, with a rationale. Keep the `图示` row as the final row of its matching detail table. A placeholder cell contains only one or more controlled `占位图：功能-状态.png` values, without explanatory prose; separate multiple placeholders with `<br>`. A user-provided video is playback evidence: embed the original local video with browser controls and inline playback; never replace it with an extracted still frame unless the user explicitly requests a frame image.

Asset filenames and alt text use the relevant functional area and key state for traceability. Do not render a separate visible image-name caption when adjacent requirement text identifies the state. Each media block uses a fixed image column, fixed gap, and flexible text column; preserve proportions and stack only for narrow output. A controlled placeholder retains its file extension only as `占位图：功能-状态.png`.

## Requirement Coverage Review

Before delivery, review every requirement-list item across three independent dimensions: visual evidence, new or changed user-visible copy, and measurement. The review records an `included` or `not_needed` decision with evidence for each dimension; absence is not a decision.

Use the current locale diff and visible source copy to decide whether the PRD needs `多语言需求`. Use user entry, meaningful action, outcome, recovery, and business decision relevance to decide whether it needs `埋点需求`. Neither section is mechanically mandatory, but a `not_needed` decision is valid only when the reviewer explains why that requirement has no new copy or no decision-relevant measurable action/outcome. If one requirement needs tracking, include the PRD tracking section with only the corresponding meaningful events.

When a field contains more than one concern, use a separate content group for each independently presented concern or media block. Every independent group restarts its heading at `一、`; rules inside that group restart at `1.`、`2.`、`3.`. Do not continue `二、` or `三、` numbering merely because another group appears in the same `需求详情` cell. In Markdown table cells, write every group heading and every numbered rule on its own explicit `<br>` line, and separate groups with one or more visible `<br>` breaks. A `需求详情` cell with two or more rules must not compress them into one paragraph or use a flat list without a group heading. Apply this hierarchy to `需求入口`、`需求详情`、`设计与交互` and other fields when it improves reviewability; do not split exception handling, permissions, recovery behavior, or screenshot groups into new `5.x` requirements.

Use the rows for distinct decisions: `用户与场景` explains need and value, `需求入口` explains where and under what eligibility a user begins, `需求详情` explains complete visible behavior and boundary conditions, and `设计与交互` explains how the behavior is understood and operated. Do not use one long sentence to blur these decisions together. Do not add unconfirmed quotas, permissions, sorting, defaults, or existing-product behavior merely to make a detail look thorough.

Flow diagrams are optional and have two distinct uses: a `用户流程图` shows the user's cross-surface path and decision points, while an `操作流程图` shows the operation, rules, permissions, states, and exceptions. Choose either diagram when it clarifies the requirement; use both only when both views add value. Place selected Mermaid diagrams immediately below the requirement title and above its detail table. When both are present, place `用户流程图` followed by `操作流程图`; the HTML delivery always renders the pair side by side, with each pane scrolling horizontally when needed. The affected detail table must follow the diagram(s). Do not add generic global flowchart sections.

Use a screenshot only when it materially clarifies a user-visible surface. Use an actual rendered source and save the image under `assets/`. Select the first viable method for the available source: Playwright for a local or hosted preview, Chrome DevTools for an existing authenticated browser surface, then Computer Use for a surface that cannot be automated. The Agent—not a fixed dimension, percentage, or filename—must make the crop decision after inspecting the visual state. Select its crop in three layers: retain the functional target, retain the locating context that tells the reader where it appears, and retain any comparison context needed to understand the rule or state. A crop is too tight if the reader cannot identify the page area, tab, section, or comparison that gives the target meaning; for example, a team-project crop may retain the adjacent personal-project area when that contrast explains the boundary. A crop is too broad when it retains unrelated global navigation, banners, feeds, blank canvas, or peripheral controls after the target and its context are already clear. Do not use a full-screen screenshot merely because it is available; use it only when the overall page layout or cross-surface relationship is the requirement. Review the capture at normal document width and record the target, retained context, removed regions, crop decision, and readability result in internal evidence. When a crop replaces a raw capture, remove the superseded raw image from `assets/` unless it independently supports another requirement. The displayed name contains only the relevant functional area and key state, such as `个人与团队项目区-已选择团队`; do not add a file extension, `图示：`, capture type, or explanatory sentence. Every real image and video uses the same `功能-状态` caption style. When one `图示` row has multiple assets, render each media-and-caption pair on its own line with one blank-line-height gap before the next pair; do not place mixed media in a compact grid or let the media type change caption typography.

For an implemented-feature PRD, every requirement that names a production user-facing page, panel, dialog, node, toolbar, media state, or flow needs one visual-coverage decision. A named production user-facing surface cannot be `not_required`: use a real figure when available; otherwise, after capture recovery, retain the controlled placeholder inline in its `需求详情` cell and record every failed path in `run-log.yaml`. Development-only scaffolding excluded under the Implemented-Feature Evidence Boundary never receives a coverage item:

```markdown
| 需求详情 | ...<br>占位图：成员管理-高危角色确认.png |
```

Each real image is paired with its matching state logic in the same `需求详情` cell; do not repeat a visible image-name caption. A placeholder uses only `占位图：功能-状态.png`; record failed capture paths and the reason for the placeholder only in internal evidence.

The legacy standalone `图示` row is accepted only as input from older PRDs; the HTML renderer migrates it into the matching `需求详情` cell. New PRDs and production controller outputs must use the single-cell media-block layout above.

Do not add separate risk, pending-confirmation, acceptance-result, or technical-test fields to requirement details. Keep only confirmed product behavior in the detail; when an unresolved product decision genuinely blocks drafting, handle it before generation or state the assumption in `需求背景`.

## 六、多语言需求（可选）

Include only when **new or changed** user-facing copy requires localization. First provide one copyable pure-text block containing only the new text, without a `6.1` subsection or explanatory lead-in. Then provide a concise checklist with exactly `文案`、`使用位置`、`参数`: `使用位置` names the affected user-visible requirement or surface; `参数` lists placeholders such as `{reason}` or uses `/` when no placeholder is needed. Existing-key copy stays out of the pure-text block and must not be presented as new copy.

The pure-text block and checklist use the smallest localizable copy unit: every user-visible string that can appear, be replaced, or be used independently has its own pure-text line and matching `文案` row. Do not join separate labels, menu items, tabs, buttons, or messages with `/`, `、`, `；`, `<br>`, or parentheses merely because they belong to the same module, page, dialog, or usage location. Preserve a source string as one unit only when it is literally displayed as one continuous string, such as `已选择 3/10 项`; a slash in the `参数` column still means “no placeholder” and never permits joining copy values.

## 七、埋点需求（可选）

Include only when product measurement, experiments, funnel evaluation, or operational monitoring is in scope. Use exactly these concise columns: `事件`, `事件名称`, `上报时机`, `附加参数`, and `备注`. `事件名称` is a unique lowercase semantic identifier in `feature_action` form, for example `login_click`, `project_create`, `project_create_result`, or `feed_engagement`; it must carry the feature context and must not use PRD section numbers or generic prefixes such as `prd_5_1_view` or `journey_view`. Never show “拟议”, taxonomy-source narration, approval narration, or other explanatory labels in the PRD; retain those details only in internal evidence or an explicitly requested detailed handoff.

Build the event set from the user journey and the decision it must support, not from an exhaustive list of controls:

1. **访问**: record entry into a measurable page, tab, feed, or key flow so reach and funnel entry can be evaluated.
2. **点击 / 操作**: record a user’s meaningful choice, submission, switch, or retry; omit decorative or duplicate clicks that cannot change a product decision.
3. **结果**: record user-visible success, failure, cancellation, or completion for important creation, submission, payment, sharing, permission, or other business actions.
4. **价值行为**: add depth, duration, exposure, completion, or retention signals when the feature’s value depends on sustained use. For example, a waterfall feed needs browsing duration and meaningful scroll/exposure depth in addition to visit and item click; creation flows need the final creation result, not only the create-button click.

`附加参数` means **additional properties beyond the event itself**, not a restatement of “click” or “visit”. List only properties needed to explain the user, object, context, result, or value of that event. For example, `创建项目` can add `创建人标识、创建时间、项目名称`; `创建画布` can add `创建人标识、创建时间、关联项目名称`. Use `/` when no additional property is needed. Avoid raw sensitive personal data and record only the least specific property that supports the product decision. For implemented-feature reconstruction, the absence of existing event code or event definitions is never evidence that tracking is not needed; make that decision from the newly changed user action or outcome.

`上报时机` must state the observable moment in one short sentence, such as “页面完成首屏展示时”, “用户点击登录按钮时”, “项目创建结果展示时”, or “用户离开瀑布流或达到有效浏览阈值时”. `备注` is optional detail for metric intent, de-duplication, thresholds, or known limitations; use `/` when no note is needed and never place engineering implementation instructions in it.

## Product Boundary

Technical implementation, technical solution, architecture, code path, component/service inventory, API definition, database design, deployment plan, command, and engineering work breakdown do not belong in a PRD. Put them only in a separately requested engineering handoff or the run trace.

Implemented-feature PRDs use observed production user-visible behavior as evidence after it passes the Implemented-Feature Evidence Boundary. Keep code, routes, tests, assets, configuration, commands, validation, confidence, gaps, and other technical evidence in the run trace; in the PRD, describe only the confirmed user-facing product implication.
