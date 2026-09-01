#!/usr/bin/env python3
"""Install or verify dependencies for UI visual validation."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from visual_validation_support import (
    PLAYWRIGHT_BROWSER_PATTERNS,
    SYSTEM_BROWSER_CANDIDATES,
    installed_browser_channel,
    playwright_cache_roots,
)


def run(command: list[str]) -> int:
    print("+ " + " ".join(command))
    return subprocess.call(command)


def has_python_playwright() -> bool:
    try:
        import playwright  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


def has_playwright_managed_browser() -> bool:
    for root in playwright_cache_roots():
        if not root.is_dir():
            continue
        for pattern in PLAYWRIGHT_BROWSER_PATTERNS:
            for path in root.glob(pattern):
                if path.is_file() and os.access(path, os.X_OK):
                    return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--install-bundled-browser",
        action="store_true",
        help="Install Playwright's Chromium headless shell even when a system browser is available.",
    )
    args = parser.parse_args()

    if not has_python_playwright():
        requirements = Path(__file__).resolve().parents[1] / "requirements-dev.txt"
        install_target = ["-r", str(requirements)] if requirements.is_file() else ["playwright"]
        result = run([sys.executable, "-m", "pip", "install", "--user", *install_target])
        if result != 0:
            sys.exit(result)

    if has_playwright_managed_browser() and not args.install_bundled_browser:
        print("Visual validation is ready with a Playwright-managed browser cache.")
        return

    result = run([sys.executable, "-m", "playwright", "install", "chromium", "--only-shell"])
    if result != 0:
        channel = installed_browser_channel()
        if channel:
            print(
                "Playwright-managed browser install failed. A system browser is available only as an explicit fallback: "
                f"`PLAYWRIGHT_BROWSER_CHANNEL={channel} python3 scripts/validate_prototype_visual.py <output-root>/<run-id>`."
            )
        sys.exit(result)
    print("Visual validation is ready with Playwright Chromium headless shell.")


if __name__ == "__main__":
    main()
