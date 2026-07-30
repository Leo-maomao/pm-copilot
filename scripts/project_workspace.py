#!/usr/bin/env python3
"""Resolve PM Copilot's per-project output workspace for embedded and global installations."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


GLOBAL_OUTPUT_DIRECTORY = "pm-copilot-outputs"
LEGACY_GLOBAL_WORKSPACE_DIRECTORY = ".pm-copilot"
DEFAULT_LEGACY_CONFIG = "# Optional: output_root: docs/prd\n"


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
                    raise ValueError("PM Copilot output_root must be project-relative.")
                return configured
    return None


def migrate_legacy_global_outputs(project_root: Path, workspace: Path) -> None:
    """Move legacy hidden global outputs into the visible default directory."""
    legacy_output_root = workspace / "outputs"
    visible_output_root = project_root / GLOBAL_OUTPUT_DIRECTORY
    if not legacy_output_root.is_dir():
        return
    visible_output_root.mkdir(parents=True, exist_ok=True)
    for source in legacy_output_root.iterdir():
        target = visible_output_root / source.name
        if target.exists():
            raise FileExistsError(
                f"Cannot migrate legacy PM Copilot output because {target} already exists."
            )
        shutil.move(str(source), str(target))
    for artifact in visible_output_root.rglob("*"):
        if not artifact.is_file():
            continue
        try:
            contents = artifact.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated = contents.replace(str(legacy_output_root), str(visible_output_root))
        if updated != contents:
            artifact.write_text(updated, encoding="utf-8")
    legacy_output_root.rmdir()
    config = workspace / "config.yaml"
    if config.is_file() and config.read_text(encoding="utf-8") == DEFAULT_LEGACY_CONFIG:
        config.unlink()
    if workspace.is_dir() and not any(workspace.iterdir()):
        workspace.rmdir()


def resolve(start: Path, ensure: bool = False) -> dict[str, str]:
    project_root = git_root(start) or start.resolve()
    embedded = project_root / "pm-copilot"
    if (embedded / "PM_COPILOT.md").is_file():
        workspace = embedded
        mode = "embedded"
    else:
        workspace = project_root / LEGACY_GLOBAL_WORKSPACE_DIRECTORY
        mode = "global"
    configured = configured_output_root(workspace)
    output_root = (project_root / configured).resolve() if configured else None
    if output_root and project_root not in output_root.parents and output_root != project_root:
        raise ValueError("PM Copilot output_root must remain inside the project root.")
    output_root = output_root or (
        workspace / "outputs" if mode == "embedded" else project_root / GLOBAL_OUTPUT_DIRECTORY
    )
    if ensure:
        if mode == "global" and not configured:
            migrate_legacy_global_outputs(project_root, workspace)
        output_root.mkdir(parents=True, exist_ok=True)
    return {
        "project_root": str(project_root),
        "workspace": str(workspace if mode == "embedded" else output_root),
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
