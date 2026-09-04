#!/usr/bin/env python3
"""Validate the complete PM Copilot Agent runtime trace in a run folder."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Sequence

import yaml

from agent_event_ledger import validate_file as validate_event_ledger
from implemented_feature_contract import (
    VISUAL_CAPTURE_METHODS,
    VISUAL_CAPTURE_STATUSES,
    VISUAL_RUNTIME_CAPABILITIES,
    VISUAL_RUNTIME_STATUSES,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


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

PRD_TRACE_TASK_MODES = {"prd_delivery", "implemented_feature_prd"}
NEW_LINEAGE_MODES = {"new", "new_run", "replacement_run"}
EXTRACTION_LINEAGE_MODES = {"extract_to_new", "extraction_run"}
IN_PLACE_LINEAGE_MODE = "in_place_revision"
SOURCE_LINEAGE_FIELDS = (
    "source_snapshot_path",
    "source_prd_display_name",
    "source_prd_sha256",
    "selected_source_scope",
    "source_scope_resolution",
)
IMPLEMENTED_EVIDENCE_PACKET_PATH = Path("source-material") / "implemented-feature-evidence.json"
NUMERIC_REQUIREMENT_RANGE_RE = re.compile(
    r"(?<![\d.])(\d+)\.(\d+)\s*(?:-|~|–|—|至|到|to|through|until)\s*(\d+)\.(\d+)(?![\d.])",
    re.IGNORECASE,
)
SOURCE_REQUIREMENT_ID_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:\d+(?:\.\d+)+|[A-Za-z][A-Za-z0-9_]*-\d+)(?![A-Za-z0-9_.-])"
)

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

USER_FACING_SURFACE_RE = re.compile(
    r"(?:页面|画布|面板|弹窗|对话框|节点|工具栏|按钮|图标|控件|列表|菜单|提示|浮层|标签页|连线|media|canvas|panel|dialog|toolbar)",
    re.IGNORECASE,
)


def scalar_value(text: str, field: str) -> str:
    match = re.search(
        rf"^(?P<indent>\s*)(?:-\s+)?{re.escape(field)}:\s*(?P<value>.*?)\s*(?:#.*)?$",
        text,
        re.MULTILINE,
    )
    if not match:
        return ""
    value = match.group("value").strip().strip("\"'")
    # For a mapping inside a sequence, sibling keys begin after ``- ``. Their
    # indentation is not a folded continuation of the first key's scalar.
    indent = len(match.group("indent")) + (2 if match.group(0).lstrip().startswith("-") else 0)
    # YAML folds an indented continuation line into a plain scalar. Preserve
    # that value rather than treating a formatter's line wrap as a different
    # review finding or identifier.
    remainder = text[match.end():].splitlines()
    continuations = []
    for line in remainder:
        if not line.strip():
            continue
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= indent:
            break
        continuations.append(line.strip())
    return " ".join([value, *continuations]).strip()


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
        # PyYAML serializes a sequence value at the same indentation as its
        # mapping key (``field:\n  - item``). That is valid YAML, so retain it
        # while still stopping at a sibling mapping key.
        if current_indent < indent or (
            current_indent == indent and not line.lstrip().startswith("-")
        ):
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
        if current_indent < indent or (
            current_indent == indent and not line.lstrip().startswith("-")
        ):
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
    block_match = re.search(rf"^(?P<indent>\s*){re.escape(field)}:\s*$", text, re.MULTILINE)
    if not block_match:
        return []
    values = []
    current = ""
    item_indent = -1
    field_indent = len(block_match.group("indent"))
    for line in text[block_match.end():].splitlines():
        if not line.strip():
            continue
        line_indent = len(line) - len(line.lstrip())
        item = re.match(r"^(?P<indent>\s*)-\s+(?P<value>.+?)\s*$", line)
        if item and line_indent >= field_indent:
            if current:
                values.append(current)
            current = item.group("value").strip().strip("\"'")
            item_indent = len(item.group("indent"))
            continue
        if current and line_indent > item_indent:
            current = f"{current} {line.strip()}"
            continue
        if line_indent <= field_indent:
            break
    if current:
        values.append(current)
    return values


def mapping_item_blocks(text: str, first_field: str) -> list[str]:
    starts = list(
        re.finditer(rf"^[ \t]*-\s+{re.escape(first_field)}:\s*.*$", text, re.MULTILINE)
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


def _load_trace_mapping(text: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse the trace once for provenance checks that cannot trust regexes."""
    try:
        trace = yaml.safe_load(text)
    except yaml.YAMLError:
        return None, "run-log.yaml must be valid YAML to validate artifact lineage"
    if not isinstance(trace, dict):
        return None, "run-log.yaml must contain a YAML mapping to validate artifact lineage"
    return trace, None


def _mapping_value(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    value = mapping.get(key)
    return value if isinstance(value, dict) else {}


def _trace_task_mode(trace: dict[str, Any]) -> str:
    value = _mapping_value(trace, "agent_strategy").get("task_mode")
    return value.strip() if isinstance(value, str) else ""


def _requires_lineage_from_text(text: str) -> bool:
    """Keep non-PRD legacy traces compatible while rejecting malformed PRD logs."""
    return bool(
        re.search(
            r"^\s*task_mode:\s*(?:prd_delivery|implemented_feature_prd)\s*(?:#.*)?$",
            text,
            re.MULTILINE,
        )
        or re.search(r"^artifact_lineage:\s*$", text, re.MULTILINE)
    )


def _nonempty_string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return None
    return [item.strip() for item in value]


def _unique_string_list(value: Any, *, allow_empty: bool = True) -> list[str] | None:
    """Return a deterministic string list without silently accepting aliases."""
    values = _nonempty_string_list(value)
    if values is None or (not allow_empty and not values):
        return None
    if len(values) != len(set(values)):
        return None
    return values


def _normalise_source_selector(value: str) -> str:
    """Normalize a human selector without treating unrelated request text as proof."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^\w\u3400-\u9fff]+", "", normalized)


def _snapshot_requirement_ids(source_text: str) -> list[str]:
    """Read stable requirement identifiers from source headings and table rows."""
    candidates: list[str] = []
    for line in source_text.splitlines():
        if not re.match(r"\s*(?:#{1,6}\s+|\|)", line):
            continue
        candidates.extend(SOURCE_REQUIREMENT_ID_RE.findall(line))
    return list(dict.fromkeys(candidates))


def _snapshot_headings(source_text: str) -> list[tuple[str, str]]:
    """Return both full and identifier-free headings for verified source lookup."""
    headings: list[tuple[str, str]] = []
    for raw_heading in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*$", source_text):
        heading = raw_heading.strip()
        without_identifier = re.sub(
            r"^(?:(?:需求|requirement)\s*)?(?:\d+(?:\.\d+)+|[A-Za-z][A-Za-z0-9_-]*-\d+)[.、:：\-\s]*",
            "",
            heading,
            flags=re.IGNORECASE,
        ).strip()
        for candidate in (heading, without_identifier):
            normalized = _normalise_source_selector(candidate)
            if normalized:
                headings.append((normalized, heading))
    return headings


def _snapshot_text_spans(source_text: str) -> list[str]:
    """Collect source prose fragments usable as a uniquely cited extraction scope."""
    spans: list[str] = []
    for line in source_text.splitlines():
        if re.match(r"\s*#{1,6}\s+", line):
            continue
        cleaned = re.sub(r"^\s*(?:[-*+]\s+|\|\s*)", "", line).strip(" |\t")
        for fragment in re.split(r"[。！？!?；;]+", cleaned):
            normalized = _normalise_source_selector(fragment)
            if normalized:
                spans.append(normalized)
    return spans


def _is_substantive_source_selector(selector: str) -> bool:
    """Do not accept generic fragments as a durable source boundary."""
    cjk_count = len(re.findall(r"[\u3400-\u9fff]", selector))
    latin_words = re.findall(r"[a-z0-9]+", selector, flags=re.IGNORECASE)
    return cjk_count >= 3 or len("".join(latin_words)) >= 8 or len(latin_words) >= 2


def _resolve_extraction_scope(
    source_text: str, selected_scope: Sequence[str],
) -> tuple[list[dict[str, object]], str | None]:
    """Independently resolve each persisted selector against immutable source bytes.

    The controller may already have resolved the scope before delivery, but a
    final validator must repeat that work from the staged snapshot.  A selector
    is valid only when it names existing IDs, one heading, or one substantive
    source fragment; unknown and ambiguous selectors are delivery blockers.
    """
    source_ids = set(_snapshot_requirement_ids(source_text))
    headings = _snapshot_headings(source_text)
    text_spans = _snapshot_text_spans(source_text)
    resolutions: list[dict[str, object]] = []

    for raw_selector in selected_scope:
        selector = str(raw_selector).strip()
        normalized = _normalise_source_selector(selector)
        if not normalized:
            return [], "contains an empty selector"

        ranges = list(NUMERIC_REQUIREMENT_RANGE_RE.finditer(selector))
        if ranges:
            for match in ranges:
                start_major, start_minor, end_major, end_minor = map(int, match.groups())
                if start_major != end_major or start_minor > end_minor:
                    return [], f"has an invalid requirement-ID range: {selector}"
                expected = [f"{start_major}.{minor}" for minor in range(start_minor, end_minor + 1)]
                missing = [item for item in expected if item not in source_ids]
                if missing:
                    return [], f"references IDs absent from the source snapshot: {', '.join(missing)}"
                resolutions.append({
                    "selector": selector,
                    "kind": "requirement_id_range",
                    "matches": expected,
                })
            continue

        selected_ids = list(dict.fromkeys(SOURCE_REQUIREMENT_ID_RE.findall(selector)))
        if selected_ids:
            unknown = [item for item in selected_ids if item not in source_ids]
            if unknown:
                return [], f"references IDs absent from the source snapshot: {', '.join(unknown)}"
            resolutions.append({
                "selector": selector,
                "kind": "requirement_id",
                "matches": selected_ids,
            })
            continue

        matched_headings = {
            original for candidate, original in headings if candidate and candidate in normalized
        }
        if len(matched_headings) == 1:
            resolutions.append({
                "selector": selector,
                "kind": "heading",
                "matches": sorted(matched_headings),
            })
            continue
        if len(matched_headings) > 1:
            return [], f"matches multiple source headings: {selector}"

        if _is_substantive_source_selector(selector):
            matched_spans = [
                span for span in text_spans
                if normalized in span or (len(span) >= 8 and span in normalized)
            ]
            if len(matched_spans) == 1:
                resolutions.append({
                    "selector": selector,
                    "kind": "source_text",
                    "matches": sorted(set(matched_spans)),
                })
                continue
            if len(matched_spans) > 1:
                return [], f"matches multiple source text locations: {selector}"

        return [], f"cannot be uniquely resolved against the source snapshot: {selector}"
    return resolutions, None


def _validate_extraction_resolution_evidence(
    snapshot: Path,
    selected_scope: list[str],
    evidence: Any,
    failures: list[str],
) -> None:
    """Require trace resolution evidence to agree with a fresh snapshot lookup."""
    try:
        expected, problem = _resolve_extraction_scope(
            snapshot.read_text(encoding="utf-8"), selected_scope,
        )
    except (OSError, UnicodeError):
        failures.append("extraction source_snapshot_path must remain readable during scope validation")
        return
    if problem:
        failures.append(f"extraction selected_source_scope {problem}")
        return
    if not isinstance(evidence, list) or len(evidence) != len(expected):
        failures.append(
            "extraction lineage requires source_scope_resolution for every selected_source_scope item"
        )
        return
    for index, (actual, expected_item) in enumerate(zip(evidence, expected), start=1):
        if not isinstance(actual, dict):
            failures.append(f"extraction source_scope_resolution item {index} must be a mapping")
            continue
        actual_selector = actual.get("selector")
        actual_kind = actual.get("kind")
        actual_matches = _unique_string_list(actual.get("matches"), allow_empty=False)
        if (
            actual_selector != expected_item["selector"]
            or actual_kind != expected_item["kind"]
            or actual_matches != expected_item["matches"]
        ):
            failures.append(
                "extraction source_scope_resolution must exactly match the immutable source snapshot"
            )


def _current_prd_requirement_ids(run_log: Path) -> set[str]:
    """Read the final staged/canonical requirement IDs without trusting trace prose."""
    prd_path = run_log.parent / "prd.md"
    if not prd_path.is_file():
        return set()
    try:
        return set(_snapshot_requirement_ids(prd_path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError):
        return set()


def _safe_run_file(
    run_log: Path,
    value: Any,
    field: str,
    failures: list[str],
) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        failures.append(f"artifact_lineage.{field} must name a non-empty relative file path")
        return None
    relative = Path(value)
    if relative.is_absolute():
        failures.append(f"artifact_lineage.{field} must stay inside the run folder")
        return None
    try:
        candidate = (run_log.parent / relative).resolve()
        candidate.relative_to(run_log.parent.resolve())
    except ValueError:
        failures.append(f"artifact_lineage.{field} must stay inside the run folder")
        return None
    if not candidate.is_file():
        failures.append(f"artifact_lineage.{field} must reference an existing file inside the run folder")
        return None
    return candidate


def _value_is_present(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return value is not None


def _source_provenance_is_present(lineage: dict[str, Any]) -> bool:
    if any(_value_is_present(lineage.get(field)) for field in SOURCE_LINEAGE_FIELDS):
        return True
    historical = lineage.get("historical_artifacts")
    if not isinstance(historical, list):
        return False
    return any(
        isinstance(item, dict)
        and item.get("role") == "user_provided_input"
        and item.get("excluded_from_current_facts") is False
        for item in historical
    )


def _validate_revision_evidence(
    evidence_path: Path,
    revised_requirement_ids: list[str],
    deleted_requirement_ids: list[str],
    final_requirement_ids: set[str],
    failures: list[str],
) -> None:
    """Bind revision scope, baseline, and explicit deletions to final PRD bytes."""
    if evidence_path.suffix.lower() != ".json":
        failures.append("in_place_revision revision evidence must be JSON")
        return
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        failures.append("in_place_revision revision evidence JSON must be readable")
        return
    if not isinstance(evidence, dict) or evidence.get("mode") != IN_PLACE_LINEAGE_MODE:
        failures.append("in_place_revision revision evidence must record mode: in_place_revision")
        return
    recorded_scope = _unique_string_list(evidence.get("controller_scope_ids"), allow_empty=False)
    if recorded_scope is None or set(recorded_scope) != set(revised_requirement_ids):
        failures.append(
            "in_place_revision revision evidence controller_scope_ids must match revised_requirement_ids"
        )
    recorded_deleted = _unique_string_list(evidence.get("deleted_requirement_ids"))
    if recorded_deleted is None or set(recorded_deleted) != set(deleted_requirement_ids):
        failures.append(
            "in_place_revision revision evidence deleted_requirement_ids must match artifact_lineage"
        )
    baseline_ids = _unique_string_list(evidence.get("baseline_requirement_ids"), allow_empty=False)
    if baseline_ids is None:
        failures.append("in_place_revision revision evidence requires baseline_requirement_ids")
        return
    baseline_set = set(baseline_ids)
    revised_set = set(revised_requirement_ids)
    deleted_set = set(deleted_requirement_ids)
    if not revised_set <= baseline_set:
        failures.append(
            "in_place_revision revised_requirement_ids must be present in revision evidence baseline_requirement_ids"
        )
    if not deleted_set <= revised_set:
        failures.append("in_place_revision deleted_requirement_ids must be a subset of revised_requirement_ids")
    if not deleted_set <= baseline_set:
        failures.append("in_place_revision deleted_requirement_ids must be present in the revision baseline")
    if deleted_set & final_requirement_ids:
        failures.append("in_place_revision deleted_requirement_ids must be absent from the final PRD")
    remaining_ids = revised_set - deleted_set
    missing_remaining = sorted(remaining_ids - final_requirement_ids)
    if missing_remaining:
        failures.append(
            "in_place_revision non-deleted revised_requirement_ids must exist in the final PRD: "
            + ", ".join(missing_remaining)
        )
    # Scope contracts were introduced after the original evidence format. Keep
    # historical completed runs readable, but when a controller records one it
    # must prove that the matching local validator passed before promotion.
    scope_manifest = evidence.get("scope_manifest")
    if scope_manifest is None:
        return
    if not isinstance(scope_manifest, dict) or scope_manifest.get("schema_version") != 1:
        failures.append("in_place_revision scope_manifest must use controller schema_version 1")
        return
    manifest_ids = _unique_string_list(scope_manifest.get("requirement_ids"), allow_empty=False)
    if manifest_ids is None or set(manifest_ids) != revised_set:
        failures.append("in_place_revision scope_manifest requirement_ids must match revised_requirement_ids")
    baseline = scope_manifest.get("baseline")
    if not isinstance(baseline, dict) or not isinstance(baseline.get("requirement_sections"), dict):
        failures.append("in_place_revision scope_manifest must retain baseline requirement section evidence")
    validation = evidence.get("scope_validation")
    if not isinstance(validation, dict) or validation.get("status") != "passed":
        failures.append("in_place_revision scope_validation must record a passed controller validation")
        return
    report_path = validation.get("report_path")
    if not isinstance(report_path, str) or not report_path.startswith("tool-results/"):
        failures.append("in_place_revision scope_validation must reference a tool-results report")
        return
    root = evidence_path.parent.resolve()
    try:
        report = (root / report_path).resolve()
        relative = report.relative_to(root)
    except ValueError:
        failures.append("in_place_revision scope_validation report must stay inside the run folder")
        return
    if not relative.parts or relative.parts[0] != "tool-results":
        failures.append("in_place_revision scope_validation must reference a tool-results report")
        return
    if not report.is_file():
        failures.append("in_place_revision scope_validation report must exist in the run folder")
        return
    try:
        report_value = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        failures.append("in_place_revision scope_validation report must be readable JSON")
        return
    if not isinstance(report_value, dict) or report_value.get("status") != "passed":
        failures.append("in_place_revision scope_validation report must record status: passed")
        return
    actual_manifest_hash = hashlib.sha256(
        json.dumps(scope_manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    recorded_manifest_hash = validation.get("manifest_sha256")
    if not isinstance(recorded_manifest_hash, str) or recorded_manifest_hash != actual_manifest_hash:
        failures.append("in_place_revision scope_validation must match the retained scope manifest")
    if report_value.get("manifest_sha256") != actual_manifest_hash:
        failures.append("in_place_revision scope_validation report must match the retained scope manifest")


def validate_artifact_lineage(
    run_log: Path,
    text: str | None = None,
    task_mode: str | None = None,
) -> list[str]:
    """Validate the durable source relationship of a PRD delivery trace.

    A PRD can be created from scratch, revised in place, or extracted from a
    prior document. Those paths have different proof requirements, and a
    model-written status line is not sufficient evidence for any of them.
    """
    text = text if text is not None else run_log.read_text(encoding="utf-8")
    trace, parse_failure = _load_trace_mapping(text)
    if trace is None:
        return [parse_failure] if parse_failure and _requires_lineage_from_text(text) else []

    trace_task_mode = _trace_task_mode(trace)
    effective_task_mode = trace_task_mode or (task_mode or "")
    lineage_value = trace.get("artifact_lineage")
    has_lineage = isinstance(lineage_value, dict)
    if effective_task_mode not in PRD_TRACE_TASK_MODES and not has_lineage:
        return []

    failures: list[str] = []
    if effective_task_mode not in PRD_TRACE_TASK_MODES:
        failures.append("artifact_lineage is only valid for a PRD delivery task_mode")
        return failures
    if task_mode and trace_task_mode and task_mode != trace_task_mode:
        failures.append("artifact_lineage task_mode does not match agent_strategy.task_mode")
    if not has_lineage:
        return [*failures, "PRD delivery requires an artifact_lineage mapping"]
    lineage = lineage_value

    resume = _mapping_value(trace, "resume_checkpoint")
    resume_task_mode = resume.get("task_mode")
    if not isinstance(resume_task_mode, str) or resume_task_mode.strip() != effective_task_mode:
        failures.append(
            "artifact_lineage requires resume_checkpoint.task_mode to match agent_strategy.task_mode"
        )

    mode = lineage.get("mode")
    if not isinstance(mode, str) or not mode.strip():
        return [*failures, "artifact_lineage.mode must identify new, in-place, or extraction delivery"]
    mode = mode.strip()

    if mode in NEW_LINEAGE_MODES:
        if lineage.get("output_folder_reset") is not True:
            failures.append("new PRD lineage requires output_folder_reset: true")
        if any(
            _value_is_present(lineage.get(field))
            for field in (
                "target_prd_path",
                "target_html_path",
                "revision_evidence_path",
                "revised_requirement_ids",
                "deleted_requirement_ids",
            )
        ):
            failures.append("new PRD lineage must not claim in-place revision targets or revision evidence")
        # Delivery semantics come from durable source provenance, not a word in
        # a request such as "extract", which may describe ordinary drafting.
        if _source_provenance_is_present(lineage):
            failures.append(
                "source-backed extraction must use artifact_lineage.mode: extraction_run, not new_run"
            )
        return failures

    if mode == IN_PLACE_LINEAGE_MODE:
        if lineage.get("output_folder_reset") is not False:
            failures.append("in_place_revision requires output_folder_reset: false")
        _safe_run_file(run_log, lineage.get("target_prd_path"), "target_prd_path", failures)
        _safe_run_file(run_log, lineage.get("target_html_path"), "target_html_path", failures)
        evidence = _safe_run_file(
            run_log,
            lineage.get("revision_evidence_path"),
            "revision_evidence_path",
            failures,
        )
        revised_requirement_ids = _unique_string_list(
            lineage.get("revised_requirement_ids"), allow_empty=False,
        )
        if not revised_requirement_ids:
            failures.append("in_place_revision requires non-empty revised_requirement_ids")
            revised_requirement_ids = []
        deleted_requirement_ids = _unique_string_list(lineage.get("deleted_requirement_ids"))
        if deleted_requirement_ids is None:
            failures.append("in_place_revision requires deleted_requirement_ids as a unique list")
            deleted_requirement_ids = []
        elif not set(deleted_requirement_ids) <= set(revised_requirement_ids):
            failures.append("in_place_revision deleted_requirement_ids must be a subset of revised_requirement_ids")
        if _source_provenance_is_present(lineage):
            failures.append("in_place_revision must not mix extraction source provenance into its lineage")
        historical = lineage.get("historical_artifacts")
        if not isinstance(historical, list) or not any(
            isinstance(item, dict)
            and item.get("path") == lineage.get("target_prd_path")
            and item.get("role") == "comparison_only"
            and item.get("excluded_from_current_facts") is True
            for item in historical
        ):
            failures.append(
                "in_place_revision requires historical_artifacts comparison evidence for target_prd_path"
            )
        if evidence is not None and revised_requirement_ids:
            _validate_revision_evidence(
                evidence,
                revised_requirement_ids,
                deleted_requirement_ids,
                _current_prd_requirement_ids(run_log),
                failures,
            )
        return failures

    if mode in EXTRACTION_LINEAGE_MODES:
        if lineage.get("output_folder_reset") is not True:
            failures.append("extraction lineage requires output_folder_reset: true")
        snapshot = _safe_run_file(
            run_log,
            lineage.get("source_snapshot_path"),
            "source_snapshot_path",
            failures,
        )
        display_name = lineage.get("source_prd_display_name")
        if not isinstance(display_name, str) or not display_name.strip():
            failures.append("extraction lineage requires source_prd_display_name")
        declared_digest = lineage.get("source_prd_sha256")
        if not isinstance(declared_digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", declared_digest):
            failures.append("extraction lineage requires a valid source_prd_sha256")
        elif snapshot is not None:
            protected_artifacts = {
                run_log.resolve(),
                (run_log.parent / "prd.md").resolve(),
                (run_log.parent / "prd.html").resolve(),
            }
            if snapshot in protected_artifacts:
                failures.append(
                    "extraction source_snapshot_path must be distinct from current delivery artifacts"
                )
            try:
                actual_digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
            except OSError:
                failures.append("extraction source_snapshot_path must remain readable during validation")
            else:
                if actual_digest.lower() != declared_digest.lower():
                    failures.append("extraction source_prd_sha256 does not match the source snapshot")
        selected_scope = _unique_string_list(lineage.get("selected_source_scope"), allow_empty=False)
        if not selected_scope:
            failures.append("extraction lineage requires a non-empty selected_source_scope list")
        elif snapshot is not None:
            _validate_extraction_resolution_evidence(
                snapshot,
                selected_scope,
                lineage.get("source_scope_resolution"),
                failures,
            )
        if any(
            _value_is_present(lineage.get(field))
            for field in (
                "target_prd_path",
                "target_html_path",
                "revision_evidence_path",
                "revised_requirement_ids",
                "deleted_requirement_ids",
            )
        ):
            failures.append("extraction lineage must not claim in-place revision targets or revision evidence")
        context = _mapping_value(trace, "context")
        if context.get("source_mode") != "document-backed":
            failures.append("extraction lineage requires context.source_mode: document-backed")
        product_documents = _nonempty_string_list(context.get("product_documents_loaded"))
        source_path = lineage.get("source_snapshot_path")
        if product_documents is None or source_path not in product_documents:
            failures.append(
                "extraction lineage requires context.product_documents_loaded to include source_snapshot_path"
            )
        historical = lineage.get("historical_artifacts")
        if not isinstance(historical, list) or not any(
            isinstance(item, dict)
            and item.get("path") == source_path
            and item.get("role") == "user_provided_input"
            and item.get("excluded_from_current_facts") is False
            for item in historical
        ):
            failures.append(
                "extraction lineage requires historical_artifacts user_provided_input evidence for source_snapshot_path"
            )
        return failures

    failures.append(
        "artifact_lineage.mode must be one of: new_run, in_place_revision, extraction_run"
    )
    return failures


def _safe_trace_file(
    run_log: Path,
    value: Any,
    field: str,
    failures: list[str],
) -> Path | None:
    """Resolve a trace-owned file while rejecting path traversal and symlink escapes."""
    if not isinstance(value, str) or not value.strip():
        failures.append(f"{field} must name a non-empty relative file path")
        return None
    relative = Path(value)
    if relative.is_absolute():
        failures.append(f"{field} must stay inside the run folder")
        return None
    try:
        candidate = (run_log.parent / relative).resolve()
        candidate.relative_to(run_log.parent.resolve())
    except ValueError:
        failures.append(f"{field} must stay inside the run folder")
        return None
    if not candidate.is_file():
        failures.append(f"{field} must reference an existing file inside the run folder")
        return None
    return candidate


def _packet_result_refs(value: Any, failures: list[str]) -> list[str]:
    """Read result references from the immutable JSON packet, not trace prose."""
    refs: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key == "result_ref":
                    if not isinstance(child, str) or not child.strip():
                        failures.append("implemented-feature evidence packet contains an empty result_ref")
                    else:
                        refs.append(child.strip())
                else:
                    visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return list(dict.fromkeys(refs))


def validate_implemented_feature_evidence_packet(
    run_log: Path,
    text: str | None = None,
    task_mode: str | None = None,
) -> list[str]:
    """Verify portable implemented-feature evidence against the current workspace.

    Evidence packets are controller-owned, immutable inputs.  The final trace
    cannot merely repeat a path and hash: it must point to the canonical packet,
    match its exact bytes, retain every packet-declared local result, and expose
    the same behavior evidence that the packet contains.
    """
    text = text if text is not None else run_log.read_text(encoding="utf-8")
    trace, parse_failure = _load_trace_mapping(text)
    if trace is None:
        return [parse_failure] if parse_failure and _requires_lineage_from_text(text) else []
    effective_task_mode = _trace_task_mode(trace) or (task_mode or "")
    if effective_task_mode != "implemented_feature_prd":
        return []

    failures: list[str] = []
    implemented = trace.get("implemented_feature_prd")
    if not isinstance(implemented, dict):
        return ["implemented_feature_prd task_mode requires an implemented_feature_prd evidence mapping"]
    evidence_packet = implemented.get("evidence_packet")
    if not isinstance(evidence_packet, dict):
        return ["implemented_feature_prd requires an evidence_packet mapping"]

    expected_path = IMPLEMENTED_EVIDENCE_PACKET_PATH.as_posix()
    packet_path = evidence_packet.get("path")
    if packet_path != expected_path:
        failures.append(
            "implemented_feature_prd evidence_packet.path must be " + expected_path
        )
    packet = _safe_trace_file(
        run_log,
        packet_path,
        "implemented_feature_prd.evidence_packet.path",
        failures,
    )
    declared_digest = evidence_packet.get("sha256")
    if not isinstance(declared_digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", declared_digest):
        failures.append("implemented_feature_prd evidence_packet.sha256 must be a valid SHA-256")
    elif packet is not None:
        try:
            actual_digest = hashlib.sha256(packet.read_bytes()).hexdigest()
        except OSError:
            failures.append("implemented_feature_prd evidence_packet must remain readable during validation")
        else:
            if actual_digest.lower() != declared_digest.lower():
                failures.append(
                    "implemented_feature_prd evidence_packet.sha256 does not match the referenced packet"
                )

    packet_payload: dict[str, Any] | None = None
    if packet is not None:
        try:
            loaded_packet = json.loads(packet.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            failures.append("implemented_feature_prd evidence_packet must contain readable JSON")
        else:
            if not isinstance(loaded_packet, dict):
                failures.append("implemented_feature_prd evidence_packet JSON must be an object")
            else:
                packet_payload = loaded_packet

    imported_refs = _unique_string_list(evidence_packet.get("imported_result_refs"))
    if imported_refs is None:
        failures.append("implemented_feature_prd evidence_packet.imported_result_refs must be a unique list")
        imported_refs = []

    if packet_payload is None:
        return failures
    for key, packet_value in packet_payload.items():
        if implemented.get(key) != packet_value:
            failures.append(
                "implemented_feature_prd evidence must match the immutable evidence_packet contents"
            )
            break

    packet_refs = _packet_result_refs(packet_payload, failures)
    if imported_refs != packet_refs:
        failures.append(
            "implemented_feature_prd evidence_packet.imported_result_refs must match packet result_ref values"
        )
    root = run_log.parent.resolve()
    for result_ref in imported_refs:
        relative = Path(result_ref)
        if relative.is_absolute():
            failures.append("implemented-feature evidence result_ref must stay inside the run folder")
            continue
        try:
            candidate = (root / relative).resolve()
            portable = candidate.relative_to(root)
        except ValueError:
            failures.append("implemented-feature evidence result_ref must stay inside the run folder")
            continue
        if portable.parts[:2] != ("tool-results", "implemented-evidence"):
            failures.append(
                "implemented-feature evidence result_ref must be under tool-results/implemented-evidence/"
            )
            continue
        if not candidate.is_file() or candidate.stat().st_size <= 0:
            failures.append(
                "implemented-feature evidence result_ref must reference a non-empty staged file"
            )
    return failures


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
    if discovered_capabilities != set(VISUAL_RUNTIME_CAPABILITIES):
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
    if not set(VISUAL_CAPTURE_METHODS).issubset(methods):
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
    failures.extend(validate_artifact_lineage(run_log, text, task_mode))

    current_run = run_log.parent.name
    task_body = section_text(text, "task")
    context_body = section_text(text, "context")
    if current_run and current_run in scalar_value(task_body, "brief_path"):
        failures.append("rewritten PRDs must use a new run folder instead of the source artifact folder")
    if current_run and current_run in context_body:
        failures.append("current run artifacts must not be loaded as product context")

    lineage = section_text(text, "artifact_lineage")
    lineage_mode = scalar_value(lineage, "mode")

    prd_path = run_log.parent / "prd.md"
    requirement_ids = set()
    requirement_bodies: dict[str, str] = {}
    if prd_path.is_file():
        prd_text = prd_path.read_text(encoding="utf-8")
        requirement_ids = set(re.findall(r"(?m)^\|\s*(\d+\.\d+)\s*\|", prd_text))
        for requirement_id in requirement_ids:
            match = re.search(
                rf"(?ms)^###\s+{re.escape(requirement_id)}(?:\s|$).*?\n(?P<body>.*?)(?=^###\s+|^##\s+|\Z)",
                prd_text,
            )
            if match:
                requirement_bodies[requirement_id] = match.group("body")
    covered_requirement_ids = requirement_ids
    if lineage_mode == IN_PLACE_LINEAGE_MODE:
        revised_ids = set(list_field_values(lineage, "revised_requirement_ids"))
        if not revised_ids:
            failures.append("in_place_revision requires artifact_lineage.revised_requirement_ids")
        elif not revised_ids <= requirement_ids:
            failures.append("revised_requirement_ids must reference existing PRD requirements")
        else:
            covered_requirement_ids = revised_ids
    coverage = section_text(text, "requirement_coverage_review")
    coverage_blocks = mapping_item_blocks(coverage, "requirement_id")
    coverage_ids = [scalar_value(block, "requirement_id") for block in coverage_blocks]
    if covered_requirement_ids and set(coverage_ids) != covered_requirement_ids:
        failures.append("requirement_coverage_review must contain exactly one decision for every PRD requirement")
    if len(coverage_ids) != len(set(coverage_ids)):
        failures.append("requirement_coverage_review requirement_id values must be unique")

    visual_coverage = mapping_item_blocks(
        nested_section_text(implemented, "screenshots_and_placeholders"),
        "target_ref",
    )
    visual_targets = [scalar_value(block, "target_ref") for block in visual_coverage]
    if covered_requirement_ids and set(visual_targets) != covered_requirement_ids:
        failures.append(
            "implemented_feature_prd requires exactly one screenshots_and_placeholders decision per requirement"
        )
    if len(visual_targets) != len(set(visual_targets)):
        failures.append("screenshots_and_placeholders target_ref values must be unique")
    for block in visual_coverage:
        target_ref = scalar_value(block, "target_ref") or "<empty>"
        decision = scalar_value(block, "coverage_decision")
        surface = scalar_value(block, "surface")
        rationale = scalar_value(block, "rationale")
        if decision not in {"real_figure", "required_placeholder", "not_required"}:
            failures.append(f"visual coverage {target_ref} has invalid coverage_decision")
        if not rationale:
            failures.append(f"visual coverage {target_ref} requires rationale")
        if surface and decision == "not_required":
            failures.append(
                f"visual coverage {target_ref} cannot omit a figure for a named user-facing surface"
            )
        if decision == "not_required" and USER_FACING_SURFACE_RE.search(
            requirement_bodies.get(target_ref, "")
        ):
            failures.append(
                f"visual coverage {target_ref} cannot omit a figure for a user-facing requirement"
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

    if task_mode == "implemented_feature_prd":
        reported_version = scalar_value(text, "pm_copilot_version")
        if reported_version != RUNTIME_VERSION:
            failures.append(
                "implemented-feature PRD pm_copilot_version must equal the active runtime VERSION "
                f"{RUNTIME_VERSION}, got {reported_version or '<empty>'}"
            )

    if task_mode == "implemented_feature_prd":
        failures.extend(validate_implemented_feature_prd_integrity(run_log, text, task_mode))
        failures.extend(validate_implemented_feature_evidence_packet(run_log, text, task_mode))
    else:
        failures.extend(validate_artifact_lineage(run_log, text, task_mode))

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
    # YAML permits quoted scalar IDs.  Normalize the scalar the same way the
    # action-reference parser does, otherwise `id: "X"` is collected as
    # `"X"` while `source_blocker_ids: ["X"]` becomes `X`.
    blocker_ids = {
        value.strip().strip("\"'")
        for value in re.findall(r"^\s+-\s+id:\s*([^\s#]+)", readiness_body, re.MULTILINE)
        if value.strip().strip("\"'")
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
