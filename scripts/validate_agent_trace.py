#!/usr/bin/env python3
"""Validate PM Copilot 3.0 agentic trace fields in a run folder."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


TASK_MODES = {
    "prd_delivery",
    "implemented_feature_prd",
    "ui_delivery",
    "tracking_plan",
    "launch_readiness",
    "dev_handoff",
    "structured_reference",
    "product_review",
    "self_improvement",
    "mixed_delivery",
}

AUTONOMY_LEVELS = {
    "clarify-first",
    "draft-with-risk",
    "full-loop",
    "self-iteration",
}

EFFORT_BUDGETS = {
    "fast-pass",
    "standard-loop",
    "deep-agentic",
    "research-intensive",
    "release/self-iteration",
}

TERMINATION_STATUSES = {
    "complete",
    "needs_input",
    "blocked",
    "degraded",
    "failed",
}

REQUIRED_3_0_SECTIONS = (
    "agent_strategy",
    "delegation_plan",
    "resume_checkpoint",
    "termination_condition",
    "tool_plan",
    "decision_record",
    "replan_triggers",
    "review_loop",
    "memory_candidates",
    "next_actions",
    "action_closure",
)

STRICT_REQUIRED_FIELDS = (
    "task_mode",
    "autonomy_level",
    "goal",
    "success_criteria",
    "selected_path",
    "final_delivery_contract",
)

NEXT_ACTION_CATEGORIES = (
    "product",
    "design",
    "engineering",
    "qa",
    "analytics",
    "launch",
)

ACTION_DUE_PHASES = {
    "now",
    "before_review",
    "before_engineering",
    "before_launch",
    "post_launch",
}

ACTION_STATUSES = {
    "ready",
    "needs_input",
    "blocked",
    "complete",
    "not_applicable",
}


def scalar_value(text: str, field: str) -> str:
    match = re.search(
        rf"^\s*(?:-\s+)?{re.escape(field)}:\s*(.*?)\s*(?:#.*)?$",
        text,
        re.MULTILINE,
    )
    if not match:
        return ""
    return match.group(1).strip().strip("\"'")


def section_text(text: str, section: str) -> str:
    match = re.search(rf"^{re.escape(section)}:\s*$", text, re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^[A-Za-z_][A-Za-z0-9_]*:\s*$", text[start:], re.MULTILINE)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end]


def field_has_list_item(text: str, field: str) -> bool:
    match = re.search(
        rf"^(?P<indent>\s*){re.escape(field)}:\s*$",
        text,
        re.MULTILINE,
    )
    if not match:
        return False
    indent = len(match.group("indent"))
    start = match.end()
    body_lines = []
    for line in text[start:].splitlines():
        if not line.strip():
            body_lines.append(line)
            continue
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= indent:
            break
        body_lines.append(line)
    return bool(re.search(r"^\s*-\s+\S", "\n".join(body_lines), re.MULTILINE))


def category_has_list_item(text: str, category: str) -> bool:
    match = re.search(rf"^\s+{re.escape(category)}:\s*$", text, re.MULTILINE)
    if not match:
        return False
    start = match.end()
    next_match = re.search(r"^\s{2}[A-Za-z_][A-Za-z0-9_]*:\s*$", text[start:], re.MULTILINE)
    end = start + next_match.start() if next_match else len(text)
    body = text[start:end]
    return bool(re.search(r"^\s*-\s+\S", body, re.MULTILINE))


def list_field_values(text: str, field: str) -> list[str]:
    inline_match = re.search(
        rf"^\s*{re.escape(field)}:\s*\[(.*?)\]\s*(?:#.*)?$",
        text,
        re.MULTILINE,
    )
    if inline_match:
        return [
            item.strip().strip("\"'")
            for item in inline_match.group(1).split(",")
            if item.strip().strip("\"'")
        ]
    block_match = re.search(
        rf"^\s*{re.escape(field)}:\s*$\n(?P<body>(?:^\s+-\s+.*$\n?)*)",
        text,
        re.MULTILINE,
    )
    if not block_match:
        return []
    return [
        value.strip().strip("\"'")
        for value in re.findall(r"^\s+-\s+(.+?)\s*$", block_match.group("body"), re.MULTILINE)
        if value.strip().strip("\"'")
    ]


def mapping_item_blocks(text: str, first_field: str) -> list[str]:
    starts = list(
        re.finditer(rf"^\s+-\s+{re.escape(first_field)}:\s*.*$", text, re.MULTILINE)
    )
    blocks = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        blocks.append(text[match.start():end])
    return blocks


def validate_run_log(run_log: Path, *, strict: bool) -> dict[str, Any]:
    text = run_log.read_text(encoding="utf-8")
    failures: list[str] = []
    warnings: list[str] = []

    present_sections = [section for section in REQUIRED_3_0_SECTIONS if f"{section}:" in text]
    missing_sections = [section for section in REQUIRED_3_0_SECTIONS if f"{section}:" not in text]

    if missing_sections and not strict:
        return {
            "status": "skipped",
            "reason": "legacy run-log has no complete PM Copilot 3.0 agentic trace",
            "present_sections": present_sections,
            "missing_sections": missing_sections,
            "failures": [],
            "warnings": [],
        }

    for section in missing_sections:
        failures.append(f"missing section: {section}")

    task_mode = scalar_value(text, "task_mode")
    autonomy_level = scalar_value(text, "autonomy_level")
    effort_budget = scalar_value(text, "effort_budget")
    termination_status = scalar_value(section_text(text, "termination_condition"), "status")
    if task_mode not in TASK_MODES:
        failures.append(f"invalid or empty task_mode: {task_mode or '<empty>'}")
    if autonomy_level not in AUTONOMY_LEVELS:
        failures.append(f"invalid or empty autonomy_level: {autonomy_level or '<empty>'}")
    if effort_budget not in EFFORT_BUDGETS:
        failures.append(f"invalid or empty effort_budget: {effort_budget or '<empty>'}")
    if termination_status not in TERMINATION_STATUSES:
        failures.append(f"invalid or empty termination_condition.status: {termination_status or '<empty>'}")

    for field in STRICT_REQUIRED_FIELDS:
        if field in {"success_criteria", "selected_path"}:
            if not field_has_list_item(text, field):
                failures.append(f"{field} must contain at least one list item")
        elif not scalar_value(text, field) and f"{field}:" not in text:
            failures.append(f"missing field: {field}")

    if "tool_id:" not in section_text(text, "tool_plan"):
        failures.append("tool_plan must name at least one tool_id or skipped tool")

    decision_body = section_text(text, "decision_record")
    if "decision:" not in decision_body or "evidence:" not in decision_body:
        failures.append("decision_record must include decision and evidence")
    decision_ids = {
        scalar_value(block, "id")
        for block in mapping_item_blocks(decision_body, "id")
        if scalar_value(block, "id")
    }
    if not decision_ids:
        failures.append("decision_record must include at least one non-empty id")
    for block in mapping_item_blocks(decision_body, "id"):
        decision_id = scalar_value(block, "id") or "<empty>"
        confidence = scalar_value(block, "confidence")
        if confidence not in {"high", "medium", "low"}:
            failures.append(
                f"decision_record {decision_id} has invalid confidence: "
                f"{confidence or '<empty>'}"
            )

    review_body = section_text(text, "review_loop")
    if "iterations:" not in review_body:
        failures.append("review_loop must include iteration count")

    next_body = section_text(text, "next_actions")
    if not any(category_has_list_item(next_body, category) for category in NEXT_ACTION_CATEGORIES):
        failures.append("next_actions must include at least one concrete action")

    readiness_body = section_text(text, "readiness")
    blocker_ids = {
        value
        for value in re.findall(r"^\s+-\s+id:\s*([^\s#]+)", readiness_body, re.MULTILINE)
        if value
    }
    closure_body = section_text(text, "action_closure")
    closure_blocks = mapping_item_blocks(closure_body, "action_id")
    if not closure_blocks:
        failures.append("action_closure.critical_path must include at least one action")
    closure_ids: set[str] = set()
    closure_statuses: list[str] = []
    for block in closure_blocks:
        action_id = scalar_value(block, "action_id")
        action = scalar_value(block, "action")
        owner = scalar_value(block, "owner")
        due_phase = scalar_value(block, "due_phase")
        completion_evidence = scalar_value(block, "completion_evidence")
        status = scalar_value(block, "status")
        decision_refs = list_field_values(block, "source_decision_ids")
        blocker_refs = list_field_values(block, "source_blocker_ids")
        if not action_id:
            failures.append("action_closure item has empty action_id")
        elif action_id in closure_ids:
            failures.append(f"duplicate action_closure action_id: {action_id}")
        else:
            closure_ids.add(action_id)
        if not action:
            failures.append(f"action_closure {action_id or '<empty>'} has empty action")
        if not owner:
            failures.append(f"action_closure {action_id or '<empty>'} has empty owner")
        if due_phase not in ACTION_DUE_PHASES:
            failures.append(
                f"action_closure {action_id or '<empty>'} has invalid due_phase: "
                f"{due_phase or '<empty>'}"
            )
        if not completion_evidence:
            failures.append(
                f"action_closure {action_id or '<empty>'} has empty completion_evidence"
            )
        if status not in ACTION_STATUSES:
            failures.append(
                f"action_closure {action_id or '<empty>'} has invalid status: "
                f"{status or '<empty>'}"
            )
        else:
            closure_statuses.append(status)
        if not decision_refs and not blocker_refs:
            failures.append(
                f"action_closure {action_id or '<empty>'} must reference a decision or blocker"
            )
        unknown_decisions = sorted(set(decision_refs) - decision_ids)
        unknown_blockers = sorted(set(blocker_refs) - blocker_ids)
        if unknown_decisions:
            failures.append(
                f"action_closure {action_id or '<empty>'} references unknown decision ids: "
                + ", ".join(unknown_decisions)
            )
        if unknown_blockers:
            failures.append(
                f"action_closure {action_id or '<empty>'} references unknown blocker ids: "
                + ", ".join(unknown_blockers)
            )
    if termination_status == "needs_input" and "needs_input" not in closure_statuses:
        failures.append("needs_input termination requires a needs_input action_closure item")
    if termination_status == "blocked" and "blocked" not in closure_statuses:
        failures.append("blocked termination requires a blocked action_closure item")

    memory_body = section_text(text, "memory_candidates")
    if not memory_body.strip():
        failures.append("memory_candidates section is empty")
    elif "write_recommendation:" not in memory_body and "none" not in memory_body.lower():
        warnings.append("memory_candidates should contain candidates or explicit none")

    return {
        "status": "failed" if failures else "passed",
        "task_mode": task_mode,
        "autonomy_level": autonomy_level,
        "action_closure_count": len(closure_blocks),
        "present_sections": present_sections,
        "missing_sections": missing_sections,
        "failures": failures,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_folder", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    run_log = args.run_folder / "run-log.yaml"
    if not run_log.is_file():
        result = {
            "status": "failed",
            "failures": [f"missing run-log.yaml: {run_log}"],
            "warnings": [],
        }
    else:
        result = validate_run_log(run_log, strict=args.strict)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"agent trace validation {result['status']}: {args.run_folder}")
        for failure in result.get("failures", []):
            print(f"FAIL: {failure}")
        for warning in result.get("warnings", []):
            print(f"WARN: {warning}")
        if result.get("status") == "skipped":
            print(f"SKIP: {result.get('reason')}")

    if result["status"] == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
