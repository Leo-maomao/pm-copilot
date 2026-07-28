# Implemented Feature PRD Workflow

Use this workflow when a feature is already available in the current product context and the user wants a PRD package reconstructed from observed behavior.

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

Avoid split Markdown files by default. The PRD should contain assumptions, questions, risks, metrics, tracking, flows, acceptance criteria, and product-facing validation. Keep engineering, data, API, and other technical notes in the run trace or a separately requested handoff.

## Evidence Pass

Before drafting:

1. Inspect the available evidence needed to understand user-visible behavior, including relevant UI surfaces, analytics, screenshots, validation results, and existing documentation.
2. Treat observed current-product behavior as evidence, not as guaranteed product intent.
3. Record technical evidence, behavior evidence, screenshot evidence or gaps, validation evidence, and unresolved product intent in `run-log.yaml`; expose only product-facing behavior and real visual evidence in the PRD.
4. Ask only for product intent, launch, legal/privacy/compliance, metrics, or screenshot gaps that cannot be recovered from the branch.

## PRD Structure

Use `templates/implemented-feature-prd-template.md` as the default structure.

The PRD should be complete enough for product review and downstream handoff; omit optional figures that lack trusted visual evidence.

The H1 must be one concise requirement sentence plus the requirement date, for example `# 优化团队权限设置体验 - 2026-06-29`. Do not use a loose topic-list title plus `PRD`.

Use the user-driven numbered structure: `文档说明`, `需求背景`, optional `需求调研`, `需求清单`, `需求详情`, optional `多语言需求`, and optional `埋点需求`.

The first screen must identify the document source, target users, status, and revision. Build `需求清单` from the observed user-visible behavior before expanding matching requirement details. Keep technical evidence and command results in `run-log.yaml`; the PRD contains only the user problem, product behavior, confidence, gap, and user-facing acceptance result.

Remove optional subsections, diagrams, image blocks, and rows that have no real content. Do not preserve empty tables or artificial `不涉及` text solely to satisfy the template.

Flow diagrams are optional. Add them only for requirements with complex user paths, cross-system behavior, state transitions, or branching logic, and place each Mermaid `flowchart` inside the specific requirement detail it explains. Do not create fixed global `用户流程图` and `功能流程图` subsections for every PRD.

## Screenshot Rules

Screenshot acquisition order:

1. Inspect the host repository and identify its runnable UI, existing browser or e2e tooling, authentication path, and stable target state.
2. Capture the real state with the best available automated browser or visual-validation integration.
3. If the browser plugin or automation dependency is missing, run the supported setup or installation flow and retry. Do not assume one browser, framework, port, or host product.
4. If login is required, ask the user to sign in in the selected browser or provide a task-scoped token through an approved secure channel, then resume the same automated flow.
5. Validate that the image is readable at normal document width. Retry with a larger viewport, higher device scale, focused target, or full-window context when an element screenshot is too small or blurred.
6. Use manual capture only when automated capture cannot reproduce the required state.
7. If automated setup, authentication recovery, and manual capture are all unavailable or unsuccessful, omit the figure unless it is required to review the behavior. For a required figure, use the controlled inline placeholder with a small location-and-purpose caption and record every failed path in `run-log.yaml`.

Never copy credentials into generated artifacts, source-controlled environment files, logs, user-visible commands, or image metadata. Record only the authentication limitation and recovery status.

Real screenshots:

- Save under `<run-folder>/assets/`.
- Reference inline from `prd.md`: `![<name>](./assets/<name>.png)`.
- Name by screenshot content, not figure number.
- If one screenshot object has multiple UI states, include both the screenshot object and the specific state, such as `资料卡片-加载中.png`, `资料卡片-加载失败.png`, `profile-card-loading.png`, or `profile-card-load-failed.png`. Do not use generic names such as `资料卡片-状态.png` or `profile-card-state.png`.

Rules:

- Put a real image exactly where it belongs in the requirement.
- Omit the optional figure row when no trusted rendered source exists and the figure is not necessary to review the behavior.
- When the figure is necessary but unavailable, use only `占位图：<name>.png<br><small>位置：...；用途：...</small>` in the affected row or blockquote; add `状态：...` when relevant.
- Do not add a standalone screenshot list, image list, figure list, appendix, or checklist by default.
- Cover every independent changed page, window, panel, or dialog. Do not split micro-states into separate screenshots when a single screenshot captures the complete window or panel.

Replacement loop:

1. First pass: attempt real automated screenshots and place successful captures inline.
2. Recovery pass: install or configure supported browser tooling, or obtain login through user sign-in or a task-scoped token, then retry failed captures.
3. Manual fallback: request a human capture only for states that automation still cannot reach.
4. Final fallback: omit a nonessential figure, or use the controlled inline placeholder for an essential unavailable figure and record the failed capture paths in the run trace.
5. Regenerate `prd.html` and verify every real image is clear, local, correctly positioned, and click-to-fullscreen capable.
6. Verify every remaining screenshot placeholder is essential, inline, and includes a small location-and-purpose caption.

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
- keep real images inline
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
