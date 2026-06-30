# PRD Contract

Use this contract when generating or reviewing `outputs/<run-id>/prd.md`.

The PRD is the primary product-manager handoff artifact. It must be template-driven, easy to scan, and detailed enough for product, design, engineering, QA, analytics, and release reviewers to work from without searching the branch manually.

## Required Output

The top-level title must be one concise requirement sentence plus the requirement date:

```markdown
# <一句话需求> - <YYYY-MM-DD>
```

Do not use a loose topic-list title such as `<topic A>、<topic B> 与 <topic C> PRD`. The title should read like a single requirement statement.

The default PRD must use these numbered sections in this order. Headings and labels must be localized into the user's language.

```markdown
## 1. 文档信息
## 2. 版本记录
## 3. 需求背景
## 4. 需求目标
## 5. 需求调研
## 6. 需求列表
## 7. 需求详情
## 8. 埋点需求
## 9. 多语言需求
## 10. 验收标准
## 11. 测试建议
```

For implemented-feature PRDs reconstructed from a branch/current diff, add these code-related sections after the default structure:

```markdown
## 12. 代码实现说明
## 13. 代码位置
## 14. 验证结果
```

Optional risk, API, parameter, state, or dependency content should live inside the relevant required section instead of creating an unnumbered appendix. For implemented-feature PRDs, place these under `12. 代码实现说明` unless the user asks for a separate artifact.

Do not show the code-related top-level sections in planned/non-implemented PRDs. If no code has been implemented or inspected, keep engineering notes inside `7. 需求详情` or `11. 测试建议` and omit `12. 代码实现说明`, `13. 代码位置`, and `14. 验证结果`.

## Applicability Rules

The default top-level sections 1-11 are the PRD skeleton. If one of these sections is genuinely not applicable, keep the section and state `不涉及：<原因>` or the localized equivalent in a short line or row so reviewers know it was intentionally considered.

Conditional or optional content must be hidden when it does not apply. This includes code-related sections for non-implemented PRDs, flow diagrams, API matrices, risk/dependency tables, screenshot/image blocks, launch notes, and any specialist subsection that has no real content.

Do not leave empty tables, unfilled angle-bracket placeholders, `待补充`, `TBD`, or similar filler in delivered PRDs. Use a concrete decision, a stated assumption, a visible blocker, or omit the optional block.

## Section Requirements

`1. 文档信息` should include one-sentence requirement name, date, source, related modules, PRD status, engineering handoff status, and launch status.

`2. 版本记录` records every meaningful artifact revision.

`3. 需求背景` explains current problems, user/business impact, and why the requirement exists now.

`4. 需求目标` defines goals, metrics, target direction, and measurement notes.

`5. 需求调研` must cover users and scenarios. It should also include current-product research, implementation findings, external research when available, research limitations, rejected options when relevant, and reusable conclusions. Repository facts are current-product context, not competitor research.

`6. 需求列表` is a short scan-level summary only. It must not replace requirement details.

`7. 需求详情` is the most important section. It must contain complete behavior for every requirement. Flow diagrams are optional and must follow the requirement they explain. Add them only for requirements with complex user paths, cross-role/cross-system movement, state transitions, or branching logic. Place each diagram inside the relevant requirement subsection, using Mermaid `flowchart` blocks for primary flow diagrams. Do not add generic `用户流程图` and `功能流程图` subsections to every PRD.

For frontend page, UI component, visual-state, or interactive-control changes, `7. 需求详情` must include the relevant interface specification in the affected requirement. Do not stop at saying "optimize UI." Include the affected page/component, layout and alignment, dimensions, spacing, typography, color/token usage, icon/image rules, component states, responsive behavior, keyboard/focus/accessibility behavior when relevant, and visual acceptance notes. Hide this row/block for requirements that do not touch UI.

`8. 埋点需求` includes event tables and property definitions by default. If no approved taxonomy was found, label the event list as proposed and disclose the source gap.

`9. 多语言需求` includes newly added or changed UI copy as pure text plus a separate usage/key mapping. If there is no new copy, say so explicitly. The pure-text block must use the current delivery language only by default; for Chinese PRDs, do not list English/Chinese copy pairs unless the user explicitly asks for bilingual output.

`10. 验收标准` links acceptance criteria to requirement IDs and gives verification methods.

`11. 测试建议` gives focused test coverage by test type.

`12. 代码实现说明` is required for implemented-feature PRDs. It should include implementation scope, parameters/rules, state/exception behavior, data/API dependencies, risks, and implementation evidence.

`13. 代码位置` lists concrete files/modules and why they matter.

`14. 验证结果` lists concrete commands, pass/fail/skipped status, and limitations. Delivered PRDs must not leave stale placeholders such as `待执行`, `should run`, or `to be verified`.

## Requirement Details

`需求详情` must be detailed enough for design, engineering, QA, and analytics to proceed. For each functional item, include the relevant subset of:

| Field | Purpose |
| --- | --- |
| Requirement ID | Stable ID such as `R1` |
| Function name | Concrete capability being delivered |
| User scenario | Who uses it and in what situation |
| Entry point / trigger | Where the user starts or what system event starts it |
| Content requirements | Copy, fields, states, and content source requirements |
| Frontend UI specification | For UI changes: affected component, layout, dimensions, spacing, typography, color/token, icon/image, states, responsive/accessibility behavior, and visual acceptance notes |
| Business logic | Conditions, branches, limits, priority, and decision rules |
| Interaction rules | Click, hover, double-click, disabled, loading, success, and failure behavior |
| Data rules | Source, save, refresh, sorting, dedupe, and retention behavior |
| Permission rules | Who can view, operate, or be blocked |
| Edge states | Loading, empty, error, no permission, offline, rollback, and fallback behavior |
| Tracking links | Related event IDs |
| Acceptance links | Related acceptance criteria IDs |
| Figures | Inline screenshot or placeholder at the exact point it explains |

The `需求列表` section is only a rough overview. Each item in `需求详情` must remain reviewable without hunting through later chapters.

For cross-module, search, feed, dashboard, upload, or aggregation features, add source-by-source rows or a companion matrix covering source module, source permission rule, redaction rule, sorting assumption, partial-failure behavior, and performance boundary.

For algorithmic labels, scores, rankings, risk bands, recommendations, AI outputs, simulations, or forecasts, include source data, calculation window, refresh cadence, missing-data behavior, confidence/limitation language, reviewer owner, and user-facing limitations.

For public Web or SEO surfaces, include indexability, canonical URL, sitemap/robots behavior, metadata/structured-data requirements, cache behavior, public-data boundary, and proof that signed-in or private user data cannot appear in indexable HTML.

For AI assistants, automations, admin exports, workflow agents, or tool-enabled features, include trusted trigger, untrusted input boundary, tool allowlist/denylist, data scope, mutation permissions, redaction, audit logging, abuse tests, and human approval gates.

For accessibility-critical surfaces such as checkout, payment, account recovery, public service, support, consent, or cancellation flows, include visible labels, accessible names, keyboard/focus behavior, screen-reader expectations, error recovery, consent/price clarity, localization, and non-dark-pattern guardrails.

## Repo-Backed Engineering Map

For repo-backed product changes, include a localized engineering implementation map. In the new numbered structure:

- For planned PRDs, place likely routes, services, components, data/config files, analytics integration points, permission boundaries, and validation entry points inside `7. 需求详情` or `11. 测试建议`.
- For implemented-feature PRDs, place this information inside `12. 代码实现说明` and `13. 代码位置`.

This is not production code, but it must be specific enough for engineering to estimate and plan the change.

## Implemented Feature Evidence

When the PRD is reconstructed from an implemented branch or current diff, include an implementation evidence and coverage map under `12. 代码实现说明`. This section must separate observed implementation behavior from inferred product intent.

Include the relevant subset of:

| Field | Purpose |
| --- | --- |
| Evidence ID | Stable ID such as `EV1` |
| Source | Branch, diff, file path, screenshot, asset, test, or user-provided note |
| Observed behavior | What the implementation proves |
| Related requirement IDs | Requirement IDs supported by this evidence |
| Coverage status | Covered, partial, unverified, or conflict |
| Gap or risk | Product intent, rollout, metric, permission, copy, or launch gap still requiring confirmation |

The PRD must be complete enough to review without manually inspecting the branch. Any behavior visible in the diff should either be represented in scope, requirement details, acceptance criteria, risks, evidence, or explicitly excluded with rationale.

## Image Rules

Images in PRD Markdown or HTML must appear where the reader needs them. Do not create a detached image, figure, screenshot list, image appendix, or screenshot inventory by default.

For Chinese implemented-feature PRDs, missing screenshots must use only the exact inline block:

```markdown
> 占位图：资料卡片-加载中.png
> 用途：展示资料卡片加载过程中的骨架屏、按钮状态和错误兜底。
```

When the real image exists, replace the whole placeholder block at the same position with:

```markdown
![资料卡片-加载中](./assets/资料卡片-加载中.png)
```

State screenshots must be named with the screenshot object plus the concrete state, such as `资料卡片-加载中.png`, `资料卡片-加载失败.png`, or `设置弹窗-无权限.png`; do not use generic names such as `资料卡片-状态.png` or `profile-card-state.png`.

Screenshot coverage should be page-level rather than micro-state inflated: every independent changed page, window, panel, or dialog must be represented, but states that are visible together in one window should stay in one screenshot or placeholder.

## Rules

- Use tables for version history, goals, research matrices, requirement list, requirement details, tracking, copy mapping, acceptance criteria, test suggestions, code positions, and validation when there are multiple items.
- Use stable IDs such as `R1`, `AC1`, and `EV1`.
- Mark MVP, optional, future, and non-goal scope explicitly inside `6. 需求列表` or `7. 需求详情` when scope needs partitioning.
- Keep project goals near the top so the rest of the PRD can be judged against them.
- Keep PRD status, engineering handoff status, and launch status separate.
- Do not put unconfirmed optional capabilities into MVP requirements or acceptance criteria.
- Specify entry point, navigation visibility, permission or eligibility states, and fallback behavior for existing-product surfaces.
- Put tracking events and property definitions in the PRD by default; create a CSV export only when useful.
- Put newly added or changed UI copy in the multi-language section as pure text that a product manager can copy for localization submission. Keep i18n keys, source-language notes, usage locations, interpolation notes, and reviewer notes in a separate table below the pure-text block. The pure-text block itself uses the current delivery language only unless bilingual output was requested.
- For implemented-feature PRD delivery, inspect current branch evidence before asking clarification questions that the code can answer.
- Markdown tables should use consistent left alignment separators (`---`) unless a user explicitly requests another alignment for a special data table.
- PRD Markdown should contain exactly one top-level title.
- PRD HTML must not create a second visible document title or leave a large unused content column.
- When `prd.html` is generated from `prd.md`, render it as a normal readable document with the fixed PM Copilot document shell: left table of contents that includes numbered `h2`/`h3`/`h4` sections, H1 excluded from the TOC, stable ASCII anchors, reading-position TOC sync, full-width content flow, complete readable left-aligned tables, rendered Mermaid diagrams through local assets, and inline images/placeholders at their relevant positions.
- For implemented-feature PRD HTML, prefer `scripts/render_prd_html.py`.
- UI delivery details belong in UI artifacts and annotations. In the new PRD structure, summarize UI delivery implications inside requirement details or code implementation notes instead of forcing a separate `UI 交付` top-level section.
- Mark assumptions explicitly.
- Do not bury unresolved decisions in prose.
- Localize headings and table labels into the user's language. Keep requirement IDs, event names, property names, and other machine-readable identifiers ASCII.
