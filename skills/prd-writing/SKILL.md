---
name: prd-writing
description: Use when generating or improving the primary PRD handoff artifact, including version history, research, goals, scope, requirement list, requirement details, flows, tracking, risks, acceptance criteria, and UI delivery reference.
---

# PRD Writing

## Goal

Create `outputs/<run-id>/prd.md`, the primary product-manager handoff artifact that product, design, engineering, QA, and analytics can review directly.

## Workflow

1. Load the PRD contract from `artifacts/prd-contract.md`.
2. Use discovery output, user answers, current product context, and research findings as the source of truth.
3. For implemented-feature PRD delivery, inspect branch/diff evidence before drafting. Record changed files, UI surfaces, business logic, data operations, permissions, screenshots/assets, tests, and unverified intent; then reconstruct the requirement from observed behavior instead of inventing product scope.
4. Localize human-facing headings and prose to the user's language, while keeping machine-readable IDs, event names, property names, and file names ASCII.
5. Add version history and requirement input / confirmation record.
6. Add separate PRD status, engineering handoff status, and launch status.
7. Write concise background and research/reference findings. Include competitor research, user/business research, existing implementation findings, historical PRD findings, screenshots, and technical solution references when available.
8. Mark source date, confidence, and limitation for external or time-sensitive facts.
9. Define project goals and metrics.
10. Separate confirmed MVP scope, optional or conditional scope, future scope, and non-goals.
11. For implemented-feature PRD delivery, add an implementation evidence and coverage map that links branch evidence to requirement IDs and exposes partial/unverified/conflicting behavior.
12. Create a requirement list with stable IDs.
13. Write requirement details for each functional item, including function, scenario, entry/trigger, content requirements, business logic, interaction rules, data rules, permission rules, edge states, tracking links, and acceptance links where relevant.
14. Place screenshots or image placeholders inline in the related requirement, flow, or evidence position. Do not create a separate image list by default.
15. Add a repo-backed engineering map when repository or implementation context is available.
16. Add functional and operation flow diagrams when they improve reviewability.
17. Add newly added or changed UI copy as a pure-text extraction block in the copy/i18n section, or explicitly state that no new UI copy is involved.
18. Add tracking plan event and property tables inside the PRD by default.
19. Add a UI delivery reference section that links the source-backed preview/delta, compatibility HTML artifact, and `prd.html` document when requested, while avoiding duplicated page-level annotations.
20. Add structured risks, open confirmations, acceptance criteria, delivery review findings, and validation results.

## Output

- `outputs/<run-id>/prd.md`
- Optional machine-readable exports only when useful or requested

## Screenshot And Placeholder Rules

- In implemented-feature PRD delivery, use `templates/implemented-feature-prd-template.md` and keep screenshots attached to the requirement, flow step, table row, state, or evidence they explain.
- Cover every independent changed page, window, panel, or dialog. Do not create separate screenshots for micro-states when one screenshot captures the complete window or panel.
- Put real screenshots under `<run-folder>/assets/` and reference them inline, for example `![文件上传-上传中](./assets/文件上传-上传中.png)`.
- If a Chinese PRD is missing a screenshot, use only the exact inline block below and avoid the marker words anywhere else:

```markdown
> 占位图：文件上传-上传中.png
> 用途：展示文件上传过程中的进度、按钮状态和不可重复提交规则。
```

- Name screenshots by content. If one object has multiple states, use object plus concrete state, for example `文件上传-上传中.png`, `文件上传-上传失败.png`, or `目标文件夹弹窗-非法目标.png`; do not use generic names such as `文件上传-状态.png` or `asset-upload-state.png`.
- Do not create a standalone image list, figure list, screenshot appendix, or screenshot inventory unless the user explicitly asks for one.
- Missing screenshots in Chinese PRDs are called `占位图`; do not use labels such as `待补真实图`.

## Flow And Copy Rules

- Functional flow sections must use Mermaid `flowchart` code blocks. Do not represent the primary flow as a table or a PNG.
- Keep Mermaid node IDs ASCII and labels localized. Prefer simple unquoted labels and avoid custom `classDef` styling unless the renderer has been verified.
- Copy/i18n sections should include a pure-text block for newly added or changed UI copy so product managers can submit it directly for localization.

## Quality Bar

- The PRD is detailed enough for design, engineering, QA, and analytics to proceed without guessing core intent.
- Requirement, function, acceptance, metric, and tracking IDs are stable and cross-linked.
- Requirement details contain concrete logic, content, rules, interactions, data behavior, permission behavior, edge states, tracking links, and acceptance links where relevant.
- Implemented-feature PRDs cover every meaningful behavior visible in the implementation or mark the missing product intent as a gap with owner and impact.
- Research and reference findings sit before requirements because they explain the solution direction.
- UI delivery details are not duplicated in the PRD; the PRD links the UI deliverable and summarizes covered screens/states.
- Images and image placeholders appear inline where they support the requirement; reviewers should not need to cross-reference a detached screenshot list.
- No unresolved decision is hidden inside prose.
- Time-sensitive or external claims are sourced, dated, or explicitly marked unverified.
- Readiness status does not imply engineering or launch approval without evidence.
