"""Shared local discovery helpers for Playwright-managed browsers."""

from __future__ import annotations

import os
import shutil
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


def playwright_cache_roots() -> list[Path]:
    env_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    roots: list[Path] = []
    if env_path and env_path != "0":
        roots.append(Path(env_path).expanduser())
    roots.extend((Path.home() / "Library" / "Caches" / "ms-playwright", Path.home() / ".cache" / "ms-playwright"))
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        roots.append(Path(local_app_data) / "ms-playwright")
    return roots


def installed_browser_channel() -> str | None:
    for channel, candidate in SYSTEM_BROWSER_CANDIDATES:
        if Path(candidate).exists() or shutil.which(candidate):
            return channel
    for env_var in ("PLAYWRIGHT_CHROME_EXECUTABLE_PATH", "CHROME_EXECUTABLE_PATH"):
        value = os.environ.get(env_var)
        if value and Path(value).exists():
            return "chrome"
    return None
