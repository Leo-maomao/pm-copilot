#!/usr/bin/env python3
"""Keep the Codex plugin manifest aligned with the repository release version."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANIFEST = ROOT / "plugins" / "pm-copilot" / ".codex-plugin" / "plugin.json"


def version_prefix(version: str) -> str:
    return version.split("+", 1)[0]


def repository_version(root: Path = ROOT) -> str:
    return (root / "VERSION").read_text(encoding="utf-8").strip()


def manifest_version(manifest_path: Path = PLUGIN_MANIFEST) -> str:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = payload.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError(f"{manifest_path} must contain a non-empty version")
    return version


def versions_are_aligned(root: Path = ROOT, manifest_path: Path = PLUGIN_MANIFEST) -> bool:
    return repository_version(root) == version_prefix(manifest_version(manifest_path))


def sync_plugin_version(
    root: Path = ROOT, manifest_path: Path = PLUGIN_MANIFEST, cachebuster: str | None = None,
) -> str:
    version = repository_version(root)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    cachebuster = cachebuster or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    payload["version"] = f"{version}+codex.{cachebuster}"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload["version"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when plugin and repository versions differ")
    parser.add_argument("--cachebuster", help="explicit Codex cachebuster for a reproducible release")
    args = parser.parse_args()
    if args.check:
        if not versions_are_aligned():
            raise SystemExit(
                f"plugin base version {version_prefix(manifest_version())} does not match VERSION {repository_version()}"
            )
        print(f"Plugin version aligned: {manifest_version()}")
        return 0
    print(f"Updated plugin version: {sync_plugin_version(cachebuster=args.cachebuster)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
