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
    |-- workflow/
    `-- outputs/
```

## Canonical Entry

Use:

```text
pm-copilot/PM_COPILOT.md
```

Do not rely on nested `pm-copilot/AGENTS.md` for embedded mode. Some tools only load instruction files from the current working directory chain, and non-Codex tools may not understand `AGENTS.md`.

## Trigger Without Remembering the Tool Name

Install an adapter into the host repository so users can say natural requests like:

```text
I need a PRD and tracking plan for checkout coupon optimization.
```

The adapter should detect product-manager tasks and delegate to `pm-copilot/PM_COPILOT.md`.

Before generating PRD, metrics, tracking, flow, or prototype artifacts, the agent should inspect relevant host project files and ask must-answer questions when the current product fit is unclear.

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

## Standalone Mode

If you open the `pm-copilot` folder directly, Codex can use the repository's own `AGENTS.md`, which is now only a thin shim pointing to `PM_COPILOT.md`.

Standalone mode is simpler for testing PM Copilot itself. Embedded mode is better when you want PM Copilot available inside a real software project.

## Expected Embedded Flow

```text
User gives a product-manager request from the host project
-> Host adapter delegates to pm-copilot/PM_COPILOT.md
-> Agent reads relevant PM Copilot workflow files
-> Agent inspects relevant host project context
-> Agent asks must-answer questions if goal, scope, platform, affected module, metrics, or risk is unclear
-> Agent stops until the user answers or explicitly accepts assumptions
-> Agent writes artifacts under pm-copilot/outputs/<run-id>/
```

For repeat or similar requests, PM Copilot should create a distinct timestamped run folder instead of overwriting prior outputs, unless the user explicitly asks to revise an existing run.

## What Not to Do

- Do not replace a software project's existing `AGENTS.md` with PM Copilot's full workflow.
- Do not assume nested `pm-copilot/AGENTS.md` will be loaded by every tool.
- Do not force users to say "Use PM Copilot" if the task clearly asks for PM work.
- Do not load all PM Copilot examples as product facts for the host project.
- Do not generate full downstream artifacts before must-answer questions are resolved.
