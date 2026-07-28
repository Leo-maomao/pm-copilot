---
name: prd-writing
description: Use when generating standardized, user-driven, product-only PRDs.
---

# PRD Writing

## Goal

Create `outputs/<run-id>/prd.md` as a product document that starts from users and their problems, then makes every proposed behavior reviewable through a requirement list and matching requirement details.

## Workflow

1. Load `artifacts/prd-contract.md` and use its seven-section structure.
2. Identify target users, their scenario, problem, desired outcome, and the source or confirmation status before drafting requirements.
3. Create `需求清单` before `需求详情`. Use the matching detail number, such as `5.1`, as the sole identifier for every coherent user need; include its user/role, scenario, user value, priority, and source status.
4. Expand each requirement only in its matching `需求详情` subsection. Do not create requirements that cannot be traced back to a user problem or scenario.
5. Structure each requirement detail as `用户与场景`, `需求入口`, `需求详情`, `设计与交互`, and `图示`. Put normal and exception states, permissions, empty/loading/error feedback, recovery, and boundaries in `需求详情`; group multi-part content with `一、`、`二、`、`三、`, then use `1.`、`2.`、`3.` for the rules under each group. Do not add risk, pending-confirmation, acceptance-result, technical-test, or standalone exception fields.
6. Use `用户流程图` for a user's cross-surface path and `操作流程图` for operation rules, permissions, states, or exceptions. Add either or both Mermaid diagrams immediately above the matching detail table only when they improve reviewability; when both are present, list the user flow first and render the pair side by side at every viewport width. For each `图示`, retain the functional target, the locating page/section context, and any comparison context needed to understand the behavior; remove unrelated navigation, banners, feeds, blank canvas, and peripheral controls. Use a full-screen screenshot only when the whole-page layout is the requirement; do not reuse an unrelated image when no relevant evidence exists.
7. Add `需求调研`, `多语言需求`, and `埋点需求` only when they have real, decision-relevant content. List a single copy set directly under `多语言需求` without a `6.1` subheading or lead-in. A tracking table uses only `名称`、`标识`、`时机`、`参数`、`备注`. Omit empty optional sections and explanatory labels.
8. For implemented-feature reconstruction, use technical evidence only to infer and verify user-visible behavior. Record technical evidence in `run-log.yaml`, never in the PRD.
9. Do not include technical implementation or solution content in a PRD, including code paths, routes, components, services, APIs, schemas, infrastructure, commands, or technical architecture. Create or link a separate engineering handoff only when the user explicitly requests one.
10. Remove empty tables, artificial `不涉及` text, and detached implementation or testing plans.

Use the exact missing-image placeholder format from the PRD contract when needed, for example `资料卡片-加载中.png` with a concrete purpose line inside the affected requirement.

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

If any answer is unknown, mark the requirement as an assumption or open question instead of expanding it into speculative details.
