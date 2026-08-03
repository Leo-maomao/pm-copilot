#!/usr/bin/env python3
"""Validate the complete PM Copilot Agent runtime trace in a run folder."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from agent_event_ledger import validate_file as validate_event_ledger


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

REQUIRED_TRACE_SECTIONS = (
    "agent_strategy",
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

LOOP_TYPES = {
    "direct",
    "execution",
    "evaluator_optimizer",
    "research",
    "self_improvement",
}

ITERATION_OUTCOMES = {
    "progress",
    "no_progress",
    "success",
    "needs_input",
    "blocked",
    "failed",
}

LOOP_NEXT_DECISIONS = {
    "continue",
    "continue_reconcile",
    "stop_success",
    "stop_needs_input",
    "stop_blocked",
    "stop_budget",
    "stop_no_progress",
    "stop_human_checkpoint",
    "stop_failed",
}

CONFLICT_RESOLUTION_STATUSES = {
    "clear",
    "reconcile",
    "needs_input",
    "blocked",
}

LOOP_STOP_REASONS = {
    "not_applicable",
    "success",
    "needs_input",
    "blocked",
    "budget",
    "no_progress",
    "human_checkpoint",
    "failed",
}

HUMAN_CHECKPOINT_STATUSES = {
    "not_required",
    "pending",
    "approved",
    "declined",
}

REVIEW_RECOMMENDATIONS = {
    "proceed",
    "proceed_with_controls",
    "revise",
    "needs_input",
    "blocked",
    "stop",
}

REVIEW_CLOSURE_DISPOSITIONS = {"fixed", "accepted_risk", "replan"}

MEMORY_CONFIDENCE_LEVELS = {"high", "medium", "low"}
MEMORY_SENSITIVITY_LEVELS = {"normal", "sensitive", "private"}
MEMORY_WRITE_RECOMMENDATIONS = {
    "suggest",
    "ask_before_writing",
    "do_not_store",
}

VISUAL_RUNTIME_CAPABILITIES = {
    "existing_preview_discovery",
    "project_runtime_activation",
    "test_state_recovery",
}
VISUAL_RUNTIME_STATUSES = {"passed", "failed", "blocked", "not_available", "not_required"}
VISUAL_CAPTURE_METHODS = {"playwright", "chrome_devtools", "computer_use"}
VISUAL_CAPTURE_STATUSES = {"passed", "failed", "blocked", "not_available"}


def scalar_value(text: str, field: str) -> str:
    match = re.search(
        rf"^\s*(?:-\s+)?{re.escape(field)}:\s*(.*?)\s*(?:#.*)?$",
        text,
        re.MULTILINE,
    )
    if not match:
        return ""
    return match.group(1).strip().strip("\"'")


def integer_value(text: str, field: str, default: int = -1) -> int:
    value = scalar_value(text, field)
    try:
        return int(value)
    except ValueError:
        return default


def boolean_value(text: str, field: str) -> bool | None:
    value = scalar_value(text, field).lower()
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def section_text(text: str, section: str) -> str:
    match = re.search(rf"^{re.escape(section)}:\s*$", text, re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^[A-Za-z_][A-Za-z0-9_]*:\s*$", text[start:], re.MULTILINE)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end]


def nested_section_text(text: str, section: str) -> str:
    match = re.search(
        rf"^(?P<indent>\s+){re.escape(section)}:\s*$",
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


def has_local_result_file(run_log: Path, result_ref: str) -> bool:
    if not result_ref:
        return False
    try:
        candidate = (run_log.parent / result_ref).resolve()
        candidate.relative_to(run_log.parent.resolve())
    except ValueError:
        return False
    return candidate.is_file() and candidate.stat().st_size > 0


def validate_visual_capture_capability(run_log: Path, implemented: str) -> list[str]:
    visual_coverage = mapping_item_blocks(
        nested_section_text(implemented, "screenshots_and_placeholders"),
        "target_ref",
    )
    if not any(scalar_value(item, "coverage_decision") == "required_placeholder" for item in visual_coverage):
        return []

    failures: list[str] = []
    capability = nested_section_text(implemented, "visual_runtime_capability")
    discovery = mapping_item_blocks(nested_section_text(capability, "runtime_discovery"), "capability")
    discovered_capabilities = {scalar_value(item, "capability") for item in discovery}
    if discovered_capabilities != VISUAL_RUNTIME_CAPABILITIES:
        failures.append(
            "required_placeholder requires existing-preview discovery, project-runtime activation, and test-state recovery records"
        )
    discovery_statuses = {scalar_value(item, "capability"): scalar_value(item, "status") for item in discovery}
    for item in discovery:
        capability_name = scalar_value(item, "capability") or "<empty>"
        status = scalar_value(item, "status")
        if status not in VISUAL_RUNTIME_STATUSES:
            failures.append(f"visual runtime capability {capability_name} has an invalid status")
        for field in ("action", "evidence"):
            if not scalar_value(item, field):
                failures.append(f"visual runtime capability {capability_name} requires {field}")
        result_ref = scalar_value(item, "result_ref")
        if status != "not_required" and not has_local_result_file(run_log, result_ref):
            failures.append(
                f"visual runtime capability {capability_name} requires a non-empty local result_ref"
            )
    if discovery_statuses.get("project_runtime_activation") == "not_required" and discovery_statuses.get("existing_preview_discovery") != "passed":
        failures.append("project-runtime activation may be not_required only after an existing preview is found")

    recovery = nested_section_text(implemented, "visual_capture_recovery")
    attempts = mapping_item_blocks(recovery, "attempt_id")
    methods = {scalar_value(attempt, "method") for attempt in attempts}
    if not VISUAL_CAPTURE_METHODS.issubset(methods):
        failures.append("required_placeholder requires Playwright, Chrome DevTools, and Computer Use recovery records")
    for attempt in attempts:
        method = scalar_value(attempt, "method")
        if method not in VISUAL_CAPTURE_METHODS:
            continue
        status = scalar_value(attempt, "status")
        if status not in VISUAL_CAPTURE_STATUSES:
            failures.append(f"visual capture recovery {method} must be attempted, not skipped")
        for field in ("action", "evidence"):
            if not scalar_value(attempt, field):
                failures.append(f"visual capture recovery {method} requires {field}")
        if not has_local_result_file(run_log, scalar_value(attempt, "result_ref")):
            failures.append(f"visual capture recovery {method} requires a non-empty local result_ref")
    return failures


def validate_implemented_feature_prd_integrity(run_log: Path, text: str, task_mode: str) -> list[str]:
    if task_mode != "implemented_feature_prd":
        return []

    failures: list[str] = []
    implemented = section_text(text, "implemented_feature_prd")
    if boolean_value(implemented, "active") is not True:
        failures.append("implemented_feature_prd task_mode requires implemented_feature_prd.active: true")
    if scalar_value(implemented, "mode") not in {"implemented_feature_prd", "implemented_feature_prd_review"}:
        failures.append("implemented_feature_prd task_mode requires a matching implemented_feature_prd.mode")

    current_run = run_log.parent.name
    task_body = section_text(text, "task")
    context_body = section_text(text, "context")
    if current_run and current_run in scalar_value(task_body, "brief_path"):
        failures.append("rewritten PRDs must use a new run folder instead of the source artifact folder")
    if current_run and current_run in context_body:
        failures.append("current run artifacts must not be loaded as product context")

    lineage = section_text(text, "artifact_lineage")
    if scalar_value(lineage, "mode") not in {"new_run", "replacement_run"}:
        failures.append("implemented-feature PRD requires artifact_lineage.mode")
    if "historical_artifacts:" not in lineage:
        failures.append("implemented-feature PRD requires artifact_lineage.historical_artifacts")
    if boolean_value(lineage, "output_folder_reset") is not True:
        failures.append("implemented-feature PRD requires output_folder_reset: true")

    prd_path = run_log.parent / "prd.md"
    requirement_ids = set()
    if prd_path.is_file():
        requirement_ids = set(
            re.findall(r"(?m)^\|\s*(\d+\.\d+)\s*\|", prd_path.read_text(encoding="utf-8"))
        )
    coverage = section_text(text, "requirement_coverage_review")
    coverage_blocks = mapping_item_blocks(coverage, "requirement_id")
    coverage_ids = [scalar_value(block, "requirement_id") for block in coverage_blocks]
    if requirement_ids and set(coverage_ids) != requirement_ids:
        failures.append("requirement_coverage_review must contain exactly one decision for every PRD requirement")
    if len(coverage_ids) != len(set(coverage_ids)):
        failures.append("requirement_coverage_review requirement_id values must be unique")

    visual_coverage = mapping_item_blocks(
        nested_section_text(implemented, "screenshots_and_placeholders"),
        "target_ref",
    )
    ui_surfaces = mapping_item_blocks(nested_section_text(implemented, "ui_surfaces"), "surface")
    visual_targets = [scalar_value(block, "target_ref") for block in visual_coverage]
    if ui_surfaces and requirement_ids and set(visual_targets) != requirement_ids:
        failures.append(
            "implemented_feature_prd user-facing requirements require exactly one screenshots_and_placeholders decision per requirement"
        )
    if len(visual_targets) != len(set(visual_targets)):
        failures.append("screenshots_and_placeholders target_ref values must be unique")
    for block in visual_coverage:
        target_ref = scalar_value(block, "target_ref") or "<empty>"
        decision = scalar_value(block, "coverage_decision")
        surface = scalar_value(block, "surface")
        if decision not in {"real_figure", "required_placeholder", "not_required"}:
            failures.append(f"visual coverage {target_ref} has invalid coverage_decision")
        if surface and decision == "not_required":
            failures.append(
                f"visual coverage {target_ref} cannot omit a figure for a named user-facing surface"
            )
    failures.extend(validate_visual_capture_capability(run_log, implemented))

    needs_localization = False
    needs_tracking = False
    for block in coverage_blocks:
        requirement_id = scalar_value(block, "requirement_id") or "<empty>"
        visual = scalar_value(block, "visual_decision")
        localization = scalar_value(block, "localization_decision")
        tracking = scalar_value(block, "tracking_decision")
        if visual not in {"real_figure", "required_placeholder", "not_required"}:
            failures.append(f"coverage review {requirement_id} has invalid visual_decision")
        if localization not in {"included", "not_needed"}:
            failures.append(f"coverage review {requirement_id} has invalid localization_decision")
        if tracking not in {"included", "not_needed"}:
            failures.append(f"coverage review {requirement_id} has invalid tracking_decision")
        for field in ("visual_rationale", "localization_rationale", "tracking_rationale"):
            if not scalar_value(block, field):
                failures.append(f"coverage review {requirement_id} requires {field}")
        if localization == "included":
            needs_localization = True
        if tracking == "included":
            needs_tracking = True
        if tracking == "not_needed" and (
            list_field_values(block, "measurable_actions")
            or list_field_values(block, "measurable_outcomes")
        ):
            failures.append(
                f"coverage review {requirement_id} cannot omit tracking while measurable actions or outcomes remain"
            )
        for field in ("measurable_actions", "measurable_outcomes"):
            if re.search(
                rf"^\s*{re.escape(field)}:\s*\[\]\s*#\s*\S",
                block,
                re.MULTILINE,
            ):
                failures.append(
                    f"coverage review {requirement_id} must record {field} as YAML data, not an inline comment"
                )
        if tracking == "not_needed" and re.search(
            r"(?:未包含|没有|缺少).{0,12}(?:事件|埋点).{0,8}(?:定义|配置)|"
            r"(?:事件|埋点).{0,8}(?:定义|配置).{0,12}(?:未包含|没有|缺少)",
            scalar_value(block, "tracking_rationale"),
        ):
            failures.append(
                f"coverage review {requirement_id} cannot omit tracking merely because implementation lacks event definitions"
            )
    prd_text = prd_path.read_text(encoding="utf-8") if prd_path.is_file() else ""
    if needs_localization and "多语言需求" not in prd_text:
        failures.append("coverage review requires 多语言需求 but the PRD omits it")
    if needs_tracking and "埋点需求" not in prd_text:
        failures.append("coverage review requires 埋点需求 but the PRD omits it")
    return failures


def validate_collaboration_protocol(
    delegation_active: bool | None,
    collaboration_body: str,
    decision_ids: set[str],
) -> list[str]:
    """Return collaboration-protocol failures for an active delegation."""
    failures: list[str] = []
    if not delegation_active:
        return failures
    if not collaboration_body:
        return ["active delegation_plan requires collaboration_protocol"]

    trigger = scalar_value(collaboration_body, "trigger")
    reason = scalar_value(collaboration_body, "reason")
    if trigger not in {"not_required", "material_conflict"}:
        return ["collaboration_protocol.trigger must be not_required or material_conflict"]
    if trigger == "not_required":
        if not reason:
            failures.append("collaboration_protocol not_required requires reason")
        return failures

    claim_blocks = mapping_item_blocks(nested_section_text(collaboration_body, "claims"), "id")
    review_blocks = mapping_item_blocks(nested_section_text(collaboration_body, "cross_reviews"), "id")
    arbitration_blocks = mapping_item_blocks(nested_section_text(collaboration_body, "arbitrations"), "id")
    claim_ids = {scalar_value(block, "id") for block in claim_blocks if scalar_value(block, "id")}
    if not claim_ids or not review_blocks or not arbitration_blocks:
        failures.append("material conflict requires claims, cross_reviews, and arbitrations")
    for block in review_blocks:
        target = scalar_value(block, "target_claim_id")
        status = scalar_value(block, "status")
        if target not in claim_ids:
            failures.append("cross_review must target a known claim")
        if status not in {"raised", "resolved", "accepted_risk", "escalated"}:
            failures.append("cross_review has invalid status")
    for block in arbitration_blocks:
        decision_ref = scalar_value(block, "decision_ref")
        outcome = scalar_value(block, "outcome")
        owner = scalar_value(block, "owner")
        if not list_field_values(block, "evidence_compared"):
            failures.append("arbitration requires evidence_compared")
        if decision_ref not in decision_ids:
            failures.append("arbitration must reference a known decision_record id")
        if outcome not in {"accepted", "rejected", "escalated_to_human"} or owner != "PM Orchestrator":
            failures.append("arbitration requires valid outcome and PM Orchestrator owner")
    return failures


def validate_run_log(run_log: Path) -> dict[str, Any]:
    text = run_log.read_text(encoding="utf-8")
    failures: list[str] = []
    warnings: list[str] = []

    present_sections = [section for section in REQUIRED_TRACE_SECTIONS if f"{section}:" in text]
    missing_sections = [section for section in REQUIRED_TRACE_SECTIONS if f"{section}:" not in text]

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

    failures.extend(validate_implemented_feature_prd_integrity(run_log, text, task_mode))

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

    delegation_body = section_text(text, "delegation_plan")
    delegation_active = boolean_value(delegation_body, "active")
    collaboration_body = section_text(text, "collaboration_protocol")
    failures.extend(
        validate_collaboration_protocol(delegation_active, collaboration_body, decision_ids)
    )

    review_body = section_text(text, "review_loop")
    review_iterations = integer_value(review_body, "iterations")
    if review_iterations < 0:
        failures.append("review_loop.iterations must be a nonnegative integer")
    review_recommendation = scalar_value(review_body, "final_recommendation")
    if review_recommendation not in REVIEW_RECOMMENDATIONS:
        failures.append(
            "review_loop.final_recommendation must be one of: "
            + ", ".join(sorted(REVIEW_RECOMMENDATIONS))
        )
    if "unresolved_findings:" not in review_body:
        failures.append("review_loop must include unresolved_findings")

    severe_findings = list_field_values(review_body, "critical_or_high_findings")
    unresolved_findings = list_field_values(review_body, "unresolved_findings")
    closure_body = nested_section_text(review_body, "finding_closures")
    closure_blocks = mapping_item_blocks(closure_body, "finding")
    closed_findings: set[str] = set()
    for block in closure_blocks:
        finding = scalar_value(block, "finding") or "<empty>"
        disposition = scalar_value(block, "disposition")
        evidence = scalar_value(block, "evidence")
        owner = scalar_value(block, "owner")
        due_phase = scalar_value(block, "due_phase")
        rationale = scalar_value(block, "rationale")
        if finding != "<empty>":
            closed_findings.add(finding)
        if disposition not in REVIEW_CLOSURE_DISPOSITIONS:
            failures.append(
                f"review finding closure {finding} has invalid disposition: "
                f"{disposition or '<empty>'}"
            )
        if not evidence:
            failures.append(f"review finding closure {finding} requires evidence")
        if disposition == "accepted_risk" and (
            not owner or due_phase not in ACTION_DUE_PHASES or not rationale
        ):
            failures.append(
                f"accepted risk closure {finding} requires owner, valid due_phase, and rationale"
            )
    missing_closures = [finding for finding in severe_findings if finding not in closed_findings]
    unexpected_closures = [finding for finding in closed_findings if finding not in severe_findings]
    if missing_closures:
        failures.append(
            "Critical/High review findings missing exact closure: "
            + ", ".join(missing_closures)
        )
    if unexpected_closures:
        failures.append(
            "review finding closures do not match a Critical/High finding: "
            + ", ".join(sorted(unexpected_closures))
        )
    if termination_status == "complete" and unresolved_findings:
        failures.append("complete termination cannot retain unresolved review findings")
    if unresolved_findings and review_recommendation in {"proceed", "proceed_with_controls"}:
        failures.append(
            "review recommendation cannot proceed while unresolved findings remain"
        )

    loop_policy_body = section_text(text, "loop_policy")
    loop_state_body = section_text(text, "loop_state")
    iteration_body = section_text(text, "iteration_trace")
    loop_summary_body = section_text(text, "loop_summary")
    loop_enabled = boolean_value(loop_policy_body, "enabled")
    loop_type = scalar_value(loop_policy_body, "loop_type")
    disabled_reason = scalar_value(loop_policy_body, "disabled_reason")
    max_iterations = integer_value(loop_policy_body, "max_iterations")
    max_tool_calls = integer_value(loop_policy_body, "max_tool_calls")
    max_elapsed_minutes = integer_value(loop_policy_body, "max_elapsed_minutes")
    max_no_progress = integer_value(loop_policy_body, "max_consecutive_no_progress")
    min_progress_delta = integer_value(loop_policy_body, "min_progress_score_delta")
    checkpoint_body = nested_section_text(loop_policy_body, "human_checkpoint")
    checkpoint_after = integer_value(checkpoint_body, "required_after_iteration")
    checkpoint_status = scalar_value(checkpoint_body, "status")
    loop_stop_reason = scalar_value(loop_summary_body, "stop_reason")
    iteration_blocks = mapping_item_blocks(iteration_body, "iteration")

    if loop_enabled is None:
        failures.append("loop_policy.enabled must be true or false")
    elif not loop_enabled:
        if not disabled_reason:
            failures.append("disabled loop_policy requires disabled_reason")
        if loop_stop_reason != "not_applicable":
            failures.append("disabled loop_policy requires loop_summary.stop_reason not_applicable")
    else:
        if loop_type not in LOOP_TYPES - {"direct"}:
            failures.append(f"enabled loop_policy has invalid loop_type: {loop_type or '<empty>'}")
        for field, value in (
            ("max_iterations", max_iterations),
            ("max_tool_calls", max_tool_calls),
            ("max_elapsed_minutes", max_elapsed_minutes),
            ("max_consecutive_no_progress", max_no_progress),
            ("min_progress_score_delta", min_progress_delta),
        ):
            if value < 1:
                failures.append(f"loop_policy.{field} must be a positive integer")
        if loop_stop_reason not in LOOP_STOP_REASONS - {"not_applicable"}:
            failures.append(
                f"enabled loop_policy has invalid loop_summary.stop_reason: "
                f"{loop_stop_reason or '<empty>'}"
            )
        if not iteration_blocks:
            failures.append("enabled loop_policy requires iteration_trace items")

    if checkpoint_after < 0:
        failures.append("loop_policy.human_checkpoint.required_after_iteration must be zero or greater")
    if checkpoint_status not in HUMAN_CHECKPOINT_STATUSES:
        failures.append(
            "loop_policy.human_checkpoint.status has invalid value: "
            f"{checkpoint_status or '<empty>'}"
        )
    if checkpoint_status == "not_required" and checkpoint_after != 0:
        failures.append("not_required human checkpoint must use required_after_iteration 0")
    if checkpoint_status != "not_required" and checkpoint_after < 1:
        failures.append("required human checkpoint must name a positive trigger iteration")

    expected_iteration = 1
    no_progress_tail = 0
    previous_score = None
    for block in iteration_blocks:
        iteration = integer_value(block, "iteration")
        outcome = scalar_value(block, "outcome")
        next_decision = scalar_value(block, "next_decision")
        before = integer_value(block, "progress_score_before")
        after = integer_value(block, "progress_score_after")
        if iteration != expected_iteration:
            failures.append(
                f"iteration_trace must be sequential from 1; expected {expected_iteration}, got {iteration}"
            )
        expected_iteration += 1
        if outcome not in ITERATION_OUTCOMES:
            failures.append(
                f"iteration {iteration} has invalid outcome: {outcome or '<empty>'}"
            )
        if next_decision not in LOOP_NEXT_DECISIONS:
            failures.append(
                f"iteration {iteration} has invalid next_decision: {next_decision or '<empty>'}"
            )
        if before < 0 or after < 0 or after > 100:
            failures.append(f"iteration {iteration} progress scores must be between 0 and 100")
        if previous_score is not None and before != previous_score:
            failures.append(
                f"iteration {iteration} progress_score_before must equal prior progress_score_after"
            )
        previous_score = after
        delta_fields = (
            "evidence_delta",
            "artifact_delta",
            "decision_delta",
            "validation_delta",
        )
        has_delta = any(list_field_values(block, field) for field in delta_fields)
        score_delta = after - before
        if outcome in {"progress", "success"}:
            if not has_delta:
                failures.append(
                    f"iteration {iteration} claims {outcome} without evidence, artifact, decision, or validation delta"
                )
            if score_delta < max(min_progress_delta, 1):
                failures.append(
                    f"iteration {iteration} claims {outcome} without minimum progress score delta"
                )
            no_progress_tail = 0
        elif outcome == "no_progress":
            if has_delta or score_delta > 0:
                failures.append(
                    f"iteration {iteration} no_progress outcome contradicts recorded delta"
                )
            no_progress_tail += 1
        else:
            no_progress_tail = 0

    current_iteration = integer_value(loop_state_body, "current_iteration")
    state_no_progress = integer_value(loop_state_body, "consecutive_no_progress")
    last_progress_score = integer_value(loop_state_body, "last_progress_score")
    iterations_completed = integer_value(loop_summary_body, "iterations_completed")
    final_progress_score = integer_value(loop_summary_body, "final_progress_score")
    if iteration_blocks:
        if current_iteration != len(iteration_blocks):
            failures.append("loop_state.current_iteration must match iteration_trace count")
        if iterations_completed != len(iteration_blocks):
            failures.append("loop_summary.iterations_completed must match iteration_trace count")
        if state_no_progress != no_progress_tail:
            failures.append("loop_state.consecutive_no_progress must match iteration trace tail")
        if last_progress_score != previous_score or final_progress_score != previous_score:
            failures.append("loop state and summary progress scores must match final iteration score")
    if loop_enabled:
        expected_final_decision = {
            "success": "stop_success",
            "needs_input": "stop_needs_input",
            "blocked": "stop_blocked",
            "budget": "stop_budget",
            "no_progress": "stop_no_progress",
            "human_checkpoint": "stop_human_checkpoint",
            "failed": "stop_failed",
        }.get(loop_stop_reason)
        if iteration_blocks and expected_final_decision:
            final_decision = scalar_value(iteration_blocks[-1], "next_decision")
            if final_decision != expected_final_decision:
                failures.append(
                    "final iteration next_decision must align with loop_summary.stop_reason"
                )
        success_criteria_met = boolean_value(loop_state_body, "success_criteria_met")
        if success_criteria_met is None:
            failures.append("loop_state.success_criteria_met must be true or false")
        elif loop_stop_reason == "success" and not success_criteria_met:
            failures.append("success stop reason requires success_criteria_met true")
        elif success_criteria_met and loop_stop_reason not in {"success", "human_checkpoint"}:
            failures.append(
                "success_criteria_met true requires success or due human_checkpoint stop reason"
            )
        conflict_resolution_status = scalar_value(loop_state_body, "conflict_resolution_status") or "clear"
        if conflict_resolution_status not in CONFLICT_RESOLUTION_STATUSES:
            failures.append("loop_state.conflict_resolution_status is invalid")
        elif conflict_resolution_status == "needs_input" and loop_stop_reason != "needs_input":
            failures.append("needs_input conflict status requires needs_input stop reason")
        elif conflict_resolution_status == "blocked" and loop_stop_reason != "blocked":
            failures.append("blocked conflict status requires blocked stop reason")
        elif conflict_resolution_status == "reconcile" and iteration_blocks:
            final_decision = scalar_value(iteration_blocks[-1], "next_decision")
            if final_decision == "continue":
                failures.append("reconcile conflict status requires continue_reconcile next decision")
        if current_iteration > max_iterations:
            failures.append("loop_state.current_iteration exceeds max_iterations")
        if integer_value(loop_state_body, "tool_calls_used") > max_tool_calls:
            failures.append("loop_state.tool_calls_used exceeds max_tool_calls")
        if integer_value(loop_state_body, "elapsed_minutes") > max_elapsed_minutes:
            failures.append("loop_state.elapsed_minutes exceeds max_elapsed_minutes")
        if state_no_progress > max_no_progress:
            failures.append("loop_state.consecutive_no_progress exceeds policy threshold")
        expected_termination_reason = {
            "complete": "success",
            "needs_input": "needs_input",
            "blocked": "blocked",
            "failed": "failed",
        }.get(termination_status)
        if expected_termination_reason and loop_stop_reason != expected_termination_reason:
            failures.append(
                "loop_summary.stop_reason must align with termination_condition.status"
            )
        checkpoint_due = checkpoint_after > 0 and current_iteration >= checkpoint_after
        if checkpoint_due and checkpoint_status in {"pending", "declined"}:
            if loop_stop_reason != "human_checkpoint":
                failures.append(
                    "pending or declined due human checkpoint requires human_checkpoint stop reason"
                )
            if iteration_blocks and scalar_value(iteration_blocks[-1], "next_decision") != "stop_human_checkpoint":
                failures.append(
                    "pending or declined due human checkpoint requires stop_human_checkpoint next decision"
                )
        elif loop_stop_reason == "human_checkpoint":
            failures.append(
                "human_checkpoint stop reason requires a due pending or declined checkpoint"
            )

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
    elif boolean_value(memory_body, "none") is not True:
        memory_candidate_count = 0
        for block in mapping_item_blocks(memory_body, "fact"):
            memory_candidate_count += 1
            fact = scalar_value(block, "fact") or "<empty>"
            source = scalar_value(block, "source")
            confidence = scalar_value(block, "confidence")
            sensitivity = scalar_value(block, "sensitivity")
            recommendation = scalar_value(block, "write_recommendation")
            if fact == "<empty>" or not source:
                failures.append(f"product memory {fact} requires fact and source")
            if confidence not in MEMORY_CONFIDENCE_LEVELS:
                failures.append(
                    f"product memory {fact} has invalid confidence: {confidence or '<empty>'}"
                )
            if sensitivity not in MEMORY_SENSITIVITY_LEVELS:
                failures.append(
                    f"product memory {fact} has invalid sensitivity: {sensitivity or '<empty>'}"
                )
            if recommendation not in MEMORY_WRITE_RECOMMENDATIONS:
                failures.append(
                    f"product memory {fact} has invalid write_recommendation: "
                    f"{recommendation or '<empty>'}"
                )
            if sensitivity in {"sensitive", "private"} and recommendation == "suggest":
                failures.append(
                    f"product memory {fact} is {sensitivity} and cannot be suggested for silent write"
                )

        for block in mapping_item_blocks(memory_body, "preference"):
            memory_candidate_count += 1
            preference = scalar_value(block, "preference") or "<empty>"
            source = scalar_value(block, "source")
            recommendation = scalar_value(block, "write_recommendation")
            if preference == "<empty>" or not source:
                failures.append(
                    f"user preference {preference} requires preference and source"
                )
            if recommendation not in MEMORY_WRITE_RECOMMENDATIONS:
                failures.append(
                    f"user preference {preference} has invalid write_recommendation: "
                    f"{recommendation or '<empty>'}"
                )

        for block in mapping_item_blocks(memory_body, "decision"):
            memory_candidate_count += 1
            decision = scalar_value(block, "decision") or "<empty>"
            rationale = scalar_value(block, "rationale")
            source = scalar_value(block, "source")
            recommendation = scalar_value(block, "write_recommendation")
            if decision == "<empty>" or not rationale or not source:
                failures.append(
                    f"decision memory {decision} requires decision, rationale, and source"
                )
            if recommendation not in MEMORY_WRITE_RECOMMENDATIONS:
                failures.append(
                    f"decision memory {decision} has invalid write_recommendation: "
                    f"{recommendation or '<empty>'}"
                )
        if memory_candidate_count == 0:
            failures.append("memory_candidates must contain validated candidates or none: true")

    self_iteration_required = (
        task_mode == "self_improvement" or autonomy_level == "self-iteration"
    )
    self_iteration_body = section_text(text, "self_iteration")
    if self_iteration_required:
        if not self_iteration_body.strip():
            failures.append("self-improvement runs require self_iteration evidence")
        else:
            if boolean_value(self_iteration_body, "triggered") is not True:
                failures.append("self_iteration.triggered must be true")
            source_present = bool(
                scalar_value(self_iteration_body, "source_run_id")
                or list_field_values(self_iteration_body, "source_run_ids")
                or list_field_values(self_iteration_body, "failure_evidence")
            )
            if not source_present:
                failures.append(
                    "self_iteration requires a source run or explicit failure evidence"
                )
            if not (
                list_field_values(self_iteration_body, "user_corrections")
                or list_field_values(self_iteration_body, "failure_evidence")
            ):
                failures.append(
                    "self_iteration requires user correction or failure evidence"
                )
            for field in (
                "generalized_failures",
                "selected_fix_surfaces",
                "regression_updates",
                "validation_commands",
            ):
                if not field_has_list_item(self_iteration_body, field):
                    failures.append(f"self_iteration.{field} requires at least one item")
            if not scalar_value(self_iteration_body, "generalization_boundary"):
                failures.append("self_iteration requires generalization_boundary")
            if not scalar_value(self_iteration_body, "version_change"):
                failures.append("self_iteration requires version_change")
            if loop_enabled is not True or loop_type != "self_improvement":
                failures.append(
                    "self-improvement runs require an enabled self_improvement loop_policy"
                )

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
        result = validate_run_log(run_log)

    event_ledger = args.run_folder / "tool-results" / "agent-events.jsonl"
    if event_ledger.is_file():
        event_failures = validate_event_ledger(event_ledger)
        if event_failures:
            result["failures"].extend(f"agent event ledger: {failure}" for failure in event_failures)
            result["status"] = "failed"

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"agent trace validation {result['status']}: {args.run_folder}")
        for failure in result.get("failures", []):
            print(f"FAIL: {failure}")
        for warning in result.get("warnings", []):
            print(f"WARN: {warning}")

    if result["status"] == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
