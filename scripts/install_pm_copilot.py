#!/usr/bin/env python3
"""Install PM Copilot once as a global Seawork-compatible runtime and Skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTECTED = {".git", ".DS_Store", ".venv", "node_modules", "outputs", "tool-results", "__pycache__"}


def ignore_copy(_: str, names: list[str]) -> set[str]:
    return {name for name in names if name in PROTECTED or name.endswith(".local.yaml")}


def _file_manifest(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in PROTECTED for part in relative.parts):
            continue
        if relative.name in {"install-state.json", "install-manifest.json"}:
            continue
        files[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def _source_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            text=True, capture_output=True, check=False,
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def publish_codex_plugin_source(source_root: Path, plugin_home: Path | None = None) -> dict[str, str]:
    """Point the personal marketplace source at the versioned repository plugin."""
    source = source_root / "plugins" / "pm-copilot"
    target = (plugin_home or Path.home() / "plugins" / "pm-copilot").expanduser()
    if not source.is_dir():
        return {"status": "failed", "reason": f"plugin source is missing: {source}"}
    if target.is_symlink() and target.resolve() == source.resolve():
        return {"status": "linked", "path": str(target)}
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = ""
    if target.exists() or target.is_symlink():
        backup_path = target.with_name(f"{target.name}.backup-{datetime.now(timezone.utc):%Y%m%d%H%M%S}")
        target.rename(backup_path)
        backup = str(backup_path)
    target.symlink_to(source, target_is_directory=True)
    return {"status": "linked", "path": str(target), "backup": backup}


def refresh_codex_plugin(source_root: Path) -> dict[str, str]:
    """Reinstall the marketplace plugin so Codex refreshes its cached manifest."""
    source_result = publish_codex_plugin_source(source_root)
    if source_result["status"] == "failed":
        return source_result
    codex = shutil.which("codex")
    if not codex:
        return {"status": "skipped", "reason": "codex CLI is not installed", "plugin_source": source_result}
    result = subprocess.run(
        [codex, "plugin", "add", "pm-copilot@personal", "--json"],
        cwd=source_root, text=True, capture_output=True, check=False,
    )
    if result.returncode:
        return {"status": "failed", "reason": (result.stderr or result.stdout).strip()[-1000:], "plugin_source": source_result}
    return {"status": "refreshed", "result": result.stdout.strip()[-1000:], "plugin_source": source_result}


def install(runtime_home: Path, skills_home: Path, *, refresh_plugin: bool = False) -> dict[str, str]:
    runtime_home = runtime_home.expanduser().resolve()
    skills_home = skills_home.expanduser().resolve()
    if runtime_home == ROOT or ROOT in runtime_home.parents:
        raise ValueError("Global runtime destination must differ from the source repository.")
    if runtime_home == skills_home or runtime_home in skills_home.parents:
        raise ValueError("Global Skill destination must not be inside the global runtime directory.")
    runtime_home.parent.mkdir(parents=True, exist_ok=True)
    staging_home = runtime_home.parent / f".{runtime_home.name}.staging"
    if staging_home.exists() or staging_home.is_symlink():
        if staging_home.is_dir() and not staging_home.is_symlink():
            shutil.rmtree(staging_home)
        else:
            staging_home.unlink()
    shutil.copytree(ROOT, staging_home, ignore=ignore_copy)
    if runtime_home.exists() or runtime_home.is_symlink():
        if runtime_home.is_dir() and not runtime_home.is_symlink():
            shutil.rmtree(runtime_home)
        else:
            runtime_home.unlink()
    staging_home.replace(runtime_home)
    skill_source = runtime_home / "distribution" / "seawork-skill"
    skill_target = skills_home / "pm-copilot"
    skills_home.mkdir(parents=True, exist_ok=True)
    if skill_target.is_symlink() or skill_target.is_file():
        skill_target.unlink()
    elif skill_target.exists():
        shutil.rmtree(skill_target)
    os.symlink(skill_source, skill_target, target_is_directory=True)
    state = {
        "version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "source_version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "source_root": str(ROOT),
        "source_commit": _source_commit(),
        "runtime_home": str(runtime_home),
        "skill_path": str(skill_target),
        "install_mode": "copy",
        "manifest_file": "install-manifest.json",
    }
    (runtime_home / "install-state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (runtime_home / "install-manifest.json").write_text(
        json.dumps({"files": _file_manifest(runtime_home)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if refresh_plugin:
        state["codex_plugin_refresh"] = refresh_codex_plugin(ROOT)
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description="Install PM Copilot for Seawork and compatible Agent Skills runtimes.")
    parser.add_argument("--runtime-home", type=Path, default=Path.home() / ".agents" / "pm-copilot")
    parser.add_argument("--skills-home", type=Path, default=Path.home() / ".agents" / "skills")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-plugin-refresh", action="store_true", help="do not reinstall the Codex plugin")
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps({"runtime_home": str(args.runtime_home.expanduser()), "skills_home": str(args.skills_home.expanduser())}, ensure_ascii=False, indent=2))
        return
    print(json.dumps(install(args.runtime_home, args.skills_home, refresh_plugin=not args.skip_plugin_refresh), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
