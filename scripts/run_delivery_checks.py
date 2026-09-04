#!/usr/bin/env python3
"""Run the small, canonical PRD delivery validation set."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(command), "status": "passed" if completed.returncode == 0 else "failed",
        "exit_code": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_folder", type=Path)
    parser.add_argument("--language", choices=["zh", "en"], default=None)
    parser.add_argument("--pre-clarification", action="store_true")
    parser.add_argument("--staging", action="store_true")
    parser.add_argument("--skip-repo", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    folder = args.output_folder.resolve()
    checks: list[dict[str, Any]] = []
    if not args.skip_repo:
        checks.append({"tool": "validate_repo", **run([sys.executable, "scripts/validate_repo.py"])})
    if not folder.is_dir():
        checks.append({"tool": "output_folder", "status": "failed", "exit_code": 2, "stdout": "", "stderr": f"not found: {folder}"})
    else:
        if not args.pre_clarification:
            checks.append({"tool": "render_prd_html", **run([sys.executable, "scripts/render_prd_html.py", str(folder)])})
        output_command = [sys.executable, "scripts/validate_outputs.py", str(folder)]
        if args.language:
            output_command.extend(["--language", args.language])
        if args.pre_clarification:
            output_command.append("--pre-clarification")
        if args.staging:
            output_command.append("--staging")
        checks.append({"tool": "validate_outputs", **run(output_command)})
        checks.append({"tool": "validate_agent_trace", **run([sys.executable, "scripts/validate_agent_trace.py", str(folder)])})
    failed = [check for check in checks if check["status"] == "failed"]
    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "output_folder": str(folder),
        "status": "failed" if failed else "passed", "results": checks,
    }
    report_path = args.report or folder / "tool-results" / "delivery-check-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PM Copilot delivery checks {report['status']}: {report_path}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
