#!/usr/bin/env python3
"""Safely migrate PM Copilot output folders and regenerate their PRD HTML."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
LEGACY_FOLDER_RE = re.compile(
    r"^(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)-(?P<date>\d{8})-(?P<time>\d{4})$"
)
TEXT_SUFFIXES = {".csv", ".html", ".json", ".md", ".mmd", ".txt", ".yaml", ".yml"}


@dataclass
class UpgradeResult:
    source: str
    target: str
    renamed: bool
    references_updated: int = 0
    metadata_files_removed: int = 0
    rendered: bool = False
    validation: str = "not_run"
    error: str = ""


def modern_folder_name(name: str) -> str | None:
    match = LEGACY_FOLDER_RE.fullmatch(name)
    if not match:
        return None
    date = match.group("date")
    return f"{match.group('slug')}-{date[:4]}-{date[4:6]}-{date[6:]}"


def unique_target(parent: Path, requested_name: str) -> Path:
    candidate = parent / requested_name
    suffix = 2
    while candidate.exists():
        candidate = parent / f"{requested_name}-{suffix}"
        suffix += 1
    return candidate


def is_text_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in TEXT_SUFFIXES


def update_references(folder: Path, replacements: dict[str, str]) -> int:
    changed = 0
    for path in folder.rglob("*"):
        if not is_text_file(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated = text
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def remove_ignored_metadata(folder: Path) -> int:
    removed = 0
    for path in folder.rglob(".DS_Store"):
        if path.is_file():
            path.unlink()
            removed += 1
    return removed


def run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def output_language(folder: Path) -> str | None:
    prd = folder / "prd.md"
    if not prd.is_file():
        return None
    text = prd.read_text(encoding="utf-8")
    return "zh" if any(token in text for token in ("文档说明", "需求背景", "需求详情")) else None


def upgrade_folder(
    folder: Path,
    renderer_root: Path,
    validate: bool,
    apply: bool,
) -> UpgradeResult:
    requested_name = modern_folder_name(folder.name)
    target = unique_target(folder.parent, requested_name) if requested_name else folder
    result = UpgradeResult(str(folder), str(target), target != folder)
    if not apply:
        return result
    old_name = folder.name
    old_path = str(folder)
    if target != folder:
        folder.rename(target)
    replacements = {
        old_name: target.name,
        old_path: str(target),
        f"outputs/{old_name}": f"outputs/{target.name}",
    }
    result.references_updated = update_references(target, replacements)
    result.metadata_files_removed = remove_ignored_metadata(target)
    prd = target / "prd.md"
    renderer = renderer_root / "scripts" / "render_prd_html.py"
    if prd.is_file():
        completed = run_command([sys.executable, str(renderer), str(target)], renderer_root)
        if completed.returncode:
            result.error = f"render failed: {completed.stdout.strip()}"
            return result
        result.rendered = True
    if validate:
        validator = renderer_root / "scripts" / "validate_outputs.py"
        command = [sys.executable, str(validator), str(target)]
        if not prd.is_file():
            command.append("--pre-clarification")
        language = output_language(target)
        if language:
            command.extend(["--language", language])
        completed = run_command(command, renderer_root)
        result.validation = "passed" if completed.returncode == 0 else "failed"
        if completed.returncode:
            result.error = completed.stdout.strip()
    return result


def discover_output_folders(roots: Iterable[Path]) -> list[Path]:
    folders: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for output_root in sorted(root.rglob("outputs")):
            if output_root.is_dir() and output_root.parent.name == "pm-copilot":
                folders.extend(sorted(item for item in output_root.iterdir() if item.is_dir()))
    return folders


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", type=Path, nargs="+", default=[ROOT])
    parser.add_argument("--renderer-root", type=Path, default=ROOT)
    parser.add_argument("--apply", action="store_true", help="perform migrations; default reports only")
    parser.add_argument("--no-validate", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results = [
        upgrade_folder(folder, args.renderer_root.resolve(), not args.no_validate, args.apply)
        for folder in discover_output_folders(args.roots)
    ]
    payload = [asdict(result) for result in results]
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for result in results:
            action = "rename" if result.renamed else "refresh"
            print(f"{action}: {result.source} -> {result.target}; validation={result.validation}")
            if result.error:
                print(f"  {result.error}")
    return 0 if all(not result.error or result.validation == "failed" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
