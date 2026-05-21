#!/usr/bin/env python3
"""Install or verify dependencies for UI visual validation."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


SYSTEM_BROWSER_CANDIDATES = (
    ("chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ("msedge", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    ("chromium", "/Applications/Chromium.app/Contents/MacOS/Chromium"),
    ("chrome", "google-chrome"),
    ("chrome", "google-chrome-stable"),
    ("msedge", "microsoft-edge"),
    ("msedge", "microsoft-edge-stable"),
    ("chromium", "chromium"),
    ("chromium", "chromium-browser"),
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


def installed_browser_channel() -> str | None:
    for channel, candidate in SYSTEM_BROWSER_CANDIDATES:
        if Path(candidate).exists() or shutil.which(candidate):
            return channel
    for env_var in ("PLAYWRIGHT_CHROME_EXECUTABLE_PATH", "CHROME_EXECUTABLE_PATH"):
        value = os.environ.get(env_var)
        if value and Path(value).exists():
            return "chrome"
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--install-bundled-browser",
        action="store_true",
        help="Install Playwright's Chromium headless shell even when a system browser is available.",
    )
    args = parser.parse_args()

    if not has_python_playwright():
        result = run([sys.executable, "-m", "pip", "install", "--user", "playwright"])
        if result != 0:
            sys.exit(result)

    channel = installed_browser_channel()
    if channel and not args.install_bundled_browser:
        print(
            "Visual validation is ready. Use "
            f"`PLAYWRIGHT_BROWSER_CHANNEL={channel} python3 scripts/validate_prototype_visual.py outputs/<run-id>`."
        )
        return

    result = run([sys.executable, "-m", "playwright", "install", "chromium", "--only-shell"])
    if result != 0:
        sys.exit(result)
    print("Visual validation is ready with Playwright Chromium headless shell.")


if __name__ == "__main__":
    main()
