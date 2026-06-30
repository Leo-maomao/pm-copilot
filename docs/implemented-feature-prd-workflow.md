# Implemented Feature PRD Workflow

Use this workflow when a feature is already implemented in the current branch and the user wants a PRD package reconstructed from actual code.

## Output Folder

- Direct PM Copilot root: `outputs/<run-id>/`
- Embedded host repository: `pm-copilot/outputs/<run-id>/`
- Run id format: `<feature-slug>-YYYY-MM-DD`
- Same-day collision suffix: `-2`, `-3`, and so on

Do not write PRD outputs to the host root, `docs/`, `zdocs/`, temporary folders, or sibling directories unless the user explicitly changes the output root.

## Required Files

- `prd.md`
- `prd.html`
- `assets/` when local screenshots or scripts are needed
- `run-log.yaml` when a persistent trace is useful

Implemented-feature PRD delivery is the exception to the general PRD rule where HTML is generated only when requested. Always render `prd.html` for this workflow.

Avoid split Markdown files by default. The PRD should contain assumptions, questions, risks, metrics, tracking, flows, acceptance criteria, validation, and engineering/data/API notes.

## Evidence Pass

Before drafting:

1. Inspect branch status, diff, touched files, nearby modules, UI entry points, dialogs, menus, stores, hooks, API services, i18n, analytics, tests, and existing docs.
2. Treat observed implementation as evidence, not as guaranteed product intent.
3. Record changed files, behavior evidence, screenshots/placeholders, validation evidence, and unresolved product intent in `run-log.yaml`.
4. Ask only for product intent, launch, legal/privacy/compliance, metrics, or screenshot gaps that cannot be recovered from the branch.

## PRD Structure

Use `templates/implemented-feature-prd-template.md` as the default structure.

The PRD should be complete enough for engineering review except for intentionally missing screenshots.

The H1 must be one concise requirement sentence plus the requirement date, for example `# 优化团队权限设置体验 - 2026-06-29`. Do not use a loose topic-list title plus `PRD`.

Use numbered top-level sections in this order:

1. 文档信息
2. 版本记录
3. 需求背景
4. 需求目标
5. 需求调研
6. 需求列表
7. 需求详情
8. 埋点需求
9. 多语言需求
10. 验收标准
11. 测试建议
12. 代码实现说明
13. 代码位置
14. 验证结果

Put scope, non-goals, information architecture, parameters/rules, states/exceptions, permission boundaries, data/API dependencies, frontend integration notes, risks/dependencies, and implementation evidence inside the relevant numbered sections rather than adding old unnumbered top-level appendices.

Because this workflow is only for already implemented features, the code-related sections 12-14 are required here. Planned/non-implemented PRDs must use the default PRD template and omit those sections.

If a required top-level section has no applicable content, keep the section and state `不涉及：原因` or the localized equivalent. Optional subsections, diagrams, image blocks, API/risk matrices, and evidence rows with no real content should be removed, not left empty.

Flow diagrams are optional. Add them only for requirements with complex user paths, cross-system behavior, state transitions, or branching logic, and place each Mermaid `flowchart` inside the specific requirement detail it explains. Do not create fixed global `用户流程图` and `功能流程图` subsections for every PRD.

## Screenshot Rules

Real screenshots:

- Save under `<run-folder>/assets/`.
- Reference inline from `prd.md`: `![<name>](./assets/<name>.png)`.
- Name by screenshot content, not figure number.
- If one screenshot object has multiple UI states, include both the screenshot object and the specific state, such as `资料卡片-加载中.png`, `资料卡片-加载失败.png`, `profile-card-loading.png`, or `profile-card-load-failed.png`. Do not use generic names such as `资料卡片-状态.png` or `profile-card-state.png`.

Missing screenshots in Chinese PRDs:

```markdown
> 占位图：<content-based-image-name>.png
> 用途：<what this screenshot should show>
```

Rules:

- Put the block exactly where the image belongs in the requirement.
- Use `占位图` only in missing-image blocks.
- Do not use labels such as `待补真实图`.
- Include the exact file name the user should save under `assets/`.
- Do not add a standalone screenshot list, image list, figure list, appendix, or checklist by default.
- Cover every independent changed page, window, panel, or dialog. Do not split micro-states into separate screenshots when a single screenshot captures the complete window or panel.

Replacement loop:

1. First pass: deliver inline placeholders.
2. Human pass: user saves screenshots under `assets/` using the recommended names.
3. Second pass: replace each placeholder block with a Markdown image reference at the same location.
4. Regenerate `prd.html`.
5. Verify no `占位图` marker remains unless screenshots are still intentionally missing.

## HTML Rendering

Prefer:

```bash
python3 scripts/render_prd_html.py outputs/<run-id>
```

Embedded mode:

```bash
python3 pm-copilot/scripts/render_prd_html.py pm-copilot/outputs/<run-id>
```

The generated `prd.html` must:

- contain one visible top-level PRD title
- use `pagetitle` behavior rather than adding an extra body title
- use the fixed PM Copilot document layout with a left table of contents
- keep the left table of contents synced to the reader's current `h2` or `h3` section, exclude the H1 title from the TOC, and use stable ASCII anchors
- use the available content width instead of a narrow fixed body
- preserve all table columns while keeping two-column field/value tables readable without squeezing the content column
- keep Markdown and HTML table cells consistently left-aligned unless a special data table explicitly needs another alignment
- merge empty trailing content cells for multi-column requirement image rows so a figure spans the relevant content area instead of widening one data column
- use local images
- keep images/placeholders inline
- support image lightbox/fullscreen viewing
- render Mermaid flowcharts through the local `assets/mermaid.min.js` runtime, not CDN
- allow normal external document links while avoiding remote scripts, stylesheets, images, and CDN runtimes
- avoid decorative cards, module blocks, unusual backgrounds, and nested scroll containers

## Flow And Copy Sections

- Functional flow diagrams must be Mermaid `flowchart` blocks inside `prd.md`. Do not use tables or PNGs as the primary flow diagram.
- Keep Mermaid syntax simple: ASCII node IDs, localized labels, plain branch labels, and no unverified styling extensions.
- Copy/i18n sections must include newly added or changed UI copy as a pure-text extraction block for PM localization submission, or explicitly state that no new copy is involved. The pure-text block contains only visible copy lines; i18n keys and usage notes belong in a separate mapping table.

## Validation

From the PM Copilot root:

```bash
python3 scripts/run_delivery_checks.py outputs/<run-id> --language zh
```

Embedded mode:

```bash
python3 pm-copilot/scripts/run_delivery_checks.py pm-copilot/outputs/<run-id> --language zh
```

If validation fails, fix the artifact or explicitly record why the requested delivery cannot satisfy the contract.
