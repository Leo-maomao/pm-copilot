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
I need a PRD, tracking plan, and H5 prototype for membership auto-renewal optimization.
```

The adapter should detect product-manager tasks and delegate to `pm-copilot/PM_COPILOT.md`.

Before generating PRD, metrics, tracking, flow, or prototype artifacts, the agent should run or record tool preflight, inspect relevant host project files, and ask must-answer questions when the current product fit is unclear.

For solution shaping, repository files are current-product context and engineering constraints. They do not replace external competitor, benchmark, comparable-feature, policy, or public-solution research when that research materially affects the product decision.

For UI work, embedded runs should reuse the host app's current surface instead of inventing a new shell. Inspect relevant routes, component-library files, page components, theme tokens, global styles, screenshots, Storybook/demo pages, local assets, and nearby UI modules; record concrete `style_evidence`, source-to-demo mappings, and, when possible, an `existing_ui_visual_baseline` in the run log.

Prototype-only UI work should be isolated from host production implementation by default. The agent should read real frontend code, assets, data shapes, and state rules, then generate a self-contained HTML demo that looks like the current online surface with the requested feature added. It should not modify production routes, pages, components, styles, assets, package files, or backend code unless the user explicitly asks for production-oriented implementation or approves a prototype branch change. Record this boundary in `isolated_ui_prototype`.

When the user expects near-online fidelity, exact iconography, or the effect of "adding it directly in source code," embedded runs should switch from hand-recreated standalone HTML to a host-rendered preview route, Storybook story, or demo entry when that mutation boundary is allowed. If source changes are not allowed, the run log and PRD must state that standalone HTML is a fidelity-limited approximation.

Repo-backed UI prototypes should be split into two layers: `baseline_layer` restores the original product UI from host code and visual evidence; `delta_layer` contains only the new feature, visible markers, explanation dialogs, interactions, backend simulation notes, and tracking or edge-case annotations. Annotation controls should not distort the restored baseline UI.

Embedded prototypes should use red component-level annotation markers, click-open local annotation popovers beside each marker, click-again-to-close marker behavior, and a current-state annotation list while preserving the product surface's real page width, scroll behavior, modals, and access states. Marker visuals should not change after click. They should not expose signed-in-only account data or privileged actions in logged-out, guest, or no-permission states.

For UI validation, embedded runs should use host context and run `scripts/validate_prototype_visual.py`. If browser tooling is missing, run or guide `scripts/setup_visual_validation.py` before deciding to skip. Store screenshot/diff evidence under the generated run folder, not in host product source directories.

Before final embedded delivery, prefer:

```bash
python3 pm-copilot/scripts/run_delivery_checks.py pm-copilot/outputs/<run-id> --language zh
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

For repeat or similar requests, PM Copilot should create a distinct timestamped run folder instead of overwriting prior outputs, unless the user explicitly asks to revise an existing run.

For benchmark or self-iteration runs where the host repository is only a validation target, clean up generated `pm-copilot/outputs/<run-id>/` folders after scoring and moving the learning back into PM Copilot. Do not leave stale generated requirements in the host repository unless the user asks to keep them.

## What Not to Do

- Do not replace a software project's existing `AGENTS.md` with PM Copilot's full workflow.
- Do not force users to say "Use PM Copilot" if the task clearly asks for PM work.
- Do not generate full downstream artifacts before must-answer questions are resolved.
