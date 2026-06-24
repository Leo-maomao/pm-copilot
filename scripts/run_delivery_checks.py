#!/usr/bin/env python3
"""Run PM Copilot delivery checks and write a machine-readable report."""

from __future__ import annotations

import argparse
import datetime as dt
from html.parser import HTMLParser
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE_NAMES = (
    "index.html",
    "prototype-web.html",
    "prototype-h5.html",
    "prototype-app.html",
    "prototype-mini-program.html",
)
PRD_HTML_NAMES = ("prd.html",)
EXTERNAL_REF_RE = re.compile(r"https?://|cdn\.|unpkg\.com|cdnjs\.", re.IGNORECASE)


class PrototypeHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.start_tags = 0
        self.buttons = 0
        self.links = 0
        self.external_refs = 0
        self.external_resource_refs = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.start_tags += 1
        if tag == "button":
            self.buttons += 1
        if tag == "a":
            self.links += 1
        for name, value in attrs:
            if not value or not EXTERNAL_REF_RE.search(value):
                continue
            self.external_refs += 1
            if not (tag == "a" and name.lower() == "href"):
                self.external_resource_refs += 1


def run_command(
    command: list[str],
    cwd: Path = ROOT,
    required: bool = True,
    print_output: bool = True,
    keep_full_stdout: bool = False,
) -> dict[str, Any]:
    print("+ " + " ".join(command))
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
        status = "passed" if result.returncode == 0 else "failed"
        if print_output and result.stdout:
            print(result.stdout.rstrip())
        if print_output and result.stderr:
            print(result.stderr.rstrip())
        output = {
            "command": " ".join(command),
            "required": required,
            "status": status,
            "exit_code": result.returncode,
            "stdout": result.stdout[-4000:],
            "stdout_truncated": len(result.stdout) > 4000,
            "stderr": result.stderr[-4000:],
            "stderr_truncated": len(result.stderr) > 4000,
        }
        if keep_full_stdout:
            output["stdout_full"] = result.stdout
        return output
    except FileNotFoundError as error:
        print(f"FAIL: {error}")
        return {
            "command": " ".join(command),
            "required": required,
            "status": "failed",
            "exit_code": 127,
            "stdout": "",
            "stderr": str(error),
        }


def parse_json_output(result: dict[str, Any]) -> dict[str, Any] | None:
    if result.get("status") != "passed":
        return None
    stdout = str(result.get("stdout_full") or result.get("stdout") or "").strip()
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def find_prototypes(folder: Path) -> list[Path]:
    return [folder / name for name in PROTOTYPE_NAMES if (folder / name).is_file()]


def find_prd_html_documents(folder: Path) -> list[Path]:
    return [folder / name for name in PRD_HTML_NAMES if (folder / name).is_file()]


def existing_visual_report_check(
    output_folder: Path,
    prototypes: list[Path],
    skip_reason: str,
) -> dict[str, Any] | None:
    report = output_folder / "visual-review" / "visual-report.json"
    if not report.is_file():
        return None
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {
            "tool": "validate_prototype_visual",
            "required": True,
            "status": "failed",
            "result": f"existing visual report is unreadable: {error}",
            "report_path": str(report),
        }

    prototype_names = {prototype.name for prototype in prototypes}
    reported_names = {
        str(item.get("prototype", ""))
        for item in data.get("prototypes", [])
        if isinstance(item, dict)
    }
    if not reported_names and data.get("prototype"):
        reported_names = {str(data.get("prototype"))}

    failures = []
    if data.get("status") != "passed":
        failures.append(f"visual report status is {data.get('status')!r}")
    missing = sorted(prototype_names - reported_names)
    if missing:
        failures.append("visual report missing compatibility UI HTML files: " + ", ".join(missing))
    viewport_reports = [
        viewport
        for prototype_report in data.get("prototypes", [])
        if isinstance(prototype_report, dict)
        for viewport in prototype_report.get("viewports", [])
        if isinstance(viewport, dict)
    ]
    if not viewport_reports:
        failures.append("visual report missing viewport evidence")
    for viewport in viewport_reports:
        dom = viewport.get("dom")
        viewport_name = str(viewport.get("name") or "unknown")
        if not isinstance(dom, dict):
            failures.append(f"visual report missing DOM smoke evidence for {viewport_name}")
            continue
        if dom.get("console_errors"):
            failures.append(f"visual report has console errors for {viewport_name}")
        if dom.get("page_errors"):
            failures.append(f"visual report has page errors for {viewport_name}")
        if int(dom.get("horizontal_overflow_px") or 0) > 2:
            failures.append(f"visual report has horizontal overflow for {viewport_name}")
        if "access_state_issues" not in dom:
            failures.append(f"visual report missing access-state smoke evidence for {viewport_name}")
        elif dom.get("access_state_issues"):
            failures.append(f"visual report has access-state issues for {viewport_name}")
        if "annotation_layout_issues" not in dom:
            failures.append(f"visual report missing annotation-layout smoke evidence for {viewport_name}")
        elif dom.get("annotation_layout_issues"):
            failures.append(f"visual report has annotation layout issues for {viewport_name}")
        if "compact_control_wrap_issues" not in dom:
            failures.append(f"visual report missing compact-control wrap evidence for {viewport_name}")
        elif dom.get("compact_control_wrap_issues"):
            failures.append(f"visual report has compact control wrap issues for {viewport_name}")

    return {
        "tool": "validate_prototype_visual",
        "required": True,
        "status": "failed" if failures else "passed",
        "result": "; ".join(failures)
        if failures
        else f"reused existing passed visual report; skip reason: {skip_reason}",
        "report_path": str(report),
    }


def html_parser_check(prototype: Path, allow_external_document_links: bool = False) -> dict[str, Any]:
    parser = PrototypeHTMLParser()
    text = prototype.read_text(encoding="utf-8")
    try:
        parser.feed(text)
        parser.close()
    except Exception as error:
        return {
            "tool": "python.html.parser",
            "prototype": prototype.name,
            "required": True,
            "status": "failed",
            "result": str(error),
        }
    failures = []
    if "<!doctype html" not in text[:200].lower():
        failures.append("missing doctype")
    if allow_external_document_links:
        if parser.external_resource_refs:
            failures.append("external network resource reference found")
    elif EXTERNAL_REF_RE.search(text):
        failures.append("external network reference found")
    if parser.start_tags <= 0:
        failures.append("no html tags parsed")
    return {
        "tool": "python.html.parser",
        "prototype": prototype.name,
        "required": True,
        "status": "failed" if failures else "passed",
        "result": "; ".join(failures) if failures else "parsed",
        "start_tags": parser.start_tags,
        "buttons": parser.buttons,
        "links": parser.links,
        "external_refs": parser.external_refs,
        "external_resource_refs": parser.external_resource_refs,
    }


def tidy_check(prototype: Path) -> dict[str, Any]:
    tidy = shutil.which("tidy")
    if not tidy:
        return {
            "tool": "tidy",
            "prototype": prototype.name,
            "required": False,
            "status": "skipped",
            "result": "tidy not found",
        }
    result = run_command([tidy, "-errors", "-quiet", "-utf8", str(prototype)], required=False)
    return {
        "tool": "tidy",
        "prototype": prototype.name,
        "required": False,
        "status": result["status"],
        "exit_code": result["exit_code"],
        "result": (result["stdout"] or result["stderr"] or "ok")[-4000:],
    }


def report_path(output_folder: Path | None, explicit: Path | None) -> Path:
    if explicit:
        return explicit
    if output_folder:
        return output_folder / "tool-results" / "delivery-check-report.json"
    return ROOT / "tool-results" / "delivery-check-report.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_folder", type=Path, nargs="?", default=None)
    parser.add_argument("--language", choices=["zh", "en"], default=None)
    parser.add_argument("--pre-clarification", action="store_true")
    parser.add_argument("--skip-repo", action="store_true")
    parser.add_argument("--skip-visual", action="store_true")
    parser.add_argument("--skip-visual-reason", default="")
    parser.add_argument(
        "--source-preview",
        default="",
        help="Source-backed preview URL or file path to validate with scripts/validate_ui_preview.py.",
    )
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    if args.skip_visual and not args.skip_visual_reason:
        print("FAIL: --skip-visual requires --skip-visual-reason")
        sys.exit(2)

    output_folder = args.output_folder.resolve() if args.output_folder else None
    results: list[dict[str, Any]] = []

    preflight = run_command(
        [sys.executable, "scripts/preflight_tools.py", "--json"],
        print_output=False,
        keep_full_stdout=True,
    )
    preflight_report = parse_json_output(preflight)
    preflight_summary = preflight_report.get("summary", {}) if preflight_report else {}
    preflight.pop("stdout_full", None)
    results.append({
        "tool": "preflight_tools",
        "summary": preflight_summary,
        **preflight,
    })

    if not args.skip_repo:
        results.append({"tool": "validate_repo", **run_command([sys.executable, "scripts/validate_repo.py"])})

    prototypes: list[Path] = []
    if output_folder:
        if not output_folder.is_dir():
            print(f"FAIL: output folder not found: {output_folder}")
            results.append({
                "tool": "output_folder",
                "required": True,
                "status": "failed",
                "result": f"not found: {output_folder}",
            })
        else:
            prototypes = find_prototypes(output_folder)

    if output_folder and prototypes and not args.pre_clarification:
        if args.skip_visual:
            visual_result = existing_visual_report_check(output_folder, prototypes, args.skip_visual_reason)
            results.append(
                visual_result
                if visual_result
                else {
                    "tool": "validate_prototype_visual",
                    "required": True,
                    "status": "skipped",
                    "result": args.skip_visual_reason,
                }
            )
        else:
            results.append({
                "tool": "validate_prototype_visual",
                **run_command([sys.executable, "scripts/validate_prototype_visual.py", str(output_folder)]),
            })

        for prototype in prototypes:
            results.append(html_parser_check(prototype))
            results.append(tidy_check(prototype))

    if output_folder and not args.pre_clarification:
        for prd_html in find_prd_html_documents(output_folder):
            results.append(html_parser_check(prd_html, allow_external_document_links=True))
            results.append(tidy_check(prd_html))

    if output_folder and args.source_preview and not args.pre_clarification:
        if args.skip_visual:
            results.append({
                "tool": "validate_ui_preview",
                "required": True,
                "status": "skipped",
                "result": args.skip_visual_reason,
            })
        else:
            results.append({
                "tool": "validate_ui_preview",
                **run_command([
                    sys.executable,
                    "scripts/validate_ui_preview.py",
                    args.source_preview,
                    "--run-folder",
                    str(output_folder),
                ]),
            })

    if output_folder:
        command = [sys.executable, "scripts/validate_outputs.py", str(output_folder)]
        if args.language:
            command.extend(["--language", args.language])
        if args.pre_clarification:
            command.append("--pre-clarification")
        results.append({"tool": "validate_outputs", **run_command(command)})

    required_failures = [
        result for result in results
        if result.get("required") and result.get("status") == "failed"
    ]
    required_skips = [
        result for result in results
        if result.get("required") and result.get("status") == "skipped"
    ]
    optional_warnings = [
        result for result in results
        if not result.get("required") and result.get("status") in {"failed", "skipped"}
    ]
    status = "failed" if required_failures else "passed"
    status_detail = "passed_with_required_skips" if status == "passed" and required_skips else status
    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repo_root": str(ROOT),
        "output_folder": str(output_folder) if output_folder else "",
        "status": status,
        "status_detail": status_detail,
        "results": results,
        "required_failures": required_failures,
        "required_skips": required_skips,
        "optional_warnings": optional_warnings,
    }

    path = report_path(output_folder, args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PM Copilot delivery checks {status_detail}: {path}")
    if required_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
