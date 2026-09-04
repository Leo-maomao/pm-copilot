#!/usr/bin/env python3
"""Refresh the local Codex plugin cache from this repository checkout."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "pm-copilot"


def publish_plugin_source(source_root: Path, plugin_home: Path | None = None) -> dict[str, str]:
    """Point the personal marketplace's local source to this checkout."""
    source = (source_root / "plugins" / PLUGIN_NAME).resolve()
    target = (plugin_home or Path.home() / "plugins" / PLUGIN_NAME).expanduser()
    if not (source / ".codex-plugin" / "plugin.json").is_file():
        return {"status": "failed", "reason": f"plugin source is missing: {source}"}
    if target.is_symlink() and target.resolve() == source:
        return {"status": "linked", "path": str(target)}

    target.parent.mkdir(parents=True, exist_ok=True)
    backup = ""
    if target.exists() or target.is_symlink():
        backup_path = target.with_name(
            f"{target.name}.backup-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
        )
        target.rename(backup_path)
        backup = str(backup_path)
    target.symlink_to(source, target_is_directory=True)
    return {"status": "linked", "path": str(target), "backup": backup}


def refresh_plugin(source_root: Path = ROOT, plugin_home: Path | None = None) -> dict[str, Any]:
    """Relink the local source, then force Codex to install its new cache entry."""
    source_root = source_root.resolve()
    source_result = publish_plugin_source(source_root, plugin_home)
    if source_result["status"] == "failed":
        return source_result
    codex = shutil.which("codex")
    if not codex:
        return {
            "status": "skipped",
            "reason": "codex CLI is not installed",
            "plugin_source": source_result,
        }
    result = subprocess.run(
        [codex, "plugin", "add", f"{PLUGIN_NAME}@personal", "--json"],
        cwd=source_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return {
            "status": "failed",
            "reason": (result.stderr or result.stdout).strip()[-1000:],
            "plugin_source": source_result,
        }
    return {
        "status": "refreshed",
        "result": result.stdout.strip()[-1000:],
        "plugin_source": source_result,
    }


def head_changes_plugin_release(source_root: Path = ROOT) -> bool:
    """Only refresh after a committed version or plugin change."""
    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
        cwd=source_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return False
    changed = set(result.stdout.splitlines())
    return "VERSION" in changed or any(path.startswith(f"plugins/{PLUGIN_NAME}/") for path in changed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--if-head-changed", action="store_true")
    args = parser.parse_args()
    if args.if_head_changed and not head_changes_plugin_release():
        print(json.dumps({"status": "skipped", "reason": "HEAD does not change the plugin release"}))
        return 0
    result = refresh_plugin()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] in {"refreshed", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
