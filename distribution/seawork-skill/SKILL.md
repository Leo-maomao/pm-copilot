---
name: pm-copilot
description: Use PM Copilot for user-driven PRDs, product reviews, tracking, handoffs, and evidence-backed self-improvement in the current project.
---

# PM Copilot Global Runtime

Resolve the runtime from `PM_COPILOT_HOME` or `~/.agents/pm-copilot`. Read its `PM_COPILOT.md` before performing product-agent work.

Before creating an artifact, resolve the active project workspace:

```bash
python3 "${PM_COPILOT_HOME:-$HOME/.agents/pm-copilot}/scripts/project_workspace.py" --cwd "$PWD" --ensure
```

For every PRD request, including natural-language requests without
`@pm-copilot`, use the canonical production controller before writing any
artifact:

```bash
python3 "${PM_COPILOT_HOME:-$HOME/.agents/pm-copilot}/scripts/prd_request_controller.py" --request "<request>"
```

For any active interactive PRD run, use this canonical control surface before
reporting progress or failure. It is the same implementation exposed as MCP
tools when the user explicitly invokes `@pm-copilot`:

```bash
python3 "${PM_COPILOT_HOME:-$HOME/.agents/pm-copilot}/plugins/pm-copilot/scripts/pm_copilot_mcp.py" \
  --run-folder "<canonical-run-folder>" --status
```

- For `needs_input`, submit the user's answer with `--answer "<answer>"`.
- For `awaiting_confirmation`, show the clarified scope. After an unambiguous
  confirmation, use `--confirm`.
- Report only the returned JSON. An artifact is generating only when
  `delivery_calls` contains it, and is created only when it appears in
  `artifacts`. Never narrate a controller state from chat text.

- In a legacy embedded project, use `pm-copilot/outputs/<run-id>/`.
- In a project without an embedded PM Copilot directory, use `pm-copilot-outputs/<run-id>/`.
- Never write project outputs into the global runtime directory.
- Treat `@pm-copilot` and natural PM requests as equivalent activation signals; use the current project only as evidence.
