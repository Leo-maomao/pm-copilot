#!/usr/bin/env python3
"""Analyze local PM Copilot run evidence for agentic quality gaps."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


AGENTIC_FIELDS = (
    "agent_strategy",
    "task_mode",
    "autonomy_level",
    "effort_budget",
    "delegation_plan",
    "resume_checkpoint",
    "termination_condition",
    "tool_plan",
    "decision_record",
    "replan_triggers",
    "review_loop",
    "loop_policy",
    "loop_state",
    "iteration_trace",
    "loop_summary",
    "memory_candidates",
    "next_actions",
    "action_closure",
)

PRD_AGENTIC_MARKERS = {
    "product_judgment": ("product judgment", "产品判断"),
    "confidence": ("confidence", "置信"),
    "alternatives": ("alternative", "替代方案", "取舍"),
    "next_actions": ("next action", "下一步"),
    "memory_candidates": ("memory candidate", "memory candidates", "记忆候选"),
    "engineering_readiness": ("engineering handoff", "研发交接"),
    "launch_readiness": ("launch status", "上线状态", "上线判断"),
}


def default_roots() -> list[Path]:
    roots = [Path.cwd() / "outputs"]
    desktop = Path.home() / "Desktop"
    if desktop.is_dir():
        roots.extend(path for path in desktop.glob("*/pm-copilot/outputs") if path.is_dir())
    deduped: dict[str, Path] = {}
    for root in roots:
        if root.is_dir():
            deduped[root.resolve().as_posix()] = root.resolve()
    return list(deduped.values())


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(errors="ignore")


def run_record(folder: Path) -> dict[str, Any]:
    run_log = folder / "run-log.yaml"
    prd = folder / "prd.md"
    report = folder / "tool-results" / "delivery-check-report.json"
    run_log_text = read(run_log) if run_log.is_file() else ""
    prd_text = read(prd).lower() if prd.is_file() else ""
    missing_fields = [field for field in AGENTIC_FIELDS if f"{field}:" not in run_log_text]
    prd_markers = {
        key: any(marker.lower() in prd_text for marker in markers)
        for key, markers in PRD_AGENTIC_MARKERS.items()
    }
    delivery_status = ""
    if report.is_file():
        try:
            delivery_status = str(json.loads(read(report)).get("status") or "")
        except json.JSONDecodeError:
            delivery_status = "unreadable"
    return {
        "run_id": folder.name,
        "path": folder.as_posix(),
        "has_run_log": run_log.is_file(),
        "has_prd": prd.is_file(),
        "has_delivery_report": report.is_file(),
        "delivery_status": delivery_status,
        "missing_agentic_fields": missing_fields,
        "agentic_field_coverage": round((len(AGENTIC_FIELDS) - len(missing_fields)) / len(AGENTIC_FIELDS), 3),
        "prd_agentic_markers": prd_markers,
    }


def summarize(runs: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(runs)
    if not total:
        return {
            "total_runs": 0,
            "risks": ["No local PM Copilot output runs found."],
        }
    missing_counts: dict[str, int] = {field: 0 for field in AGENTIC_FIELDS}
    marker_counts: dict[str, int] = {key: 0 for key in PRD_AGENTIC_MARKERS}
    for run in runs:
        for field in run["missing_agentic_fields"]:
            missing_counts[field] += 1
        for marker, present in run["prd_agentic_markers"].items():
            if present:
                marker_counts[marker] += 1
    complete_traces = sum(1 for run in runs if not run["missing_agentic_fields"])
    risks = []
    if complete_traces < total:
        risks.append(
            f"{total - complete_traces} run(s) lack complete PM Copilot agentic trace fields."
        )
    if missing_counts["action_closure"]:
        risks.append(
            f"{missing_counts['action_closure']} run(s) lack accountable action closure."
        )
    if missing_counts["loop_policy"]:
        risks.append(
            f"{missing_counts['loop_policy']} run(s) lack bounded Loop policy and iteration evidence."
        )
    if marker_counts["next_actions"] < total:
        risks.append(f"{total - marker_counts['next_actions']} PRD run(s) lack explicit next actions.")
    if marker_counts["product_judgment"] < total:
        risks.append(f"{total - marker_counts['product_judgment']} PRD run(s) lack explicit product judgment.")
    return {
        "total_runs": total,
        "runs_with_complete_agentic_trace": complete_traces,
        "agentic_trace_completion_rate": round(complete_traces / total, 3),
        "missing_field_counts": missing_counts,
        "prd_marker_counts": marker_counts,
        "risks": risks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", type=Path, default=[])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    roots = [root.resolve() for root in args.root] if args.root else default_roots()
    runs = []
    for root in roots:
        runs.extend(run_record(path) for path in sorted(root.iterdir()) if path.is_dir())
    report = {
        "roots": [root.as_posix() for root in roots],
        "summary": summarize(runs),
        "runs": runs,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = report["summary"]
        print("PM Copilot local run evidence")
        print(f"runs: {summary['total_runs']}")
        print(f"complete_agentic_trace: {summary.get('runs_with_complete_agentic_trace', 0)}")
        for risk in summary.get("risks", []):
            print(f"- {risk}")


if __name__ == "__main__":
    main()
