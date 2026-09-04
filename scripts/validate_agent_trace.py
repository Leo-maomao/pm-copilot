#!/usr/bin/env python3
"""Validate the compact, PRD-only PM Copilot delivery trace."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

import yaml

from runtime_identity_contract import complete_runtime_identity_failures
from revision_scope import (
    aggregate_visual_evidence_by_requirement,
    requirement_ids,
    requirement_linked_rows,
)


TASK_MODES = {"new_prd", "implemented_feature_prd", "prd_revision", "prd_composition"}
LINEAGE_MODES = {"new_run", "implemented_feature_run", "in_place_revision", "composition_run"}
SPECIALIST_ROLES = {"functional_logic", "frontend_evidence", "source_resolution"}
SPECIALIST_STATUSES = {"passed", "failed", "skipped"}
REVIEW_STATUSES = {"pending", "passed", "failed"}
VALIDATION_STATUSES = {"pending", "passed", "failed"}
FIGURE_KINDS = {"real_capture", "reconstructed", "placeholder"}
VISUAL_DECISIONS = {"real_figure", "required_placeholder", "not_required"}
MODE_TO_LINEAGE = {
    "new_prd": "new_run",
    "implemented_feature_prd": "implemented_feature_run",
    "prd_revision": "in_place_revision",
    "prd_composition": "composition_run",
}


def _load(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        return None, str(error)
    return (payload, None) if isinstance(payload, dict) else (None, "run-log.yaml must be a YAML mapping")


def _text_mapping(text: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError:
        return {}
    return value if isinstance(value, dict) else {}


def scalar_value(text: str, field: str) -> str:
    """Compatibility helper for callers which inspect small YAML fragments."""
    value = _text_mapping(text)

    def walk(item: Any) -> str:
        if isinstance(item, Mapping):
            if field in item and not isinstance(item[field], (Mapping, list)):
                return str(item[field] or "").strip()
            for child in item.values():
                found = walk(child)
                if found:
                    return found
        elif isinstance(item, list):
            for child in item:
                found = walk(child)
                if found:
                    return found
        return ""

    return walk(value)


def section_text(text: str, section: str) -> str:
    value = _text_mapping(text).get(section)
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False) if value is not None else ""


def nested_section_text(text: str, section: str) -> str:
    return section_text(text, section)


def list_field_values(text: str, field: str) -> list[str]:
    value = _text_mapping(text)

    def walk(item: Any) -> list[str] | None:
        if isinstance(item, Mapping):
            candidate = item.get(field)
            if isinstance(candidate, list):
                return [str(part) for part in candidate if str(part).strip()]
            for child in item.values():
                found = walk(child)
                if found is not None:
                    return found
        elif isinstance(item, list):
            for child in item:
                found = walk(child)
                if found is not None:
                    return found
        return None

    return walk(value) or []


def field_has_list_item(text: str, field: str) -> bool:
    return bool(list_field_values(text, field))


def mapping_item_blocks(text: str, first_field: str) -> list[str]:
    value = _text_mapping(text)
    blocks: list[str] = []

    def walk(item: Any) -> None:
        if isinstance(item, Mapping):
            if first_field in item:
                blocks.append(yaml.safe_dump(dict(item), allow_unicode=True, sort_keys=False))
            for child in item.values():
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    return blocks


def _task_mode(trace: Mapping[str, Any], supplied: str | None = None) -> str:
    if supplied:
        return supplied
    strategy = trace.get("agent_strategy")
    return str(strategy.get("task_mode", "")) if isinstance(strategy, Mapping) else ""


def _safe_local_file(root: Path, value: object) -> Path | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    relative = Path(raw)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        return None
    try:
        candidate = (root / relative).resolve()
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    # A resolved path can still be a symlink inside the run folder. The
    # delivery controller rejects symlink trees; keep the validator equally
    # conservative when it checks trace-owned evidence.
    current = root.resolve()
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return None
    return candidate


def _sha256_matches(path: Path, expected: object) -> bool:
    digest = str(expected or "").strip().lower()
    return bool(re.fullmatch(r"[0-9a-f]{64}", digest)) and hashlib.sha256(path.read_bytes()).hexdigest() == digest


def _string_list(value: object, *, allow_empty: bool = True) -> list[str] | None:
    if not isinstance(value, list):
        return None
    values = [str(item).strip() for item in value]
    if any(not item for item in values) or (not allow_empty and not values):
        return None
    if len(values) != len(set(values)):
        return None
    return values


def _nonempty_mapping(value: object) -> bool:
    return isinstance(value, Mapping) and bool(value)


def _source_records(lineage: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources = lineage.get("source_prds")
    return [item for item in sources if isinstance(item, Mapping)] if isinstance(sources, list) else []


def validate_artifact_lineage(
    run_log: Path, text: str | None = None, task_mode: str | None = None,
) -> list[str]:
    """Validate source snapshots and revision baseline without legacy task metadata."""
    trace = _text_mapping(text) if text is not None else (_load(run_log)[0] or {})
    mode = _task_mode(trace, task_mode)
    lineage = trace.get("artifact_lineage")
    if not isinstance(lineage, Mapping):
        # The complete validator enforces this for compact PRD traces. Keep
        # this helper tolerant for callers inspecting a deliberately minimal
        # non-PRD fixture.
        return [] if mode not in TASK_MODES else ["PRD delivery requires an artifact_lineage mapping"]
    lineage_mode = str(lineage.get("mode") or "").strip()
    failures: list[str] = []
    if lineage_mode not in LINEAGE_MODES:
        return [f"invalid artifact_lineage.mode: {lineage_mode or '<empty>'}"]
    expected_mode = MODE_TO_LINEAGE.get(mode)
    if expected_mode and lineage_mode != expected_mode:
        failures.append(f"{mode} requires artifact_lineage.mode: {expected_mode}")

    if lineage_mode == "composition_run":
        sources = _source_records(lineage)
        if not sources:
            failures.append("prd_composition requires one or more immutable source_prds")
        source_ids: set[str] = set()
        source_paths: set[str] = set()
        for index, source in enumerate(sources, 1):
            source_id = str(source.get("source_id") or "").strip()
            if not source_id or source_id in source_ids:
                failures.append(f"source_prds[{index}] requires a unique source_id")
            source_ids.add(source_id)
            raw_snapshot = source.get("snapshot_path") or source.get("source_snapshot_path")
            snapshot_ref = str(raw_snapshot or "").strip()
            if snapshot_ref in source_paths:
                failures.append(f"source_prds[{index}] snapshot_path must be unique")
            source_paths.add(snapshot_ref)
            snapshot = _safe_local_file(run_log.parent, raw_snapshot)
            if not snapshot or not snapshot.is_file():
                failures.append(f"source_prds[{index}] requires a run-local snapshot_path")
                continue
            digest = source.get("sha256") or source.get("source_prd_sha256")
            if not _sha256_matches(snapshot, digest):
                failures.append(f"source_prds[{index}] snapshot SHA-256 does not match")
            selectors = _string_list(
                source.get("selected_scope") or source.get("selected_source_scope"),
                allow_empty=False,
            )
            if selectors is None:
                failures.append(f"source_prds[{index}] requires selected requirement selectors")
            resolution = source.get("scope_resolution") or source.get("selection_resolution")
            if resolution is not None and not isinstance(resolution, list):
                failures.append(f"source_prds[{index}] scope_resolution must be a list when present")
    elif lineage_mode == "in_place_revision":
        ids = _string_list(lineage.get("revised_requirement_ids"), allow_empty=False)
        if ids is None:
            failures.append("in_place_revision requires unique revised_requirement_ids")
            ids = []
        deleted = _string_list(lineage.get("deleted_requirement_ids", []))
        if deleted is None:
            failures.append("in_place_revision deleted_requirement_ids must be a unique list")
        elif not set(deleted).issubset(ids):
            failures.append("in_place_revision deleted_requirement_ids must be a subset of revised_requirement_ids")
        baseline = lineage.get("revision_baseline")
        evidence_ref = str(lineage.get("revision_evidence_path") or "").strip()
        evidence_path = _safe_local_file(run_log.parent, evidence_ref) if evidence_ref else None
        if not _nonempty_mapping(baseline) and evidence_path is None:
            failures.append("in_place_revision requires a non-empty frozen revision_baseline or revision_evidence_path")
        if evidence_ref and (evidence_path is None or not evidence_path.is_file()):
            failures.append("revision_evidence_path must reference a run-local file")
        if evidence_path and evidence_path.suffix.lower() != ".json":
            failures.append("revision_evidence_path must reference a JSON file")
        if evidence_path and evidence_path.is_file():
            try:
                evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                failures.append("revision_evidence_path must reference readable JSON")
            else:
                if not isinstance(evidence, Mapping):
                    failures.append("revision evidence must be a JSON object")
                else:
                    recorded_ids = _string_list(evidence.get("controller_scope_ids"), allow_empty=False)
                    if ids and recorded_ids is not None and set(recorded_ids) != set(ids):
                        failures.append("revision evidence controller_scope_ids must match revised_requirement_ids")
                    baseline_ids = _string_list(evidence.get("baseline_requirement_ids"), allow_empty=False)
                    if baseline_ids is None:
                        failures.append("revision evidence requires baseline_requirement_ids")
                    elif ids and not set(ids).issubset(baseline_ids):
                        failures.append("revised_requirement_ids must be present in revision evidence baseline_requirement_ids")
    return failures


def validate_implemented_feature_evidence_packet(
    run_log: Path, text: str | None = None, task_mode: str | None = None,
) -> list[str]:
    trace = _text_mapping(text) if text is not None else (_load(run_log)[0] or {})
    if _task_mode(trace, task_mode) != "implemented_feature_prd":
        return []
    implemented = trace.get("implemented_feature_prd")
    if not isinstance(implemented, Mapping) or implemented.get("active") is not True:
        return ["implemented_feature_prd requires active: true"]
    packet = implemented.get("evidence_packet")
    if not isinstance(packet, Mapping):
        return ["implemented_feature_prd requires evidence_packet"]
    path = _safe_local_file(run_log.parent, packet.get("path"))
    if not path or not path.is_file() or path.stat().st_size == 0:
        return ["implemented_feature_prd evidence_packet.path must be a non-empty run-local file"]
    if not _sha256_matches(path, packet.get("sha256")):
        return ["implemented_feature_prd evidence_packet SHA-256 does not match"]
    return []


def validate_implemented_feature_prd_integrity(run_log: Path, text: str, task_mode: str) -> list[str]:
    if task_mode != "implemented_feature_prd":
        return []
    return [
        *validate_artifact_lineage(run_log, text, task_mode),
        *validate_implemented_feature_evidence_packet(run_log, text, task_mode),
    ]


def _implemented_feature_runtime_provenance_failures(text: str, version: str) -> list[str]:
    trace = _text_mapping(text)
    identity = trace.get("runtime_identity")
    if not identity:
        return []
    if not isinstance(identity, Mapping):
        return ["runtime_identity must be a mapping"]
    failures = complete_runtime_identity_failures(identity)
    if version and str(identity.get("version") or "") != version:
        failures.append("frozen runtime_identity.version must match pm_copilot_version")
    return failures


def _validate_specialists(trace: Mapping[str, Any], root: Path) -> list[str]:
    specialists = trace.get("specialist_evidence", [])
    if specialists is None:
        return []
    if not isinstance(specialists, list):
        return ["specialist_evidence must be a list"]
    failures: list[str] = []
    ids: set[str] = set()
    for item in specialists:
        if not isinstance(item, Mapping):
            failures.append("specialist evidence item must be a mapping")
            continue
        identifier = str(item.get("id") or "")
        if not identifier or identifier in ids:
            failures.append("specialist evidence requires unique id")
        ids.add(identifier)
        if str(item.get("role") or "") not in SPECIALIST_ROLES:
            failures.append(f"specialist {identifier or '<empty>'} has invalid role")
        status = str(item.get("status") or "")
        if status not in SPECIALIST_STATUSES:
            failures.append(f"specialist {identifier or '<empty>'} has invalid status")
        if not str(item.get("subject") or ""):
            failures.append(f"specialist {identifier or '<empty>'} requires subject")
        if status == "passed" and not str(item.get("path") or ""):
            failures.append(f"passed specialist {identifier or '<empty>'} requires persisted evidence path")
        if status == "passed":
            path = _safe_local_file(root, item.get("path"))
            if not path or not path.is_file():
                failures.append(f"passed specialist {identifier or '<empty>'} evidence path is missing")
        if status == "failed" and not str(item.get("error") or ""):
            failures.append(f"failed specialist {identifier or '<empty>'} requires error")
    return failures


def _validate_pm_arbitration(trace: Mapping[str, Any]) -> list[str]:
    specialists = trace.get("specialist_evidence")
    if not isinstance(specialists, list) or not specialists:
        return []
    arbitration = trace.get("pm_arbitration")
    decisions = arbitration.get("decisions") if isinstance(arbitration, Mapping) else None
    if not isinstance(decisions, list) or not decisions:
        return ["specialist evidence requires a PM Orchestrator arbitration record"]
    if any(not isinstance(item, Mapping) or item.get("owner") != "PM Orchestrator" for item in decisions):
        return ["PM Orchestrator must own every arbitration decision"]
    return []


def _validate_figure_evidence(trace: Mapping[str, Any], root: Path) -> list[str]:
    figures = trace.get("frontend_figure_evidence")
    if not isinstance(figures, list):
        return ["frontend_figure_evidence must be a list"]
    failures: list[str] = []
    for index, item in enumerate(figures, 1):
        if not isinstance(item, Mapping):
            failures.append(f"frontend_figure_evidence[{index}] must be a mapping")
            continue
        requirement_id = str(item.get("requirement_id") or "").strip()
        if not requirement_id:
            failures.append(f"frontend_figure_evidence[{index}] requires requirement_id")
        kind = str(item.get("kind") or "").strip()
        if kind not in FIGURE_KINDS:
            failures.append(f"frontend_figure_evidence[{index}] has invalid kind")
        if kind in {"real_capture", "reconstructed"}:
            path = _safe_local_file(root, item.get("path"))
            if not path or not path.is_file():
                failures.append(f"frontend_figure_evidence[{index}] requires a run-local asset path")
            elif not _sha256_matches(path, item.get("asset_sha256")):
                failures.append(f"frontend_figure_evidence[{index}] asset SHA-256 does not match")
        elif kind == "placeholder":
            if not str(item.get("missing_reason") or "").strip():
                failures.append(f"frontend_figure_evidence[{index}] placeholder requires missing_reason")
            if not str(item.get("replacement_action") or "").strip():
                failures.append(f"frontend_figure_evidence[{index}] placeholder requires replacement_action")
    return failures


def validate_run_log(run_log: Path) -> dict[str, Any]:
    trace, error = _load(run_log)
    if error:
        return {"failures": [error], "warnings": []}
    assert trace is not None
    failures: list[str] = []
    if not str(trace.get("run_id") or "").strip():
        failures.append("run_id is required")
    version = str(trace.get("pm_copilot_version") or "").strip()
    identity = trace.get("runtime_identity")
    if not version:
        failures.append("pm_copilot_version is required")
    failures.extend(complete_runtime_identity_failures(identity))
    if isinstance(identity, Mapping) and version and str(identity.get("version") or "") != version:
        failures.append("runtime_identity.version must match pm_copilot_version")
    strategy = trace.get("agent_strategy")
    task = trace.get("task")
    if not isinstance(task, Mapping) or not str(task.get("raw_request") or ""):
        failures.append("task.raw_request is required")
    if not isinstance(strategy, Mapping):
        failures.append("agent_strategy is required")
        mode = ""
    else:
        mode = str(strategy.get("task_mode") or "")
        if mode not in TASK_MODES:
            failures.append(f"invalid task mode: {mode or '<empty>'}")
        if not str(strategy.get("goal") or ""):
            failures.append("agent_strategy.goal is required")
    confirmation = trace.get("confirmation")
    if not isinstance(confirmation, Mapping):
        failures.append("confirmation is required")
    else:
        if confirmation.get("status") != "confirmed":
            failures.append("confirmation.status must be confirmed")
        if not isinstance(confirmation.get("scope"), list) or not confirmation.get("scope"):
            failures.append("confirmation.scope must be a non-empty list")
        if not str(confirmation.get("confirmed_at") or "").strip():
            failures.append("confirmation.confirmed_at is required")
    quality = trace.get("quality_decision")
    is_complete = isinstance(quality, Mapping) and quality.get("passed") is True
    if is_complete and (not isinstance(confirmation, Mapping) or confirmation.get("status") != "confirmed"):
        failures.append("completed delivery requires confirmed scope")
    failures.extend(validate_artifact_lineage(run_log, task_mode=mode))
    failures.extend(validate_implemented_feature_evidence_packet(run_log, task_mode=mode))
    failures.extend(_validate_specialists(trace, run_log.parent))
    failures.extend(_validate_pm_arbitration(trace))
    failures.extend(_validate_figure_evidence(trace, run_log.parent))
    review = trace.get("review")
    if not isinstance(review, Mapping):
        failures.append("review is required")
    else:
        status = str(review.get("status") or "")
        if status not in REVIEW_STATUSES:
            failures.append("review.status must be pending, passed, or failed")
        findings = review.get("findings", [])
        if not isinstance(findings, list):
            failures.append("review.findings must be a list")
        elif is_complete and any(
            isinstance(item, Mapping) and str(item.get("severity") or "").lower() in {"critical", "high"}
            and str(item.get("disposition") or "").lower() not in {"fixed", "resolved"}
            for item in findings
        ):
            failures.append("completed delivery cannot retain unresolved Critical or High review findings")
    validation = trace.get("validation_results")
    if not isinstance(validation, list):
        failures.append("validation_results must be a list")
    quality = trace.get("quality_decision")
    if not isinstance(quality, Mapping) or not isinstance(quality.get("passed"), bool):
        failures.append("quality_decision.passed must be a boolean")
    final_status = str(trace.get("final_status") or "").strip()
    if not final_status:
        failures.append("final_status is required")
    if is_complete:
        if not isinstance(validation, list) or not validation:
            failures.append("completed delivery requires validation_results")
        elif any(not isinstance(item, Mapping) or item.get("status") != "passed" for item in validation):
            failures.append("completed delivery requires passed validation results")
    return {"failures": failures, "warnings": []}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_folder", type=Path)
    args = parser.parse_args()
    result = validate_run_log(args.run_folder / "run-log.yaml")
    if result["failures"]:
        for failure in result["failures"]:
            print(f"FAIL: {failure}")
        raise SystemExit(1)
    print(f"PM Copilot trace validation passed: {args.run_folder}")


if __name__ == "__main__":
    main()
