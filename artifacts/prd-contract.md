# PRD Contract

## Purpose

A PM Copilot PRD is a decision and execution artifact. It must help a reviewer answer, in order:

1. What product direction is recommended?
2. Why is that direction credible?
3. What is in scope and explicitly out of scope?
4. What behavior must exist?
5. What risks, decisions, or confirmations remain?
6. Can product review, engineering handoff, or launch move forward now?

Format completeness is not the objective. A shorter PRD that makes the product decision and execution boundary clear is better than a long PRD filled with empty or not-applicable tables.

## Canonical Structure

Planned PRDs use these numbered top-level sections in order:

```text
## 1. 产品决策摘要
## 2. 背景与证据
## 3. 目标与成功标准
## 4. 范围与非目标
## 5. 需求详情
## 6. 交付设计
## 7. 风险、决策与待确认
## 8. 验收与就绪度
```

Implemented-feature PRDs append:

```text
## 9. 实现证据与覆盖映射
## 10. 验证结果
```

The H1 is one concise requirement sentence plus date, for example:

```markdown
# 优化团队权限变更的安全性与可追溯性 - 2026-07-10
```

Do not center the title on the word `PRD`.

## Decision-First Opening

The first rendered screen must show the current product judgment rather than document administration.

`1. 产品决策摘要` must include:

- recommended direction, or reconstructed product definition for an implemented feature
- confidence or implementation-intent alignment with evidence basis
- separate PRD, engineering handoff, and launch statuses
- key blocker or an explicit statement that none is known
- next checkpoint with owner or phase and expected completion evidence
- compact metadata such as source, date, affected modules/platform, and current revision summary

Version history is not a mandatory top-level section. Record the current revision in the summary; add a compact revision subsection only when multiple artifact revisions materially affect review.

## Evidence And Goals

`2. 背景与证据` separates:

- current problem and affected user scenario
- repository/product evidence
- external or authoritative evidence when relevant
- assumptions, unknowns, source gaps, and their product impact

Do not present repository facts as competitor research. Do not manufacture external research when it is not needed or unavailable.

`3. 目标与成功标准` connects each goal to a user or business result, an observable signal, direction or threshold, and validation window. Add guardrails when optimization can create abuse, fatigue, privacy, quality, support, compliance, or revenue risk.

## Scope

`4. 范围与非目标` must explicitly separate:

- MVP
- optional or conditional scope
- future scope
- non-goals

Do not put unconfirmed optional capabilities into MVP requirements or acceptance criteria. Scope partitions are product decisions, not labels added after drafting.

## Requirement Details

`5. 需求详情` is the behavioral source of truth. Do not create a separate top-level summary list that duplicates the same requirements.

Use stable IDs such as `R1`, `R2`, `AC1`, and `EV1`. Each coherent requirement should include the relevant subset of:

- product judgment and user value
- scenario, entry point, and trigger
- main flow and business rules
- content and copy behavior
- UI hierarchy, interaction, responsive and accessibility behavior when UI is in scope
- data, states, persistence, sync, and consistency rules
- permissions, eligibility, security, privacy, compliance, and operational boundaries
- loading, empty, error, retry, recovery, partial-success, and unavailable states
- dependencies, fallbacks, and degradation behavior
- links to goals, evidence, tracking, and acceptance criteria

Each requirement must remain reviewable without hunting through later sections. Keep only applicable rows; do not emit empty tables or repeated boilerplate.

Flow diagrams are optional. Use Mermaid `flowchart` blocks only for requirements with meaningful branches, cross-role or cross-system movement, or complex state transitions. Place the diagram inside the requirement it explains.

## Delivery Design

`6. 交付设计` contains only the cross-functional subsections that apply:

- data and tracking
- copy and localization
- UI and engineering handoff
- focused test coverage

Tracking is required when measurement, experiment evaluation, funnel behavior, or operational monitoring is part of the goal. If no approved taxonomy is found, label events as proposed and disclose the source gap.

For new UI copy, provide a pure-text extraction block only for copy without an existing i18n key. Existing-key copy belongs in the usage/key mapping, not in the pure-text block. The block uses the current delivery language unless bilingual output was requested.

Do not duplicate full `dev-tasks.yaml`, UI annotations, or launch decisions inside the PRD. Link or summarize their product-relevant implications.

## Risks And Readiness

`7. 风险、决策与待确认` must keep product decisions visible:

- selected decision and evidence
- strongest rejected alternative and why it was not selected
- risks or blockers with severity, impact, mitigation, owner, and required-before phase
- open questions with explicit default handling and whether work may continue

Do not bury unresolved decisions in narrative prose.

`8. 验收与就绪度` must include:

- acceptance criteria linked to requirement IDs
- observable verification method, preferably Given/When/Then or an equally testable result
- separate product-review, engineering-handoff, and launch readiness
- evidence already available, missing evidence with owner, and next action
- actual validation results or a concrete limitation; never leave `待执行`, `should run`, or `to be verified`

Engineering readiness does not imply launch readiness. Human approvals cannot be inferred from successful technical validation.

## Implemented-Feature Mode

Implemented-feature PRDs use implementation as primary evidence, not as automatic product truth.

Before drafting, inspect the current branch, diff, changed files, entry points, UI surfaces, assets, analytics changes, tests, and existing documentation. Separate:

- observed implementation behavior
- inferred product intent
- behavior that is not proven
- product gaps or recommendations

`9. 实现证据与覆盖映射` must map code, routes, tests, assets, configuration, and screenshots to requirements and show whether every observed behavior is represented and accepted.

`10. 验证结果` records concrete commands, results, coverage, evidence, and limitations. Generate `prd.html` with `scripts/render_prd_html.py` for implemented-feature delivery.

## Screenshots And Figures

Place every image or missing-image placeholder exactly where the requirement needs it. Do not create a detached screenshot inventory or image appendix by default.

For Chinese PRDs, a missing screenshot outside a table uses exactly:

```markdown
> 占位图：资料卡片-加载中.png
> 用途：展示资料卡片加载过程中的骨架屏、按钮状态和错误兜底。
```

Inside a requirement detail table, keep it in the same value cell:

```markdown
| 图示 | 占位图：资料卡片-加载中.png<br>用途：展示资料卡片加载过程中的骨架屏、按钮状态和错误兜底。 |
```

Replace the same block or cell with a local image when available. Screenshot names must identify the surface and concrete state, not a generic word such as `状态`.

## Output Rules

- Use exactly one H1.
- Localize human-facing headings, labels, statuses, and notes.
- Keep machine IDs, event names, property names, paths, and Mermaid node IDs ASCII.
- Remove optional subsections that do not apply; do not leave empty tables, placeholders, or artificial `Not applicable` rows merely to satisfy a format.
- Prefer compact tables for comparable records and prose for product reasoning.
- Render PRD HTML as a readable document with numbered-section navigation, stable anchors, complete tables, Mermaid rendering, and inline figures.
- Keep PRD status, engineering handoff status, and launch status separate everywhere.
