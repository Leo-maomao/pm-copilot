#!/usr/bin/env python3
"""Synchronize PM Copilot source files into local embedded copies safely."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
PROTECTED_TOP_LEVEL = {".git", "outputs", ".pytest_cache", "__pycache__"}


@dataclass
class SyncResult:
    destination: str
    copied: int = 0
    skipped_protected: int = 0
    skipped_dirty: bool = False
    error: str = ""


def discover_copies(roots: Iterable[Path], source: Path) -> list[Path]:
    source = source.resolve()
    copies: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for candidate in root.rglob("pm-copilot"):
            if (
                candidate.is_dir()
                and ".git" not in candidate.parts
                and (candidate / "PM_COPILOT.md").is_file()
                and candidate.resolve() != source
            ):
                copies.append(candidate)
    return sorted(set(copies))


def protected(relative: Path) -> bool:
    if not relative.parts:
        return True
    if relative.parts[0] in PROTECTED_TOP_LEVEL:
        return True
    return relative.parts[0] == "context" and relative.name.endswith(".local.yaml")


def git_dirty(destination: Path) -> bool:
    git_dir = destination / ".git"
    if not git_dir.exists():
        return False
    import subprocess

    completed = subprocess.run(
        ["git", "-C", str(destination), "status", "--porcelain"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0 and bool(completed.stdout.strip())


def sync_copy(source: Path, destination: Path, apply: bool, force_dirty: bool) -> SyncResult:
    result = SyncResult(destination=str(destination))
    if git_dirty(destination) and not force_dirty:
        result.skipped_dirty = True
        return result
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if protected(relative):
            result.skipped_protected += 1
            continue
        target = destination / relative
        if path.is_dir():
            if apply:
                target.mkdir(parents=True, exist_ok=True)
            continue
        if not path.is_file():
            continue
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        result.copied += 1
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--roots", type=Path, nargs="+", default=[ROOT.parent])
    parser.add_argument("--apply", action="store_true", help="copy source files; default reports only")
    parser.add_argument("--force-dirty", action="store_true", help="overwrite source files in dirty Git copies")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    results = [sync_copy(source, copy, args.apply, args.force_dirty) for copy in discover_copies(args.roots, source)]
    payload = [asdict(result) for result in results]
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for result in results:
            print(
                f"sync: {result.destination}; copied={result.copied}; "
                f"protected={result.skipped_protected}; dirty_skipped={result.skipped_dirty}"
            )
    return 0 if all(not result.error for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
