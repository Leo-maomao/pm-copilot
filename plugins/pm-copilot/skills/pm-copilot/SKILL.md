---
name: pm-copilot
description: Activate the globally installed PM Copilot runtime for product-manager work in the current project.
---

# PM Copilot Plugin Adapter

Use the shared PM Copilot runtime rather than copying rules into this plugin. Resolve `PM_COPILOT_HOME` or `~/.agents/pm-copilot`; if neither exists, ask the user to install the runtime with `scripts/install_pm_copilot.py` from a PM Copilot source checkout.

Read the runtime's `PM_COPILOT.md`, then resolve the project workspace before creating artifacts:

```bash
python3 "${PM_COPILOT_HOME:-$HOME/.agents/pm-copilot}/scripts/project_workspace.py" --cwd "$PWD" --ensure
```

Never place product outputs in the plugin or global runtime directory. Use `pm-copilot/outputs/<run-id>/` for embedded projects and `pm-copilot-outputs/<run-id>/` for global use.
