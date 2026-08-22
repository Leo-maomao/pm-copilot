#!/usr/bin/env python3
"""Keep a copied global PM Copilot runtime aligned with its source checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import subprocess
import sys
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _file_manifest(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    ignored = {".git", ".DS_Store", ".venv", "node_modules", "outputs", "tool-results", "__pycache__"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in ignored for part in relative.parts):
            continue
        if relative.name in {"install-state.json", "install-manifest.json"}:
            continue
        files[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def _local_changes(runtime_home: Path, expected: dict[str, str]) -> list[str]:
    actual = _file_manifest(runtime_home)
    changed = sorted(
        path for path in set(actual) | set(expected)
        if actual.get(path) != expected.get(path)
    )
    return changed


def _source_commit(source_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            text=True, capture_output=True, check=False,
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _sync_from_source(source_root: Path, runtime_home: Path, skills_home: Path) -> dict[str, Any]:
    command = [
        sys.executable, str(source_root / "scripts" / "install_pm_copilot.py"),
        "--runtime-home", str(runtime_home), "--skills-home", str(skills_home),
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return {"status": "blocked", "reason": "automatic sync failed", "stderr": result.stderr[-2000:]}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {"output": result.stdout[-2000:]}
    return {"status": "synced", **payload}


def ensure_current(
    runtime_home: Path, skills_home: Path, *, require_current: bool = False,
) -> dict[str, Any]:
    runtime_home = runtime_home.expanduser().resolve()
    skills_home = skills_home.expanduser().resolve()
    state_path = runtime_home / "install-state.json"
    state = _read_json(state_path)
    source_root = Path(str(state.get("source_root", ""))).expanduser() if state.get("source_root") else None
    current_version = (runtime_home / "VERSION").read_text(encoding="utf-8").strip() if (runtime_home / "VERSION").is_file() else None
    if source_root is None or not (source_root / "VERSION").is_file():
        result = {"status": "source_unavailable", "runtime_version": current_version}
        if require_current:
            result["action_required"] = "install from a source checkout or set PM_COPILOT_HOME"
        return result
    source_version = (source_root / "VERSION").read_text(encoding="utf-8").strip()
    source_commit = _source_commit(source_root)
    installed_commit = str(state.get("source_commit", "")).strip() or None
    if current_version == source_version and (not installed_commit or not source_commit or installed_commit == source_commit):
        return {
            "status": "up_to_date", "version": current_version, "source_root": str(source_root),
            "source_commit": source_commit,
        }
    expected = _read_json(runtime_home / str(state.get("manifest_file", "install-manifest.json"))).get("files", {})
    changes = _local_changes(runtime_home, expected if isinstance(expected, dict) else {})
    if changes:
        return {
            "status": "blocked_local_changes", "runtime_version": current_version,
            "source_version": source_version, "source_commit": source_commit,
            "changed_files": changes[:50],
            "reason": "global runtime contains local changes; automatic overwrite was refused",
        }
    return _sync_from_source(source_root, runtime_home, skills_home)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-home", type=Path, default=Path.home() / ".agents" / "pm-copilot")
    parser.add_argument("--skills-home", type=Path, default=Path.home() / ".agents" / "skills")
    parser.add_argument("--require-current", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = ensure_current(args.runtime_home, args.skills_home, require_current=args.require_current)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"up_to_date", "synced"} else (2 if args.require_current else 0)


if __name__ == "__main__":
    raise SystemExit(main())
