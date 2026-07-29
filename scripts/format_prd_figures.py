#!/usr/bin/env python3
"""Normalize inline PRD figure captions to one caption per image."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from prd_evidence_upgrade import discover_output_folders


FIGURE_ROW_RE = re.compile(r"(?m)^(\|\s*(?:图示|截图|需求图|图片)\s*\|\s*)(.*?)(\|\s*)$")
IMAGE_RE = re.compile(r"!\[([^\]]+)\]\(([^)]+)\)")


def normalize_row(match: re.Match[str]) -> str:
    prefix, content, suffix = match.groups()
    if not IMAGE_RE.search(content):
        return match.group(0)
    content = re.sub(r"\s*(?:<br>\s*)?<small>.*?</small>", "", content, flags=re.IGNORECASE)

    def caption(image: re.Match[str]) -> str:
        alt, source = image.groups()
        return f"![{alt}]({source})<small>{alt}</small>"

    content = IMAGE_RE.sub(caption, content)
    content = re.sub(r"</small>(?:\s*<br>)+\s*(?=!\[)", "</small><br>", content)
    return f"{prefix}{content}{suffix}"


def normalize_prd(path: Path) -> tuple[bool, str]:
    original = path.read_text(encoding="utf-8")
    normalized = FIGURE_ROW_RE.sub(normalize_row, original)
    return normalized != original, normalized


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", type=Path, nargs="+", default=[Path(__file__).resolve().parents[1]])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changed = 0
    for folder in discover_output_folders(args.roots):
        prd_path = folder / "prd.md"
        if not prd_path.is_file():
            continue
        dirty, normalized = normalize_prd(prd_path)
        if not dirty:
            continue
        changed += 1
        if args.apply:
            prd_path.write_text(normalized, encoding="utf-8")
        print(f"{'updated' if args.apply else 'would update'}: {prd_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
