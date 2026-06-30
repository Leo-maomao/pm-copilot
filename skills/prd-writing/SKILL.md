---
name: prd-writing
description: Use when generating or improving the primary PRD handoff artifact, including document information, version history, background, goals, research, requirement list, requirement details, tracking, i18n, acceptance criteria, test suggestions, and code evidence for implemented features.
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
6. Use the fixed numbered top-level structure: `文档信息`, `版本记录`, `需求背景`, `需求目标`, `需求调研`, `需求列表`, `需求详情`, `埋点需求`, `多语言需求`, `验收标准`, and `测试建议`.
7. For implemented-feature PRD delivery, append `代码实现说明`, `代码位置`, and `验证结果`. Omit these code-related top-level sections when no implementation has been inspected.
8. Add separate PRD status, engineering handoff status, and launch status inside `文档信息`.
9. Write concise background and research/reference findings. Include user/business research, scenarios, current-product research, existing implementation findings, historical PRD findings, screenshots, and technical solution references when available.
10. Mark source date, confidence, and limitation for external or time-sensitive facts.
11. Define project goals and metrics.
12. Separate confirmed MVP scope, optional or conditional scope, future scope, and non-goals inside `需求列表` or `需求详情` rather than creating an unnumbered scope appendix.
13. Create a requirement list with stable IDs, but keep it scan-level only.
14. Write requirement details for each functional item, including function, scenario, entry/trigger, content requirements, business logic, interaction rules, data rules, permission rules, edge states, tracking links, and acceptance links where relevant.
15. Place screenshots or image placeholders inline in the related requirement, flow, or evidence position. Do not create a separate image list by default.
16. For frontend page, UI component, visual-state, or interactive-control changes, include UI specifications in the affected requirement detail: component/surface, layout/alignment, dimensions, spacing, typography, color/token, icon/image rules, states, responsive behavior, accessibility/focus behavior when relevant, and visual acceptance notes.
17. Add flow diagrams only when they improve reviewability for a specific requirement. Place each Mermaid diagram inside that requirement's detail subsection, not as fixed global `用户流程图` and `功能流程图` sections.
18. Add tracking plan event and property tables inside `埋点需求` by default.
19. Add newly added or changed UI copy as a pure-text extraction block in `多语言需求`, or explicitly state that no new UI copy is involved. Use only the current delivery language in that pure-text block unless the user explicitly asks for bilingual output.
20. For implemented-feature PRDs, add a code implementation section with risks/dependencies and implementation evidence that links branch evidence to requirement IDs and exposes partial/unverified/conflicting behavior.
21. Add code locations and concrete validation results when implementation evidence exists.
22. For required top-level sections with no applicable content, write one explicit localized `Not applicable: <reason>` line or row. Remove optional subsections, diagrams, tables, and image blocks that have no real content; never ship empty placeholders or `待补充`.

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

- Name screenshots by content. If one object has multiple states, use object plus concrete state, for example `资料卡片-加载中.png`, `资料卡片-加载失败.png`, or `设置弹窗-无权限.png`; do not use generic names such as `资料卡片-状态.png` or `profile-card-state.png`.
- Do not create a standalone image list, figure list, screenshot appendix, or screenshot inventory unless the user explicitly asks for one.
- Missing screenshots in Chinese PRDs are called `占位图`; do not use labels such as `待补真实图`.

## Flow And Copy Rules

- Functional flow sections, when present, must use Mermaid `flowchart` code blocks. Do not represent the primary flow as a table or a PNG.
- Flow diagrams are not mandatory for every PRD or every requirement; include them only for complex user paths, cross-system processes, or state-heavy interactions.
- Keep Mermaid node IDs ASCII and labels localized. Prefer simple unquoted labels and avoid custom `classDef` styling unless the renderer has been verified.
- Copy/i18n sections should include a pure-text block for newly added or changed UI copy so product managers can submit it directly for localization. Chinese PRDs should not list English/Chinese copy pairs in the pure-text block unless bilingual output was requested; put source-language notes, keys, and usage mapping in the table below instead.

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
