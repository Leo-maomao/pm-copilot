---
name: prd-writing
description: Use when generating decision-first PRDs with evidence, scope, requirements, risks, readiness, and implementation traceability.
---

# PRD Writing

## Goal

Create `outputs/<run-id>/prd.md`, the primary product-manager handoff artifact that product, design, engineering, QA, and analytics can review directly.

## Workflow

1. Load the PRD contract from `artifacts/prd-contract.md`.
2. Use discovery output, user answers, current product context, and research findings as the source of truth.
3. For implemented-feature PRD delivery, inspect branch/diff evidence before drafting. Record changed files, UI surfaces, business logic, data operations, permissions, screenshots/assets, tests, and unverified intent; then reconstruct the requirement from observed behavior instead of inventing product scope.
4. Localize human-facing headings and prose to the user's language, while keeping machine-readable IDs, event names, property names, and file names ASCII.
5. Make the H1 a one-sentence requirement plus date, for example `# 优化团队权限设置体验 - 2026-06-29`. Do not use a loose topic-list title plus `PRD`.
6. Use the decision-first structure: `产品决策摘要`, `背景与证据`, `目标与成功标准`, `范围与非目标`, `需求详情`, `交付设计`, `风险、决策与待确认`, and `验收与就绪度`.
7. For implemented-feature PRD delivery, append `实现证据与覆盖映射` and `验证结果`. Omit these sections when no implementation has been inspected.
8. Put the recommendation, confidence, separate PRD/engineering/launch states, key blocker, and next checkpoint on the first rendered screen.
9. Write concise background and evidence findings. Separate user/business evidence, current-product evidence, external evidence, assumptions, and unknowns.
10. Mark source date, confidence, and limitation for external or time-sensitive facts.
11. Define project goals and metrics.
12. Separate confirmed MVP scope, optional or conditional scope, future scope, and non-goals in `范围与非目标`.
13. Use `需求详情` as the single behavioral source of truth; do not duplicate it with a scan-only top-level requirement list.
14. Write requirement details for each coherent product capability, including product judgment, scenario, entry/trigger, business logic, interaction, data, permissions, recovery states, dependencies, and goal/acceptance links where relevant.
15. Place screenshots or image placeholders inline in the related requirement, flow, table row, or evidence position. Do not create a separate image list by default. If a requirement detail is a two-column field/value table, put the screenshot or placeholder in the same `Figures`/`图示` row value cell instead of placing it below the table.
16. For frontend page, UI component, visual-state, or interactive-control changes, include UI specifications in the affected requirement detail: component/surface, layout/alignment, dimensions, spacing, typography, color/token, icon/image rules, states, responsive behavior, accessibility/focus behavior when relevant, and visual acceptance notes.
17. Add flow diagrams only when they improve reviewability for a specific requirement. Place each Mermaid diagram inside that requirement's detail subsection, not as fixed global `用户流程图` and `功能流程图` sections.
18. Add tracking only when measurement, experiment evaluation, funnel behavior, or operational monitoring is relevant; place it in the applicable `交付设计` subsection.
19. Add new UI copy as a pure-text extraction block only when new copy without an existing i18n key exists. Search repo translation sources before adding it; keep existing-key copy only in the usage mapping.
20. Make key decisions, the strongest rejected alternative, risks, owners, required-before phases, and open-question defaults explicit.
21. For implemented-feature PRDs, map implementation evidence to requirement IDs and expose partial, unverified, or conflicting behavior.
22. Remove optional subsections, diagrams, tables, and image blocks that have no real content; never ship empty placeholders, artificial `Not applicable` filler, or `待补充`.

## Output

- `outputs/<run-id>/prd.md`
- Optional machine-readable exports only when useful or requested

## Screenshot And Placeholder Rules

- In implemented-feature PRD delivery, use `templates/implemented-feature-prd-template.md` and keep screenshots attached to the requirement, flow step, table row, state, or evidence they explain.
- Cover every independent changed page, window, panel, or dialog. Do not create separate screenshots for micro-states when one screenshot captures the complete window or panel.
- Put real screenshots under `<run-folder>/assets/` and reference them inline, for example `![资料卡片-加载中](./assets/资料卡片-加载中.png)`.
- If a Chinese PRD is missing a screenshot, use only the exact inline block below and avoid the marker words anywhere else:

```markdown
> 占位图：资料卡片-加载中.png
> 用途：展示资料卡片加载过程中的骨架屏、按钮状态和错误兜底。
```

- If the missing screenshot belongs in a Markdown table cell, do not use the blockquote form. Use the same-cell inline form instead:

```markdown
| 图示 | 占位图：资料卡片-加载中.png<br>用途：展示资料卡片加载过程中的骨架屏、按钮状态和错误兜底。 |
```

- When the real image exists for a table row, replace the same cell with `![资料卡片-加载中](./assets/资料卡片-加载中.png)`. Do not move the image above or below the table during replacement.
- Name screenshots by content. If one object has multiple states, use object plus concrete state, for example `资料卡片-加载中.png`, `资料卡片-加载失败.png`, or `设置弹窗-无权限.png`; do not use generic names such as `资料卡片-状态.png` or `profile-card-state.png`.
- Do not create a standalone image list, figure list, screenshot appendix, or screenshot inventory unless the user explicitly asks for one.
- Missing screenshots in Chinese PRDs are called `占位图`; do not use labels such as `待补真实图`.

## Flow And Copy Rules

- Functional flow sections, when present, must use Mermaid `flowchart` code blocks. Do not represent the primary flow as a table or a PNG.
- Flow diagrams are not mandatory for every PRD or every requirement; include them only for complex user paths, cross-system processes, or state-heavy interactions.
- Keep Mermaid node IDs ASCII and labels localized. Prefer simple unquoted labels and avoid custom `classDef` styling unless the renderer has been verified.
- Copy/i18n sections should include a pure-text block only for newly added or changed UI copy that has no existing i18n key, so product managers can submit it directly for localization. Chinese PRDs should not list English/Chinese copy pairs in the pure-text block unless bilingual output was requested; put source-language notes, existing keys, and usage mapping in the table below instead.

## Quality Bar

- The PRD is detailed enough for design, engineering, QA, and analytics to proceed without guessing core intent.
- Requirement, function, acceptance, metric, and tracking IDs are stable and cross-linked.
- Requirement details contain concrete logic, content, rules, interactions, data behavior, permission behavior, edge states, tracking links, and acceptance links where relevant.
- Implemented-feature PRDs cover every meaningful behavior visible in the implementation or mark the missing product intent as a gap with owner and impact.
- Research and reference findings sit before requirements because they explain the solution direction.
- UI delivery details are not a separate required top-level chapter in the fixed PRD template. Summarize UI implications inside requirement details or code implementation notes unless the user explicitly asks for a separate UI artifact reference.
- Images and image placeholders appear inline where they support the requirement; reviewers should not need to cross-reference a detached screenshot list.
- No unresolved decision is hidden inside prose.
- Time-sensitive or external claims are sourced, dated, or explicitly marked unverified.
- Readiness status does not imply engineering or launch approval without evidence.
