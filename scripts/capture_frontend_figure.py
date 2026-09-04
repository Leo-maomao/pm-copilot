#!/usr/bin/env python3
"""Capture one local or remote frontend state as PRD figure evidence."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Page URL or local HTML path")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=1000)
    args = parser.parse_args()
    source = args.source
    if "://" not in source:
        source = Path(source).resolve().as_uri()
    try:
        from playwright.sync_api import sync_playwright

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": args.width, "height": args.height})
            page.goto(source, wait_until="networkidle")
            page.screenshot(path=str(args.output), full_page=True)
            browser.close()
    except Exception as error:  # Capture failure is handled by the controller fallback.
        print(f"capture failed: {error}")
        return 2
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
