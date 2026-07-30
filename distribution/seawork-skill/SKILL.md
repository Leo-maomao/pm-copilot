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

- In a legacy embedded project, use `pm-copilot/outputs/<run-id>/`.
- In a project without an embedded PM Copilot directory, use `pm-copilot-outputs/<run-id>/`.
- Never write project outputs into the global runtime directory.
- Treat `@pm-copilot` and natural PM requests as activation signals; use the current project only as evidence.
