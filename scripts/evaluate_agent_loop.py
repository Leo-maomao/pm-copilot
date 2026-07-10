#!/usr/bin/env python3
"""Evaluate the next bounded-loop decision from a PM Copilot run log."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def scalar(text: str, field: str) -> str:
    match = re.search(
        rf"^\s*(?:-\s+)?{re.escape(field)}:\s*(.*?)\s*(?:#.*)?$",
        text,
        re.MULTILINE,
    )
    return match.group(1).strip().strip("\"'") if match else ""


def section(text: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}:\s*$", text, re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^[A-Za-z_][A-Za-z0-9_]*:\s*$", text[start:], re.MULTILINE)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end]


def nested_section(text: str, name: str) -> str:
    match = re.search(
        rf"^(?P<indent>\s+){re.escape(name)}:\s*$",
        text,
        re.MULTILINE,
    )
    if not match:
        return ""
    indent = len(match.group("indent"))
    body_lines = []
    for line in text[match.end():].splitlines():
        if not line.strip():
            body_lines.append(line)
            continue
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= indent:
            break
        body_lines.append(line)
    return "\n".join(body_lines)


def integer(text: str, field: str, default: int = 0) -> int:
    value = scalar(text, field)
    try:
        return int(value)
    except ValueError:
        return default


def boolean(text: str, field: str) -> bool:
    return scalar(text, field).lower() == "true"


def evaluate(run_log: Path) -> dict[str, Any]:
    text = run_log.read_text(encoding="utf-8")
    policy = section(text, "loop_policy")
    state = section(text, "loop_state")
    summary = section(text, "loop_summary")
    termination = section(text, "termination_condition")
    if not policy or not state:
        return {
            "status": "failed",
            "decision": "stop_failed",
            "reason": "missing loop_policy or loop_state",
        }

    enabled_value = scalar(policy, "enabled").lower()
    if enabled_value not in {"true", "false"}:
        return {
            "status": "failed",
            "decision": "stop_failed",
            "reason": "loop_policy.enabled must be true or false",
        }
    enabled = enabled_value == "true"
    if not enabled:
        reason = scalar(policy, "disabled_reason") or scalar(summary, "stop_reason")
        return {
            "status": "passed",
            "decision": "not_applicable",
            "reason": reason or "loop disabled for this run",
        }

    current_iteration = integer(state, "current_iteration")
    tool_calls_used = integer(state, "tool_calls_used")
    elapsed_minutes = integer(state, "elapsed_minutes")
    consecutive_no_progress = integer(state, "consecutive_no_progress")
    max_iterations = integer(policy, "max_iterations")
    max_tool_calls = integer(policy, "max_tool_calls")
    max_elapsed_minutes = integer(policy, "max_elapsed_minutes")
    max_no_progress = integer(policy, "max_consecutive_no_progress")
    termination_status = scalar(termination, "status")
    checkpoint = nested_section(policy, "human_checkpoint")
    checkpoint_status = scalar(checkpoint, "status")
    checkpoint_after = integer(checkpoint, "required_after_iteration")
    checkpoint_due = checkpoint_after > 0 and current_iteration >= checkpoint_after

    invalid_budgets = [
        name
        for name, value in (
            ("max_iterations", max_iterations),
            ("max_tool_calls", max_tool_calls),
            ("max_elapsed_minutes", max_elapsed_minutes),
            ("max_consecutive_no_progress", max_no_progress),
        )
        if value < 1
    ]
    if invalid_budgets:
        return {
            "status": "failed",
            "decision": "stop_failed",
            "reason": "invalid positive loop budget(s): " + ", ".join(invalid_budgets),
        }

    if termination_status == "failed":
        decision, reason = "stop_failed", "termination condition is failed"
    elif termination_status == "needs_input":
        decision, reason = "stop_needs_input", "required user input is missing"
    elif termination_status == "blocked":
        decision, reason = "stop_blocked", "a required dependency is blocked"
    elif checkpoint_due and checkpoint_status in {"pending", "declined"}:
        decision, reason = "stop_human_checkpoint", f"human checkpoint is {checkpoint_status}"
    elif boolean(state, "success_criteria_met"):
        decision, reason = "stop_success", "success criteria are met"
    elif current_iteration >= max_iterations:
        decision, reason = "stop_budget", "iteration budget exhausted"
    elif tool_calls_used >= max_tool_calls:
        decision, reason = "stop_budget", "tool-call budget exhausted"
    elif elapsed_minutes >= max_elapsed_minutes:
        decision, reason = "stop_budget", "elapsed-time budget exhausted"
    elif consecutive_no_progress >= max_no_progress:
        decision, reason = "stop_no_progress", "consecutive no-progress threshold reached"
    else:
        decision, reason = "continue", "budget remains and progress is still possible"

    stop_reason = scalar(summary, "stop_reason")
    expected_reason = {
        "stop_success": "success",
        "stop_needs_input": "needs_input",
        "stop_blocked": "blocked",
        "stop_budget": "budget",
        "stop_no_progress": "no_progress",
        "stop_human_checkpoint": "human_checkpoint",
        "stop_failed": "failed",
    }.get(decision, "")
    summary_matches = (
        not expected_reason
        or stop_reason == expected_reason
    )
    return {
        "status": "passed" if summary_matches else "failed",
        "decision": decision,
        "reason": reason,
        "current_iteration": current_iteration,
        "budgets": {
            "max_iterations": max_iterations,
            "tool_calls_used": tool_calls_used,
            "max_tool_calls": max_tool_calls,
            "elapsed_minutes": elapsed_minutes,
            "max_elapsed_minutes": max_elapsed_minutes,
            "consecutive_no_progress": consecutive_no_progress,
            "max_consecutive_no_progress": max_no_progress,
        },
        "expected_stop_reason": expected_reason,
        "recorded_stop_reason": stop_reason,
        "summary_matches": summary_matches,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_folder", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    run_log = args.run_folder / "run-log.yaml"
    if not run_log.is_file():
        result = {"status": "failed", "decision": "stop_failed", "reason": f"missing {run_log}"}
    else:
        result = evaluate(run_log)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"agent loop evaluation {result['status']}: {result['decision']}")
        print(result["reason"])
    if result["status"] == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
