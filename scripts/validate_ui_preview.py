#!/usr/bin/env python3
"""Validate a source-backed UI preview URL or file with browser evidence."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import validate_prototype_visual as visual  # noqa: E402


def fail(message: str, code: int = 1) -> None:
    print(f"FAIL: {message}")
    sys.exit(code)


def target_to_url(target: str) -> str:
    if target.startswith(("http://", "https://", "file://")):
        return target
    path = Path(target).expanduser().resolve()
    if not path.exists():
        fail(f"Preview target is neither a URL nor an existing file: {target}")
    return path.as_uri()


def capture_preview(
    target_url: str,
    viewports: list[tuple[str, int, int]],
    output_dir: Path,
    wait_ms: int,
    wait_until: str,
    nav_timeout_ms: int,
    browser_channel: str | None,
    auto_setup: bool,
) -> list[dict[str, Any]]:
    sync_playwright = visual.load_playwright(auto_setup)
    output_dir.mkdir(parents=True, exist_ok=True)
    captures: list[dict[str, Any]] = []

    with sync_playwright() as playwright:
        browser = visual.launch_browser(playwright, browser_channel, auto_setup)
        for name, width, height in viewports:
            page = browser.new_page(viewport={"width": width, "height": height})
            console_errors: list[str] = []
            page_errors: list[str] = []
            page.on(
                "console",
                lambda message: console_errors.append(message.text)
                if message.type == "error"
                else None,
            )
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            try:
                page.goto(target_url, wait_until=wait_until, timeout=nav_timeout_ms)
                page.wait_for_timeout(wait_ms)
                screenshot_path = output_dir / f"{name}.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                dom = visual.inspect_page_dom(page)
                dom["console_errors"] = console_errors[:5]
                dom["page_errors"] = page_errors[:5]
                captures.append({"viewport": name, "path": screenshot_path, "dom": dom})
            except Exception as error:
                captures.append({
                    "viewport": name,
                    "error": str(error),
                    "console_errors": console_errors[:5],
                    "page_errors": page_errors[:5],
                })
            finally:
                page.close()
        browser.close()

    return captures


def path_for_report(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="Preview URL, file:// URL, or local HTML file path.")
    parser.add_argument(
        "--run-folder",
        type=Path,
        default=None,
        help="Run folder where visual-review/source-preview-report.json should be written.",
    )
    parser.add_argument(
        "--viewport",
        action="append",
        default=None,
        help="Viewport in name=WIDTHxHEIGHT format. Can be repeated.",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--wait-ms", type=int, default=500)
    parser.add_argument(
        "--wait-until",
        choices=["commit", "domcontentloaded", "load", "networkidle"],
        default="domcontentloaded",
        help="Navigation readiness state. Use networkidle only for static pages without long-lived dev-server requests.",
    )
    parser.add_argument("--nav-timeout-ms", type=int, default=15000)
    parser.add_argument("--min-nonblank-ratio", type=float, default=0.01)
    parser.add_argument(
        "--browser-channel",
        default=None,
        help="Use an installed browser channel such as chrome or msedge.",
    )
    parser.add_argument(
        "--no-auto-setup",
        action="store_true",
        help="Do not run setup_visual_validation.py automatically when dependencies are missing.",
    )
    args = parser.parse_args()

    run_folder = args.run_folder.resolve() if args.run_folder else Path.cwd()
    output_dir = (
        args.output_dir
        if args.output_dir
        else run_folder / "visual-review" / "source-preview"
    )
    report_path = (
        args.report
        if args.report
        else run_folder / "visual-review" / "source-preview-report.json"
    )
    viewport_values = args.viewport or ["desktop=1440x1000", "mobile=390x844"]
    viewports = [visual.parse_viewport(value) for value in viewport_values]
    browser_channel = (
        args.browser_channel
        or os.environ.get("PLAYWRIGHT_BROWSER_CHANNEL")
    )
    target_url = target_to_url(args.target)

    captures = capture_preview(
        target_url,
        viewports,
        output_dir,
        args.wait_ms,
        args.wait_until,
        args.nav_timeout_ms,
        browser_channel,
        not args.no_auto_setup,
    )

    failures: list[str] = []
    viewport_reports: list[dict[str, Any]] = []
    for capture in captures:
        if capture.get("error"):
            failures.append(
                f"{capture.get('viewport', 'viewport')} navigation/capture failed: "
                f"{capture.get('error')}"
            )
            viewport_reports.append({
                "name": capture.get("viewport", "unknown"),
                "status": "failed",
                "error": capture.get("error"),
                "console_errors": capture.get("console_errors", []),
                "page_errors": capture.get("page_errors", []),
            })
            continue
        screenshot = Path(capture["path"])
        dom = dict(capture.get("dom", {}))
        stats = visual.screenshot_stats(screenshot)
        viewport_report: dict[str, Any] = {
            "name": screenshot.stem,
            "screenshot": path_for_report(screenshot, run_folder),
            "stats": stats,
            "dom": dom,
        }
        if stats["non_blank_ratio"] < args.min_nonblank_ratio:
            failures.append(f"{screenshot.name} appears blank")
        if int(dom.get("body_text_length") or 0) < 20:
            failures.append(f"{screenshot.name} has too little visible text")
        if int(dom.get("horizontal_overflow_px") or 0) > 2:
            failures.append(
                f"{screenshot.name} has horizontal overflow "
                f"{dom.get('horizontal_overflow_px')}px"
            )
        if dom.get("console_errors"):
            failures.append(f"{screenshot.name} has console errors: {dom.get('console_errors')}")
        if dom.get("page_errors"):
            failures.append(f"{screenshot.name} has page errors: {dom.get('page_errors')}")
        if dom.get("access_state_issues"):
            failures.append(
                f"{screenshot.name} has access-state issues: {dom.get('access_state_issues')}"
            )
        if dom.get("annotation_layout_issues"):
            failures.append(
                f"{screenshot.name} has annotation layout issues: "
                f"{dom.get('annotation_layout_issues')}"
            )
        if dom.get("compact_control_wrap_issues"):
            failures.append(
                f"{screenshot.name} has compact control wrap issues: "
                f"{dom.get('compact_control_wrap_issues')}"
            )
        viewport_reports.append(viewport_report)

    report = {
        "target": args.target,
        "target_url": target_url,
        "browser_channel": browser_channel,
        "wait_until": args.wait_until,
        "nav_timeout_ms": args.nav_timeout_ms,
        "output_dir": output_dir.as_posix(),
        "status": "failed" if failures else "passed",
        "failures": failures,
        "viewports": viewport_reports,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if failures:
        fail(f"Source-backed UI preview validation failed; see {report_path}")
    print(f"PM Copilot source-backed UI preview validation passed: {report_path}")


if __name__ == "__main__":
    main()
