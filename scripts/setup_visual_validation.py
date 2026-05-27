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
PLAYWRIGHT_BROWSER_PATTERNS = (
    "chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell",
    "chromium-*/chrome-mac*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    "chromium-*/chrome-linux/chrome",
    "chromium-*/chrome-win/chrome.exe",
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


def playwright_cache_roots() -> list[Path]:
    env_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    roots: list[Path] = []
    if env_path and env_path != "0":
        roots.append(Path(env_path).expanduser())
    roots.append(Path.home() / "Library" / "Caches" / "ms-playwright")
    roots.append(Path.home() / ".cache" / "ms-playwright")
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        roots.append(Path(local_app_data) / "ms-playwright")
    return roots


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
                f"`PLAYWRIGHT_BROWSER_CHANNEL={channel} python3 scripts/validate_prototype_visual.py outputs/<run-id>`."
            )
        sys.exit(result)
    print("Visual validation is ready with Playwright Chromium headless shell.")


if __name__ == "__main__":
    main()
