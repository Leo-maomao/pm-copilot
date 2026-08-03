---
name: prd-writing
description: Use when generating standardized, user-driven, product-only PRDs.
---

# PRD Writing

## Goal

Create `outputs/<run-id>/prd.md` as a product document that starts from users and their problems, then makes every proposed behavior reviewable through a requirement list and matching requirement details.

## Workflow

1. Load `artifacts/prd-contract.md` and use its canonical ordered structure. When optional sections are omitted, renumber visible H2 sections consecutively; never leave a visible numeral jump.
2. Identify target users, their scenario, problem, desired outcome, and the source or confirmation status before drafting requirements.
3. Create `需求清单` before `需求详情`. Use the matching detail number, such as `5.1`, as the sole identifier for every coherent user need; include its user/role, scenario, user value, priority, and source status.
4. Expand each requirement only in its matching `需求详情` subsection. Do not create requirements that cannot be traced back to a user problem or scenario.
5. Structure each requirement detail with the four required rows: `用户与场景`, `需求入口`, `需求详情`, and `设计与交互`, followed by `图示` as the final table row when visual evidence is required. For an implemented-feature PRD, create a coverage item for every independently reviewable user-facing state: `real_figure`, `required_placeholder`, or `not_required`, with rationale. A named user-facing page, panel, dialog, node, toolbar, media state, or flow is visual evidence required; do not mark it `not_required`. Do not combine several states into one coverage item or placeholder name. Add each required figure or placeholder inline with its matching requirement. Before `required_placeholder`, execute and record the capability chain: discover existing previews, reuse or activate the project runtime using its actual project configuration, recover the target test state, then attempt Playwright, Chrome DevTools, and Computer Use. Do not assume or require a fixed port, and do not use `skipped` as a capture result. Every attempted capability and capture records `action`、`evidence` and a non-empty local `result_ref` under `tool-results/`. When capture recovery fails, continue with `required_placeholder`, set the PRD status to `可评审（图示待人工补全）`, and record the named manual replacement instruction in `run-log.yaml`; do not label the PRD as degraded or block its review. A placeholder cell contains only controlled `占位图：功能-状态.png` values, separated by `<br>` when several states need placeholders. Put normal and exception states, permissions, empty/loading/error feedback, recovery, and boundaries in `需求详情`; group multi-part content with `一、`、`二、`、`三、`, then use `1.`、`2.`、`3.` for the rules under each group. Do not add risk, pending-confirmation, acceptance-result, technical-test, or standalone exception fields.
6. Use `用户流程图` for a user's cross-surface or cross-state interaction path and `操作流程图` for operation rules, conditions, permissions, state transitions, or exceptions. Neither is mandatory: add either or both Mermaid diagrams immediately above the matching detail table only when they improve reviewability; when both are present, list the user flow first.
7. Treat a screenshot as evidence, not decoration. Follow the canonical visual-evidence, crop, naming, caption, placeholder, and multi-figure layout rules in `artifacts/prd-contract.md`; this workflow must not restate or override them. Record the required visual-capture review only in internal evidence. If a figure does not improve reviewability, omit the `图示` row.
8. Add `需求调研`, `多语言需求`, and `埋点需求` only when they have real, decision-relevant content. Before omitting `多语言需求` or `埋点需求`, complete the per-requirement coverage review in `run-log.yaml`: `not_needed` requires evidence that the requirement has no changed visible copy or no decision-relevant measurable action/outcome. Record measurable actions and outcomes as real YAML lists, never comments. The absence of existing event code or event definitions is not evidence for omission. For every research row, state the source fact and the PRD decision it changes. In a Chinese PRD, the multilingual pure-text block and `文案` column contain the localized Chinese copy only, not an English source string. A multilingual section contains only new or changed user-visible copy in one copyable pure-text block, followed by `文案`、`使用位置`、`参数` rows; list placeholders such as `{reason}` in `参数` and use `/` when none exist. A tracking table uses only `事件`、`事件名称`、`上报时机`、`附加参数`、`备注`: use unique lowercase semantic `feature_action` identifiers such as `login_click`, never PRD-location or generic IDs such as `prd_5_1_view` or `journey_view`. Select access events, meaningful clicks/operations, important outcomes, and value signals such as duration, depth, exposure, completion, or retention when the user journey needs them. Keep `上报时机` to one observable sentence, put only event-external properties in `附加参数`, and use `/` when either `附加参数` or `备注` has no content. Omit empty optional sections and explanatory labels.
9. Clean user input before writing: retain user-confirmed facts, source-backed observations, and explicit product decisions; remove template guidance, process narration, technical evidence, duplicated explanation, and vague filler. Mark an unresolved product rule as `待确认` only where it affects the requirement; never invent behavior from model intuition.
10. Add a version record only for the initial document or a material change to a user need, product behavior, scope, rule, or user-visible copy. Do not record rendering, formatting, validation, synchronization, or other document operations.
11. For implemented-feature reconstruction, use technical evidence only to infer and verify user-visible behavior. Record technical evidence in `run-log.yaml`, never in the PRD.
12. Do not include technical implementation or solution content in a PRD, including code paths, routes, components, services, APIs, schemas, infrastructure, commands, or technical architecture. Create or link a separate engineering handoff only when the user explicitly requests one.
13. Remove empty tables, artificial `不涉及` text, instructional prose, duplicated restatement, and detached implementation or testing plans. Before delivery, check that background explains a causal user problem, every list row names an independently reviewable user outcome, every detail row makes a distinct product decision, and every tracking event can answer a product or business question.

## Output

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/prd.html` when requested or when an implemented-feature PRD requires it

## Quality Bar

Before delivery, confirm that every requirement-list row answers all of these questions:

- Which user has the need?
- In what scenario or trigger does it occur?
- What problem or desired outcome does the user have?
- What product behavior addresses it?
- Where is the corresponding product behavior detail?

If any answer is unknown, ask for a decision or mark only the affected product rule as `待确认`; do not expand it into speculative details.
