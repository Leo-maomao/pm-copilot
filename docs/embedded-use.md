# Embedded Use

Use embedded mode when PM Copilot lives inside another development repository.

## Why Embedded Mode Exists

Many software projects already have their own agent instruction files:

- Codex: `AGENTS.md`
- Claude Code: `CLAUDE.md`
- Cursor: `.cursor/rules/*.mdc` or legacy `.cursorrules`

PM Copilot should not replace those instructions. It should be delegated to only when the user asks for product-manager work.

In embedded mode, PM Copilot must use the host project's current product and code context. It should not generate a greenfield requirement that ignores the existing app, routes, data model, permissions, analytics conventions, or UI patterns.

## Recommended Structure

```text
host-repo/
|-- AGENTS.md or CLAUDE.md or .cursor/rules/
|-- src/
|-- docs/
`-- pm-copilot/
    |-- PM_COPILOT.md
    |-- agents/
    |-- skills/
    |-- prompts/
    |-- context/
    `-- workflow/
```

## Canonical Entry

Use:

```text
pm-copilot/PM_COPILOT.md
```

Do not rely on nested tool-specific instruction files for embedded mode. The host project's own adapter should delegate product-manager tasks to `pm-copilot/PM_COPILOT.md`.

## Trigger Without Remembering the Tool Name

Install an adapter into the host repository so users can say natural requests like:

```text
I need a PRD, tracking plan, and H5 UI deliverable for membership auto-renewal optimization.
```

The adapter should detect product-manager tasks and delegate to `pm-copilot/PM_COPILOT.md`.

Before generating PRD, metrics, tracking, flow, or UI-delivery artifacts, the agent should run or record tool preflight, inspect relevant host project files, and ask must-answer questions when the current product fit is unclear.

For solution shaping, repository files are current-product context and engineering constraints. They do not replace external competitor, benchmark, comparable-feature, policy, or public-solution research when that research materially affects the product decision.

For UI work, embedded runs should reuse the host app's current surface instead of inventing a new shell. First record `host_frontend_inventory`: platform source kind, frontend entry files, route/page/screen files, component-library files, style token/global style files, icon/asset sources, data/mock sources, render command, and preview surface. Pass the user requirement or target surface into the inventory query when available so relevant routes/components rank ahead of unrelated files. Inspect relevant routes, component-library files, page components, theme tokens, global styles, screenshots, Storybook/demo pages, local assets, and nearby UI modules; record concrete `style_evidence`, source-to-demo mappings, and, when possible, an `existing_ui_visual_baseline` in the run log.

UI-delivery-only work should be isolated from host production implementation by default. The agent should read real frontend code, assets, data shapes, and state rules, then use the host source as the baseline whenever it exists. It should not modify production flows unless the user explicitly asks for production-oriented implementation. Record this boundary in `isolated_ui_prototype`.

When host frontend source exists, embedded runs should switch from hand-recreated standalone HTML to a source-rendered delta patch, preview route, Storybook story, demo entry, Mini Program preview page, or App preview screen. Source availability is enough permission for isolated preview-only delta files, not production implementation. The original page/screen should be imported/rendered from host source; new ideas are layered through wrapper/story/page/screen composition and mock state. If the product manager needs to hand engineering an independent HTML file after shaping or implementing the UI in the original project, use `source_extract_html` and `scripts/extract_ui_region.py` to extract the target region from the running source preview or user-approved implementation. If source rendering is blocked, the run log and PRD must state that standalone HTML is a fidelity-limited approximation.

Repo-backed UI deliverables should be split into two layers: `baseline_import` renders the original product UI from host code and visual evidence without rewriting it; `delta_patch` contains only the new feature, visible markers, explanation dialogs, interactions, backend simulation notes, and tracking or edge-case annotations. Annotation controls should not distort the imported baseline UI. Standalone HTML fallback is acceptable only when the raw request asks for portable/standalone/HTML output, explicitly asks to redesign/rebuild/from-scratch/stop reusing the original UI, or when source rendering was attempted and blocked by concrete command, browser, simulator, dependency, or preview-surface evidence. "Only generate a prototype" means review scope only, not standalone HTML or greenfield UI.

When the selected artifact is source-backed, the final handoff should name the changed preview/delta files or user-approved implementation files, preview route/screen/story, run command, and validation evidence; a localhost URL alone is not sufficient. When the selected artifact is `source_extract_html`, also provide the source target, selector, extraction command, region screenshot, generated HTML path, style capture method, asset handling, editable annotation layer, source-change scope, validation report, and limitations. When the selected artifact is compatibility HTML, provide the generated HTML path and fidelity limitation.

Embedded UI deliverables should use red/white borderless component-level annotation markers generated from one editable annotation configuration, with body-only click-open local annotation popovers beside each marker, click-again-to-close marker behavior, a short `注释`/`Notes` floating control, and a right-edge full-height current-state annotation panel while preserving the product surface's real page width, scroll behavior, modals, and access states. Marker popovers must not repeat the number, title/name, or close button, and must not introduce horizontal scrolling. The side panel may include numbered notes and titles, and it should close through its close control or by clicking outside the panel. Marker visuals should not change after click. Required states should be driven by realistic controls, form submissions, permission gates, retry actions, or mocked data/API transitions; reviewer-only state switching controls should be fixed, collapsed, marked `data-reviewer-only="true"`, and outside the product layout. They should not expose signed-in-only account data or privileged actions in logged-out, guest, or no-permission states.

Generated UI should use realistic product copy. Do not add visible example/demo/not-production labels to the product surface; put delivery boundaries in metadata, comments, run logs, PRD notes, or annotations unless visible draft status is part of the product requirement.

For UI validation, embedded runs should use host context. Use `scripts/validate_prototype_visual.py` for compatibility HTML; use the host dev/preview/Storybook/simulator path for source-backed previews and `scripts/validate_ui_preview.py` when a browser URL or local preview file is available. If browser tooling is missing, run or guide `scripts/setup_visual_validation.py` before deciding to skip. Store screenshot/diff evidence under the generated run folder, not in host product source directories.

Before final embedded delivery, prefer:

```bash
python3 pm-copilot/scripts/run_delivery_checks.py pm-copilot/outputs/<run-id> --language zh
```

For implemented-feature-to-PRD delivery in embedded mode, generated files must live under `pm-copilot/outputs/<run-id>/`. Use `pm-copilot/templates/implemented-feature-prd-template.md` as the structure source, save real screenshots under `pm-copilot/outputs/<run-id>/assets/`, and render browser-readable PRD HTML with:

```bash
python3 pm-copilot/scripts/render_prd_html.py pm-copilot/outputs/<run-id>
```

Missing screenshots must stay inline with the relevant requirement, using only the exact `占位图` block and a recommended content-based file name such as `文件上传-上传中.png` or `文件上传-上传失败.png`. Do not create a standalone screenshot list, and do not write generated PRD files to the host root `outputs/` folder.

For source-backed previews with a browser URL, include the preview target:

```bash
python3 pm-copilot/scripts/run_delivery_checks.py pm-copilot/outputs/<run-id> --language zh --source-preview <preview-url-or-file>
```

For source-extracted HTML handoff, extract from the running preview first:

```bash
python3 pm-copilot/scripts/extract_ui_region.py --target <preview-url-or-file> --selector '<css-selector>' --output pm-copilot/outputs/<run-id>/prototype-web.html --run-folder pm-copilot/outputs/<run-id>
```

Record the resulting `tool-results/delivery-check-report.json` in the run log.

For engineering handoff, embedded runs may create `dev-tasks.yaml` with likely host files and validation commands. For release readiness, embedded runs may create `launch-decision.yaml`, but unattended decisions must remain gate recommendations unless explicit human approvals are present.

## One-Command Install

From the PM Copilot repository, run:

```bash
python3 scripts/install_adapter.py --host /path/to/host-repo --tool codex
```

Available tools:

```text
codex
claude-code
cursor
all
```

Examples:

```bash
python3 scripts/install_adapter.py --host .. --tool codex
python3 scripts/install_adapter.py --host .. --tool claude-code
python3 scripts/install_adapter.py --host .. --tool cursor
python3 scripts/install_adapter.py --host .. --tool all
```

The installer assumes PM Copilot is inside the host repository and calculates the relative path automatically. If PM Copilot lives somewhere else, pass the path the host agent should use:

```bash
python3 scripts/install_adapter.py --host /path/to/host-repo --tool codex --pm-path tools/pm-copilot
```

The installer is idempotent. Running it again updates the PM Copilot adapter block instead of duplicating it.

## Codex Adapter

Append the snippet in:

```text
adapters/codex/AGENTS.snippet.md
```

to the host repository's root `AGENTS.md`.

Codex reads `AGENTS.md` as project instructions. When PM Copilot is nested in a host repository, the host root `AGENTS.md` is the safer place to add the delegation rule.

Installer equivalent:

```bash
python3 scripts/install_adapter.py --host /path/to/host-repo --tool codex
```

## Claude Code Adapter

Append the snippet in:

```text
adapters/claude-code/CLAUDE.snippet.md
```

to the host repository's `CLAUDE.md`.

Installer equivalent:

```bash
python3 scripts/install_adapter.py --host /path/to/host-repo --tool claude-code
```

## Cursor Adapter

Copy:

```text
adapters/cursor/.cursor/rules/pm-copilot.mdc
```

to:

```text
<host-repo>/.cursor/rules/pm-copilot.mdc
```

Installer equivalent:

```bash
python3 scripts/install_adapter.py --host /path/to/host-repo --tool cursor
```

## Local Memory

For long-term use, keep private memory files inside `pm-copilot/context/`:

```text
context/product-memory.local.yaml
context/user-preferences.local.yaml
context/decision-log.local.yaml
```

These files are ignored by Git. They let PM Copilot remember stable product facts, the user's working style, and durable decisions. Current host repository context and current user instructions still override memory.

## Expected Embedded Flow

```text
User gives a product-manager request from the host project
-> Host adapter delegates to pm-copilot/PM_COPILOT.md
-> Agent reads relevant PM Copilot workflow files
-> Agent inspects relevant host project context
-> Agent asks must-answer questions if goal, scope, platform, affected module, metrics, or risk is unclear
-> Agent stops until the user answers or explicitly asks for a draft with assumption or confirmation risk
-> Agent writes artifacts under pm-copilot/outputs/<run-id>/
```

For repeat or similar requests, PM Copilot should create a distinct dated run folder such as `requirement-slug-YYYY-MM-DD`, with a numeric suffix for same-day collisions, instead of overwriting prior outputs unless the user explicitly asks to revise an existing run.

If PM Copilot is expected to update a separate repository but that checkout cannot be found, the agent may write the same source changes into a same-name local Desktop folder when it exists. The final handoff must say that this was a local source-folder update and that the user can push from there.

For benchmark or self-iteration runs where the host repository is only a validation target, clean up generated `pm-copilot/outputs/<run-id>/` folders after scoring and moving the learning back into PM Copilot. Do not leave stale generated requirements in the host repository unless the user asks to keep them.

## What Not to Do

- Do not replace a software project's existing `AGENTS.md` with PM Copilot's full workflow.
- Do not force users to say "Use PM Copilot" if the task clearly asks for PM work.
- Do not generate full downstream artifacts before must-answer questions are resolved.
