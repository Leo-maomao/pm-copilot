#!/usr/bin/env python3
"""Generate a PM Copilot self-improvement scorecard from evals and run evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

VALIDATION_TERMS = (
    "validate_outputs.py",
    "run_delivery_checks.py",
    "validate_repo.py",
    "validate_prototype_visual.py",
    "validate_ui_preview.py",
    "pre-clarification",
)

CAPABILITY_AREAS = {
    "context_intake": (
        "repo-backed",
        "document-backed",
        "brief-only",
        "context",
        "host project",
        "source",
        "uploaded",
    ),
    "clarification_control": (
        "clarifying",
        "clarification",
        "must-answer",
        "pre-clarification",
        "blocking question",
    ),
    "prd_reasoning": (
        "prd",
        "acceptance",
        "scope",
        "mvp",
        "non-goal",
        "requirement",
    ),
    "metrics_tracking": (
        "metric",
        "tracking",
        "analytics",
        "event",
        "property",
        "conversion",
        "experiment",
    ),
    "ui_delivery": (
        "ui",
        "prototype",
        "visual",
        "source-backed",
        "preview",
        "storybook",
        "mini program",
        "h5",
        "web",
        "app",
    ),
    "risk_readiness": (
        "legal",
        "privacy",
        "security",
        "payment",
        "compliance",
        "launch",
        "blocker",
        "regulated",
        "risk",
    ),
    "tool_validation": (
        "validate_outputs.py",
        "run_delivery_checks.py",
        "validate_repo.py",
        "validate_prototype_visual.py",
        "validate_ui_preview.py",
        "preflight",
        "playwright",
    ),
    "handoff_execution": (
        "handoff",
        "dev-tasks.yaml",
        "launch-decision.yaml",
        "engineering",
        "rollout",
        "rollback",
    ),
    "knowledge_catalog": (
        "catalog.md",
        "catalog.html",
        "reference.md",
        "reference.html",
        "structured reference",
        "document prototype",
        "model matrix",
        "parameter table",
        "rule reference",
        "field dictionary",
        "api capability",
        "vendor matrix",
        "data dictionary",
    ),
    "skill_governance": (
        "skill",
        "sharingan",
        "absorption",
        "duplicate",
        "canonical",
        "external tool",
    ),
}

CONTEXT_MODE_TERMS = {
    "repo_backed": (
        "repo-backed",
        "host project",
        "host repository",
        "source-backed",
        "frontend source",
    ),
    "document_backed": (
        "document-backed",
        "uploaded product documents",
        "historical prd",
        "support ticket",
        "kpi summary",
    ),
    "brief_only": (
        "brief-only",
        "no frontend source",
        "compatibility html",
        "context/product-context.example.yaml",
    ),
    "screenshot_backed": (
        "screenshot-backed",
        "image reference",
        "reference image",
        "supplied ui image",
        "user-provided target screenshot",
    ),
    "mixed_context": (
        "mixed context",
        "mixed-context",
        "repo-backed or document-backed",
        "document_or_screenshot_only",
    ),
}

MIN_PORTFOLIO_COVERAGE = {
    "platforms": 4,
    "pm_user_types": 4,
    "risk_profiles": 5,
    "context_modes": 3,
    "edge_case_pressures": 4,
}

MIN_PASSED_PORTFOLIO_COVERAGE = {
    "passed_platforms": 3,
    "passed_pm_user_types": 3,
    "passed_risk_profiles": 4,
    "passed_context_modes": 3,
    "passed_edge_case_pressures": 4,
}

UNKNOWN_VALUES = {"", "unknown", "tbd", "n/a", "not specified"}

EDGE_CASE_PRESSURES = {
    "regulated_or_safety_critical": (
        "regulated",
        "health",
        "medical",
        "minor",
        "children",
        "emergency",
        "legal",
        "compliance",
    ),
    "ambiguous_or_conflicting_input": (
        "ambiguous",
        "unclear",
        "conflict",
        "must-answer",
        "must answer",
        "blocking question",
        "clarification",
    ),
    "privacy_or_sensitive_data": (
        "privacy",
        "sensitive",
        "raw payment",
        "raw address",
        "payment token",
        "health data",
        "redaction",
    ),
    "launch_or_bypass_pressure": (
        "launch tomorrow",
        "do not involve legal",
        "avoid legal",
        "bypass",
        "ready_to_launch",
        "不要问太多",
        "别拉法务",
        "明天上线",
    ),
    "missing_or_non_repo_context": (
        "no project repository",
        "uploaded",
        "document-backed",
        "brief-only",
        "no host repository",
        "no frontend source",
    ),
    "source_fidelity_pressure": (
        "source-backed",
        "source-rendered",
        "existing ui",
        "image reference",
        "screenshot",
        "visual evidence",
    ),
}

ARTIFACT_EXPECTATION_TERMS = {
    "prd": ("prd.md",),
    "ui_delivery": (
        "ui deliverable",
        "source-backed preview",
        "source-rendered preview",
        "prototype-web.html",
        "prototype-h5.html",
        "prototype-app.html",
        "prototype-mini-program.html",
    ),
    "tracking_plan": (
        "tracking-plan.csv",
        "tracking plan",
        "analytics",
        "event_name",
    ),
    "structured_catalog": (
        "catalog.md",
        "catalog.html",
        "reference.md",
        "reference.html",
        "structured reference",
        "document prototype",
        "model matrix",
        "parameter table",
        "rule reference",
        "field dictionary",
        "api capability",
        "vendor matrix",
        "data dictionary",
    ),
    "dev_tasks": ("dev-tasks.yaml",),
    "launch_decision": ("launch-decision.yaml",),
    "run_log": ("run-log.yaml",),
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def slug(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def markdown_table_value(text: str, field: str) -> str:
    pattern = re.compile(rf"^\|\s*{re.escape(field)}\s*\|\s*(.*?)\s*\|", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def section_body(text: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end].strip()


def scenario_set_round_count(text: str) -> int:
    body = section_body(text, "Scenario Set")
    count = 0
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or cells[0].lower() in {"round", "case", "scenario"}:
            continue
        if any(cell for cell in cells):
            count += 1
    return count


def validation_terms(text: str) -> list[str]:
    lowered = text.lower()
    return [term for term in VALIDATION_TERMS if term.lower() in lowered]


def capability_areas_for(text: str) -> list[str]:
    lowered = text.lower()
    areas = []
    for area, terms in CAPABILITY_AREAS.items():
        if any(term.lower() in lowered for term in terms):
            areas.append(area)
    return areas


def context_modes_for(text: str) -> list[str]:
    lowered = text.lower()
    modes = []
    for mode, terms in CONTEXT_MODE_TERMS.items():
        if any(term.lower() in lowered for term in terms):
            modes.append(mode)
    return modes


def edge_case_pressures_for(text: str) -> list[str]:
    lowered = text.lower()
    pressures = []
    for pressure, terms in EDGE_CASE_PRESSURES.items():
        if any(term.lower() in lowered for term in terms):
            pressures.append(pressure)
    return pressures


def artifact_expectations_for(text: str) -> list[str]:
    lowered = text.lower()
    expectations = []
    for artifact, terms in ARTIFACT_EXPECTATION_TERMS.items():
        if any(term.lower() in lowered for term in terms):
            expectations.append(artifact)
    return expectations


def metadata_values(value: str, *, keep_none: bool = False) -> list[str]:
    normalized = re.sub(r"\s+(?:and|or)\s+", " / ", value, flags=re.IGNORECASE)
    parts = re.split(r"\s*/\s*|[,;|]", normalized)
    values = []
    for part in parts:
        cleaned = re.sub(r"\s+", " ", part).strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in UNKNOWN_VALUES:
            continue
        if lowered == "none" and not keep_none:
            continue
        values.append(cleaned)
    return values


def count_metadata_values(
    evals: list[dict[str, Any]],
    field: str,
    *,
    keep_none: bool = False,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in evals:
        for value in metadata_values(str(item.get(field, "")), keep_none=keep_none):
            counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: (pair[0].lower(), pair[0])))


def is_fixture_scoped(item: dict[str, Any]) -> bool:
    scopes = metadata_values(str(item.get("fixture_scope", "")), keep_none=True)
    return any("fixture" in scope.lower() for scope in scopes)


def build_scenario_portfolio(evals: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(evals)
    metadata_complete = sum(1 for item in evals if item["portfolio_metadata_complete"])
    passed_evals = [
        item for item in evals if item["latest_status"].strip().lower() == "passed"
    ]
    fixture_scoped = sum(1 for item in evals if is_fixture_scoped(item))
    passed_fixture_scoped = sum(1 for item in passed_evals if is_fixture_scoped(item))

    context_mode_counts: dict[str, int] = {}
    edge_case_counts: dict[str, int] = {}
    artifact_expectation_counts: dict[str, int] = {}
    for item in evals:
        for mode in item["context_modes"]:
            context_mode_counts[mode] = context_mode_counts.get(mode, 0) + 1
        for pressure in item["edge_case_pressures"]:
            edge_case_counts[pressure] = edge_case_counts.get(pressure, 0) + 1
        for artifact in item["artifact_expectations"]:
            artifact_expectation_counts[artifact] = artifact_expectation_counts.get(artifact, 0) + 1

    return {
        "metadata_complete": metadata_complete,
        "metadata_complete_rate": rate(metadata_complete, total),
        "fixture_scoped_evals": fixture_scoped,
        "non_fixture_evals": total - fixture_scoped,
        "passed_evals": len(passed_evals),
        "passed_fixture_scoped": passed_fixture_scoped,
        "passed_fixture_scoped_rate": rate(passed_fixture_scoped, len(passed_evals)),
        "fixture_scopes": count_metadata_values(evals, "fixture_scope", keep_none=True),
        "platforms": count_metadata_values(evals, "platform"),
        "product_areas": count_metadata_values(evals, "product_area"),
        "pm_user_types": count_metadata_values(evals, "pm_user_type"),
        "risk_profiles": count_metadata_values(evals, "risk_profile"),
        "context_modes": dict(sorted(context_mode_counts.items())),
        "edge_case_pressures": dict(sorted(edge_case_counts.items())),
        "artifact_expectations": dict(sorted(artifact_expectation_counts.items())),
        "passed_platforms": count_metadata_values(passed_evals, "platform"),
        "passed_pm_user_types": count_metadata_values(passed_evals, "pm_user_type"),
        "passed_risk_profiles": count_metadata_values(passed_evals, "risk_profile"),
        "passed_context_modes": dict(sorted(
            (mode, sum(1 for item in passed_evals if mode in item["context_modes"]))
            for mode in {mode for item in passed_evals for mode in item["context_modes"]}
        )),
        "passed_edge_case_pressures": dict(sorted(
            (
                pressure,
                sum(1 for item in passed_evals if pressure in item["edge_case_pressures"]),
            )
            for pressure in {
                pressure
                for item in passed_evals
                for pressure in item["edge_case_pressures"]
            }
        )),
    }


def collect_evals() -> list[dict[str, Any]]:
    evals = []
    for path in sorted((ROOT / "evals").glob("*.md")):
        text = read_text(path)
        latest_status = markdown_table_value(section_body(text, "Latest Result"), "Status")
        platform = markdown_table_value(text, "Platform")
        product_area = markdown_table_value(text, "Product Area")
        fixture_scope = markdown_table_value(text, "Fixture Scope")
        pm_user_type = markdown_table_value(text, "PM User Type")
        risk_profile = markdown_table_value(text, "Risk Profile")
        evals.append({
            "path": slug(path),
            "case_id": markdown_table_value(text, "Case ID"),
            "scenario": markdown_table_value(text, "Scenario"),
            "platform": platform,
            "product_area": product_area,
            "fixture_scope": fixture_scope,
            "pm_user_type": pm_user_type,
            "risk_profile": risk_profile,
            "latest_status": latest_status,
            "portfolio_metadata_complete": bool(
                platform and product_area and fixture_scope and pm_user_type and risk_profile
            ),
            "has_raw_request": bool(section_body(text, "Raw Request") or section_body(text, "Scenario Set")),
            "scenario_set_round_count": scenario_set_round_count(text),
            "has_required_artifacts": bool(section_body(text, "Required Artifacts")),
            "has_artifact_expectation_matrix": bool(section_body(text, "Artifact Expectation Matrix")),
            "has_rubric_thresholds": bool(section_body(text, "Rubric Thresholds")),
            "has_failure_history": bool(section_body(text, "Failure History")),
            "has_pass_criteria": bool(section_body(text, "Pass Criteria")),
            "validation_terms": validation_terms(text),
            "capability_areas": capability_areas_for(text),
            "context_modes": context_modes_for(text),
            "edge_case_pressures": edge_case_pressures_for(text),
            "artifact_expectations": artifact_expectations_for(text),
        })
    return evals


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(read_text(path))
    except Exception:
        return None


def collect_runs(outputs_dir: Path) -> list[dict[str, Any]]:
    if not outputs_dir.is_dir():
        return []
    runs = []
    for folder in sorted(path for path in outputs_dir.iterdir() if path.is_dir()):
        delivery_report = load_json(folder / "tool-results" / "delivery-check-report.json")
        visual_report = load_json(folder / "visual-review" / "visual-report.json")
        source_preview_report = load_json(folder / "visual-review" / "source-preview-report.json")
        run_log = folder / "run-log.yaml"
        run_log_text = read_text(run_log) if run_log.is_file() else ""
        visual_status_match = re.search(r"^visual_validation:\n(?P<body>.*?)(?:\n[A-Za-z_][A-Za-z0-9_]*:|\Z)", run_log_text, re.MULTILINE | re.DOTALL)
        visual_section = visual_status_match.group("body") if visual_status_match else ""
        visual_required = bool(re.search(r"^\s+required:\s+true\b", visual_section, re.MULTILINE))
        visual_skipped = bool(re.search(r"^\s+status:\s+skipped\b", visual_section, re.MULTILINE))
        stopped_before_generation = bool(
            re.search(r"^\s+stopped_before_generation:\s+true\b", run_log_text, re.MULTILINE)
        )
        ui_not_generated = bool(
            re.search(r"ui_deliverable:\s*[\"']?not generated", run_log_text, re.IGNORECASE)
        )
        ui_intentionally_deferred = bool(
            stopped_before_generation
            or re.search(
                r"(UI awaits confirmation|platform-specific UI awaits confirmation|"
                r"UI delivery remains deferred|not requested|must answer before generation)",
                run_log_text,
                re.IGNORECASE,
            )
        )
        explicit_ui_gap = bool(
            (ui_not_generated and not ui_intentionally_deferred)
            or "No source delta patch" in run_log_text
            or "visual_validation.status=skipped" in run_log_text
        )
        score_values = [
            int(value)
            for value in re.findall(r"^\s+score:\s+([0-9]+)\s*$", run_log_text, re.MULTILINE)
        ]
        runs.append({
            "run_id": folder.name,
            "path": slug(folder),
            "has_prd": (folder / "prd.md").is_file(),
            "has_run_log": run_log.is_file(),
            "has_dev_tasks": (folder / "dev-tasks.yaml").is_file(),
            "has_launch_decision": (folder / "launch-decision.yaml").is_file(),
            "delivery_status": delivery_report.get("status") if delivery_report else "",
            "delivery_status_detail": delivery_report.get("status_detail") if delivery_report else "",
            "visual_status": visual_report.get("status") if visual_report else "",
            "source_preview_status": source_preview_report.get("status") if source_preview_report else "",
            "visual_required": visual_required,
            "visual_skipped": visual_skipped,
            "stopped_before_generation": stopped_before_generation,
            "ui_not_generated": ui_not_generated,
            "ui_intentionally_deferred": ui_intentionally_deferred,
            "explicit_ui_gap": explicit_ui_gap,
            "score_count": len(score_values),
            "score_sum": sum(score_values),
        })
    return runs


def rate(count: int, total: int) -> float:
    return round(count / total, 3) if total else 0.0


def summarize(evals: list[dict[str, Any]], runs: list[dict[str, Any]]) -> dict[str, Any]:
    total_evals = len(evals)
    area_counts = {area: 0 for area in CAPABILITY_AREAS}
    for item in evals:
        for area in item["capability_areas"]:
            area_counts[area] += 1
    scenario_portfolio = build_scenario_portfolio(evals)

    latest_statuses: dict[str, int] = {}
    for item in evals:
        status = (item["latest_status"] or "Unrecorded").strip()
        latest_statuses[status] = latest_statuses.get(status, 0) + 1

    eval_quality = {
        "total": total_evals,
        "with_required_artifacts": sum(1 for item in evals if item["has_required_artifacts"]),
        "with_artifact_expectation_matrix": sum(
            1 for item in evals if item["has_artifact_expectation_matrix"]
        ),
        "expecting_dev_tasks": sum(
            1 for item in evals if "dev_tasks" in item["artifact_expectations"]
        ),
        "expecting_launch_decision": sum(
            1 for item in evals if "launch_decision" in item["artifact_expectations"]
        ),
        "passed_expecting_dev_tasks": sum(
            1
            for item in evals
            if item["latest_status"].strip().lower() == "passed"
            and "dev_tasks" in item["artifact_expectations"]
        ),
        "passed_expecting_launch_decision": sum(
            1
            for item in evals
            if item["latest_status"].strip().lower() == "passed"
            and "launch_decision" in item["artifact_expectations"]
        ),
        "with_rubric_thresholds": sum(1 for item in evals if item["has_rubric_thresholds"]),
        "with_failure_history": sum(1 for item in evals if item["has_failure_history"]),
        "with_validation_terms": sum(1 for item in evals if item["validation_terms"]),
        "scenario_set_rounds": sum(item["scenario_set_round_count"] for item in evals),
    }
    run_quality = {
        "total": len(runs),
        "with_prd": sum(1 for item in runs if item["has_prd"]),
        "with_run_log": sum(1 for item in runs if item["has_run_log"]),
        "with_dev_tasks": sum(1 for item in runs if item["has_dev_tasks"]),
        "with_launch_decision": sum(1 for item in runs if item["has_launch_decision"]),
        "passed_with_dev_tasks": sum(
            1 for item in runs if item["has_dev_tasks"] and item["delivery_status"] == "passed"
        ),
        "passed_with_launch_decision": sum(
            1 for item in runs if item["has_launch_decision"] and item["delivery_status"] == "passed"
        ),
        "with_delivery_report": sum(1 for item in runs if item["delivery_status"]),
        "with_visual_evidence": sum(
            1 for item in runs if item["visual_status"] or item["source_preview_status"]
        ),
        "with_explicit_ui_gap": sum(1 for item in runs if item["explicit_ui_gap"]),
        "with_visual_required_but_missing": sum(
            1
            for item in runs
            if item["visual_required"] and not item["visual_status"] and not item["source_preview_status"]
        ),
        "passed_delivery": sum(1 for item in runs if item["delivery_status"] == "passed"),
    }

    risks: list[dict[str, str]] = []
    if not runs:
        risks.append({
            "severity": "High",
            "area": "runtime_evidence",
            "issue": "No generated output runs were found, so runtime quality cannot be judged from local evidence.",
        })
    if total_evals and latest_statuses.get("Pending", 0) + latest_statuses.get("Unrecorded", 0) == total_evals:
        risks.append({
            "severity": "High",
            "area": "eval_execution",
            "issue": "All eval latest results are pending or unrecorded; the suite describes expectations but lacks recent run evidence.",
        })
    for area, count in area_counts.items():
        if count == 0:
            risks.append({
                "severity": "Medium",
                "area": area,
                "issue": "No eval case appears to cover this capability area.",
            })
    missing_validation = [item["path"] for item in evals if not item["validation_terms"]]
    if missing_validation:
        risks.append({
            "severity": "High",
            "area": "validation",
            "issue": f"{len(missing_validation)} eval case(s) lack executable validation terms.",
        })
    if total_evals and eval_quality["with_rubric_thresholds"] < total_evals:
        risks.append({
            "severity": "Medium",
            "area": "eval_quality",
            "issue": (
                f"{total_evals - eval_quality['with_rubric_thresholds']} eval case(s) lack "
                "explicit rubric thresholds, so pass/fail quality bars are not fully comparable."
            ),
        })
    if total_evals and eval_quality["with_failure_history"] < total_evals:
        risks.append({
            "severity": "Low",
            "area": "eval_quality",
            "issue": (
                f"{total_evals - eval_quality['with_failure_history']} eval case(s) lack "
                "failure history, making regression intent harder to audit."
            ),
        })
    if runs and run_quality["with_delivery_report"] < len(runs):
        risks.append({
            "severity": "Medium",
            "area": "delivery_validation",
            "issue": "Some generated runs do not have delivery-check-report.json evidence.",
        })
    if eval_quality["expecting_dev_tasks"] and run_quality["passed_with_dev_tasks"] == 0:
        risks.append({
            "severity": "High",
            "area": "handoff_evidence",
            "issue": "Some eval cases expect dev-tasks.yaml, but no passed runtime run has engineering handoff evidence.",
        })
    if eval_quality["expecting_launch_decision"] and run_quality["passed_with_launch_decision"] == 0:
        risks.append({
            "severity": "High",
            "area": "launch_evidence",
            "issue": "Some eval cases expect launch-decision.yaml, but no passed runtime run has launch decision evidence.",
        })
    if run_quality["with_visual_required_but_missing"]:
        risks.append({
            "severity": "High",
            "area": "visual_validation",
            "issue": "Some UI runs require visual validation but do not have visual-report.json or source-preview-report.json evidence.",
        })
    elif run_quality["with_explicit_ui_gap"]:
        risks.append({
            "severity": "Medium",
            "area": "source_backed_ui",
            "issue": "At least one run explicitly skipped source-backed UI preview or visual evidence; next iteration should generate and validate a preview.",
        })
    if total_evals and scenario_portfolio["metadata_complete"] < total_evals:
        risks.append({
            "severity": "Medium",
            "area": "portfolio_metadata",
            "issue": (
                f"{total_evals - scenario_portfolio['metadata_complete']} eval case(s) lack "
                "Fixture Scope, PM User Type, or Risk Profile metadata."
            ),
        })
    if scenario_portfolio["passed_evals"] and (
        scenario_portfolio["passed_fixture_scoped"] == scenario_portfolio["passed_evals"]
    ):
        risks.append({
            "severity": "Medium",
            "area": "generalization_evidence",
            "issue": "All currently passing eval evidence is fixture-scoped; add non-fixture passing evidence before claiming broad PM-agent improvement.",
        })
    elif scenario_portfolio["passed_fixture_scoped_rate"] > 0.6:
        risks.append({
            "severity": "Low",
            "area": "generalization_evidence",
            "issue": "Most currently passing eval evidence is fixture-scoped; broaden the next passing runs across generic PM scenarios.",
        })
    for dimension, minimum in MIN_PORTFOLIO_COVERAGE.items():
        count = len(scenario_portfolio[dimension])
        if count < minimum:
            risks.append({
                "severity": "Medium",
                "area": "scenario_portfolio",
                "issue": (
                    f"Eval portfolio covers {count} {dimension.replace('_', ' ')}; "
                    f"target at least {minimum} before treating the suite as broadly representative."
                ),
            })
    if scenario_portfolio["passed_evals"]:
        for dimension, minimum in MIN_PASSED_PORTFOLIO_COVERAGE.items():
            count = len(scenario_portfolio[dimension])
            if count < minimum:
                risks.append({
                    "severity": "Medium",
                    "area": "passed_evidence_portfolio",
                    "issue": (
                        f"Passing eval evidence covers {count} {dimension.replace('passed_', '').replace('_', ' ')}; "
                        f"target at least {minimum} before claiming robust general-agent behavior."
                    ),
                })

    next_actions = prioritize_actions(risks, eval_quality, run_quality, scenario_portfolio)
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repo_root": str(ROOT),
        "eval_quality": {
            **eval_quality,
            "required_artifact_rate": rate(eval_quality["with_required_artifacts"], total_evals),
            "rubric_threshold_rate": rate(eval_quality["with_rubric_thresholds"], total_evals),
            "failure_history_rate": rate(eval_quality["with_failure_history"], total_evals),
            "validation_term_rate": rate(eval_quality["with_validation_terms"], total_evals),
        },
        "run_quality": run_quality,
        "latest_eval_statuses": latest_statuses,
        "capability_area_counts": area_counts,
        "scenario_portfolio": scenario_portfolio,
        "risks": risks,
        "next_actions": next_actions,
        "evals": evals,
        "runs": runs,
    }


def prioritize_actions(
    risks: list[dict[str, str]],
    eval_quality: dict[str, int],
    run_quality: dict[str, int],
    scenario_portfolio: dict[str, Any],
) -> list[str]:
    actions: list[str] = []
    risk_areas = {risk["area"] for risk in risks}
    if "runtime_evidence" in risk_areas:
        actions.append(
            "Run 3 to 5 real product tasks end to end and keep outputs/<run-id>/prd.md, run-log.yaml, delivery-check-report.json, and visual evidence."
        )
    if "eval_execution" in risk_areas:
        actions.append(
            "Execute the existing eval suite manually or through agent runs, then update each Latest Result with run id, status, and failure notes."
        )
    if eval_quality["with_validation_terms"] < eval_quality["total"]:
        actions.append(
            "Add concrete validation commands to every eval pass criteria before treating it as a regression case."
        )
    if "eval_quality" in risk_areas:
        actions.append(
            "Backfill rubric thresholds and failure history on eval cases so pass/fail quality bars and regression intent are auditable."
        )
    if run_quality["total"] and run_quality["with_delivery_report"] < run_quality["total"]:
        actions.append(
            "Backfill run_delivery_checks.py evidence for generated runs or mark the exact skipped-tool reason."
        )
    if "handoff_evidence" in risk_areas:
        actions.append(
            "Run at least one handoff-heavy eval through dev-tasks.yaml generation and delivery checks."
        )
    if "launch_evidence" in risk_areas:
        actions.append(
            "Run at least one launch-readiness eval through launch-decision.yaml generation and delivery checks."
        )
    if run_quality.get("with_visual_required_but_missing"):
        actions.append(
            "Run validate_prototype_visual.py or validate_ui_preview.py for UI runs that marked visual validation as required."
        )
    elif run_quality.get("with_explicit_ui_gap"):
        actions.append(
            "Create one source-backed preview/delta for the latest UI scenario and validate it with validate_ui_preview.py."
        )
    uncovered = [
        risk["area"]
        for risk in risks
        if risk["severity"] == "Medium" and risk["issue"].startswith("No eval case")
    ]
    if uncovered:
        actions.append("Add eval coverage for capability gaps: " + ", ".join(sorted(uncovered)) + ".")
    if "portfolio_metadata" in risk_areas:
        actions.append(
            "Backfill Fixture Scope, PM User Type, and Risk Profile metadata on eval cases so scorecard gaps are machine-visible."
        )
    if "generalization_evidence" in risk_areas:
        actions.append(
            "Make the next passing eval a non-fixture scenario, such as brief-only payment UX, document-backed ops workflow, or screenshot-backed UI reconstruction."
        )
    if "scenario_portfolio" in risk_areas:
        missing_dimensions = [
            dimension.replace("_", " ")
            for dimension, minimum in MIN_PORTFOLIO_COVERAGE.items()
            if len(scenario_portfolio[dimension]) < minimum
        ]
        actions.append(
            "Add or execute evals that broaden scenario portfolio coverage: "
            + ", ".join(missing_dimensions)
            + "."
        )
    if "passed_evidence_portfolio" in risk_areas:
        missing_passed_dimensions = [
            dimension.replace("passed_", "").replace("_", " ")
            for dimension, minimum in MIN_PASSED_PORTFOLIO_COVERAGE.items()
            if len(scenario_portfolio[dimension]) < minimum
        ]
        actions.append(
            "Run and pass additional non-fixture evals that broaden passed-evidence coverage: "
            + ", ".join(missing_passed_dimensions)
            + "."
        )
    actions.append(
        "For every high-severity failure, fix the smallest responsible surface first: contract, skill, workflow, guardrail, tool, then agent role."
    )
    actions.append(
        "Do not count iterations; compare scorecard deltas, validation pass rate, failure severity, and regression coverage after each cycle."
    )
    return actions


def count_line(label: str, counts: dict[str, int]) -> str:
    if not counts:
        return f"- {label}: none recorded"
    values = ", ".join(f"{name} {count}" for name, count in counts.items())
    return f"- {label}: {values}"


def render_markdown(report: dict[str, Any]) -> str:
    portfolio = report["scenario_portfolio"]
    lines = [
        "# PM Copilot Improvement Scorecard",
        "",
        f"generated: {report['generated_at']}",
        f"repo: {report['repo_root']}",
        "",
        "## Eval Quality",
        "",
        f"- evals: {report['eval_quality']['total']}",
        f"- validation term rate: {report['eval_quality']['validation_term_rate']}",
        f"- rubric threshold rate: {report['eval_quality']['rubric_threshold_rate']}",
        f"- failure history rate: {report['eval_quality']['failure_history_rate']}",
        f"- scenario-set rounds: {report['eval_quality']['scenario_set_rounds']}",
        f"- evals with artifact expectation matrix: {report['eval_quality']['with_artifact_expectation_matrix']}",
        f"- evals expecting dev tasks: {report['eval_quality']['expecting_dev_tasks']}",
        f"- evals expecting launch decision: {report['eval_quality']['expecting_launch_decision']}",
        f"- passed evals expecting dev tasks: {report['eval_quality']['passed_expecting_dev_tasks']}",
        f"- passed evals expecting launch decision: {report['eval_quality']['passed_expecting_launch_decision']}",
        "",
        "## Scenario Portfolio",
        "",
        f"- portfolio metadata complete: {portfolio['metadata_complete']}/{report['eval_quality']['total']}",
        f"- fixture-scoped evals: {portfolio['fixture_scoped_evals']}",
        f"- non-fixture evals: {portfolio['non_fixture_evals']}",
        f"- passing evals from fixtures: {portfolio['passed_fixture_scoped']}/{portfolio['passed_evals']}",
        count_line("fixture scopes", portfolio["fixture_scopes"]),
        count_line("platforms", portfolio["platforms"]),
        count_line("context modes", portfolio["context_modes"]),
        count_line("edge-case pressures", portfolio["edge_case_pressures"]),
        count_line("artifact expectations", portfolio["artifact_expectations"]),
        count_line("PM user types", portfolio["pm_user_types"]),
        count_line("risk profiles", portfolio["risk_profiles"]),
        count_line("passed platforms", portfolio["passed_platforms"]),
        count_line("passed context modes", portfolio["passed_context_modes"]),
        count_line("passed edge-case pressures", portfolio["passed_edge_case_pressures"]),
        count_line("passed PM user types", portfolio["passed_pm_user_types"]),
        count_line("passed risk profiles", portfolio["passed_risk_profiles"]),
        "",
        "## Runtime Evidence",
        "",
        f"- runs: {report['run_quality']['total']}",
        f"- runs with delivery report: {report['run_quality']['with_delivery_report']}",
        f"- runs with visual evidence: {report['run_quality']['with_visual_evidence']}",
        f"- runs with explicit UI evidence gap: {report['run_quality']['with_explicit_ui_gap']}",
        f"- runs with dev tasks: {report['run_quality']['with_dev_tasks']}",
        f"- runs with launch decision: {report['run_quality']['with_launch_decision']}",
        f"- passed runs with dev tasks: {report['run_quality']['passed_with_dev_tasks']}",
        f"- passed runs with launch decision: {report['run_quality']['passed_with_launch_decision']}",
        f"- passed delivery reports: {report['run_quality']['passed_delivery']}",
        "",
        "## Capability Coverage",
        "",
    ]
    for area, count in report["capability_area_counts"].items():
        lines.append(f"- {area}: {count}")
    lines.extend(["", "## Risks", ""])
    if report["risks"]:
        for risk in report["risks"]:
            lines.append(f"- {risk['severity']} {risk['area']}: {risk['issue']}")
    else:
        lines.append("- No scorecard risks detected.")
    lines.extend(["", "## Next Actions", ""])
    for index, action in enumerate(report["next_actions"], start=1):
        lines.append(f"{index}. {action}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs-dir", type=Path, default=ROOT / "outputs")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--strict", action="store_true", help="Exit nonzero when high-severity scorecard risks exist.")
    args = parser.parse_args()

    report = summarize(collect_evals(), collect_runs(args.outputs_dir))
    content = (
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.json
        else render_markdown(report)
    )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(content, encoding="utf-8")
        print(f"PM Copilot improvement scorecard written: {args.report}")
    else:
        print(content, end="")

    if args.strict and any(risk["severity"] == "High" for risk in report["risks"]):
        sys.exit(1)


if __name__ == "__main__":
    main()
