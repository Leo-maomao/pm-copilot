# PRD Contract

## Purpose

A PM Copilot PRD is a user-driven product document. It explains what identified users need, why they need it, and what experience and business rules the product must provide. It is not an engineering design, implementation plan, or technical solution document.

Every requirement must be traceable from a user, user scenario, or user-confirmed business problem in `需求清单` to a matching item in `需求详情`.

## Canonical Structure

Use these top-level sections and titles in order:

```text
## 一、文档说明
## 二、需求背景
## 三、需求调研                 # optional
## 四、需求清单
## 五、需求详情
## 六、多语言需求               # optional
## 七、埋点需求                 # optional
```

`需求调研` is included only when user research, competitive research, analytics, interviews, or other evidence materially shapes a requirement. `多语言需求` and `埋点需求` are included only when they contain real content. When an optional section is omitted, retain the canonical Chinese numeral of the sections that follow.

The H1 is a concise requirement sentence plus date, for example:

```markdown
# 支持团队项目协作 - 2026-07-28
```

Do not center the title on the word `PRD`.

## 一、文档说明

This section starts with two required subsections:

1. `文档信息`: requirement source, target users, affected product surface, document owner/status, and current revision summary.
2. `版本记录`: version, date, change summary, and owner for every material revision.

Keep document administration compact. It must not replace the user problem, requirement list, or requirement details.

## 二、需求背景

State the user problem before proposing product behavior. Include the relevant subset of:

- target users and their role or segment
- current user journey, problem, and impact
- business context and expected user or business result
- confirmed scope boundary, assumptions, and open product questions
- current-product evidence, clearly labeled as observed behavior rather than product truth

Do not put repository files, technical architecture, or implementation options in this section.

## 三、需求调研（可选）

Use this section only for evidence that changes the product decision. For each finding, state its source, date or confidence, insight, and affected requirement IDs. Do not manufacture research or present implementation observations as external research.

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

## 五、需求详情

`需求详情` is the behavioral source of truth. Create one numbered subsection for every requirement-list row, such as `### 5.1 团队项目入口`. Do not add a second identifier such as `R1`.

Each detail starts from the affected user and uses the smallest applicable set of merged fields:

- `用户与场景`: target user, user story, scenario, problem, and value
- `需求入口`: visible entry point, trigger, eligibility, and navigation context
- `需求详情`: main flow, business rules, permissions, normal and exception states, empty/loading/error feedback, recovery, degradation, and other user-visible boundaries
- `设计与交互`: information hierarchy, visible controls, interaction, accessibility, and feedback
- `图示`: inline screenshot, figure, or exact missing-image placeholder when visual evidence is needed

When a field contains more than one concern, use `一、`、`二、`、`三、` to group the concerns, then use `1.`、`2.`、`3.` for the detailed rules under each group. Apply this hierarchy to `需求入口`、`需求详情`、`设计与交互` and other fields when it improves reviewability; do not present every rule as one flat `1.`、`2.`、`3.` list. Do not split exception handling, permissions, or recovery behavior into repetitive standalone rows.

Flow diagrams are optional and have two distinct uses: a `用户流程图` shows the user's cross-surface path and decision points, while an `操作流程图` shows the operation, rules, permissions, states, and exceptions. Choose either diagram when it clarifies the requirement; use both only when both views add value. Place selected Mermaid diagrams immediately below the requirement title and above its detail table. When both are present, place `用户流程图` followed by `操作流程图`; the HTML delivery always renders the pair side by side, with each pane scrolling horizontally when needed. The affected detail table must follow the diagram(s). Do not add generic global flowchart sections.

Use a screenshot only when it materially clarifies a user-visible surface. Select its crop in three layers: retain the functional target, retain the locating context that tells the reader where it appears, and retain any comparison context needed to understand the rule or state. A crop is too tight if the reader cannot identify the page area, tab, section, or comparison that gives the target meaning; for example, a team-project crop may retain the adjacent personal-project area when that contrast explains the boundary. A crop is too broad when it retains unrelated global navigation, banners, feeds, blank canvas, or peripheral controls after the target and its context are already clear. Do not use a full-screen screenshot merely because it is available; use it only when the overall page layout or cross-surface relationship is the requirement. When no relevant visual evidence exists, write `无需补充图示。` instead of reusing an unrelated screenshot. Name and caption the figure to indicate the relevant area and state, such as `个人与团队项目区-已选择团队（局部截图）`.

Do not add separate risk, pending-confirmation, acceptance-result, or technical-test fields to requirement details. Keep only confirmed product behavior in the detail; when an unresolved product decision genuinely blocks drafting, handle it before generation or state the assumption in `需求背景`.

When a required visual is unavailable, place this exact-style block inside the affected requirement:

```markdown
> 占位图：资料卡片-加载中.png
> 用途：展示资料卡片加载过程中的骨架屏、按钮状态和错误兜底。
```

## 六、多语言需求（可选）

Include only when new or changed user-facing copy requires localization. When the section has one copy set, list the copy directly without a `6.1` subsection or explanatory lead-in; use a mapping table only when it adds real reuse or context value. Existing-key copy stays in the mapping table and does not belong in the direct copy list.

## 七、埋点需求（可选）

Include only when product measurement, experiments, funnel evaluation, or operational monitoring is in scope. Use exactly these concise columns: `名称`, `标识`, `时机`, `参数`, and `备注`; the values provide the Chinese event name and engineering event identifier. Label events as proposed when no approved taxonomy exists.

## Product Boundary

Technical implementation, technical solution, architecture, code path, component/service inventory, API definition, database design, deployment plan, command, and engineering work breakdown do not belong in a PRD. Put them only in a separately requested engineering handoff or the run trace.

Implemented-feature PRDs use observed user-visible behavior as evidence. Keep code, routes, tests, assets, configuration, commands, and other technical evidence in the run trace; in the PRD, describe only the product implication, confidence, gap, and user-facing acceptance result.
