# Global Installation

Install PM Copilot once when you want to activate the same runtime from multiple projects:

```bash
python3 /path/to/pm-copilot/scripts/install_pm_copilot.py
```

The installer copies reusable runtime files to `~/.agents/pm-copilot` and creates the Seawork-compatible Skill link at `~/.agents/skills/pm-copilot`. Run the same command again from a newer source checkout to replace the global runtime safely.

The repository also contains the Codex plugin bundle at `plugins/pm-copilot`. It uses the same shared runtime and the same project-output rule; it does not duplicate or relocate product artifacts.

Before any delivery, PM Copilot resolves the active project workspace:

- embedded project: `pm-copilot/outputs/<run-id>/`;
- global runtime: `.pm-copilot/outputs/<run-id>/`.

The global runtime never stores product outputs. A project may set a project-relative override in `.pm-copilot/config.yaml`:

```yaml
output_root: docs/product-outputs
```

Set `PM_COPILOT_HOME` only when the runtime is installed somewhere other than `~/.agents/pm-copilot`.
