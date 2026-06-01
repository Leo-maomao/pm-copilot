#!/usr/bin/env python3
"""Inspect local tool availability for PM Copilot runs."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STRICT_BLOCKING_STATUSES = {"unavailable", "setup_required", "skipped"}

SYSTEM_BROWSER_CANDIDATES = (
    ("chrome", "Google Chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ("msedge", "Microsoft Edge", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    ("chromium", "Chromium", "/Applications/Chromium.app/Contents/MacOS/Chromium"),
    ("chrome", "Google Chrome", "google-chrome"),
    ("chrome", "Google Chrome", "google-chrome-stable"),
    ("msedge", "Microsoft Edge", "microsoft-edge"),
    ("msedge", "Microsoft Edge", "microsoft-edge-stable"),
    ("chromium", "Chromium", "chromium"),
    ("chromium", "Chromium", "chromium-browser"),
)
PLAYWRIGHT_BROWSER_PATTERNS = (
    "chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell",
    "chromium-*/chrome-mac*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    "chromium-*/chrome-linux/chrome",
    "chromium-*/chrome-win/chrome.exe",
)


def run(command: list[str], cwd: Path = ROOT) -> tuple[int, str, str]:
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    except FileNotFoundError as error:
        return 127, "", str(error)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def command_version(command: str, args: list[str] | None = None) -> dict[str, str | bool]:
    executable = shutil.which(command)
    if not executable:
        return {"available": False, "path": "", "version": ""}
    version_args = args or ["--version"]
    code, stdout, stderr = run([executable, *version_args])
    version = (stdout or stderr).splitlines()[0] if (stdout or stderr) else ""
    return {"available": code == 0, "path": executable, "version": version}


def git_info() -> dict[str, str | bool]:
    git = shutil.which("git")
    if not git:
        return {"available": False, "revision": "", "dirty": False, "status": "git not found"}
    rev_code, revision, rev_err = run([git, "rev-parse", "--short", "HEAD"])
    status_code, status, status_err = run([git, "status", "--short"])
    changed_files = [line for line in status.splitlines() if line.strip()] if status_code == 0 else []
    return {
        "available": rev_code == 0 and status_code == 0,
        "revision": revision if rev_code == 0 else "",
        "dirty": bool(status.strip()) if status_code == 0 else False,
        "changed_file_count": len(changed_files),
        "status": "dirty" if changed_files else "clean" if status_code == 0 else (rev_err or status_err),
    }


def playwright_info() -> dict[str, str | bool]:
    try:
        version = importlib.metadata.version("playwright")
    except importlib.metadata.PackageNotFoundError:
        return {"available": False, "version": "", "status": "python package not installed"}
    return {"available": True, "version": version, "status": "installed"}


def browser_info() -> dict[str, Any]:
    found = []
    seen_channels = set()
    for channel, label, candidate in SYSTEM_BROWSER_CANDIDATES:
        path = candidate if Path(candidate).exists() else shutil.which(candidate)
        if path and channel not in seen_channels:
            seen_channels.add(channel)
            found.append({"channel": channel, "name": label, "path": str(path)})
    for env_var in ("PLAYWRIGHT_CHROME_EXECUTABLE_PATH", "CHROME_EXECUTABLE_PATH"):
        value = os.environ.get(env_var)
        if value and Path(value).exists():
            found.append({"channel": "chrome", "name": env_var, "path": value})
    cached = playwright_cached_browser_paths()
    return {
        "available": bool(found or cached),
        "recommended_channel": "",
        "system_browser_channel": found[0]["channel"] if found else "",
        "browsers": found,
        "cached_playwright_browsers": [str(path) for path in cached],
    }


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


def playwright_cached_browser_paths() -> list[Path]:
    candidates: list[Path] = []
    for root in playwright_cache_roots():
        if not root.is_dir():
            continue
        for pattern in PLAYWRIGHT_BROWSER_PATTERNS:
            candidates.extend(path for path in root.glob(pattern) if path.is_file())
    return sorted(
        [path for path in candidates if os.access(path, os.X_OK)],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def script_available(relative_path: str) -> bool:
    return (ROOT / relative_path).is_file()


def network_info(url: str | None, timeout: float) -> dict[str, Any]:
    if not url:
        return {
            "status": "skipped",
            "url": "",
            "available": None,
            "evidence": "network check not requested",
        }
    try:
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {
                "status": "available",
                "url": url,
                "available": True,
                "code": response.status,
                "evidence": f"HEAD {url} returned {response.status}",
            }
    except Exception as error:
        return {
            "status": "unavailable",
            "url": url,
            "available": False,
            "error": str(error),
            "evidence": str(error),
        }


def capability(
    tool_id: str,
    status: str,
    evidence: str,
    required: bool,
    command: str = "",
    setup_command: str = "",
) -> dict[str, Any]:
    return {
        "id": tool_id,
        "status": status,
        "required": required,
        "command": command,
        "setup_command": setup_command,
        "evidence": evidence,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    git = git_info()
    playwright = playwright_info()
    browsers = browser_info()
    cached_browsers = browsers.get("cached_playwright_browsers", [])
    tidy = command_version("tidy", ["--version"])
    python = {
        "executable": sys.executable,
        "version": platform.python_version(),
        "platform": platform.platform(),
    }
    network = network_info(args.check_network, args.timeout)
    research_required = bool(args.require_network)

    visual_status = "available"
    visual_evidence = "Playwright package and Playwright-managed browser are available"
    if not (
        script_available("scripts/validate_prototype_visual.py")
        and script_available("scripts/validate_ui_preview.py")
    ):
        visual_status = "unavailable"
        visual_evidence = "visual validation script missing"
    elif not playwright["available"]:
        visual_status = "setup_required"
        visual_evidence = "Playwright package is missing"
    elif not cached_browsers:
        visual_status = "setup_required"
        visual_evidence = "Playwright-managed browser is missing; system browser is optional only"

    tools = [
        capability(
            "repo_context.file_read",
            "available" if ROOT.is_dir() else "unavailable",
            f"repo_root={ROOT}",
            True,
            "Agent-native file read/search tools",
        ),
        capability(
            "repo_context.git_inspection",
            "available" if git["available"] else "unavailable",
            f"revision={git['revision']} dirty={git['dirty']}",
            False,
            "git status --short; git rev-parse --short HEAD",
        ),
        capability(
            "repo_context.host_frontend_inventory",
            "available" if script_available("scripts/inspect_host_frontend.py") else "unavailable",
            "scripts/inspect_host_frontend.py",
            True,
            "python3 scripts/inspect_host_frontend.py --host <host-repo> --query '<requirement or target surface>' --pretty",
        ),
        capability(
            "research.web_search",
            str(network["status"]),
            str(network.get("evidence") or f"url={network['url'] or 'not checked by default'}"),
            research_required,
            "Agent-native web search/browser tools",
        ),
        capability(
            "external_integrations.catalog",
            "available" if (
                script_available("scripts/preflight_integrations.py")
                and script_available("tools/external-tool-catalog.json")
            ) else "unavailable",
            "scripts/preflight_integrations.py and tools/external-tool-catalog.json",
            False,
            "python3 scripts/preflight_integrations.py --tier recommended",
        ),
        capability(
            "validation.repo",
            "available" if script_available("scripts/validate_repo.py") else "unavailable",
            "scripts/validate_repo.py",
            True,
            "python3 scripts/validate_repo.py",
        ),
        capability(
            "validation.outputs",
            "available" if script_available("scripts/validate_outputs.py") else "unavailable",
            "scripts/validate_outputs.py",
            True,
            "python3 scripts/validate_outputs.py outputs/<run-id> --language <zh|en>",
        ),
        capability(
            "validation.visual",
            visual_status,
            visual_evidence,
            True,
            "python3 scripts/validate_prototype_visual.py outputs/<run-id>; python3 scripts/validate_ui_preview.py <preview-url> --run-folder outputs/<run-id>",
            "python3 scripts/setup_visual_validation.py",
        ),
        capability(
            "ui_delivery.source_extract",
            "available" if script_available("scripts/extract_ui_region.py") else "unavailable",
            "scripts/extract_ui_region.py",
            False,
            "python3 scripts/extract_ui_region.py --target <preview-url-or-file> --selector '<css-selector>' --output outputs/<run-id>/prototype-<platform>.html --run-folder outputs/<run-id>",
            "python3 scripts/setup_visual_validation.py",
        ),
        capability(
            "validation.html",
            "available",
            f"html.parser available; tidy={'available' if tidy['available'] else 'not found'}",
            True,
            "python3 scripts/run_delivery_checks.py outputs/<run-id>",
        ),
        capability(
            "validation.delivery_orchestrator",
            "available" if script_available("scripts/run_delivery_checks.py") else "unavailable",
            "scripts/run_delivery_checks.py",
            True,
            "python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>",
        ),
        capability(
            "optimization.scorecard",
            "available" if script_available("scripts/agent_improvement_scorecard.py") else "unavailable",
            "scripts/agent_improvement_scorecard.py",
            False,
            "python3 scripts/agent_improvement_scorecard.py",
        ),
        capability(
            "handoff.dev_tasks",
            "available" if script_available("templates/dev-tasks-template.yaml") else "unavailable",
            "templates/dev-tasks-template.yaml",
            False,
            "Generate outputs/<run-id>/dev-tasks.yaml",
        ),
        capability(
            "launch.decision_support",
            "available" if script_available("templates/launch-decision-template.yaml") else "unavailable",
            "templates/launch-decision-template.yaml",
            False,
            "Generate outputs/<run-id>/launch-decision.yaml",
        ),
    ]

    summary: dict[str, int] = {}
    for item in tools:
        summary[item["status"]] = summary.get(item["status"], 0) + 1

    recommended = ["python3 scripts/validate_repo.py"]
    if research_required and not args.check_network:
        recommended.insert(
            0,
            "python3 scripts/preflight_tools.py --check-network <url> --require-network --strict",
        )
    if visual_status == "setup_required":
        recommended.insert(0, "python3 scripts/setup_visual_validation.py")
    if visual_status == "available":
        recommended.append("python3 scripts/validate_prototype_visual.py outputs/<run-id>")
        recommended.append("python3 scripts/validate_ui_preview.py <preview-url> --run-folder outputs/<run-id>")
    recommended.append("python3 scripts/agent_improvement_scorecard.py")

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repo_root": str(ROOT),
        "tool_registry": "tools/tool-registry.yaml",
        "environment": {
            "python": python,
            "git": git,
            "playwright": playwright,
            "browsers": browsers,
            "tidy": tidy,
            "network": network,
        },
        "tools": tools,
        "summary": summary,
        "recommended_next_commands": recommended,
    }


def print_human(report: dict[str, Any]) -> None:
    print("PM Copilot tool preflight")
    print(f"repo_root: {report['repo_root']}")
    print(f"registry: {report['tool_registry']}")
    for item in report["tools"]:
        setup = f" setup={item['setup_command']}" if item["setup_command"] else ""
        print(f"- {item['id']}: {item['status']} ({item['evidence']}){setup}")
    print("recommended_next_commands:")
    for command in report["recommended_next_commands"]:
        print(f"- {command}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON only.")
    parser.add_argument("--output", type=Path, default=None, help="Write JSON report to this path.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when a required tool is unavailable.")
    parser.add_argument("--check-network", default=None, help="Optional URL to HEAD-check for web access.")
    parser.add_argument(
        "--require-network",
        action="store_true",
        help="Treat web-search/network availability as required for this preflight.",
    )
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()

    report = build_report(args)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)

    if args.strict:
        failing = [
            item for item in report["tools"]
            if item["required"] and item["status"] in STRICT_BLOCKING_STATUSES
        ]
        if failing:
            for item in failing:
                print(
                    f"FAIL: required capability {item['id']} is {item['status']} "
                    f"({item['evidence']})",
                    file=sys.stderr,
                )
            sys.exit(1)


if __name__ == "__main__":
    main()
