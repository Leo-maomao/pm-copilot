#!/usr/bin/env python3
"""Resolve PM Copilot's per-project workspace for embedded and global installations."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def git_root(start: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 and result.stdout.strip() else None


def configured_output_root(workspace: Path) -> Path | None:
    config = workspace / "config.yaml"
    if not config.is_file():
        return None
    for line in config.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("output_root:"):
            value = line.split(":", 1)[1].strip().strip('"\'')
            if value:
                configured = Path(value).expanduser()
                if configured.is_absolute():
                    raise ValueError(".pm-copilot/config.yaml output_root must be project-relative.")
                return configured
    return None


def resolve(start: Path, ensure: bool = False) -> dict[str, str]:
    project_root = git_root(start) or start.resolve()
    embedded = project_root / "pm-copilot"
    if (embedded / "PM_COPILOT.md").is_file():
        workspace = embedded
        mode = "embedded"
    else:
        workspace = project_root / ".pm-copilot"
        mode = "global"
    configured = configured_output_root(workspace)
    output_root = (project_root / configured).resolve() if configured else None
    if output_root and project_root not in output_root.parents and output_root != project_root:
        raise ValueError(".pm-copilot/config.yaml output_root must remain inside the project root.")
    output_root = output_root or workspace / "outputs"
    if ensure:
        output_root.mkdir(parents=True, exist_ok=True)
        if mode == "global":
            workspace.mkdir(parents=True, exist_ok=True)
            config = workspace / "config.yaml"
            if not config.exists():
                config.write_text("# Optional: output_root: docs/prd\n", encoding="utf-8")
    return {
        "project_root": str(project_root),
        "workspace": str(workspace),
        "output_root": str(output_root),
        "mode": mode,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve PM Copilot output workspace for the current project.")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--ensure", action="store_true")
    args = parser.parse_args()
    print(json.dumps(resolve(args.cwd, args.ensure), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
