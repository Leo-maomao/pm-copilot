---
name: pm-copilot
description: Activate the globally installed PM Copilot runtime for product-manager work in the current project.
---

# PM Copilot Plugin Adapter

Use the shared PM Copilot runtime rather than copying rules into this plugin. Resolve `PM_COPILOT_HOME` or `~/.agents/pm-copilot`; if neither exists, ask the user to install the runtime with `scripts/install_pm_copilot.py` from a PM Copilot source checkout.

Before reading runtime instructions, synchronize the copied global runtime with
its source checkout when possible. The command is safe against local runtime
edits and exits non-zero instead of overwriting them:

```bash
python3 "${PM_COPILOT_HOME:-$HOME/.agents/pm-copilot}/scripts/ensure_runtime_current.py" --require-current --json
```

Then read the runtime's `PM_COPILOT.md` and resolve the project workspace:

```bash
python3 "${PM_COPILOT_HOME:-$HOME/.agents/pm-copilot}/scripts/project_workspace.py" --cwd "$PWD" --ensure
```

Never place product outputs in the plugin or global runtime directory. Use `pm-copilot/outputs/<run-id>/` for embedded projects and `pm-copilot-outputs/<run-id>/` for global use.

For every PRD request, route through the production controller before writing
any artifact:

```bash
python3 "${PM_COPILOT_HOME:-$HOME/.agents/pm-copilot}/scripts/prd_request_controller.py" --request "<request>"
```

Do not return a direct model-written PRD. The controller must provide one
canonical run folder, attributable provider/model Agent calls, stage reviews,
and final validation evidence.
