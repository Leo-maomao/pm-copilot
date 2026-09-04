#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the production, user-driven PM Copilot clarification gate.

This entry point deliberately does not use ``evals/scenario-confirmations.json``.
It persists a resumable conversation, asks the local Agent for only the next
branch-changing questions, and refuses downstream generation until the user
has explicitly confirmed the clarified scope.
"""

from __future__ import annotations

import argparse
import datetime as dt
import errno
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, Sequence

import yaml

from agent_runtime import execute
from collect_implemented_feature_evidence import collect as collect_implemented_feature_evidence
from specialist_dispatch import dispatch as dispatch_specialists
from delivery_failure_guard import (
    build_delivery_failure_fingerprint,
    decide_delivery_failure_attempt,
    failure_attempt_record,
)
from project_workspace import resolve as resolve_project_workspace
from revision_scope import (
    aggregate_visual_evidence_by_requirement,
    asset_digests as _revision_asset_digests,
    build_revision_asset_attestation,
    build_revision_scope_manifest,
    constrain_revision_markdown,
    is_content_asset_relative_path,
    requirement_ids,
    requirement_linked_rows,
    requirement_rows,
    requirement_sections,
    resolve_multi_source_extraction_scope,
    revision_artifact_set_snapshot,
    revision_scope_manifest_digest,
    validate_rendered_html_scope,
    validate_revision_scope,
)
from runtime_identity_contract import (
    RUNTIME_IDENTITY_MANIFEST_FILES,
    RUNTIME_IDENTITY_MANIFEST_SCHEMA_VERSION,
    complete_runtime_identity_failures,
    runtime_manifest_digest,
)
from prd_visual_contract import PLACEHOLDER_DECLARATION_RE
from validate_agent_trace import (
    validate_artifact_lineage,
    validate_implemented_feature_evidence_packet,
)


ROOT = Path(__file__).resolve().parents[1]
# Delivery defaults are local to the only production controller. They remain
# CLI-overridable; no legacy portfolio, loop, or multi-runtime policy applies.
DEFAULT_EXECUTION_TIMEOUT_MINUTES = 15
DEFAULT_INTERACTIVE_TIMEOUT_MINUTES = 60
DEFAULT_MAX_REVISIONS = 3
DEFAULT_INTERACTIVE_IDENTICAL_FAILURE_LIMIT = 2
MAX_ATTRIBUTABLE_AGENT_ATTEMPTS = 2
# Remote stage reviews remain bounded, but run-log.yaml never uses this route:
# its provenance is controller state and is generated locally.
STAGE_REVIEW_TIMEOUT_MINUTES = 3
CONTROLLER_TRACE_PROVIDER = "pm-copilot-controller"
CONTROLLER_TRACE_MODEL = "deterministic-trace-v2"
CONTROLLER_TRACE_REVISION = "controller-deterministic-trace"
CONTROLLER_TRACE_EXECUTION_MODES = {
    "deterministic_trace_materialization",
    "deterministic_trace_validation",
}
DERIVED_REFRESH_MUTABLE_FILES = frozenset({
    "interactive-run.json",
    "prd.html",
    "revision-evidence.json",
    "run-log.yaml",
})
DERIVED_REFRESH_TRANSACTION_SCHEMA_VERSION = 1
TRACE_TEMPLATE = ROOT / "templates" / "agent-run-log-template.yaml"
CLARIFICATION_COVERAGE_AREAS = (
    "goal", "users", "scope", "success_evidence", "constraints_and_risk",
)
DELIVERY_VARIANTS = {"new", "in_place_revision", "compose_to_new"}
LEGACY_DELIVERY_VARIANT_ALIASES = {"extract_to_new": "compose_to_new"}
IMPLEMENTED_EVIDENCE_PACKET_PATH = Path("source-material") / "implemented-feature-evidence.json"
INPUT_ASSET_SNAPSHOT_DIRECTORY = Path("source-material") / "input-assets"
INPUT_ASSET_MANIFEST_PATH = INPUT_ASSET_SNAPSHOT_DIRECTORY / "manifest.json"
INPUT_ASSET_MANIFEST_SCHEMA_VERSION = 1
SUPPORTED_INPUT_ASSET_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".mov", ".m4v", ".ogv", ".ogg",
})
REVISION_REVIEWER_FINDING_TYPES = {
    "selected_behavior_gap",
    "selected_copy_gap",
    "selected_acceptance_gap",
    "selected_media_semantics_gap",
}
PRD_MARKERS = (
    "prd", "产品需求", "需求文档", "产品需求文档", "生成需求", "写需求",
)

# An extraction must have all three semantics: a source context, an operation
# that separates material, and a new independent PRD target.  Keeping the
# signals separate makes English and Chinese requests work without classifying
# ordinary in-place edits or a greenfield PRD as an extraction.
EXTRACTION_DOCUMENT_RE = re.compile(
    r"(?:\bprd\b|\bproduct\s+requirements?(?:\s+document)?\b|"
    r"\brequirements?\s+doc(?:ument)?\b|需求(?:文档)?|产品需求(?:文档)?)",
    re.IGNORECASE,
)
EXTRACTION_ACTION_RE = re.compile(
    r"(?:\bextract(?:ed|ing)?\b|\bsplit(?:ting)?(?:\s+(?:out|off))?\b|"
    r"\bseparat(?:e|ed|ing)\b|\bcarv(?:e|ed|ing)\s+out\b|"
    r"\bpull(?:ed|ing)?\s+out\b|\bspin(?:ning)?\s+off\b|\bbreak(?:ing)?\s+out\b|"
    r"\bderiv(?:e|ed|ing)\b|\bmigrat(?:e|ed|ing)\b|\bmov(?:e|ed|ing)\b|"
    r"\bturn(?:ed|ing)?\b|\bconvert(?:ed|ing)?\b|"
    r"提取|抽取|拆分|分拆|拆出(?:来)?|抽出|分离|剥离|迁移|转成|转为|做成|改成|整理成|独立成|单列成|另起)",
    re.IGNORECASE,
)
EXTRACTION_NEW_TARGET_RE = re.compile(
    r"(?:\b(?:(?:new|independent|separate|standalone|own)\s+){1,3}(?:prd|product\s+requirements?(?:\s+document)?|requirements?\s+doc(?:ument)?)\b|"
    r"\b(?:prd|product\s+requirements?(?:\s+document)?|requirements?\s+doc(?:ument)?)\s+(?:for\s+)?(?:a\s+)?(?:new|independent|separate|standalone)\b|"
    r"(?:(?:新(?:的)?|独立|单独|单列)\s*){1,3}(?:一(?:个|份))?\s*(?:prd|需求(?:文档)?|产品需求(?:文档)?))",
    re.IGNORECASE,
)
EXTRACTION_SOURCE_CONTEXT_RE = re.compile(
    r"(?:\b(?:old|existing|current|legacy|historical|previous|source)\s+(?:prd|product\s+requirements?(?:\s+document)?|requirements?\s+doc(?:ument)?|requirements?)\b|"
    r"\b(?:from|out\s+of|of|based\s+on|using|derived\s+from)\s+(?:the\s+)?(?:prd|product\s+requirements?(?:\s+document)?|requirements?\s+doc(?:ument)?)\b|"
    r"(?:旧|原有|已有|现有|历史|之前).{0,32}(?:prd|需求(?:文档)?|产品需求(?:文档)?|部分内容|内容|需求|功能)|"
    r"(?:从|基于|根据|把|将).{0,64}(?:prd|需求(?:文档)?|产品需求(?:文档)?))",
    re.IGNORECASE,
)
EXTRACTION_CONSTRUCTION_RE = re.compile(
    r"(?:\b(?:create|make|build|write|generate)\b|创建|新建|生成|形成|制作)",
    re.IGNORECASE,
)
IMPLEMENTED_FEATURE_REQUEST_RE = re.compile(
    r"(?:\b(?:already\s+)?implemented(?:[-\s]feature)?\b|"
    r"\b(?:feature|functionality|capability)\s+(?:is\s+)?(?:already\s+)?(?:implemented|built|completed)\b|"
    r"\b(?:already\s+(?:built|completed)|current\s+(?:branch|diff).{0,48}(?:implemented|built|complete))\b|"
    r"(?:已实现|已经实现|已开发(?:完成)?|已经开发(?:完成)?|"
    r"(?:功能|特性|能力|需求).{0,12}(?:已|已经)(?:实现|完成|开发完成)|"
    r"当前分支.{0,24}(?:已完成|已实现)|已完成(?:的)?(?:功能|特性|能力|需求)))",
    re.IGNORECASE,
)
SOURCE_REQUIREMENT_ID_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:\d+(?:\.\d+)+|[A-Za-z][A-Za-z0-9_]*-\d+)(?![A-Za-z0-9_.-])"
)


class RevisionSourceDriftError(RuntimeError):
    """A confirmed in-place revision can no longer safely replace its source."""


class DerivedRefreshSourceDriftError(RuntimeError):
    """A completed PRD changed while a derived-artifact refresh was staged."""


@dataclass(frozen=True)
class PrdRequestPlan:
    """One normalized CLI intent before the controller reads or mutates run state."""

    args: argparse.Namespace
    raw_request: str
    folder: Path
    task_mode: str
    delivery_variant: str
    entrypoint: Literal["interactive", "natural"]


def _ensure_runtime_current(
    argv: Sequence[str], *,
    entrypoint: Literal["interactive", "natural"] = "interactive",
) -> None:
    """Keep the historical hook without maintaining a copied global runtime.

    The controller now always runs from the repository checkout selected by the
    caller or the Codex plugin.  There is therefore no second runtime tree to
    synchronize or overwrite before a PRD run starts.
    """
    del argv, entrypoint


def _artifact_digest(path: Path) -> str | None:
    """Return a content digest so a repair loop cannot mistake no-op work for progress."""
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _capture_runtime_identity(root: Path = ROOT) -> dict[str, Any]:
    """Capture the bytes loaded by this controller process at import time.

    Runtime installation can replace files while a long delivery is running.
    Reading those paths again at trace materialization would make the already
    loaded process claim the later build.  The module-level snapshot below is
    therefore the only source for controller provenance during this process.
    """
    runtime_root = root.resolve()
    files: dict[str, str] = {}
    for relative_path in RUNTIME_IDENTITY_MANIFEST_FILES:
        digest = _artifact_digest(runtime_root / relative_path)
        if digest is None:
            raise RuntimeError(f"runtime identity source is missing: {relative_path}")
        files[relative_path] = digest
    return {
        # Keep the existing public trace shape compatible.  Reuse requires the
        # manifest below, so legacy v1 identities without it are fail-closed.
        "identity_version": 1,
        "runtime_root": str(runtime_root),
        "version": (runtime_root / "VERSION").read_text(encoding="utf-8").strip(),
        "controller_sha256": files["scripts/run_interactive_request.py"],
        "plugin_entry_sha256": files["plugins/pm-copilot/scripts/pm_copilot_mcp.py"],
        "runtime_manifest": {
            "schema_version": RUNTIME_IDENTITY_MANIFEST_SCHEMA_VERSION,
            "files": files,
        },
        "runtime_manifest_sha256": runtime_manifest_digest(files),
    }


# This snapshot is intentionally captured after all imported controller
# dependencies have loaded but before command-line parsing or delivery work.
# A later install can exec a fresh process; it cannot rewrite this provenance.
_PROCESS_RUNTIME_IDENTITY = _capture_runtime_identity()


def _request_looks_like_extraction(raw_request: str) -> bool:
    """Recognize an extraction request without mistaking an edit for a new PRD."""
    text = unicodedata.normalize("NFKC", raw_request or "").casefold()
    if not EXTRACTION_DOCUMENT_RE.search(text) or not EXTRACTION_NEW_TARGET_RE.search(text):
        return False
    has_source = bool(EXTRACTION_SOURCE_CONTEXT_RE.search(text))
    has_extraction_action = bool(EXTRACTION_ACTION_RE.search(text))
    has_construction_action = bool(EXTRACTION_CONSTRUCTION_RE.search(text))
    return has_source and (has_extraction_action or has_construction_action)


def is_prd_request(request: str) -> bool:
    """Classify the natural-language facade's scope without changing run state."""
    lowered = request.casefold()
    return any(marker.casefold() in lowered for marker in PRD_MARKERS)


def _request_looks_like_implemented_feature(raw_request: str) -> bool:
    """Recognize an explicit already-built-feature PRD request.

    The request only selects the evidence-backed mode. It never stands in for
    the required implementation evidence packet, which remains a controller
    gate before delivery.
    """
    return bool(IMPLEMENTED_FEATURE_REQUEST_RE.search(unicodedata.normalize("NFKC", raw_request or "")))


def _delivery_variant(state: dict[str, Any]) -> str:
    """Return the persisted delivery shape; history never selects a workflow."""
    raw_variant = str(state.get("delivery_variant", "")).strip()
    variant = LEGACY_DELIVERY_VARIANT_ALIASES.get(raw_variant, raw_variant)
    task_mode = str(state.get("task_mode", "")).strip()
    if variant in {"", "new"}:
        if task_mode == "prd_revision":
            return "in_place_revision"
        if task_mode in {"prd_composition", "extract_to_new"}:
            return "compose_to_new"
    if variant in DELIVERY_VARIANTS:
        return variant
    return "new"


def _is_implemented_feature_append(state: Mapping[str, Any]) -> bool:
    """Keep append-to-current-PRD semantics distinct from a user revision."""
    return bool(state.get("append_implemented_feature")) and _delivery_variant(dict(state)) == "in_place_revision"


def _clear_inactive_revision_scope(state: dict[str, Any]) -> None:
    """Keep historical revision audit data from becoming active delivery state."""
    if _delivery_variant(state) == "in_place_revision":
        return
    for key in (
        "revision_requirement_ids",
        "revision_scope_manifest",
        "revision_scope_precheck",
        "revision_scope_validation",
        "revision_request",
        "revision_stop_reason",
        "scope_clarification",
    ):
        state.pop(key, None)


def _task_mode(state: dict[str, Any]) -> str:
    """Return the four supported PRD workflow modes."""
    value = str(state.get("task_mode", "")).strip()
    legacy = {
        "prd_delivery": "new_prd",
        "extract_to_new": "prd_composition",
    }
    value = legacy.get(value, value or "new_prd")
    variant = _delivery_variant(state)
    if value == "new_prd" and variant == "in_place_revision":
        return "prd_revision"
    if value == "new_prd" and variant == "compose_to_new":
        return "prd_composition"
    return value


def _context_source_mode(state: dict[str, Any]) -> str:
    source = state.get("context_source")
    if isinstance(source, dict):
        value = str(source.get("mode", "")).strip()
        if value in {"brief-only", "document-backed", "repo-backed"}:
            return value
    if _delivery_variant(state) == "compose_to_new":
        return "document-backed"
    if _task_mode(state) == "implemented_feature_prd":
        return "repo-backed"
    return "brief-only"


def _set_needs_input(
    state: dict[str, Any], question: str, *, reason: str, field: str,
) -> None:
    """Pause before generation when a branch-changing source detail is absent."""
    state["status"] = "needs_input"
    state["termination"] = "needs_input"
    state["last_error"] = reason
    state["required_input"] = {"field": field, "question": question, "reason": reason}
    turns = state.get("turns")
    if isinstance(turns, list) and turns and isinstance(turns[-1], dict):
        turns[-1]["questions"] = [question]
        turns[-1].setdefault("buckets", {})["must_answer_before_generation"] = [question]


def _extraction_sources(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized plural source state while accepting legacy runs.

    Older in-progress folders hold one ``extraction_source`` descriptor.  The
    migration is deliberately in-place and idempotent so a resume gains the
    plural representation without changing the old snapshot bytes or forcing
    a new request.  A one-source run keeps the singular alias for older tools.
    """
    raw_sources = state.get("extraction_sources")
    if isinstance(raw_sources, list):
        sources = [item for item in raw_sources if isinstance(item, dict)]
    else:
        legacy = state.get("extraction_source")
        sources = [legacy] if isinstance(legacy, dict) else []
        if sources:
            state["extraction_sources"] = sources
    for index, descriptor in enumerate(sources, start=1):
        source_id = str(descriptor.get("source_id", "")).strip()
        if not source_id:
            descriptor["source_id"] = f"source-{index}"
    if len(sources) == 1:
        state["extraction_source"] = sources[0]
    elif len(sources) > 1:
        state.pop("extraction_source", None)
    return sources


def _normalise_persisted_prd_mode(state: dict[str, Any]) -> bool:
    """Upgrade known historical task-mode pairs without widening an active scope.

    Older interactive states used ``prd_delivery`` for every workflow and
    ``extract_to_new`` for a source-backed new PRD.  The delivery shape is the
    durable authority for those generic records.  Revision history alone is
    deliberately not enough to select a revision: the existing legacy
    revision migration still has to verify its frozen baseline and selector.
    """
    raw_mode = str(state.get("task_mode", "")).strip()
    raw_variant = str(state.get("delivery_variant", "")).strip()
    variant = LEGACY_DELIVERY_VARIANT_ALIASES.get(raw_variant, raw_variant)
    legacy_or_new_mode = raw_mode in {"", "prd_delivery", "new_prd"}
    has_extraction_source = isinstance(state.get("extraction_source"), dict) or isinstance(
        state.get("extraction_sources"), list,
    )

    if state.get("append_implemented_feature") and variant == "in_place_revision":
        task_mode, delivery_variant = "implemented_feature_prd", "in_place_revision"
    elif variant == "in_place_revision" or raw_mode == "prd_revision":
        task_mode, delivery_variant = "prd_revision", "in_place_revision"
    elif variant == "compose_to_new" or raw_mode in {"prd_composition", "extract_to_new"}:
        task_mode, delivery_variant = "prd_composition", "compose_to_new"
    elif raw_mode == "implemented_feature_prd":
        task_mode, delivery_variant = "implemented_feature_prd", "new"
    elif variant not in DELIVERY_VARIANTS and legacy_or_new_mode and has_extraction_source:
        task_mode, delivery_variant = "prd_composition", "compose_to_new"
    elif variant in {"", "new"} and legacy_or_new_mode:
        task_mode, delivery_variant = "new_prd", "new"
    else:
        # Preserve an unknown persisted value for the normal failure path
        # instead of relabeling a corrupted run as a new PRD.
        return False

    changed = (
        state.get("task_mode") != task_mode
        or state.get("delivery_variant") != delivery_variant
    )
    state["task_mode"] = task_mode
    state["delivery_variant"] = delivery_variant
    if delivery_variant == "compose_to_new":
        before_source_state = json.dumps({
            "extraction_source": state.get("extraction_source"),
            "extraction_sources": state.get("extraction_sources"),
        }, ensure_ascii=False, sort_keys=True)
        _extraction_sources(state)
        after_source_state = json.dumps({
            "extraction_source": state.get("extraction_source"),
            "extraction_sources": state.get("extraction_sources"),
        }, ensure_ascii=False, sort_keys=True)
        changed = changed or before_source_state != after_source_state
    return changed


def _extraction_snapshot_path(
    state: dict[str, Any], descriptor: Mapping[str, Any] | None = None,
) -> Path | None:
    if descriptor is None:
        sources = _extraction_sources(state)
        descriptor = sources[0] if len(sources) == 1 else None
    if not isinstance(descriptor, Mapping):
        return None
    relative = str(descriptor.get("snapshot_path", "")).strip()
    if not relative:
        return None
    root = _canonical_folder(state).resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _extraction_source_configuration_problem(
    state: dict[str, Any], sources: Sequence[Mapping[str, Any]] | None = None,
) -> str | None:
    sources = list(sources if sources is not None else _extraction_sources(state))
    if not sources:
        return "未提供可验证的旧 PRD 来源。请指定要提取的源文档。"
    source_ids = [str(item.get("source_id", "")).strip() for item in sources]
    if not all(source_ids) or len(source_ids) != len(set(source_ids)):
        return "提取来源标识无效或重复；请重新指定每份旧 PRD。"
    return None


def _extraction_selection(state: dict[str, Any]) -> list[str]:
    persisted = _trace_values(state.get("extraction_selection"))
    if persisted:
        return persisted
    sources = _extraction_sources(state)
    selected_by_source = [
        (str(source.get("source_id", "")).strip(), _trace_values(source.get("selected_scope")))
        for source in sources
    ]
    if len(sources) == 1 and selected_by_source[0][1]:
        return selected_by_source[0][1]
    qualified = [
        f"{source_id}: {selector}"
        for source_id, selected in selected_by_source
        for selector in selected
        if source_id
    ]
    if qualified:
        return qualified
    packet = state.get("confirmed_fact_packet")
    if not isinstance(packet, dict):
        turns = state.get("turns")
        packet = turns[-1] if isinstance(turns, list) and turns and isinstance(turns[-1], dict) else {}
    scope = packet.get("scope") if isinstance(packet, dict) else {}
    return _trace_values(scope.get("in_scope") if isinstance(scope, dict) else [])


def _extraction_source_texts(
    state: dict[str, Any],
) -> tuple[dict[str, str], dict[str, list[str]], str | None]:
    sources = _extraction_sources(state)
    configuration_problem = _extraction_source_configuration_problem(state, sources)
    if configuration_problem:
        return {}, {}, configuration_problem
    source_texts: dict[str, str] = {}
    source_aliases: dict[str, list[str]] = {}
    for descriptor in sources:
        source_id = str(descriptor["source_id"])
        snapshot = _extraction_snapshot_path(state, descriptor)
        if snapshot is None or not snapshot.is_file():
            return {}, {}, "未提供可验证的旧 PRD 来源。请指定要提取的源文档。"
        try:
            source_texts[source_id] = snapshot.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return {}, {}, "旧 PRD 快照不可读取；请重新指定来源并确认提取范围。"
        source_aliases[source_id] = [str(descriptor.get("display_name", "")).strip()]
    return source_texts, source_aliases, None


def _localize_extraction_resolution_problem(problem: str) -> str:
    """Keep delivery pauses actionable while sharing canonical resolver logic."""
    if "matches more than one extraction source" in problem:
        return (
            "提取范围同时匹配多份旧 PRD；请使用 source-1: 5.1 或 文件名.md: 5.1 "
            "这类来源限定选择，系统不会猜测来源。"
        )
    if "uses an ambiguous source qualifier" in problem:
        return "提取来源文件名不唯一；请使用 source-1: 5.1 这类稳定来源标识限定选择。"
    if "matches multiple source text locations" in problem:
        return "提取范围匹配多个旧 PRD 文本位置；请改用需求 ID、完整章节标题或来源限定选择。"
    if "matches multiple source headings" in problem:
        return "提取范围匹配多个旧 PRD 章节；请提供完整章节标题、需求 ID 或来源限定选择。"
    if "cannot be uniquely resolved" in problem:
        return (
            "提取范围无法在旧 PRD 快照中唯一定位；请提供存在的需求 ID、完整章节标题、"
            "可唯一匹配的原文范围或来源限定选择。"
        )
    if "references IDs absent" in problem or "invalid requirement-ID range" in problem:
        return "提取范围未完整匹配旧 PRD 快照中的需求 ID；请检查来源和需求编号。"
    if "contains an empty selector" in problem:
        return "提取范围包含空选择；请提供需求 ID、完整章节标题或可唯一匹配的原文范围。"
    return problem


def _resolve_extraction_selection(
    state: dict[str, Any], selected_scope: Sequence[str],
) -> tuple[list[dict[str, object]], str | None]:
    """Resolve selectors against every immutable snapshot through one helper."""
    source_texts, source_aliases, source_problem = _extraction_source_texts(state)
    if source_problem:
        return [], source_problem
    resolutions, problem = resolve_multi_source_extraction_scope(
        source_texts, selected_scope, source_aliases=source_aliases,
    )
    return resolutions, _localize_extraction_resolution_problem(problem) if problem else None


def _extraction_resolution_groups(
    state: dict[str, Any], resolutions: Sequence[Mapping[str, object]],
) -> dict[str, dict[str, list[dict[str, object]] | list[str]]]:
    groups: dict[str, dict[str, list[dict[str, object]] | list[str]]] = {
        str(source.get("source_id", "")): {"selected_scope": [], "scope_resolution": []}
        for source in _extraction_sources(state)
        if str(source.get("source_id", ""))
    }
    for resolution in resolutions:
        source_id = str(resolution.get("source_id", "")).strip()
        selector = str(resolution.get("selector", "")).strip()
        if not source_id or not selector or source_id not in groups:
            continue
        source_resolution = {
            "selector": selector,
            "kind": str(resolution.get("kind", "")),
            "matches": list(resolution.get("matches", [])),
        }
        selected = groups[source_id]["selected_scope"]
        evidence = groups[source_id]["scope_resolution"]
        if isinstance(selected, list) and selector not in selected:
            selected.append(selector)
        if isinstance(evidence, list) and source_resolution not in evidence:
            evidence.append(source_resolution)
    return groups


def _extraction_selection_problem(state: dict[str, Any]) -> str | None:
    """Return a stable input stop when a source subset is unclear or ambiguous."""
    sources = _extraction_sources(state)
    configuration_problem = _extraction_source_configuration_problem(state, sources)
    if configuration_problem:
        return configuration_problem
    selected = _extraction_selection(state)
    if not selected:
        return "未明确要从旧 PRD 提取哪些内容；请提供需求 ID、章节标题或可核验的范围。"
    resolutions, problem = _resolve_extraction_selection(state, selected)
    if problem:
        return problem
    if len(sources) > 1:
        groups = _extraction_resolution_groups(state, resolutions)
        missing = [
            str(source.get("display_name") or source.get("source_id"))
            for source in sources
            if not groups.get(str(source.get("source_id", "")), {}).get("selected_scope")
        ]
        if missing:
            return (
                "多份旧 PRD 中仍有未明确提取范围的来源：" + "、".join(missing)
                + "。请为每份来源指定需求 ID、章节标题或范围。"
            )
    return None


def _next_extraction_source_id(sources: Sequence[Mapping[str, Any]]) -> str:
    used = {str(source.get("source_id", "")).strip() for source in sources}
    index = 1
    while f"source-{index}" in used:
        index += 1
    return f"source-{index}"


def _next_extraction_snapshot_path(
    canonical: Path, source_id: str, sources: Sequence[Mapping[str, Any]],
) -> Path:
    existing = {str(source.get("snapshot_path", "")).strip() for source in sources}
    legacy = Path("source-material") / "source-prd.md"
    if not sources and legacy.as_posix() not in existing and not (canonical / legacy).exists():
        return legacy
    index = 1
    while True:
        suffix = "" if index == 1 else f"-{index}"
        candidate = Path("source-material") / "extraction-sources" / f"{source_id}{suffix}.md"
        if candidate.as_posix() not in existing and not (canonical / candidate).exists():
            return candidate
        index += 1


def _clear_extraction_selection(state: dict[str, Any], sources: Sequence[Mapping[str, Any]]) -> None:
    state.pop("extraction_selection", None)
    for descriptor in sources:
        if isinstance(descriptor, dict):
            descriptor["selected_scope"] = []
            descriptor.pop("selection_resolution", None)
            descriptor.pop("selection_recorded_at", None)


def _refresh_extraction_context(state: dict[str, Any], sources: Sequence[Mapping[str, Any]]) -> None:
    context = state.get("context_source")
    context = dict(context) if isinstance(context, dict) else {}
    context.update({
        "mode": "document-backed",
        "files_loaded": [
            str(source.get("snapshot_path", "")) for source in sources
            if str(source.get("snapshot_path", "")).strip()
        ],
    })
    state["context_source"] = context


def register_extraction_source(state: dict[str, Any], source: Path) -> None:
    """Append or refresh one immutable source PRD snapshot for extraction.

    Repeating ``--extract-from`` appends distinct sources.  Supplying the same
    unchanged file again is idempotent; supplying changed bytes creates a new
    snapshot generation and invalidates all confirmed source selections.
    """
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Extraction source PRD not found: {source}")
    if source.suffix.lower() not in {".md", ".markdown", ".mdown", ".txt"}:
        raise ValueError("Extraction source must be a Markdown or text PRD")
    source_digest = _artifact_digest(source)
    if not source_digest:
        raise ValueError("Extraction source PRD is empty")

    canonical = _canonical_folder(state)
    sources = _extraction_sources(state)
    matching = next(
        (descriptor for descriptor in sources if str(descriptor.get("source_path", "")) == str(source)),
        None,
    )
    if matching is not None:
        snapshot = _extraction_snapshot_path(state, matching)
        if snapshot is not None and snapshot.is_file() and str(matching.get("sha256", "")) == source_digest:
            state["delivery_variant"] = "compose_to_new"
            state["task_mode"] = "prd_composition"
            _clear_inactive_revision_scope(state)
            _refresh_extraction_context(state, sources)
            state.pop("required_input", None)
            return
        source_id = str(matching.get("source_id", "")).strip() or _next_extraction_source_id(sources)
        snapshot_relative = _next_extraction_snapshot_path(canonical, source_id, sources)
        matching.update({
            "source_id": source_id,
            "display_name": source.name,
            "snapshot_path": snapshot_relative.as_posix(),
            "sha256": source_digest,
            "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        })
        _clear_extraction_selection(state, sources)
    else:
        source_id = _next_extraction_source_id(sources)
        snapshot_relative = _next_extraction_snapshot_path(canonical, source_id, sources)
        descriptor = {
            "source_id": source_id,
            "source_path": str(source),
            "display_name": source.name,
            "snapshot_path": snapshot_relative.as_posix(),
            "sha256": source_digest,
            "selected_scope": [],
            "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        sources.append(descriptor)
        state["extraction_sources"] = sources
        _clear_extraction_selection(state, sources)

    snapshot = canonical / snapshot_relative
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    _atomic_copy(source, snapshot)
    if _artifact_digest(snapshot) != source_digest:
        raise ValueError("Extraction source snapshot hash does not match the supplied PRD")
    if len(sources) == 1:
        state["extraction_source"] = sources[0]
    else:
        state.pop("extraction_source", None)
    state["delivery_variant"] = "compose_to_new"
    state["task_mode"] = "prd_composition"
    _clear_inactive_revision_scope(state)
    _refresh_extraction_context(state, sources)
    state.pop("required_input", None)


def _load_implemented_feature_evidence(source: Path) -> dict[str, Any]:
    """Load an explicit implementation evidence packet without parsing user text."""
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Implemented-feature evidence file not found: {source}")
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Implemented-feature evidence must be a JSON object: {error.msg}") from error
    if not isinstance(value, dict):
        raise ValueError("Implemented-feature evidence must be a JSON object")
    return value


def _implemented_evidence_packet_path(state: dict[str, Any]) -> Path | None:
    """Resolve the immutable packet path in either canonical or staged state."""
    descriptor = state.get("implemented_feature_evidence_source")
    if not isinstance(descriptor, dict):
        return None
    relative = str(descriptor.get("packet_path", "")).strip()
    if relative != IMPLEMENTED_EVIDENCE_PACKET_PATH.as_posix():
        return None
    root = _canonical_folder(state).resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _write_implemented_evidence_packet(state: dict[str, Any], evidence: dict[str, Any]) -> tuple[str, str]:
    """Materialize one portable evidence packet before staging is created."""
    packet = _canonical_folder(state) / IMPLEMENTED_EVIDENCE_PACKET_PATH
    packet.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(packet, json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    digest = _artifact_digest(packet)
    if not digest:
        raise ValueError("could not persist the implemented-feature evidence packet")
    return IMPLEMENTED_EVIDENCE_PACKET_PATH.as_posix(), digest


def _implemented_evidence_result_refs_problem(state: dict[str, Any], evidence: dict[str, Any]) -> str | None:
    """Ensure packet-declared result files remain portable and present pre-write."""
    root = _canonical_folder(state).resolve()

    def visit(value: object) -> str | None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "result_ref":
                    if not isinstance(child, str) or not child.strip():
                        return "已实现功能证据包包含空的 result_ref。"
                    raw_reference = child.strip()
                    candidate = (root / raw_reference).resolve()
                    try:
                        relative = candidate.relative_to(root)
                    except ValueError:
                        return "已实现功能证据包的 result_ref 必须位于当前运行目录内。"
                    if relative.parts[:2] != ("tool-results", "implemented-evidence"):
                        return "已实现功能证据包的 result_ref 必须位于 tool-results/implemented-evidence/。"
                    if not candidate.is_file():
                        return f"已实现功能证据包引用的结果文件不存在：{raw_reference}。"
                else:
                    problem = visit(child)
                    if problem:
                        return problem
        elif isinstance(value, list):
            for child in value:
                problem = visit(child)
                if problem:
                    return problem
        return None

    return visit(evidence)


def _import_implemented_evidence_result_files(
    state: dict[str, Any], source: Path, evidence: dict[str, Any],
) -> list[str]:
    """Package evidence JSON result references under the canonical run folder.

    An implementation-evidence packet is an input bundle, so any referenced
    local result must travel with the bundle instead of becoming an external
    path that cannot survive staging or promotion.  Paths are intentionally
    limited to the JSON file's directory; accepting arbitrary absolute paths
    would turn a PRD evidence import into an unrelated filesystem reader.
    """
    bundle_root = source.parent.resolve()
    canonical = _canonical_folder(state).resolve()
    temporary_root = canonical / ".implemented-evidence.importing"
    if temporary_root.exists():
        shutil.rmtree(temporary_root)
    copied: list[str] = []

    def import_reference(raw_reference: str) -> str:
        candidate = (bundle_root / raw_reference).resolve()
        try:
            relative_to_bundle = candidate.relative_to(bundle_root)
        except ValueError as error:
            raise ValueError(
                "implemented-feature evidence result_ref must stay inside the evidence bundle"
            ) from error
        if not candidate.is_file():
            raise FileNotFoundError(
                f"implemented-feature evidence result_ref is missing: {raw_reference}"
            )
        destination_relative = (
            Path("tool-results") / "implemented-evidence" / relative_to_bundle
        )
        destination = temporary_root / relative_to_bundle
        _atomic_copy(candidate, destination)
        portable = destination_relative.as_posix()
        copied.append(portable)
        return portable

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "result_ref" and isinstance(child, str) and child.strip():
                    value[key] = import_reference(child.strip())
                else:
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    try:
        visit(evidence)
        destination_root = canonical / "tool-results" / "implemented-evidence"
        if destination_root.exists():
            if destination_root.is_dir():
                shutil.rmtree(destination_root)
            else:
                destination_root.unlink()
        if copied:
            destination_root.parent.mkdir(parents=True, exist_ok=True)
            temporary_root.replace(destination_root)
    finally:
        if temporary_root.exists():
            shutil.rmtree(temporary_root)
    return list(dict.fromkeys(copied))


def register_implemented_feature_evidence(state: dict[str, Any], source: Path) -> None:
    """Persist supplied implementation evidence for the implemented-feature route."""
    source = source.expanduser().resolve()
    evidence = _load_implemented_feature_evidence(source)
    imported_result_refs = _import_implemented_evidence_result_files(state, source, evidence)
    packet_path, packet_sha256 = _write_implemented_evidence_packet(state, evidence)
    state["task_mode"] = "implemented_feature_prd"
    if not _is_implemented_feature_append(state):
        state["delivery_variant"] = "new"
    _clear_inactive_revision_scope(state)
    context = state.get("context_source")
    context = dict(context) if isinstance(context, dict) else {}
    files_loaded = _trace_values(context.get("files_loaded"))
    if packet_path not in files_loaded:
        files_loaded.append(packet_path)
    context.update({
        "mode": "repo-backed",
        "files_loaded": files_loaded,
        "host_project_root": str(context.get("host_project_root", "")),
        "host_project_files_loaded": _trace_values(context.get("host_project_files_loaded")),
        "product_documents_loaded": _trace_values(context.get("product_documents_loaded")),
    })
    state["context_source"] = context
    state["implemented_feature_evidence"] = evidence
    state["implemented_feature_evidence_source"] = {
        "display_name": source.name,
        # Retain the caller's raw file hash as provenance, but the packet hash
        # is the one writers and validators use after portable result refs are
        # normalized into the run folder.
        "sha256": _artifact_digest(source),
        "source_sha256": _artifact_digest(source),
        "packet_path": packet_path,
        "packet_sha256": packet_sha256,
        "imported_result_refs": imported_result_refs,
    }
    state.pop("required_input", None)


def register_automatic_implemented_feature_evidence(state: dict[str, Any], host_project_root: Path) -> None:
    """Freeze host-repository evidence before clarification without a hand-authored JSON gate."""
    canonical = _canonical_folder(state)
    evidence = collect_implemented_feature_evidence(host_project_root, str(state.get("raw_request", "")), canonical)
    packet_path, packet_sha256 = _write_implemented_evidence_packet(state, evidence)
    context = state.get("context_source")
    context = dict(context) if isinstance(context, dict) else {}
    files_loaded = _trace_values(context.get("files_loaded"))
    if packet_path not in files_loaded:
        files_loaded.append(packet_path)
    context.update({
        "mode": "repo-backed",
        "files_loaded": files_loaded,
        "host_project_root": str(host_project_root.resolve()),
        "host_project_files_loaded": _trace_values(evidence.get("changed_files")),
        "product_documents_loaded": _trace_values(context.get("product_documents_loaded")),
    })
    state["task_mode"] = "implemented_feature_prd"
    if not _is_implemented_feature_append(state):
        state["delivery_variant"] = "new"
    state["context_source"] = context
    state["implemented_feature_evidence"] = evidence
    state["implemented_feature_evidence_source"] = {
        "display_name": "automatic-host-repository-collection",
        "sha256": packet_sha256,
        "source_sha256": packet_sha256,
        "packet_path": packet_path,
        "packet_sha256": packet_sha256,
        "imported_result_refs": ["tool-results/implemented-evidence/collection.json"],
        "host_project_root": str(host_project_root.resolve()),
        "collection_mode": "automatic",
    }
    state.pop("required_input", None)


def apply_revision_requirement_ids(
    state: dict[str, Any], selectors: object, *, authority: str = "explicit command-line selector",
) -> None:
    """Apply explicit, existing PRD IDs as the authoritative revision boundary."""
    selected = list(dict.fromkeys(_trace_values(selectors)))
    if not selected:
        return
    known = _trace_requirement_ids(_canonical_folder(state) / "prd.md")
    if not known:
        raise ValueError("Canonical PRD has no identifiable requirement IDs for --revision-requirement-id")
    unknown = [item for item in selected if item not in known]
    if unknown:
        raise ValueError(
            "--revision-requirement-id is not present in the canonical PRD: " + ", ".join(unknown)
        )
    state["revision_requirement_ids"] = selected
    state["task_mode"] = "prd_revision"
    manifest = state.get("revision_scope_manifest")
    manifest = dict(manifest) if isinstance(manifest, dict) else {}
    manifest.update({
        "mode": "in_place_revision",
        "requirement_ids": selected,
        "selectors": selected,
        "selector_status": "resolved",
        "authority": authority,
    })
    state["revision_scope_manifest"] = manifest
    state["delivery_variant"] = "in_place_revision"
    state["task_mode"] = "prd_revision"
    state.pop("required_input", None)


def _legacy_revision_baseline_matches(state: dict[str, Any]) -> bool:
    """Require a legacy revision's recorded source snapshot before migration."""
    history = state.get("revision_history")
    latest = history[-1] if isinstance(history, list) and history and isinstance(history[-1], dict) else {}
    prd_digest = str(latest.get("prd_before_sha256", "")).strip()
    html_digest = str(latest.get("html_before_sha256", "")).strip()
    folder = _canonical_folder(state)
    return bool(
        prd_digest
        and html_digest
        and _artifact_digest(folder / "prd.md") == prd_digest
        and _artifact_digest(folder / "prd.html") == html_digest
    )


def _migrate_legacy_confirmed_revision_scope(state: dict[str, Any]) -> bool:
    """Restore a provable in-place selector omitted by an older run format.

    This migration is deliberately narrower than normal natural-language scope
    parsing. It trusts only the frozen confirmation packet, requires one exact
    current requirement ID, and refuses source-drifted or ambiguous records.
    """
    variant = _delivery_variant(state)
    history = state.get("revision_history")
    required = state.get("required_input")
    legacy_default_revision = bool(
        variant == "new"
        and isinstance(history, list)
        and history
        and isinstance(history[-1], dict)
        and history[-1].get("mode") == "in_place_revision"
        and isinstance(required, dict)
        and str(required.get("field", "")).strip() == "revision_selector"
    )
    if variant != "in_place_revision" and not legacy_default_revision:
        return False
    if _trace_values(state.get("revision_requirement_ids")):
        return False
    if isinstance(required, dict) and str(required.get("field", "")).strip() not in {"", "revision_selector"}:
        return False
    packet = state.get("confirmed_fact_packet")
    if not isinstance(packet, dict) or not packet or not _legacy_revision_baseline_matches(state):
        return False
    scope = packet.get("scope")
    if not isinstance(scope, dict):
        return False
    known = _trace_requirement_ids(_canonical_folder(state) / "prd.md")
    if not known:
        return False
    source_fields: list[str] = []
    candidates: list[str] = []
    goal = scope.get("goal")
    if isinstance(goal, str):
        candidates.extend(_extract_requirement_ids(goal, known))
        if candidates:
            source_fields.append("confirmed_fact_packet.scope.goal")
    in_scope = scope.get("in_scope")
    for item in _trace_values(in_scope):
        matched = _extract_requirement_ids(item, known)
        if matched:
            candidates.extend(matched)
            source_fields.append("confirmed_fact_packet.scope.in_scope")
    selected = list(dict.fromkeys(candidates))
    if len(selected) != 1:
        return False
    state["delivery_variant"] = "in_place_revision"
    state["task_mode"] = "prd_revision"
    state["revision_requirement_ids"] = selected
    state["revision_scope_manifest"] = {
        "mode": "in_place_revision",
        "requirement_ids": selected,
        "selectors": selected,
        "selector_status": "resolved",
        "authority": "legacy confirmed-fact-packet migration",
        "source_fields": list(dict.fromkeys(source_fields)),
        "baseline_verified": True,
    }
    state.pop("required_input", None)
    return True


def _confirmed_revision_scope_text(state: dict[str, Any]) -> str:
    """Collect only user-confirmed text used to form a revision contract."""
    latest = _confirmed_fact_source(state) if state.get("turns") or state.get("confirmed_fact_packet") else {}
    history = state.get("revision_history") if _delivery_variant(state) == "in_place_revision" else []
    latest_revision = history[-1] if isinstance(history, list) and history and isinstance(history[-1], dict) else {}
    values = [
        str(latest_revision.get("request", "")),
        str(state.get("raw_request", "")),
        str(latest.get("user_text", "")) if isinstance(latest, dict) else "",
        json.dumps(latest.get("scope", {}), ensure_ascii=False) if isinstance(latest, dict) else "",
        json.dumps(latest.get("decisions", []), ensure_ascii=False) if isinstance(latest, dict) else "",
    ]
    return "\n".join(item for item in values if item.strip())


def _confirmed_input_asset_digests(state: dict[str, Any]) -> dict[str, str]:
    """Allow only verified controller snapshots to become new revision assets."""
    return {
        str(record["asset_path"]): str(record["sha256"])
        for record in _input_asset_records(state, _canonical_folder(state))
    }


def _materialize_revision_scope_manifest(state: dict[str, Any]) -> dict[str, Any] | None:
    """Freeze a revision's local semantics after the user confirms them.

    Older runs retained only selected IDs.  Rebuild their contract from the
    frozen confirmation packet and untouched canonical baseline before a new
    delivery attempt, so recovery does not keep depending on a stale prompt.
    """
    if _delivery_variant(state) != "in_place_revision":
        return None
    canonical = _canonical_folder(state)
    prd_path = canonical / "prd.md"
    if not prd_path.is_file():
        return None
    selected = _trace_values(state.get("revision_requirement_ids"))
    if not selected:
        return None
    previous = state.get("revision_scope_manifest")
    previous = previous if isinstance(previous, dict) else {}
    manifest = build_revision_scope_manifest(
        baseline_markdown=prd_path.read_text(encoding="utf-8"),
        baseline_assets=_revision_asset_digests(canonical),
        requirement_ids=selected,
        confirmed_scope_text=_confirmed_revision_scope_text(state),
        authority=str(previous.get("authority", "user-confirmed revision scope")),
        selectors=_trace_values(previous.get("selectors")),
        allowed_new_assets=_confirmed_input_asset_digests(state),
    )
    manifest["selector_status"] = "resolved"
    state["revision_scope_manifest"] = manifest
    return manifest


def _delivery_input_question(state: dict[str, Any]) -> tuple[str, str]:
    """Return the exact next question for controller-owned delivery input gaps."""
    if _input_asset_problem(state):
        return (
            "input_assets",
            "已确认的图片或视频附件无法从控制器快照验证。请重新通过 --asset 附加原始文件；"
            "重新确认后才会继续生成，系统不会用现有图替代或猜测附件内容。",
        )
    if _delivery_variant(state) == "compose_to_new":
        if _extraction_source_configuration_problem(state):
            return (
                "extraction_source",
                "请指定要提取的旧 PRD 文件，并为每份来源明确要保留的需求 ID、章节标题或范围。",
            )
        return (
            "extraction_scope",
            "请明确每份旧 PRD 中要提取的需求 ID、章节标题或范围；同名需求请用 source-1: 5.1 或文件名.md: 5.1 区分。",
        )
    if _task_mode(state) == "implemented_feature_prd":
        return (
            "implementation_evidence",
            "请提供已检查的分支、diff、变更文件、行为和验证证据；缺少这些证据不能把已实现功能伪装成普通 PRD。",
        )
    return (
        "revision_selector",
        "请指定本次原地修改涉及的现有 PRD 需求 ID；范围不明确时不会改写整份文档。",
    )


def _confirmed_delivery_needs_input_field(state: dict[str, Any]) -> str | None:
    """Identify a delivery-level input pause without bypassing clarification pauses."""
    confirmation = state.get("user_confirmation")
    required = state.get("required_input")
    field = str(required.get("field", "")).strip() if isinstance(required, dict) else ""
    if (
        state.get("status") == "needs_input"
        and isinstance(confirmation, dict)
        and confirmation.get("confirmed")
        and field in {
            "extraction_source", "extraction_scope", "implementation_evidence", "revision_selector", "input_assets",
        }
    ):
        return field
    return None


def _migrate_stale_internal_scope_clarification(state: dict[str, Any]) -> bool:
    """Release old model-scope pauses that never represented a user question.

    Older controllers converted an unauthorized writer edit into a request for
    permission to broaden an already confirmed revision.  That is an internal
    repair condition, not missing product intent.  Preserve an audit marker but
    return the run to the ordinary confirmation checkpoint so ``--confirm`` can
    resume it with the controller-side constrained merge.
    """
    clarification = state.get("scope_clarification")
    confirmation = state.get("user_confirmation")
    required_input = state.get("required_input")
    clarification_review = state.get("clarification_review")
    if not (
        _delivery_variant(state) == "in_place_revision"
        and state.get("status") == "needs_input"
        and isinstance(clarification, dict)
        and clarification.get("artifact") == "prd.md"
        and isinstance(confirmation, dict)
        and confirmation.get("confirmed") is True
        and _trace_values(state.get("revision_requirement_ids"))
        and required_input in (None, {})
    ):
        return False
    if (
        isinstance(clarification_review, dict)
        and str(clarification_review.get("status", "")).strip().lower() == "needs_input"
    ):
        return False
    stale_question = str(clarification.get("question", "")).strip()
    violation = str(clarification.get("violation", "")).strip()
    if not stale_question or not violation:
        return False
    turns = state.get("turns")
    if not (isinstance(turns, list) and turns and isinstance(turns[-1], dict)):
        return False
    latest_turn = turns[-1]
    remaining_questions = [
        item for item in _trace_values(latest_turn.get("questions"))
        if item != stale_question
    ]
    buckets = latest_turn.get("buckets")
    remaining_must_answer = [
        item for item in _trace_values(buckets.get("must_answer_before_generation"))
        if item != stale_question
    ] if isinstance(buckets, dict) else []
    if remaining_questions or remaining_must_answer:
        return False
    state.setdefault("legacy_scope_clarification_migrations", []).append({
        "at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "artifact": "prd.md",
        "reason": "unauthorized writer edits are controller-repairable and do not require scope expansion",
    })
    state.pop("scope_clarification", None)
    state.pop("required_input", None)
    if isinstance(turns, list) and turns and isinstance(turns[-1], dict) and stale_question:
        turns[-1]["questions"] = [
            item for item in _trace_values(turns[-1].get("questions"))
            if item != stale_question
        ]
        buckets = turns[-1].get("buckets")
        if isinstance(buckets, dict):
            buckets["must_answer_before_generation"] = [
                item for item in _trace_values(buckets.get("must_answer_before_generation"))
                if item != stale_question
            ]
    state["status"] = "awaiting_confirmation"
    state["termination"] = "human_checkpoint"
    state["last_error"] = None
    state["resume_from_status"] = "needs_input"
    return True


def _resume_confirmed_delivery_after_cli_input(state: dict[str, Any], prior_field: str | None) -> bool:
    """Return a resolved delivery pause to confirmation after explicit new input.

    The user must still supply ``--confirm`` before delivery restarts. Other
    ``needs_input`` states, such as an unresolved scope violation, remain in
    place and continue through the normal clarification path.
    """
    if prior_field is None:
        return False
    problem = _delivery_input_problem(state, require_selection=True)
    if problem:
        field, question = _delivery_input_question(state)
        _set_needs_input(state, question, reason=problem, field=field)
        return False
    state.pop("required_input", None)
    state["status"] = "awaiting_confirmation"
    state["termination"] = "human_checkpoint"
    state["last_error"] = None
    state["resume_from_status"] = "needs_input"
    return True


def _submit_confirmed_delivery_answer(state: dict[str, Any], answer: str) -> bool:
    """Handle typed delivery input without reopening conversational intake.

    A confirmed delivery pause is not a new product discussion. Re-running the
    Intake Agent here can overwrite the frozen fact packet and turn a precise
    selector into an unrelated clarification loop. Only deterministic input
    shapes are consumed; every other delivery input remains at its own gate.
    """
    field = _confirmed_delivery_needs_input_field(state)
    if field is None:
        return False
    if field != "revision_selector":
        expected_field, question = _delivery_input_question(state)
        _set_needs_input(
            state,
            question,
            reason=(
                f"已确认交付所需的 {expected_field} 必须通过对应的受检输入提供；"
                "不会将本次文本回答重新解释为新的需求澄清。"
            ),
            field=expected_field,
        )
        return True
    normalized = answer.strip()
    if re.search(r"(?:\b(?:all|whole|entire)\b|整份|全部|全量|所有)", normalized, re.IGNORECASE):
        _set_needs_input(
            state,
            "请仅列出需要原地修改的现有 PRD 需求 ID；整份文档重写需要重新发起并明确确认范围。",
            reason="revision selector answer mixes a whole-document rewrite with requirement IDs",
            field="revision_selector",
        )
        return True
    selectors = list(dict.fromkeys(SOURCE_REQUIREMENT_ID_RE.findall(normalized)))
    if not selectors:
        _set_needs_input(
            state,
            "请指定本次原地修改涉及的现有 PRD 需求 ID；范围不明确时不会改写整份文档。",
            reason="revision selector answer did not contain an explicit requirement ID",
            field="revision_selector",
        )
        return True
    try:
        apply_revision_requirement_ids(state, selectors, authority="explicit user answer")
    except ValueError as error:
        _set_needs_input(
            state,
            "请指定存在于当前 PRD 中的需求 ID；范围不明确时不会改写整份文档。",
            reason=str(error),
            field="revision_selector",
        )
        return True
    answers = state.get("delivery_input_answers")
    if not isinstance(answers, list):
        answers = []
        state["delivery_input_answers"] = answers
    answers.append({
        "field": "revision_selector",
        "selectors": selectors,
        "source": "explicit --answers",
        "at": dt.datetime.now(dt.timezone.utc).isoformat(),
    })
    _resume_confirmed_delivery_after_cli_input(state, field)
    return True


def _needs_input_questions(state: dict[str, Any]) -> list[str]:
    """Read controller-owned questions even when no Intake Agent turn exists."""
    required = state.get("required_input")
    question = str(required.get("question", "")).strip() if isinstance(required, dict) else ""
    if question:
        return [question]
    turns = state.get("turns")
    if isinstance(turns, list) and turns and isinstance(turns[-1], dict):
        return _trace_values(turns[-1].get("questions"))
    return []


def _extraction_source_problem(state: dict[str, Any], *, require_selection: bool) -> str | None:
    if _delivery_variant(state) != "compose_to_new":
        return None
    sources = _extraction_sources(state)
    configuration_problem = _extraction_source_configuration_problem(state, sources)
    if configuration_problem:
        return configuration_problem
    for descriptor in sources:
        snapshot = _extraction_snapshot_path(state, descriptor)
        if snapshot is None or not snapshot.is_file():
            return "未提供可验证的旧 PRD 来源。请指定要提取的源文档。"
        expected = str(descriptor.get("sha256", "")).strip()
        if not expected or _artifact_digest(snapshot) != expected:
            return "旧 PRD 快照与已确认来源不一致；请重新指定来源并确认提取范围。"
        source_path = Path(str(descriptor.get("source_path", ""))).expanduser()
        if source_path.is_file() and _artifact_digest(source_path) != expected:
            return "原始旧 PRD 在确认后已发生变化；请重新确认要提取的范围。"
    if require_selection:
        return _extraction_selection_problem(state)
    return None


def _implemented_evidence_problem(state: dict[str, Any]) -> str | None:
    if _task_mode(state) != "implemented_feature_prd":
        return None
    evidence = state.get("implemented_feature_evidence")
    if not isinstance(evidence, dict):
        return "缺少已实现功能的实施证据包；请提供已检查的分支、diff、变更文件、行为和验证证据。"
    source = state.get("implemented_feature_evidence_source")
    packet = _implemented_evidence_packet_path(state)
    expected_packet_sha256 = str(source.get("packet_sha256", "")).strip() if isinstance(source, dict) else ""
    if packet is None or not expected_packet_sha256:
        return "已实现功能证据未固化为可校验的 source-material JSON 包；请重新提供实施证据。"
    if not packet.is_file() or _artifact_digest(packet) != expected_packet_sha256:
        return "已实现功能证据包与已确认哈希不一致；请重新提供并确认实施证据。"
    try:
        packet_evidence = _load_implemented_feature_evidence(packet)
    except ValueError as error:
        return f"已实现功能证据包不可读取：{error}"
    if packet_evidence != evidence:
        return "已实现功能证据状态与 source-material 证据包不一致；请重新提供实施证据。"
    result_refs_problem = _implemented_evidence_result_refs_problem(state, packet_evidence)
    if result_refs_problem:
        return result_refs_problem
    required = ("branch_name", "diff_commands", "changed_files", "behavior_evidence", "validation_evidence")
    for field in required:
        value = evidence.get(field)
        if not value or not isinstance(value, (str, list, tuple, dict)):
            return f"已实现功能证据包缺少 {field}；请补充后再生成 PRD。"
    return None


def _delivery_input_problem(state: dict[str, Any], *, require_selection: bool = True) -> str | None:
    asset_problem = _input_asset_problem(state)
    if asset_problem:
        return asset_problem
    if _delivery_variant(state) == "in_place_revision" and not _trace_values(state.get("revision_requirement_ids")):
        return "未明确原地修改的 PRD 需求 ID；请指定一个或多个现有需求 ID，或明确确认整份 PRD 都可重写。"
    return _extraction_source_problem(state, require_selection=require_selection) or _implemented_evidence_problem(state)


def _record_confirmed_extraction_selection(state: dict[str, Any]) -> None:
    """Freeze the source selection alongside the user's delivery confirmation."""
    if _delivery_variant(state) != "compose_to_new":
        return
    sources = _extraction_sources(state)
    if _extraction_source_configuration_problem(state, sources):
        return
    selected = _extraction_selection(state)
    if not selected:
        return
    resolutions, problem = _resolve_extraction_selection(state, selected)
    if problem:
        # Keep an unresolved selection in the current clarification packet, not
        # in immutable source state. A later user answer can then replace it.
        _clear_extraction_selection(state, sources)
        return
    groups = _extraction_resolution_groups(state, resolutions)
    state["extraction_selection"] = selected
    for descriptor in sources:
        source_id = str(descriptor.get("source_id", ""))
        group = groups.get(source_id, {"selected_scope": [], "scope_resolution": []})
        descriptor["selected_scope"] = list(group["selected_scope"])
        descriptor["selection_resolution"] = list(group["scope_resolution"])
        descriptor["selection_recorded_at"] = dt.datetime.now(dt.timezone.utc).isoformat()


def _record_revision(
    state: dict[str, Any], artifact: str, before: str | None, after: str | None,
    outcome: str,
) -> None:
    state.setdefault("revision_trace", []).append({
        "artifact": artifact,
        "before_sha256": before,
        "after_sha256": after,
        "outcome": outcome,
        "at": dt.datetime.now(dt.timezone.utc).isoformat(),
    })


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value[:48] or "interactive-request"


def resolved_output_root(cwd: Path | None = None) -> Path:
    """Use the invoking project, never the PM Copilot installation, for outputs."""
    context = resolve_project_workspace((cwd or Path.cwd()).resolve(), ensure=True)
    return Path(context["output_root"]).resolve()


def new_requirement_folder(request: str, root: Path | None = None) -> Path:
    """Allocate a canonical folder only for an explicitly new requirement."""
    root = (root or resolved_output_root()).resolve()
    stem = f"{_slug(request)}-{dt.datetime.now(dt.timezone.utc):%Y-%m-%d}"
    folder = root / stem
    if folder.exists():
        raise FileExistsError(
            f"Canonical PRD folder already exists: {folder}. Use --run-folder {folder} "
            "to revise that requirement; do not create a suffixed copy."
        )
    return folder


def _write_json(path: Path, value: dict[str, Any]) -> None:
    """Persist a run checkpoint without exposing a partially-written JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False,
    ) as temporary:
        temporary.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def _atomic_copy(source: Path, destination: Path) -> None:
    """Promote a complete staged artifact without exposing a partial replacement."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="wb", dir=destination.parent, prefix=f".{destination.name}.", delete=False) as temporary:
        with source.open("rb") as input_handle:
            shutil.copyfileobj(input_handle, temporary)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    temporary_path.replace(destination)


def _input_asset_path(root: Path, relative: str, *, label: str) -> Path:
    """Resolve a controller asset reference without permitting a root escape."""
    candidate_relative = Path(relative)
    if not relative or candidate_relative.is_absolute() or ".." in candidate_relative.parts:
        raise ValueError(f"{label} must stay inside the current run folder")
    root = root.resolve()
    candidate = root / candidate_relative
    try:
        candidate.resolve().relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} must stay inside the current run folder") from error
    return candidate


def _input_asset_manifest_file(root: Path) -> Path:
    """Return the one controller-owned manifest location for a run folder."""
    return _input_asset_path(
        root,
        INPUT_ASSET_MANIFEST_PATH.as_posix(),
        label="input asset manifest path",
    )


def _input_asset_snapshot_file(root: Path, digest: str) -> Path:
    """Resolve one content-addressed snapshot under the controller asset root."""
    return _input_asset_path(
        root,
        (INPUT_ASSET_SNAPSHOT_DIRECTORY / digest).as_posix(),
        label="input asset snapshot path",
    )


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value.lower()))


def _input_asset_manifest_descriptor(state: dict[str, Any]) -> dict[str, Any] | None:
    """Validate the state-held commitment before reading or rebuilding its file."""
    descriptor = state.get("input_asset_manifest")
    if descriptor is None:
        return None
    if not isinstance(descriptor, dict):
        raise ValueError("input asset snapshot manifest descriptor is malformed")
    if descriptor.get("schema_version") != INPUT_ASSET_MANIFEST_SCHEMA_VERSION:
        raise ValueError("input asset snapshot manifest uses an unsupported schema")
    if descriptor.get("manifest_path") != INPUT_ASSET_MANIFEST_PATH.as_posix():
        raise ValueError("input asset snapshot manifest path is not controller-owned")
    expected_digest = descriptor.get("manifest_sha256")
    if not _is_sha256(expected_digest):
        raise ValueError("input asset snapshot manifest is missing its SHA-256")
    count = descriptor.get("asset_count")
    if type(count) is not int or count < 0:
        raise ValueError("input asset snapshot manifest asset count is invalid")
    return {
        "schema_version": INPUT_ASSET_MANIFEST_SCHEMA_VERSION,
        "manifest_path": INPUT_ASSET_MANIFEST_PATH.as_posix(),
        "manifest_sha256": str(expected_digest).lower(),
        "asset_count": count,
    }


def _input_asset_manifest_payload(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": INPUT_ASSET_MANIFEST_SCHEMA_VERSION,
        "assets": list(records),
    }


def _input_asset_manifest_payload_digest(manifest: dict[str, Any]) -> str:
    """Match `_write_json` so a reattached manifest can be verified pre-write."""
    # `_write_json` uses a normal text file, whose default newline translation
    # is platform-native. Match it before comparing a durable byte digest.
    serialized = json.dumps(manifest, ensure_ascii=False, indent=2) + os.linesep
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _input_asset_record_from_source(source: Path) -> tuple[dict[str, Any], Path]:
    """Validate one caller file before it becomes durable controller input."""
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Input screenshot asset not found: {source}")
    if source.suffix.lower() not in SUPPORTED_INPUT_ASSET_SUFFIXES:
        raise ValueError(f"Unsupported PRD visual asset: {source.name}")
    digest = _artifact_digest(source)
    size = source.stat().st_size
    if not digest or size <= 0:
        raise ValueError(f"Input screenshot asset is empty or unreadable: {source.name}")
    name = source.name
    if not name or Path(name).name != name or not is_content_asset_relative_path(Path(name)):
        raise ValueError("Input screenshot asset must have a plain file name")
    return {
        "name": name,
        "asset_path": f"assets/{name}",
        "snapshot_path": (INPUT_ASSET_SNAPSHOT_DIRECTORY / digest).as_posix(),
        "sha256": digest,
        "size_bytes": size,
        "suffix": source.suffix.lower(),
    }, source


def _legacy_attested_input_asset_source(state: dict[str, Any], name: str) -> Path | None:
    """Recover a legacy path-only asset only from already hash-bound bytes.

    Older runs did not retain a snapshot manifest.  Their canonical ``assets/``
    directory is not generally trustworthy as a replacement for a vanished
    caller file, but a revision contract may already bind a particular input
    path to its SHA-256.  Only in that case can a surviving canonical asset be
    snapshotted without weakening the confirmation boundary.
    """
    manifest = state.get("revision_scope_manifest")
    allowed = manifest.get("allowed_new_assets") if isinstance(manifest, dict) else None
    expected = allowed.get(f"assets/{name}") if isinstance(allowed, dict) else None
    if not _is_sha256(expected):
        return None
    candidate = _input_asset_path(
        _canonical_folder(state), f"assets/{name}", label="legacy input asset path",
    )
    if candidate.is_symlink() or not candidate.is_file():
        return None
    return candidate if _artifact_digest(candidate) == str(expected).lower() else None


def _validated_input_asset_record(
    record: object, root: Path, *, verify_snapshot: bool = True,
) -> dict[str, Any]:
    """Validate an immutable asset record before a writer can consume it.

    Explicit ``--asset`` recovery may inspect a still-attested manifest before
    replacing a missing/corrupt snapshot with the same supplied bytes.  The
    normal read path always verifies both record shape and snapshot bytes.
    """
    if not isinstance(record, dict):
        raise ValueError("input asset manifest contains a non-mapping record")
    name = record.get("name")
    digest = record.get("sha256")
    asset_path = record.get("asset_path")
    snapshot_path = record.get("snapshot_path")
    size = record.get("size_bytes")
    suffix = record.get("suffix")
    if (
        not isinstance(name, str)
        or not name
        or Path(name).name != name
        or not is_content_asset_relative_path(Path(name))
    ):
        raise ValueError("input asset manifest record has an unsafe asset name")
    if not _is_sha256(digest):
        raise ValueError(f"input asset manifest record has an invalid SHA-256: {name}")
    digest = str(digest).lower()
    if not isinstance(asset_path, str) or asset_path != f"assets/{name}":
        raise ValueError(f"input asset manifest record has an invalid canonical asset path: {name}")
    expected_snapshot_path = (INPUT_ASSET_SNAPSHOT_DIRECTORY / digest).as_posix()
    if not isinstance(snapshot_path, str) or snapshot_path != expected_snapshot_path:
        raise ValueError(f"input asset manifest record has an invalid snapshot path: {name}")
    if not isinstance(size, int) or size <= 0:
        raise ValueError(f"input asset manifest record has an invalid size: {name}")
    if not isinstance(suffix, str) or suffix.lower() not in SUPPORTED_INPUT_ASSET_SUFFIXES:
        raise ValueError(f"input asset manifest record has an unsupported suffix: {name}")
    if Path(name).suffix.lower() != suffix.lower():
        raise ValueError(f"input asset manifest record suffix does not match its name: {name}")

    if verify_snapshot:
        snapshot = _input_asset_snapshot_file(root, digest)
        if snapshot.is_symlink() or not snapshot.is_file():
            raise ValueError(f"input asset snapshot is missing or not a regular file: {name}")
        if snapshot.stat().st_size != size or _artifact_digest(snapshot) != digest:
            raise ValueError(f"input asset snapshot SHA-256 does not match the manifest: {name}")
    return {
        "name": name,
        "asset_path": asset_path,
        "snapshot_path": snapshot_path,
        "sha256": digest,
        "size_bytes": size,
        "suffix": suffix.lower(),
    }


def _load_input_asset_manifest(
    state: dict[str, Any], root: Path, *, verify_snapshots: bool = True,
) -> list[dict[str, Any]]:
    """Load the state-bound immutable asset manifest from a canonical or stage root."""
    descriptor = _input_asset_manifest_descriptor(state)
    if descriptor is None:
        return []
    expected_digest = descriptor["manifest_sha256"]
    manifest_path = _input_asset_manifest_file(root)
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("input asset snapshot manifest is missing from the current run folder")
    if _artifact_digest(manifest_path) != expected_digest:
        raise ValueError("input asset snapshot manifest SHA-256 does not match controller state")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"input asset snapshot manifest is not readable JSON: {error}") from error
    if not isinstance(manifest, dict) or manifest.get("schema_version") != INPUT_ASSET_MANIFEST_SCHEMA_VERSION:
        raise ValueError("input asset snapshot manifest has an unsupported shape")
    raw_records = manifest.get("assets")
    if not isinstance(raw_records, list):
        raise ValueError("input asset snapshot manifest assets must be a list")
    declared_count = descriptor["asset_count"]
    if declared_count != len(raw_records):
        raise ValueError("input asset snapshot manifest asset count does not match controller state")

    records = [
        _validated_input_asset_record(item, root, verify_snapshot=verify_snapshots)
        for item in raw_records
    ]
    asset_paths = [str(item["asset_path"]) for item in records]
    if len(asset_paths) != len(set(asset_paths)):
        raise ValueError("input asset snapshot manifest contains duplicate canonical asset paths")
    return sorted(records, key=lambda item: (str(item["asset_path"]), str(item["sha256"])))


def _snapshot_input_assets(
    state: dict[str, Any], sources: Sequence[Path | str] = (),
) -> list[dict[str, Any]]:
    """Persist caller attachments once, then bind all future use to their hashes.

    ``input_assets`` used to hold transient caller paths.  This migration keeps
    an old run usable only while those paths still exist, then replaces them
    with controller-owned source-material records.  No recovery path reads a
    caller path after the manifest has been written.
    """
    root = _canonical_folder(state)
    descriptor = _input_asset_manifest_descriptor(state)
    # A supplied asset is allowed to repair its content-addressed snapshot, but
    # only after the manifest descriptor and record metadata remain attested.
    # Loading with byte verification first would reject the very recovery the
    # controller asks the user to perform.
    manifest_recovery = False
    if descriptor is None:
        existing: list[dict[str, Any]] = []
    else:
        try:
            existing = _load_input_asset_manifest(
                state, root, verify_snapshots=not bool(sources),
            )
        except ValueError:
            if not sources:
                raise
            # The state descriptor is still an immutable commitment. Rebuild
            # only from explicitly reattached bytes and require it to recreate
            # that exact committed manifest before replacing the damaged file.
            existing = []
            manifest_recovery = True
    legacy_sources = state.get("input_assets", []) if descriptor is None else []
    if not isinstance(legacy_sources, list):
        raise ValueError("input_assets must be a list before it is migrated to a snapshot manifest")

    # Explicitly supplied files take precedence over a stale legacy path with
    # the same output name, allowing a user to reattach a cleaned-up temporary
    # asset without accepting unknown bytes under that name.
    pending = [*sources, *legacy_sources]
    records_by_path = {str(record["asset_path"]): record for record in existing}
    source_by_digest: dict[str, Path] = {}
    seen_raw_paths: set[str] = set()
    for raw_source in pending:
        raw_text = str(raw_source).strip()
        if not raw_text or raw_text in seen_raw_paths:
            continue
        seen_raw_paths.add(raw_text)
        source_path = Path(raw_text).expanduser()
        try:
            record, resolved_source = _input_asset_record_from_source(source_path)
        except FileNotFoundError:
            # A newly supplied replacement with the same canonical path is
            # sufficient to migrate a stale legacy reference.  A missing path
            # without verified replacement bytes remains a hard input gap.
            legacy_name = source_path.name
            if legacy_name and f"assets/{legacy_name}" in records_by_path:
                continue
            recovered_source = _legacy_attested_input_asset_source(state, legacy_name) if legacy_name else None
            if recovered_source is None:
                raise
            record, resolved_source = _input_asset_record_from_source(recovered_source)
        previous = records_by_path.get(str(record["asset_path"]))
        if previous is not None and previous["sha256"] != record["sha256"]:
            raise FileExistsError(
                "Input screenshot asset name conflicts with another confirmed asset: "
                f"{record['name']}"
            )
        records_by_path[str(record["asset_path"])] = record
        source_by_digest[str(record["sha256"])] = resolved_source

    records = sorted(records_by_path.values(), key=lambda item: (str(item["asset_path"]), str(item["sha256"])))
    if descriptor is not None and not source_by_digest:
        return existing
    manifest = _input_asset_manifest_payload(records)
    if manifest_recovery and (
        len(records) != descriptor["asset_count"]
        or _input_asset_manifest_payload_digest(manifest) != descriptor["manifest_sha256"]
    ):
        raise ValueError(
            "input asset snapshot manifest cannot be recovered from the supplied files; "
            "reattach every originally confirmed asset with unchanged name and bytes"
        )

    snapshot_root = root / INPUT_ASSET_SNAPSHOT_DIRECTORY
    snapshot_root.mkdir(parents=True, exist_ok=True)
    for record in records:
        digest = str(record["sha256"])
        snapshot = _input_asset_snapshot_file(root, digest)
        source = source_by_digest.get(digest)
        if snapshot.exists():
            if snapshot.is_symlink() or not snapshot.is_file() or _artifact_digest(snapshot) != digest:
                if source is None:
                    raise ValueError(f"input asset snapshot conflicts with its recorded SHA-256: {record['name']}")
                _atomic_copy(source, snapshot)
        elif source is not None:
            _atomic_copy(source, snapshot)
        else:
            raise FileNotFoundError(f"input asset snapshot is missing: {record['name']}")
        if snapshot.stat().st_size != record["size_bytes"] or _artifact_digest(snapshot) != digest:
            raise ValueError(f"input asset snapshot copy could not be verified: {record['name']}")

    manifest_path = _input_asset_manifest_file(root)
    _write_json(manifest_path, manifest)
    manifest_digest = _artifact_digest(manifest_path)
    if not manifest_digest:
        raise ValueError("input asset snapshot manifest could not be persisted")
    if manifest_recovery and manifest_digest != descriptor["manifest_sha256"]:
        raise ValueError("input asset snapshot manifest changed while it was being recovered")
    state["input_asset_manifest"] = {
        "schema_version": INPUT_ASSET_MANIFEST_SCHEMA_VERSION,
        "manifest_path": INPUT_ASSET_MANIFEST_PATH.as_posix(),
        "manifest_sha256": manifest_digest,
        "asset_count": len(records),
    }
    # Do not retain private or short-lived caller paths in a resumable run.
    # The list remains for backwards-compatible state readers, but now points
    # only at controller-owned content-addressed snapshots.
    state["input_assets"] = [str(record["snapshot_path"]) for record in records]
    return records


def register_input_assets(state: dict[str, Any], sources: Sequence[Path | str]) -> list[dict[str, Any]]:
    """Accept user visual inputs by snapshotting them before confirmation or staging."""
    if not sources:
        return _load_input_asset_manifest(state, _canonical_folder(state))
    return _snapshot_input_assets(state, sources)


def _input_asset_records(state: dict[str, Any], root: Path | None = None) -> list[dict[str, Any]]:
    """Return only verified snapshot records, migrating readable legacy state once."""
    canonical = _canonical_folder(state)
    if state.get("input_asset_manifest") is None and state.get("input_assets"):
        _snapshot_input_assets(state)
    return _load_input_asset_manifest(state, (root or canonical).resolve())


def _input_asset_problem(state: dict[str, Any]) -> str | None:
    """Convert stale/tampered attachment state into a pre-Agent input gate."""
    if state.get("input_asset_manifest") is None and not state.get("input_assets"):
        return None
    try:
        _input_asset_records(state, _canonical_folder(state))
    except (FileNotFoundError, FileExistsError, ValueError) as error:
        return (
            "已确认的图片或视频附件快照不可用、越出当前运行目录或与记录哈希不一致；"
            f"请通过 --asset 重新附加原始文件后重新确认。详情：{error}"
        )
    return None


def _atomic_write_text(path: Path, value: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as temporary:
        temporary.write(value)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def _checkpoint(state: dict[str, Any], state_path: Path | None) -> None:
    if state_path is not None:
        _write_json(state_path, state)


def _stage(state: dict[str, Any], artifact: str) -> dict[str, Any]:
    return state.setdefault("delivery_stages", {}).setdefault(artifact, {})


def _quarantine_unconfirmed_workspace(
    state: dict[str, Any], workspace_root: Path, artifact: str, phase: str,
    result: dict[str, Any],
) -> Path | None:
    """Keep an unknown detached writer away from both retries and cleanup.

    A launch without trustworthy terminal evidence may still have been
    accepted by its executor. Moving its private stage aside preserves that
    evidence and ensures a later user-confirmed retry starts in a distinct
    workspace instead of racing the unconfirmed writer.
    """
    canonical_name = _canonical_folder(state).name
    destination = workspace_root.with_name(
        f".{canonical_name}.quarantine-{phase}-{time.time_ns()}"
    )
    try:
        workspace_root.replace(destination)
    except OSError:
        return None
    record = {
        "phase": phase,
        "artifact": artifact,
        "path": str(destination),
        "failure_category": result.get("failure_category"),
        "agent_id": result.get("agent_id"),
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    state.setdefault("quarantined_workspaces", []).append(record)
    state["status"] = "recovery_required"
    state["termination"] = "retry_required"
    state["recovery"] = {
        "status": "isolation_required",
        "failed_stage": artifact,
        "failure_category": result.get("failure_category"),
        "message": "Agent launch or cleanup is unconfirmed; its isolated workspace was quarantined before any retry.",
        "quarantined_workspace": str(destination),
        "retry_entry": "--confirm",
    }
    return destination


def _delivery_folder(state: dict[str, Any]) -> Path:
    """Return the unpromoted workspace while a confirmed delivery is running."""
    return Path(str(state.get("delivery_workspace") or state["folder"])).resolve()


def _discard_non_content_assets(folder: Path) -> list[str]:
    """Remove filesystem metadata from an isolated PRD asset tree.

    A delivery workspace is intentionally a content copy rather than a mirror
    of Finder/Explorer state. This keeps copied stages aligned with the asset
    manifest and never mutates the pre-promotion canonical directory.
    """
    assets = folder / "assets"
    if not assets.is_dir():
        return []
    discarded: list[str] = []
    for path in sorted(assets.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        relative = path.relative_to(assets)
        if is_content_asset_relative_path(relative):
            continue
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
        discarded.append(relative.as_posix())
    return sorted(discarded)


def _assert_delivery_tree_has_no_symlinks(folder: Path, *, label: str) -> None:
    """Reject links before an isolated delivery copy can dereference them.

    Delivery workspaces are durable artifact trees, not a filesystem overlay.
    ``copytree`` follows links by default, which otherwise permits a link in a
    prior run's assets, source material, or tool results to silently turn into
    external bytes in staging. Scan the complete run tree so each copy and
    promotion path shares the same boundary rather than protecting assets only
    during an in-place revision.
    """
    if folder.is_symlink():
        raise ValueError(f"{label} must not be a symbolic link")
    if not folder.is_dir():
        raise ValueError(f"{label} is not a directory")
    links: list[str] = []
    try:
        for root, directories, files in os.walk(folder, followlinks=False):
            root_path = Path(root)
            for name in [*directories, *files]:
                path = root_path / name
                if path.is_symlink():
                    links.append(path.relative_to(folder).as_posix())
    except OSError as error:
        raise ValueError(f"{label} could not be inspected for symbolic links: {error}") from error
    if links:
        raise ValueError(
            f"{label} must not contain symbolic links: " + ", ".join(sorted(links))
        )


def _snapshot_delivery_workspace(source: Path, snapshot: Path) -> None:
    """Freeze a real workspace before an Agent receives only its isolated copy."""
    _assert_delivery_tree_has_no_symlinks(source, label="delivery workspace")
    shutil.copytree(source, snapshot, symlinks=True)


def _restore_delivery_workspace_snapshot(snapshot: Path, destination: Path) -> None:
    """Undo every out-of-stage write before a staged artifact can be promoted."""
    _assert_delivery_tree_has_no_symlinks(snapshot, label="delivery workspace snapshot")
    if destination.exists() or destination.is_symlink():
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        else:
            destination.unlink()
    shutil.copytree(snapshot, destination, symlinks=True)
    _assert_delivery_tree_has_no_symlinks(destination, label="restored delivery workspace")


def _canonical_folder(state: dict[str, Any]) -> Path:
    return Path(str(state["folder"])).resolve()


def _is_retryable_agent_failure(result: dict[str, Any]) -> bool:
    detail = " ".join(str(result.get(key, "")) for key in ("status", "error", "output")).lower()
    return (
        "stream disconnected" in detail
        or "stream_disconnected" in detail
        or result.get("failure_category") == "agent_no_output"
        or result.get("failure_category") in {
            "agent_execution_error", "agent_no_progress", "agent_timeout", "agent_launch_error",
        }
    )


def _delivery_worker(
    provider: str, prompt: str, cwd: Path, timeout: int, model: str | None,
    schema: str | None, dry_run: bool, output_limit: int,
) -> dict[str, Any]:
    """PRD content stages use the full stage deadline, not a first-write deadline."""
    return execute(
        provider, prompt, cwd, timeout, model, schema, dry_run, output_limit,
        first_artifact_seconds=None,
    )


def _normalise_trace_runtime_evidence(
    run_log: Path, runtime_identity: Mapping[str, Any] | None = None,
) -> int:
    """Keep controller-owned runtime provenance and figure hashes tied to promoted bytes."""
    try:
        trace = yaml.safe_load(run_log.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        # Keep an invalid Agent-written trace available to the trace validator;
        # normalisation must not hide the original parsing failure.
        return 0
    if not isinstance(trace, dict):
        return 0

    identity = dict(runtime_identity) if isinstance(runtime_identity, Mapping) else _runtime_identity()
    trace["pm_copilot_version"] = str(identity["version"])
    trace["runtime_identity"] = identity
    updated = 0
    root = run_log.parent.resolve()

    def refresh_asset(record: object) -> None:
        nonlocal updated
        if not isinstance(record, dict):
            return
        raw_path = record.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            return
        asset = (root / raw_path.strip()).resolve()
        try:
            asset.relative_to(root)
        except ValueError:
            return
        if not asset.is_file():
            return
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        if record.get("asset_sha256") != digest:
            record["asset_sha256"] = digest
            updated += 1

    def refresh_figure_assets(record: object) -> None:
        """Refresh the primary figure and any controller-declared variants."""
        if not isinstance(record, dict) or record.get("kind") not in {"real_capture", "reconstructed"}:
            return
        refresh_asset(record)
        for key in ("additional_assets", "asset_variants"):
            children = record.get(key)
            if isinstance(children, list):
                for child in children:
                    refresh_asset(child)

    figures = trace.get("frontend_figure_evidence")
    if isinstance(figures, list):
        for item in figures:
            refresh_figure_assets(item)

    _atomic_write_text(
        run_log,
        yaml.safe_dump(trace, allow_unicode=True, sort_keys=False, default_flow_style=False),
    )
    return updated


def _replace_trace_section(text: str, section: str, replacement: str) -> str:
    """Replace one top-level YAML section without exposing partial trace bytes."""
    pattern = rf"(?ms)^{re.escape(section)}:\n.*?(?=^[A-Za-z_][A-Za-z0-9_]*:\n|\Z)"
    updated, count = re.subn(pattern, replacement.rstrip() + "\n\n", text, count=1)
    if count == 1:
        return updated
    # Historical in-place traces may predate newer contract sections. Append
    # the controller-owned section so a revision can be migrated atomically.
    if re.search(rf"(?m)^{re.escape(section)}:", text):
        raise ValueError(f"run-log.yaml has malformed {section} section")
    return text.rstrip() + "\n\n" + replacement.rstrip() + "\n"


def _trace_values(value: object) -> list[str]:
    """Normalize controller state into compact, non-empty YAML list values."""
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _trace_requirement_ids(prd_path: Path) -> list[str]:
    """Read only stable PRD requirement identifiers from the staged artifact."""
    if not prd_path.is_file():
        return []
    return requirement_ids(prd_path.read_text(encoding="utf-8"))


def _implemented_requirement_coverage_review(
    prd_path: Path, implemented_evidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Build controller-owned coverage from final PRD rows and immutable evidence.

    The trace must not infer a visual decision from a generated PRD.  For an
    implemented-feature delivery, the immutable evidence packet is the sole
    source for that decision and its rationale.  Localization and tracking are
    delivery decisions expressed by final PRD sections, so those are derived
    from the staged bytes rather than a model response.
    """
    if not prd_path.is_file():
        return []
    prd_text = prd_path.read_text(encoding="utf-8")
    final_requirement_ids = requirement_ids(prd_text)
    visual_evidence = implemented_evidence.get("screenshots_and_placeholders")
    if not isinstance(visual_evidence, list):
        raise ValueError(
            "implemented-feature trace requires screenshots_and_placeholders in immutable evidence"
        )
    visual_by_requirement, visual_failures = aggregate_visual_evidence_by_requirement(
        visual_evidence, final_requirement_ids,
    )
    if visual_failures:
        raise ValueError("implemented-feature trace visual evidence is invalid: " + "; ".join(visual_failures))

    localization_rows, unlinked_localization_rows = requirement_linked_rows(
        prd_text,
        ("多语言需求", "localization requirements", "i18n requirements"),
    )
    tracking_rows, unlinked_tracking_rows = requirement_linked_rows(
        prd_text,
        ("埋点需求", "tracking requirements", "analytics requirements"),
    )
    if unlinked_localization_rows:
        raise ValueError(
            "implemented-feature PRD localization rows must explicitly link to final requirement IDs"
        )
    if unlinked_tracking_rows:
        raise ValueError(
            "implemented-feature PRD tracking rows must explicitly link to final requirement IDs"
        )
    coverage: list[dict[str, Any]] = []
    for requirement_id in final_requirement_ids:
        visual = visual_by_requirement.get(requirement_id)
        # Automatic repository collection happens before a writer determines
        # final IDs. A missing final-ID capture stays an explicit manual-
        # completion requirement rather than becoming an invented figure.
        if visual is None:
            visual = {
                "decision": "required_placeholder",
                "rationales": ["No final-ID-specific capture was available; retain a controlled manual-completion figure requirement."],
                "records": [],
            }
        localization_count = len(localization_rows.get(requirement_id, []))
        tracking_count = len(tracking_rows.get(requirement_id, []))
        coverage.append({
            "requirement_id": requirement_id,
            "visual_decision": visual["decision"],
            "visual_rationale": "；".join(visual["rationales"]),
            "visual_evidence_count": len(visual["records"]),
            "localization_decision": "included" if localization_count else "not_needed",
            "localization_rationale": (
                f"{localization_count} localization checklist row(s) explicitly link to requirement {requirement_id}."
                if localization_count else
                f"No localization checklist row explicitly links to requirement {requirement_id}."
            ),
            "tracking_decision": "included" if tracking_count else "not_needed",
            "tracking_rationale": (
                f"{tracking_count} tracking row(s) explicitly link to requirement {requirement_id}."
                if tracking_count else
                f"No tracking row explicitly links to requirement {requirement_id}."
            ),
            "measurable_actions": [],
            "measurable_outcomes": [],
        })
    return coverage


def _trace_frontend_figure_evidence(
    state: Mapping[str, Any], implemented_evidence: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Preserve auditable figure facts without copying the full evidence packet.

    Implemented-feature evidence remains immutable in ``source-material``. The
    trace carries only the packet reference plus a compact, final-artifact view
    of figures created or retained for this delivery. This keeps reconstructed
    captures visible while retaining the packet as the authority for coverage.
    """
    records: list[tuple[Mapping[str, Any], bool]] = []
    if isinstance(implemented_evidence, Mapping):
        supplied = implemented_evidence.get("screenshots_and_placeholders")
        if isinstance(supplied, list):
            records.extend((item, True) for item in supplied if isinstance(item, Mapping))
    controller_records = state.get("frontend_figure_evidence")
    if isinstance(controller_records, list):
        records.extend((item, False) for item in controller_records if isinstance(item, Mapping))

    kind_by_provenance = {
        "real_figure": "real_capture",
        "real_capture": "real_capture",
        "reconstructed_figure": "reconstructed",
        "reconstructed": "reconstructed",
        "required_placeholder": "placeholder",
        "placeholder": "placeholder",
    }
    figures: list[dict[str, Any]] = []
    for record, from_immutable_packet in records:
        provenance = str(
            record.get("provenance") or record.get("kind") or record.get("coverage_decision") or ""
        ).strip()
        if provenance == "not_required":
            continue
        kind = kind_by_provenance.get(provenance, "placeholder")
        figure: dict[str, Any] = {
            "requirement_id": str(record.get("target_ref") or record.get("requirement_id") or "").strip(),
            "kind": kind,
            "path": str(record.get("path") or "").strip(),
            "asset_sha256": str(record.get("asset_sha256") or "").strip(),
            "source": str(
                record.get("capture_source")
                or record.get("capture_report")
                or record.get("reconstruction_path")
                or ""
            ).strip(),
            "rationale": str(record.get("rationale") or "").strip(),
        }
        if kind == "placeholder":
            figure["missing_reason"] = str(
                record.get("missing_reason")
                or record.get("capture_error")
                or (
                    "No verified local frontend capture was supplied in the immutable evidence packet."
                    if from_immutable_packet else
                    "The isolated reconstruction did not produce a local figure."
                )
            ).strip()
            figure["replacement_action"] = str(
                record.get("replacement_action")
                or record.get("replacement_instruction")
                or "Capture the required frontend state and attach it to this PRD delivery."
            ).strip()
        figures.append(figure)
    return figures


def _trace_language(state: dict[str, Any], prd_path: Path) -> str:
    explicit = str(state.get("language", "")).strip().lower()
    if explicit in {"zh", "en"}:
        return explicit
    evidence = str(state.get("raw_request", ""))
    if prd_path.is_file():
        evidence += prd_path.read_text(encoding="utf-8")[:4000]
    return "zh" if re.search(r"[\u3400-\u9fff]", evidence) else "en"


def _trace_scope_ids(state: dict[str, Any], prd_path: Path) -> list[str]:
    """Return the IDs confirmed at the revision gate, including deleted IDs.

    A deletion intentionally makes an ID absent from the candidate PRD. The
    lineage must retain the original confirmed selector rather than rewriting
    scope history to only the IDs which happen to remain in the final file.
    """
    current_ids = _trace_requirement_ids(prd_path)
    if _is_implemented_feature_append(state):
        return _trace_values(state.get("append_requirement_ids"))
    requested = _trace_values(state.get("revision_requirement_ids"))
    if not requested and _delivery_variant(state) == "in_place_revision" and state.get("revision_history"):
        requested = _extract_requirement_ids(
            str(state["revision_history"][-1].get("request", state.get("raw_request", ""))),
            current_ids,
        )
    return list(dict.fromkeys(requested))


def _revision_baseline_requirement_ids(state: dict[str, Any], prd_path: Path) -> list[str]:
    """Return the requirement inventory frozen before an in-place revision."""
    if _delivery_variant(state) != "in_place_revision":
        return []
    history = state.get("revision_history")
    latest = history[-1] if isinstance(history, list) and history and isinstance(history[-1], dict) else {}
    recorded = _trace_values(latest.get("baseline_requirement_ids"))
    if recorded:
        return list(dict.fromkeys(recorded))
    staged_baseline = prd_path.parent / ".revision-baseline" / "prd.md"
    staged_ids = _trace_requirement_ids(staged_baseline)
    # A legacy trace can be materialized directly in the canonical folder,
    # where no isolated baseline survives. In that compatibility path the
    # current PRD is the only available before-state inventory.
    return staged_ids or _trace_requirement_ids(prd_path)


def _deleted_revision_requirement_ids(state: dict[str, Any], prd_path: Path) -> list[str]:
    """Identify confirmed selectors intentionally absent from the staged PRD."""
    baseline_ids = set(_revision_baseline_requirement_ids(state, prd_path))
    if not baseline_ids:
        return []
    current_ids = set(_trace_requirement_ids(prd_path))
    return [
        requirement_id
        for requirement_id in _trace_scope_ids(state, prd_path)
        if requirement_id in baseline_ids and requirement_id not in current_ids
    ]


def _trace_lineage(state: dict[str, Any], prd_path: Path) -> dict[str, Any]:
    variant = _delivery_variant(state)
    revision = variant == "in_place_revision"
    scope_ids = _trace_scope_ids(state, prd_path)
    deleted_ids = _deleted_revision_requirement_ids(state, prd_path) if revision else []
    if variant == "compose_to_new":
        sources = _extraction_sources(state)
        configuration_problem = _extraction_source_configuration_problem(state, sources)
        if configuration_problem:
            raise ValueError(configuration_problem)
        selected_scope = _extraction_selection(state)
        selection_problem = _extraction_selection_problem(state)
        if selection_problem:
            raise ValueError(selection_problem)
        resolutions, resolution_problem = _resolve_extraction_selection(state, selected_scope)
        if resolution_problem:
            raise ValueError(resolution_problem)
        groups = _extraction_resolution_groups(state, resolutions)
        source_prds: list[dict[str, Any]] = []
        for descriptor in sources:
            source_id = str(descriptor.get("source_id", "")).strip()
            snapshot = _extraction_snapshot_path(state, descriptor)
            source_sha256 = str(descriptor.get("sha256", "")).strip()
            if not source_id or snapshot is None or not source_sha256:
                raise ValueError("extraction trace requires immutable source PRD snapshots")
            if _artifact_digest(snapshot) != source_sha256:
                raise ValueError("extraction trace source PRD snapshot hash is not current")
            group = groups.get(source_id, {"selected_scope": [], "scope_resolution": []})
            local_scope = list(group["selected_scope"])
            local_resolution = list(group["scope_resolution"])
            if not local_scope:
                raise ValueError(f"extraction trace source {source_id} has no confirmed selected scope")
            source_prds.append({
                "source_id": source_id,
                "snapshot_path": str(descriptor.get("snapshot_path", "")),
                "display_name": str(descriptor.get("display_name", "")),
                "sha256": source_sha256,
                "selected_scope": local_scope,
                "scope_resolution": local_resolution,
            })
        legacy = source_prds[0] if len(source_prds) == 1 else None
        return {
            "mode": "composition_run",
            "target_prd_path": "",
            "target_html_path": "",
            "revision_evidence_path": "",
            "revised_requirement_ids": [],
            "deleted_requirement_ids": [],
            # Keep the original one-source fields so an old installed
            # validator can still inspect a newly generated one-source run.
            "source_snapshot_path": legacy["snapshot_path"] if legacy else "",
            "source_prd_display_name": legacy["display_name"] if legacy else "",
            "source_prd_sha256": legacy["sha256"] if legacy else "",
            "selected_source_scope": legacy["selected_scope"] if legacy else [],
            "source_scope_resolution": legacy["scope_resolution"] if legacy else [],
            "source_prds": source_prds,
            "historical_artifacts": [{
                "path": source["snapshot_path"],
                "role": "user_provided_input",
                "excluded_from_current_facts": False,
            } for source in source_prds],
        }
    return {
        "mode": "in_place_revision" if revision else "new_run",
        "target_prd_path": "prd.md" if revision else "",
        "target_html_path": "prd.html" if revision else "",
        "revision_evidence_path": "revision-evidence.json" if revision else "",
        "revised_requirement_ids": scope_ids,
        "deleted_requirement_ids": deleted_ids,
        "source_snapshot_path": "",
        "source_prd_display_name": "",
        "source_prd_sha256": "",
        "selected_source_scope": [],
        "source_scope_resolution": [],
        "source_prds": [],
        "historical_artifacts": (
            [{"path": "prd.md", "role": "comparison_only", "excluded_from_current_facts": True}]
            if revision else []
        ),
    }


def _materialize_revision_evidence(state: dict[str, Any], target: Path) -> None:
    """Persist the before-state proof for any in-place update before promotion."""
    if _delivery_variant(state) != "in_place_revision":
        return
    history = state.get("revision_history") or []
    if not history:
        return
    manifest = state.get("revision_scope_manifest")
    if isinstance(manifest, Mapping) and manifest.get("schema_version") == 1:
        _, attestation_problems = _final_revision_scope_attestation_problems(state, target.parent)
        if attestation_problems:
            raise ValueError(
                "cannot materialize revision evidence before final artifact-set attestation: "
                + "; ".join(attestation_problems)
            )
    latest = history[-1]
    prd_path = target.parent / "prd.md"
    _write_json(target.parent / "revision-evidence.json", {
        "mode": "in_place_revision",
        "request": latest.get("request", state.get("raw_request", "")),
        "prd_before_sha256": latest.get("prd_before_sha256"),
        "html_before_sha256": latest.get("html_before_sha256"),
        "recorded_at": latest.get("at"),
        "controller_scope_ids": _trace_scope_ids(state, prd_path),
        "deleted_requirement_ids": _deleted_revision_requirement_ids(state, prd_path),
        "baseline_requirement_ids": _revision_baseline_requirement_ids(state, prd_path),
        "scope_manifest": state.get("revision_scope_manifest", {}),
        "scope_validation": state.get("revision_scope_validation", {
            "status": "not_run",
            "report_path": "tool-results/revision-scope-validation.json",
        }),
    })


def _materialize_controller_trace(state: dict[str, Any], target: Path) -> None:
    """Write only the evidence needed to audit one of the four PRD workflows."""
    problem = _delivery_input_problem(state, require_selection=True)
    if problem:
        raise ValueError(problem)

    prd_path = target.parent / "prd.md"
    latest = _confirmed_fact_source(state) if state.get("turns") or state.get("confirmed_fact_packet") else {}
    scope = latest.get("scope", {}) if isinstance(latest, dict) else {}
    scope = scope if isinstance(scope, dict) else {}
    task_mode = _task_mode(state)
    lineage = _trace_lineage(state, prd_path)
    revision = lineage["mode"] == "in_place_revision"
    runtime_identity = _state_runtime_identity(state)
    goal = str(scope.get("goal") or state.get("raw_request") or "Produce the confirmed PRD delivery").strip()
    confirmed_scope = _trace_values(scope.get("in_scope")) or [goal]

    if task_mode == "implemented_feature_prd":
        evidence = state.get("implemented_feature_evidence")
        source = state.get("implemented_feature_evidence_source")
        if not isinstance(evidence, dict) or not isinstance(source, dict):
            raise ValueError("implemented-feature trace requires a verified implementation evidence packet")
        implemented = {
            "active": True,
            "evidence_packet": {
                "path": str(source.get("packet_path") or ""),
                "sha256": str(source.get("packet_sha256") or ""),
            },
        }
        requirement_coverage_review = _implemented_requirement_coverage_review(prd_path, evidence)
    else:
        implemented = {"active": False, "evidence_packet": {}}
        evidence = None
        requirement_coverage_review = []

    specialist_evidence = [
        dict(item) for item in state.get("specialist_evidence", [])
        if isinstance(item, Mapping)
    ]
    figures = _trace_frontend_figure_evidence(state, evidence)
    arbitration_sources = [
        item for item in specialist_evidence
        if (
            str(item.get("status") or "") == "failed"
            or item.get("adopted") is False
            or bool(item.get("conflict"))
            or item.get("requires_pm_arbitration") is True
        )
    ]
    confirmation = state.get("user_confirmation")
    confirmed_at = (
        str(confirmation.get("at") or confirmation.get("confirmed_at") or "").strip()
        if isinstance(confirmation, Mapping) else ""
    )
    if not confirmed_at:
        packet_confirmed_at = latest.get("confirmed_at") if isinstance(latest, Mapping) else ""
        confirmed_at = str(packet_confirmed_at or state.get("confirmed_at") or "").strip()

    trace = {
        "run_id": target.parent.name,
        "date": dt.datetime.now(dt.timezone.utc).date().isoformat(),
        "language": _trace_language(state, prd_path),
        "pm_copilot_version": str(runtime_identity["version"]),
        "pm_copilot_revision": CONTROLLER_TRACE_REVISION,
        "runtime_identity": runtime_identity,
        "task": {"raw_request": str(state.get("raw_request") or ""), "request_source": "conversation"},
        "agent_strategy": {"task_mode": task_mode, "goal": goal},
        "confirmation": {
            "status": "confirmed",
            "scope": confirmed_scope,
            "confirmed_at": confirmed_at,
        },
        "artifact_lineage": {
            "mode": "implemented_feature_run" if task_mode == "implemented_feature_prd" else lineage["mode"],
            "source_prds": lineage.get("source_prds", []),
            "revision_baseline": (
                state.get("revision_scope_manifest")
                or (state.get("revision_history") or [{}])[-1]
                if revision else {}
            ),
            "revised_requirement_ids": lineage.get("revised_requirement_ids", []),
            "revision_evidence_path": "revision-evidence.json" if revision else "",
            "linked_changes": [],
        },
        "implemented_feature_prd": implemented,
        "frontend_figure_evidence": figures,
        "requirement_coverage_review": requirement_coverage_review,
        "specialist_evidence": specialist_evidence,
        "pm_arbitration": {"decisions": ([{
            "id": "PM-1", "owner": "PM Orchestrator",
            "decision": "The PM Orchestrator evaluated the unresolved specialist evidence against the confirmed scope.",
            "evidence_ids": [str(item.get("id") or "") for item in arbitration_sources],
        }] if arbitration_sources else [])},
        "review": {"status": "pending", "findings": []},
        "validation_results": [
            {"command": command, "status": "pending"}
            for command in ("render_prd_html.py", "validate_outputs.py", "validate_agent_trace.py", "run_delivery_checks.py")
        ],
        "quality_decision": {"passed": False, "rationale": "final validation pending"},
        "failures": [],
        "final_status": "staged delivery awaiting validation",
    }
    if revision:
        _materialize_revision_evidence(state, target)
    _atomic_write_text(target, yaml.safe_dump(trace, allow_unicode=True, sort_keys=False, default_flow_style=False))
    _normalise_trace_runtime_evidence(target, runtime_identity)


def _copy_input_assets(state: dict[str, Any], destination: Path) -> None:
    assets = destination / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for record in _input_asset_records(state, destination):
        source = _input_asset_snapshot_file(destination, str(record["sha256"]))
        target = _input_asset_path(destination, str(record["asset_path"]), label="input asset output path")
        if target.is_symlink():
            raise ValueError(f"Input screenshot asset target must not be a symlink: {record['name']}")
        if target.exists() and _artifact_digest(target) != record["sha256"]:
            raise FileExistsError(
                "Input screenshot asset name conflicts with an existing canonical asset: "
                f"{record['name']}"
            )
        if not target.exists():
            _atomic_copy(source, target)
        if _artifact_digest(target) != record["sha256"]:
            raise ValueError(f"Input screenshot asset copy could not be verified: {record['name']}")


def _validate_input_asset_materialization(state: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    """Require every confirmed attachment to match its durable snapshot.

    The manifest attests the controller-owned source bytes, but a delivery
    Agent can still overwrite the separately published ``assets/<name>`` file
    in its isolated workspace.  Recheck both the manifest/snapshot and the
    materialized output immediately before validation and promotion so neither
    a stale file nor a different same-name image can enter the canonical PRD.
    """
    records = _input_asset_records(state, root)
    for record in records:
        target = _input_asset_path(root, str(record["asset_path"]), label="input asset output path")
        if target.is_symlink() or not target.is_file():
            raise ValueError(
                f"confirmed input asset is missing or not a regular file: {record['name']}"
            )
        if target.stat().st_size != record["size_bytes"] or _artifact_digest(target) != record["sha256"]:
            raise ValueError(
                f"confirmed input asset SHA-256 does not match controller snapshot: {record['name']}"
            )
    return records


def _runtime_identity() -> dict[str, Any]:
    """Return a copy of this process's import-time runtime identity.

    Do not replace this with a fresh file read.  A controller can remain alive
    while an installer updates the runtime directory; the process keeps the
    Python code it imported, so its trace must keep this original identity.
    """
    return json.loads(json.dumps(_PROCESS_RUNTIME_IDENTITY, sort_keys=True))


def _has_complete_runtime_identity(identity: object) -> bool:
    """Accept only current, bounded identities for cache reuse.

    Earlier identities contained just a controller and plugin digest.  They
    cannot establish that the validator/template/runtime contract was the same,
    so reusable delivery artifacts produced under that shape are never trusted.
    """
    return not complete_runtime_identity_failures(identity)


def _runtime_identities_match(left: object, right: object) -> bool:
    """Compare the complete loaded-runtime identity used for reusable work."""
    if not _has_complete_runtime_identity(left) or not _has_complete_runtime_identity(right):
        return False
    return json.dumps(left, ensure_ascii=False, sort_keys=True, separators=(",", ":")) == json.dumps(
        right, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _freeze_delivery_runtime_identity(state: dict[str, Any]) -> dict[str, Any]:
    """Replace any persisted identity before a new controller attempt starts."""
    identity = _runtime_identity()
    state["active_runtime_identity"] = identity
    return identity


def _state_runtime_identity(state: Mapping[str, Any]) -> dict[str, Any]:
    recorded = state.get("active_runtime_identity")
    process_identity = _runtime_identity()
    if _runtime_identities_match(recorded, process_identity):
        return dict(recorded)
    return process_identity


def _reusable_delivery_runtime_identity(state: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return persisted identity only when it authorizes retry-cache reuse.

    Trace provenance can truthfully fall back to the currently loaded process
    when an old state has no usable identity.  A retry cache is different: it
    is authorization to copy artifacts from a prior workspace, so a missing,
    stale, or tampered persisted identity must fail closed instead of being
    silently relabelled with the current process identity.
    """
    recorded = state.get("active_runtime_identity")
    process_identity = _runtime_identity()
    if not _runtime_identities_match(recorded, process_identity):
        return None
    return dict(recorded)


def _state_runtime_version(state: Mapping[str, Any]) -> str:
    return str(_state_runtime_identity(state)["version"])


def _active_runtime_version() -> str:
    """Return the process-frozen version used by delivery provenance."""
    return _runtime_identity()["version"]


def _confirmed_scope_fingerprint(state: dict[str, Any]) -> str:
    """Fingerprint only the facts that make an accepted stage reusable."""
    revision = _delivery_variant(state) == "in_place_revision"
    packet = state.get("confirmed_fact_packet")
    if not isinstance(packet, dict):
        turns = state.get("turns")
        packet = turns[-1] if isinstance(turns, list) and turns and isinstance(turns[-1], dict) else {}
    # Confirmation timestamps are evidence of *when* the user approved, not
    # part of the approved scope. Everything else in the frozen packet can
    # change a generated artifact and therefore participates in reuse.
    packet_copy = json.loads(json.dumps(packet, ensure_ascii=False, sort_keys=True))
    if isinstance(packet_copy, dict):
        packet_copy.pop("confirmed_at", None)
    revisions = state.get("revision_history") if revision else []
    latest_revision = revisions[-1] if isinstance(revisions, list) and revisions else {}
    revision_evidence = {
        key: value
        for key, value in latest_revision.items()
        if key != "at"
    } if isinstance(latest_revision, dict) else {}
    try:
        input_assets = [
            {"path": record["asset_path"], "sha256": record["sha256"]}
            for record in _input_asset_records(state, _canonical_folder(state))
        ]
    except (FileNotFoundError, FileExistsError, ValueError):
        # The delivery gate surfaces the underlying integrity error.  Keep this
        # fingerprint deterministic while a failed state is being recorded.
        descriptor = state.get("input_asset_manifest")
        input_assets = [{
            "manifest_sha256": descriptor.get("manifest_sha256", "") if isinstance(descriptor, dict) else "",
            "status": "unavailable",
        }]
    payload = {
        "raw_request": str(state.get("raw_request", "")).strip(),
        "task_mode": _task_mode(state),
        "delivery_variant": _delivery_variant(state),
        "context_source": state.get("context_source", {}),
        "confirmed_fact_packet": packet_copy,
        "revision": revision_evidence,
        "revision_scope_manifest": state.get("revision_scope_manifest", {}) if revision else {},
        "revision_requirement_ids": sorted(_trace_values(state.get("revision_requirement_ids"))) if revision else [],
        "extraction_source": state.get("extraction_source", {}),
        "extraction_sources": _extraction_sources(state) if _delivery_variant(state) == "compose_to_new" else [],
        "extraction_selection": _extraction_selection(state) if _delivery_variant(state) == "compose_to_new" else [],
        "implemented_feature_evidence": state.get("implemented_feature_evidence", {}),
        "input_assets": sorted(
            input_assets,
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        ),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _revision_baseline_fingerprint(state: dict[str, Any]) -> str | None:
    """Identify the immutable PRD baseline that a recovery must not replay over."""
    if _delivery_variant(state) != "in_place_revision":
        return None
    history = state.get("revision_history")
    latest = history[-1] if isinstance(history, list) and history and isinstance(history[-1], dict) else {}
    baseline = {
        "prd": latest.get("prd_before_sha256") or _artifact_digest(_canonical_folder(state) / "prd.md"),
        "html": latest.get("html_before_sha256") or _artifact_digest(_canonical_folder(state) / "prd.html"),
    }
    if not any(baseline.values()):
        return None
    encoded = json.dumps(baseline, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _delivery_precondition_fingerprint(state: dict[str, Any]) -> str:
    """Capture inputs whose change makes a recovered attempt meaningful again."""
    canonical = _canonical_folder(state)
    revision = _delivery_variant(state) == "in_place_revision"
    payload = {
        "prd_sha256": _artifact_digest(canonical / "prd.md"),
        "html_sha256": _artifact_digest(canonical / "prd.html"),
        "scope_manifest": state.get("revision_scope_manifest", {}) if revision else {},
        "input_assets": _confirmed_input_asset_digests(state),
        "context_source": state.get("context_source", {}),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _failed_delivery_artifact(state: dict[str, Any]) -> str:
    recovery = state.get("recovery")
    if isinstance(recovery, dict) and str(recovery.get("failed_stage", "")).strip():
        return str(recovery["failed_stage"]).strip()
    for artifact, stage in reversed(list(state.get("delivery_stages", {}).items())):
        if isinstance(stage, dict) and stage.get("artifact_status") == "failed":
            return str(artifact)
    return "delivery"


def _normalise_delivery_failure_category(value: object) -> str:
    detail = str(value or "").strip().lower()
    if "control_plane" in detail or "control plane" in detail or "inspect response" in detail:
        return "control_plane_unavailable"
    if "stream disconnected" in detail or "stream_disconnected" in detail:
        return "stream_disconnected"
    if "revision_scope" in detail or "scope contract" in detail:
        return "revision_scope_violation"
    if "not changed" in detail or "no_output" in detail:
        return "artifact_unchanged"
    if "validation" in detail:
        return "validation_failed"
    return re.sub(r"[^a-z0-9]+", "_", detail).strip("_")[:80] or "delivery_failed"


def _failed_delivery_runtime(
    state: dict[str, Any], artifact: str, provider: str, model: str | None,
) -> tuple[str, str | None]:
    for call in reversed(state.get("agent_calls", [])):
        if not isinstance(call, dict) or str(call.get("artifact", "")) != artifact:
            continue
        return str(call.get("provider") or provider), str(call.get("model") or model or "") or None
    recovery = state.get("recovery")
    failed_runtime = recovery.get("failed_runtime") if isinstance(recovery, dict) else None
    if isinstance(failed_runtime, dict):
        return (
            str(failed_runtime.get("provider") or provider),
            str(failed_runtime.get("model") or model or "") or None,
        )
    return provider, model


def _delivery_failure_guard_context(
    state: dict[str, Any], provider: str, model: str | None,
) -> dict[str, Any]:
    artifact = _failed_delivery_artifact(state)
    failed_provider, failed_model = _failed_delivery_runtime(state, artifact, provider, model)
    category = _normalise_delivery_failure_category(
        state.get("last_failure_category") or state.get("last_error")
    )
    runtime_identity = _state_runtime_identity(state)
    return {
        "scope_fingerprint": _confirmed_scope_fingerprint(state),
        "baseline_digest": _revision_baseline_fingerprint(state),
        "runtime_version": str(runtime_identity["version"]),
        "controller_version": str(runtime_identity["controller_sha256"]),
        "requested_provider": failed_provider,
        "requested_model": failed_model,
        "failed_artifact": artifact,
        "failure_category": category,
        "precondition_digest": _delivery_precondition_fingerprint(state),
    }


def _retry_failure_guard_decision(
    state: dict[str, Any], provider: str, model: str | None,
) -> dict[str, Any]:
    context = _delivery_failure_guard_context(state, provider, model)
    fingerprint = build_delivery_failure_fingerprint(**context)
    history = state.get("delivery_failure_history", [])
    decision = decide_delivery_failure_attempt(
        history if isinstance(history, list) else [],
        fingerprint=fingerprint,
        no_progress_limit=DEFAULT_INTERACTIVE_IDENTICAL_FAILURE_LIMIT,
    )
    result = {**decision.as_dict(), "context": context}
    state["delivery_failure_guard"] = result
    return result


def _record_delivery_failure(state: dict[str, Any], provider: str, model: str | None) -> None:
    """Persist a compact no-progress fact once a launched delivery reaches failure."""
    if state.get("status") not in {"failed", "recovery_required"}:
        return
    active = state.pop("active_delivery_attempt", None)
    if not isinstance(active, dict):
        return
    context = _delivery_failure_guard_context(state, provider, model)
    fingerprint = build_delivery_failure_fingerprint(**context)
    record = failure_attempt_record(fingerprint)
    record.update({
        "at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "failed_artifact": context["failed_artifact"],
        "failure_category": context["failure_category"],
        "runtime_version": context["runtime_version"],
        "requested_provider": context["requested_provider"],
        "requested_model": context["requested_model"],
    })
    state.setdefault("delivery_failure_history", []).append(record)
    state["delivery_failure_guard"] = _retry_failure_guard_decision(state, provider, model)


def _retry_reuse_cache_folder(state: dict[str, Any]) -> Path:
    canonical = _canonical_folder(state)
    return canonical.parent / f".{canonical.name}.delivery-reuse"


def _snapshot_reusable_delivery_artifacts(state: dict[str, Any]) -> None:
    """Snapshot only fully reviewed staged artifacts for one explicit retry.

    Failed stages, stale stage folders, a changed confirmed scope, and a new
    runtime version deliberately produce no cache.  The cache is outside both
    the canonical folder and the disposable delivery workspace and is verified
    again before it is consumed.
    """
    cache = _retry_reuse_cache_folder(state)
    if cache.exists():
        shutil.rmtree(cache)
    workspace = _delivery_folder(state)
    canonical = _canonical_folder(state)
    expected_workspace = canonical.parent / f".{canonical.name}.delivery-stage" / canonical.name
    if workspace != expected_workspace.resolve():
        state.pop("retry_reuse", None)
        return
    fingerprint = _confirmed_scope_fingerprint(state)
    runtime_identity = _reusable_delivery_runtime_identity(state)
    if runtime_identity is None:
        state.pop("retry_reuse", None)
        return
    version = str(runtime_identity["version"])
    reusable: list[dict[str, Any]] = []
    for artifact in ("confirmed-requirements.md", "prd.md"):
        stage = state.get("delivery_stages", {}).get(artifact, {})
        source = workspace / artifact
        digest = _artifact_digest(source)
        if not isinstance(stage, dict) or not source.is_file():
            continue
        if (
            stage.get("artifact_status") != "promoted"
            or stage.get("review_status") != "passed"
            or stage.get("artifact_sha256") != digest
            or stage.get("reviewed_sha256") != digest
            or stage.get("scope_fingerprint") != fingerprint
            or stage.get("pm_copilot_version") != version
            or not _runtime_identities_match(stage.get("runtime_identity"), runtime_identity)
        ):
            continue
        if not cache.exists():
            cache.mkdir(parents=True)
        _atomic_copy(source, cache / artifact)
        reusable.append({"artifact": artifact, "sha256": digest})
        if artifact == "prd.md":
            html = workspace / "prd.html"
            html_digest = _artifact_digest(html)
            if html_digest:
                _atomic_copy(html, cache / html.name)
                reusable[-1]["html_sha256"] = html_digest
    if not reusable:
        state.pop("retry_reuse", None)
        return
    manifest = {
        "scope_fingerprint": fingerprint,
        "pm_copilot_version": version,
        "runtime_identity": runtime_identity,
        "artifacts": reusable,
    }
    _write_json(cache / "manifest.json", manifest)
    state["retry_reuse"] = {
        "status": "available",
        "scope_fingerprint": fingerprint,
        "pm_copilot_version": version,
        "runtime_identity": runtime_identity,
        "artifacts": reusable,
    }


def _restore_reusable_delivery_artifacts(state: dict[str, Any], workspace: Path) -> None:
    """Restore verified retry artifacts into a fresh delivery workspace only."""
    reuse = state.get("retry_reuse")
    cache = _retry_reuse_cache_folder(state)
    if not isinstance(reuse, dict) or reuse.get("status") != "available" or not cache.is_dir():
        return
    try:
        manifest = json.loads((cache / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        manifest = {}
    fingerprint = _confirmed_scope_fingerprint(state)
    runtime_identity = _reusable_delivery_runtime_identity(state)
    if runtime_identity is None:
        shutil.rmtree(cache)
        state["retry_reuse"] = {"status": "discarded", "reason": "scope_or_runtime_changed"}
        return
    version = str(runtime_identity["version"])
    if (
        not isinstance(manifest, dict)
        or manifest.get("scope_fingerprint") != fingerprint
        or manifest.get("pm_copilot_version") != version
        or reuse.get("scope_fingerprint") != fingerprint
        or reuse.get("pm_copilot_version") != version
        or not _runtime_identities_match(manifest.get("runtime_identity"), runtime_identity)
        or not _runtime_identities_match(reuse.get("runtime_identity"), runtime_identity)
    ):
        shutil.rmtree(cache)
        state["retry_reuse"] = {"status": "discarded", "reason": "scope_or_runtime_changed"}
        return
    restored: list[str] = []
    reuse_reason = "verified_stage_reused"
    for item in manifest.get("artifacts", []):
        if not isinstance(item, dict):
            continue
        artifact = str(item.get("artifact", ""))
        if artifact not in {"confirmed-requirements.md", "prd.md"}:
            continue
        source = cache / artifact
        digest = str(item.get("sha256", ""))
        if not digest or _artifact_digest(source) != digest:
            continue
        _atomic_copy(source, workspace / artifact)
        stage = {
            "artifact_status": "promoted",
            "review_status": "passed",
            "artifact_sha256": digest,
            "reviewed_sha256": digest,
            "scope_fingerprint": fingerprint,
            "pm_copilot_version": version,
            "runtime_identity": runtime_identity,
            "reuse_source": "prior_verified_delivery_workspace",
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        state.setdefault("delivery_stages", {})[artifact] = stage
        if artifact not in state.setdefault("artifacts", []):
            state["artifacts"].append(artifact)
        if artifact == "prd.md":
            html = cache / "prd.html"
            html_digest = str(item.get("html_sha256", ""))
            if html_digest and _artifact_digest(html) == html_digest:
                _atomic_copy(html, workspace / html.name)
        restored.append(artifact)
    if "prd.md" in restored and _delivery_variant(state) == "in_place_revision":
        # A cached PRD is content evidence, not a substitute for the scope
        # report that binds it to this attempt's frozen baseline. Regenerate
        # the report inside the new workspace before trace materialization;
        # otherwise revision-evidence.json could point to a discarded prior
        # staging directory.
        scope_report = _validate_staged_revision_scope(state, workspace)
        if not isinstance(scope_report, dict) or scope_report.get("status") != "passed":
            baseline = workspace / ".revision-baseline" / "prd.md"
            if baseline.is_file():
                _atomic_copy(baseline, workspace / "prd.md")
            state.get("delivery_stages", {}).pop("prd.md", None)
            state["artifacts"] = [
                artifact for artifact in state.get("artifacts", []) if artifact != "prd.md"
            ]
            restored.remove("prd.md")
            reuse_reason = "scope_validation_failed"
    shutil.rmtree(cache)
    state["retry_reuse"] = {
        "status": "consumed" if restored else "discarded",
        "reason": reuse_reason if restored else "cache_hash_mismatch",
        "artifacts": restored,
        "scope_fingerprint": fingerprint,
        "pm_copilot_version": version,
        "runtime_identity": runtime_identity,
    }


def _revision_source_drift_problem(state: dict[str, Any]) -> str | None:
    """Reject an in-place revision when its canonical baseline changed.

    The initial hashes are the revision's source snapshot. Replacing that
    snapshot with whatever another writer placed in the canonical folder would
    let a confirmed narrow edit silently apply to unrelated current content.
    """
    if _delivery_variant(state) != "in_place_revision":
        return None
    history = state.get("revision_history")
    if not isinstance(history, list) or not history or not isinstance(history[-1], dict):
        return None
    baseline = history[-1]
    canonical = _canonical_folder(state)
    for name, key in (("prd.md", "prd_before_sha256"), ("prd.html", "html_before_sha256")):
        # Older runs without a recorded fingerprint cannot provide CAS
        # protection, but a recorded absent file (None) is still a baseline
        # that must not become present before promotion.
        if key not in baseline:
            continue
        expected = baseline.get(key)
        if _artifact_digest(canonical / name) != expected:
            return (
                f"canonical {name} changed after this in-place revision began; "
                "restart the revision from the current PRD and reconfirm its scope"
            )
    # A promotion replaces the whole assets/ tree, not only the files named by
    # the selected requirement. Treat its complete digest map as the same
    # compare-and-swap boundary as prd.md and prd.html so a collaborator's
    # media change cannot be overwritten by the older staged copy.
    expected_assets = baseline.get("assets_before_sha256")
    if not isinstance(expected_assets, Mapping):
        manifest = state.get("revision_scope_manifest")
        manifest_baseline = manifest.get("baseline") if isinstance(manifest, Mapping) else None
        expected_assets = (
            manifest_baseline.get("assets")
            if isinstance(manifest_baseline, Mapping) else None
        )
    if isinstance(expected_assets, Mapping):
        expected = {str(path): str(digest) for path, digest in expected_assets.items()}
        try:
            actual = _revision_asset_digests(canonical)
        except ValueError as error:
            return (
                "canonical assets changed after this in-place revision began "
                f"or cannot be verified: {error}; restart the revision from the current PRD and reconfirm its scope"
            )
        if actual != expected:
            return (
                "canonical assets changed after this in-place revision began; "
                "restart the revision from the current PRD and reconfirm its scope"
            )
    return None


def _prepare_delivery_workspace(state: dict[str, Any]) -> Path:
    canonical = _canonical_folder(state)
    source_drift = _revision_source_drift_problem(state)
    if source_drift:
        raise ValueError(source_drift)
    # Materialize old path-only state before copying canonical into staging.
    # The stage itself must consume the copied snapshot, never a caller path.
    _input_asset_records(state, canonical)
    workspace = canonical.parent / f".{canonical.name}.delivery-stage" / canonical.name
    if workspace.exists():
        shutil.rmtree(workspace.parent)
    workspace.parent.mkdir(parents=True, exist_ok=True)
    _assert_delivery_tree_has_no_symlinks(canonical, label="canonical PRD folder")
    shutil.copytree(canonical, workspace, ignore=shutil.ignore_patterns(".delivery-stage", ".DS_Store"))
    _discard_non_content_assets(workspace)
    if _delivery_variant(state) == "in_place_revision" and (workspace / "prd.md").is_file():
        baseline = workspace / ".revision-baseline"
        baseline.mkdir(parents=True, exist_ok=True)
        shutil.copy2(workspace / "prd.md", baseline / "prd.md")
        # Old canonical proof belongs to the baseline, never to the new
        # isolated revision attempt. A fresh rendered artifact set must earn
        # its own report, evidence, and trace before promotion.
        (workspace / "revision-evidence.json").unlink(missing_ok=True)
        _revision_scope_report_path(workspace).unlink(missing_ok=True)
        _revision_scope_precheck_path(workspace).unlink(missing_ok=True)
        state.pop("revision_scope_precheck", None)
        state.pop("revision_scope_validation", None)
    else:
        # A prior canonical revision may retain provenance for audit, but a
        # new/extracted delivery must neither validate nor republish it.
        (workspace / "revision-evidence.json").unlink(missing_ok=True)
        stale_baseline = workspace / ".revision-baseline"
        if stale_baseline.is_dir():
            shutil.rmtree(stale_baseline)
        elif stale_baseline.exists():
            stale_baseline.unlink()
    _copy_automatic_implemented_capture(state, workspace)
    _copy_input_assets(state, workspace)
    _validate_input_asset_materialization(state, workspace)
    state["delivery_workspace"] = str(workspace)
    _restore_reusable_delivery_artifacts(state, workspace)
    _refresh_revision_asset_attestation(state, workspace)
    return workspace


def _copy_automatic_implemented_capture(state: Mapping[str, Any], workspace: Path) -> None:
    """Expose a frozen real capture to the staged PRD without mutating its baseline."""
    evidence = state.get("implemented_feature_evidence")
    if not isinstance(evidence, Mapping):
        return
    capability = evidence.get("visual_runtime_capability")
    capability = capability if isinstance(capability, Mapping) else {}
    capture = capability.get("real_frontend_capture")
    capture = capture if isinstance(capture, Mapping) else {}
    if capture.get("status") != "captured":
        return
    source_ref = str(capture.get("path") or "").strip()
    asset_ref = str(capture.get("prd_asset_path") or "").strip()
    if not source_ref.startswith("tool-results/implemented-evidence/") or not asset_ref.startswith("assets/"):
        return
    source = workspace / source_ref
    destination = workspace / asset_ref
    if not source.is_file() or destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    _atomic_copy(source, destination)


def _revision_scope_violation(stage_target: Path, baseline: Path, allowed_ids: Sequence[str]) -> str | None:
    """Reject in-place PRD edits outside IDs explicitly named by the revision."""
    if not stage_target.is_file() or not baseline.is_file():
        return None
    candidate = stage_target.read_text(encoding="utf-8")
    original = baseline.read_text(encoding="utf-8")
    ids = {str(item).strip() for item in allowed_ids if str(item).strip()}
    if not ids:
        return "in-place revision has no confirmed requirement selector; ask the user before changing the document"
    id_pattern = "|".join(re.escape(item) for item in sorted(ids, key=len, reverse=True))
    section_re = re.compile(rf"(?ms)^### (?:{id_pattern})\b.*?(?=^### |^## |\Z)")
    row_re = re.compile(rf"(?m)^\|\s*(?:{id_pattern})\s*\|.*$\n?")
    def outside_scope(text: str) -> str:
        text = section_re.sub("", text)
        text = row_re.sub("", text)
        return text
    if outside_scope(candidate) != outside_scope(original):
        scope = ", ".join(sorted(ids)) or "confirmed scope"
        return f"in-place revision changed PRD content outside confirmed requirement scope ({scope})"
    return None


def _revision_scope_report_path(folder: Path) -> Path:
    return folder / "tool-results" / "revision-scope-validation.json"


def _revision_scope_precheck_path(folder: Path) -> Path:
    """Keep markdown-only scope checks out of the final attestation path."""
    return folder / "tool-results" / "revision-scope-precheck.json"


def _revision_artifact_set_snapshot(folder: Path) -> dict[str, Any]:
    """Use the shared snapshot contract while reporting incomplete staging cleanly."""
    return revision_artifact_set_snapshot(folder, allow_missing_artifacts=True)


def _final_revision_scope_attestation_problems(
    state: Mapping[str, Any], folder: Path,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Verify that the final scope report still names this workspace's bytes.

    A markdown-only precheck is useful feedback for the PRD writer, but it is
    not evidence that the rendered document can be promoted.  This verifier is
    intentionally read-only so later validation cannot overwrite the report
    that revision-evidence.json has already bound to.
    """
    validation = state.get("revision_scope_validation")
    if not isinstance(validation, Mapping):
        return None, ["final in-place revision scope attestation was not materialized"]
    if validation.get("status") != "passed":
        return None, ["final in-place revision scope attestation is not passed"]
    if validation.get("report_path") != "tool-results/revision-scope-validation.json":
        return None, ["final in-place revision scope attestation has an unexpected report path"]
    report_path = _revision_scope_report_path(folder)
    if not report_path.is_file():
        return None, ["final in-place revision scope report is missing"]
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, ["final in-place revision scope report is not readable JSON"]
    if not isinstance(report, dict):
        return None, ["final in-place revision scope report must be a JSON object"]
    if report.get("status") != "passed" or report.get("validation_phase") != "final":
        return report, ["final in-place revision scope report does not record a passed final validation"]
    manifest = state.get("revision_scope_manifest")
    if not isinstance(manifest, Mapping):
        return report, ["final in-place revision scope attestation is missing its scope manifest"]
    manifest_sha256 = revision_scope_manifest_digest(manifest)
    if report.get("manifest_sha256") != manifest_sha256:
        return report, ["final in-place revision scope report does not match the active scope manifest"]
    if validation.get("manifest_sha256") != manifest_sha256:
        return report, ["final in-place revision scope state does not match the active scope manifest"]
    expected_report_sha256 = validation.get("report_sha256")
    actual_report_sha256 = _artifact_digest(report_path)
    if not isinstance(expected_report_sha256, str) or expected_report_sha256 != actual_report_sha256:
        return report, ["final in-place revision scope report changed after attestation"]
    expected_snapshot = _revision_artifact_set_snapshot(folder)
    if report.get("artifact_set") != expected_snapshot:
        return report, ["final in-place revision scope report does not match current PRD, HTML, and asset bytes"]
    if validation.get("artifact_set_sha256") != expected_snapshot["sha256"]:
        return report, ["final in-place revision scope state does not match current artifact bytes"]
    if validation.get("attestation_schema_version") != 1:
        return report, ["final in-place revision scope attestation schema is missing"]
    return report, []


def _refresh_revision_asset_attestation(
    state: dict[str, Any], folder: Path,
) -> dict[str, Any] | None:
    """Bind a revision's usable media paths to bytes in its current workspace."""
    if _delivery_variant(state) != "in_place_revision":
        state.pop("revision_asset_attestation", None)
        return None
    manifest = state.get("revision_scope_manifest")
    candidate = folder / "prd.md"
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1 or not candidate.is_file():
        state.pop("revision_asset_attestation", None)
        return None
    attestation = build_revision_asset_attestation(
        manifest,
        candidate_markdown=candidate.read_text(encoding="utf-8"),
        candidate_assets=_revision_asset_digests(folder),
    )
    state["revision_asset_attestation"] = attestation
    return attestation


def _validate_staged_revision_scope(
    state: dict[str, Any], folder: Path, *, include_rendered_html: bool = False,
) -> dict[str, Any] | None:
    """Validate an in-place revision against its controller-owned baseline.

    General document validators continue to check resource integrity across the
    whole PRD. This check owns only revision semantics: selected requirement
    constraints and preservation of everything the user did not authorize.
    """
    if _delivery_variant(state) != "in_place_revision":
        return None
    validation_phase = "final" if include_rendered_html else "precheck"
    manifest = state.get("revision_scope_manifest")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return {
            "schema_version": 1,
            "status": "failed",
            "failures": ["in-place revision scope contract was not materialized before validation"],
        }
    baseline = folder / ".revision-baseline" / "prd.md"
    candidate = folder / "prd.md"
    if not baseline.is_file() or not candidate.is_file():
        return {
            "schema_version": 1,
            "status": "failed",
            "failures": ["in-place revision scope validation requires staged baseline and prd.md"],
        }
    if _is_implemented_feature_append(state):
        original = baseline.read_text(encoding="utf-8")
        candidate_text = candidate.read_text(encoding="utf-8")
        baseline_ids = requirement_ids(original)
        candidate_ids = requirement_ids(candidate_text)
        new_ids = [item for item in candidate_ids if item not in baseline_ids]
        failures: list[str] = []
        if any(item not in candidate_ids for item in baseline_ids):
            failures.append("append removed an existing requirement ID")
        next_minor = max((int(item.split(".", 1)[1]) for item in baseline_ids if item.startswith("5.")), default=0) + 1
        expected = [f"5.{index}" for index in range(next_minor, next_minor + len(new_ids))]
        if not new_ids or new_ids != expected:
            failures.append("append must add contiguous requirement IDs after the existing 5.x sequence")
        baseline_sections = requirement_sections(original)
        candidate_sections = requirement_sections(candidate_text)
        for requirement_id in baseline_ids:
            before = str(baseline_sections.get(requirement_id, {}).get("content", "")).rstrip()
            after = str(candidate_sections.get(requirement_id, {}).get("content", "")).rstrip()
            if after != before:
                failures.append(f"append changed existing requirement detail {requirement_id}")
        baseline_rows = requirement_rows(original)
        candidate_rows = requirement_rows(candidate_text)
        for requirement_id, row in baseline_rows.items():
            if candidate_rows.get(requirement_id) != row:
                failures.append(f"append changed existing requirement row {requirement_id}")
        baseline_assets = manifest.get("baseline", {}).get("assets", {})
        candidate_assets = _revision_asset_digests(folder)
        if isinstance(baseline_assets, Mapping):
            for path, digest in baseline_assets.items():
                if candidate_assets.get(path) != digest:
                    failures.append(f"append changed existing asset {path}")
        report = {
            "schema_version": 1, "status": "failed" if failures else "passed", "failures": failures,
            "checks": ["append-only baseline preservation"],
            "asset_attestation": {"status": "passed" if not failures else "failed"},
        }
        state["append_requirement_ids"] = new_ids if not failures else []
    else:
        baseline_assets = manifest.get("baseline", {}).get("assets", {})
        baseline_assets = baseline_assets if isinstance(baseline_assets, dict) else {}
        report = validate_revision_scope(
            manifest,
            baseline_markdown=baseline.read_text(encoding="utf-8"),
            candidate_markdown=candidate.read_text(encoding="utf-8"),
            baseline_assets={str(path): str(digest) for path, digest in baseline_assets.items()},
            candidate_assets=_revision_asset_digests(folder),
        )
    state["revision_asset_attestation"] = report.get("asset_attestation", {})
    if include_rendered_html and report.get("status") == "passed" and not _is_implemented_feature_append(state):
        html_path = folder / "prd.html"
        if not html_path.is_file():
            report.setdefault("failures", []).append("rendered prd.html is missing for revision scope validation")
        else:
            report.setdefault("failures", []).extend(
                validate_rendered_html_scope(report, html_path.read_text(encoding="utf-8"))
            )
        if report.get("failures"):
            report["status"] = "failed"
    report["validation_phase"] = validation_phase
    report["validated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    report["manifest_sha256"] = revision_scope_manifest_digest(manifest)
    report_path = _revision_scope_report_path(folder) if include_rendered_html else _revision_scope_precheck_path(folder)
    if include_rendered_html:
        report["attestation_schema_version"] = 1
        snapshot = _revision_artifact_set_snapshot(folder)
        if not snapshot["prd_md_sha256"] or not snapshot["prd_html_sha256"]:
            report.setdefault("failures", []).append(
                "final revision scope validation requires current prd.md and prd.html bytes"
            )
            report["status"] = "failed"
        report["artifact_set"] = snapshot
    _write_json(report_path, report)
    validation = {
        "status": report.get("status"),
        "report_path": str(report_path.relative_to(folder)),
        "manifest_sha256": report["manifest_sha256"],
        "failures": list(report.get("failures", [])),
    }
    if include_rendered_html:
        validation.update({
            "attestation_schema_version": 1,
            "report_sha256": _artifact_digest(report_path),
            "artifact_set_sha256": report["artifact_set"]["sha256"],
        })
        state["revision_scope_validation"] = validation
    else:
        # A new PRD candidate invalidates every final report/evidence copied
        # into staging from an earlier attempt.  It must earn a fresh rendered
        # attestation before a controller trace can cite it.
        _revision_scope_report_path(folder).unlink(missing_ok=True)
        (folder / "revision-evidence.json").unlink(missing_ok=True)
        state.pop("revision_scope_validation", None)
        state["revision_scope_precheck"] = validation
    return report


def _restart_delivery_attempt(state: dict[str, Any]) -> None:
    """Discard stale stage acceptance before a user-confirmed recovery attempt."""
    _snapshot_reusable_delivery_artifacts(state)
    state.setdefault("delivery_attempts", []).append({
        "at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "reason": "explicit_confirmation_after_incomplete_delivery",
        "prior_status": state.get("resume_from_status"),
    })
    state["delivery_stages"] = {}
    state["validation"] = []
    state["artifacts"] = [item for item in state.get("artifacts", []) if item == "discussion.md"]
    state.pop("recovery", None)
    state.pop("revision_scope_precheck", None)
    state.pop("revision_scope_validation", None)
    state.pop("revision_stop_reason", None)


def _staged_tool_result_file(
    root: Path, raw_reference: str, *, reference_name: str,
) -> tuple[Path, Path]:
    """Resolve one retained tool result without allowing a staged-root escape."""
    candidate = (root / raw_reference).resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError as error:
        raise RuntimeError(
            f"{reference_name} escapes the staged run folder: {raw_reference}"
        ) from error
    if not relative.parts or relative.parts[0] != "tool-results":
        raise RuntimeError(
            f"{reference_name} must be under tool-results/: {raw_reference}"
        )
    if not candidate.is_file():
        raise FileNotFoundError(
            f"{reference_name} is missing from the staged run folder: {raw_reference}"
        )
    return relative, candidate


def _trace_result_files(run_log: Path) -> list[tuple[Path, Path]]:
    """Resolve the exact local evidence files a trace promises to retain.

    Result references are part of the published trace contract.  Promotion
    cannot discard them merely because the controller's broader diagnostic
    directory is disposable.  Resolve them structurally and require every
    retained reference to stay under ``tool-results/`` in the staged run.
    """
    try:
        trace = yaml.safe_load(run_log.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise RuntimeError(f"cannot resolve trace result references: {error}") from error
    if not isinstance(trace, dict):
        raise RuntimeError("cannot resolve trace result references from a non-mapping trace")

    root = run_log.parent.resolve()
    found: dict[Path, Path] = {}

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "result_ref" and isinstance(child, str) and child.strip():
                    raw_reference = child.strip()
                    relative, candidate = _staged_tool_result_file(
                        root, raw_reference, reference_name="trace result_ref",
                    )
                    found[relative] = candidate
                else:
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(trace)
    return sorted(found.items(), key=lambda item: item[0].as_posix())


def _revision_evidence_result_files(revision_evidence: Path) -> list[tuple[Path, Path]]:
    """Resolve controller validation evidence retained through revision evidence.

    ``revision-evidence.json`` is an artifact-lineage dependency rather than a
    trace ``result_ref``.  Its scope report must therefore be retained in the
    same publish transaction, with the same root and symlink protections as
    direct trace references.
    """
    if not revision_evidence.is_file():
        return []
    root = revision_evidence.parent.resolve()
    evidence_path = revision_evidence.resolve()
    try:
        evidence_path.relative_to(root)
    except ValueError as error:
        raise RuntimeError("revision evidence escapes the staged run folder") from error
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # The candidate lineage validator will surface malformed evidence. Do
        # not infer a retention path from unreadable content.
        return []
    if not isinstance(evidence, dict):
        return []
    validation = evidence.get("scope_validation")
    if not isinstance(validation, dict):
        return []
    raw_reference = validation.get("report_path")
    if not isinstance(raw_reference, str) or not raw_reference.strip():
        return []
    return [_staged_tool_result_file(
        root,
        raw_reference.strip(),
        reference_name="revision scope_validation report_path",
    )]


def _promote_trace_result_files(
    destination_root: Path, referenced_files: Sequence[tuple[Path, Path]],
) -> None:
    """Atomically retain only controller-authorized staged tool-result evidence."""
    temporary_results = destination_root / ".tool-results.promoting"
    if temporary_results.exists():
        shutil.rmtree(temporary_results)
    if referenced_files:
        temporary_results.mkdir(parents=True)
        for relative, source in referenced_files:
            destination = temporary_results / relative.relative_to("tool-results")
            _atomic_copy(source, destination)
    current_results = destination_root / "tool-results"
    if current_results.exists():
        if current_results.is_dir():
            shutil.rmtree(current_results)
        else:
            current_results.unlink()
    if referenced_files:
        temporary_results.replace(current_results)


def _rollback_delivery_promotion(canonical: Path, backup: Path | None) -> None:
    """Restore the pre-promotion canonical folder after a rejected publish."""
    if backup is None or not backup.exists():
        return
    rejected = canonical.parent / f".{canonical.name}.promotion-rejected-{time.time_ns()}"
    moved_candidate = False
    try:
        if canonical.exists():
            canonical.replace(rejected)
            moved_candidate = True
        backup.replace(canonical)
    except OSError:
        if not canonical.exists() and moved_candidate and rejected.exists():
            rejected.replace(canonical)
        raise
    if moved_candidate and rejected.exists():
        shutil.rmtree(rejected, ignore_errors=True)


def _commit_delivery_promotion(backup: Path | None) -> None:
    """Discard a pre-promotion backup only after canonical validation passes."""
    if backup is not None and backup.exists():
        shutil.rmtree(backup, ignore_errors=True)


def _promote_delivery_workspace(state: dict[str, Any]) -> Path:
    """Build and swap a complete canonical delivery as one recoverable transaction.

    The delivery workspace is already validated. This function still treats
    every official artifact as one publish unit so an I/O failure cannot leave
    a new PRD paired with an old trace, asset tree, or requirements handoff.
    The returned backup remains available until canonical validation commits it.
    """
    canonical = _canonical_folder(state)
    workspace = _delivery_folder(state)
    try:
        _assert_delivery_tree_has_no_symlinks(workspace, label="validated delivery workspace")
    except ValueError as error:
        raise RuntimeError(str(error)) from error
    revision = _delivery_variant(state) == "in_place_revision"
    revision_evidence = workspace / "revision-evidence.json" if revision else None
    retained_result_files = {
        relative: source
        for relative, source in _trace_result_files(workspace / "run-log.yaml")
    }
    if revision_evidence is not None:
        for relative, source in _revision_evidence_result_files(revision_evidence):
            retained_result_files[relative] = source
    referenced_result_files = sorted(
        retained_result_files.items(), key=lambda item: item[0].as_posix(),
    )
    for name in ("confirmed-requirements.md", "prd.md", "prd.html", "run-log.yaml"):
        source = workspace / name
        if not source.is_file():
            raise FileNotFoundError(f"Validated delivery artifact is missing: {source}")
    source_assets = workspace / "assets"
    if not source_assets.is_dir():
        raise FileNotFoundError("Validated delivery assets/ folder is missing")
    if not canonical.is_dir():
        raise FileNotFoundError(f"Canonical PRD folder is missing: {canonical}")

    publish_root = Path(tempfile.mkdtemp(prefix=f".{canonical.name}.publishing-", dir=canonical.parent))
    candidate = publish_root / canonical.name
    backup = canonical.parent / f".{canonical.name}.promotion-backup-{time.time_ns()}"
    moved_original = False
    try:
        # The canonical tree may have changed during delivery. Verify it again
        # before copytree can dereference a collaborator-created nested link.
        _assert_delivery_tree_has_no_symlinks(canonical, label="canonical PRD folder before promotion")
        shutil.copytree(canonical, candidate, ignore=shutil.ignore_patterns(".delivery-stage", ".DS_Store"))
        for name in ("confirmed-requirements.md", "prd.md", "prd.html", "run-log.yaml"):
            _atomic_copy(workspace / name, candidate / name)

        candidate_assets = candidate / "assets"
        if candidate_assets.exists():
            if candidate_assets.is_dir():
                shutil.rmtree(candidate_assets)
            else:
                candidate_assets.unlink()
        shutil.copytree(source_assets, candidate_assets, ignore=shutil.ignore_patterns(".DS_Store"))
        _discard_non_content_assets(candidate)

        # Source snapshots and implemented-feature packets are part of the
        # validated delivery input.  Reuse from canonical here would permit a
        # post-staging mutation to be published beside a staged trace that
        # still names the prior hash, so replace the complete controller-owned
        # source-material tree from the isolated workspace.
        source_material = workspace / "source-material"
        candidate_source_material = candidate / "source-material"
        if source_material.exists():
            if not source_material.is_dir():
                raise RuntimeError("Validated delivery source-material must be a directory")
            try:
                source_material.resolve().relative_to(workspace.resolve())
            except ValueError as error:
                raise RuntimeError("Validated delivery source-material escapes the staged run folder") from error
            _assert_delivery_tree_has_no_symlinks(
                source_material, label="validated delivery source-material"
            )
            if candidate_source_material.exists():
                if candidate_source_material.is_dir():
                    shutil.rmtree(candidate_source_material)
                else:
                    candidate_source_material.unlink()
            shutil.copytree(source_material, candidate_source_material, ignore=shutil.ignore_patterns(".DS_Store"))
        elif candidate_source_material.exists():
            if candidate_source_material.is_dir():
                shutil.rmtree(candidate_source_material)
            else:
                candidate_source_material.unlink()

        specialist_evidence = workspace / "specialist-evidence"
        candidate_specialist_evidence = candidate / "specialist-evidence"
        if specialist_evidence.is_dir():
            if candidate_specialist_evidence.exists():
                shutil.rmtree(candidate_specialist_evidence)
            shutil.copytree(specialist_evidence, candidate_specialist_evidence)
        elif candidate_specialist_evidence.exists():
            shutil.rmtree(candidate_specialist_evidence)

        candidate_revision_evidence = candidate / "revision-evidence.json"
        if revision_evidence is not None and revision_evidence.is_file():
            _atomic_copy(revision_evidence, candidate / revision_evidence.name)
        else:
            candidate_revision_evidence.unlink(missing_ok=True)
        _promote_trace_result_files(candidate, referenced_result_files)
        (candidate / ".DS_Store").unlink(missing_ok=True)
        (candidate / "assets" / ".DS_Store").unlink(missing_ok=True)
        _assert_delivery_tree_has_no_symlinks(candidate, label="promotion candidate")
        try:
            # The manifest is state-bound, so reread it from the exact
            # candidate directory after all source material has been copied.
            # This prevents a late snapshot/link mutation from riding beside a
            # trace that still names its original attachment hash.
            _validate_input_asset_materialization(state, candidate)
        except (FileNotFoundError, FileExistsError, ValueError) as error:
            raise RuntimeError(
                "candidate delivery input asset validation failed: " + str(error)
            ) from error

        # The staged run can change after its final validator completes. Check
        # the exact candidate bytes after source-material has been copied and
        # immediately before publication, so a mismatched packet or source
        # snapshot cannot be promoted under an earlier trace hash.
        provenance_failures = [
            *validate_artifact_lineage(candidate / "run-log.yaml"),
            *validate_implemented_feature_evidence_packet(candidate / "run-log.yaml"),
        ]
        if provenance_failures:
            raise RuntimeError(
                "candidate delivery provenance validation failed: "
                + "; ".join(provenance_failures)
            )

        # This is deliberately adjacent to the directory swap. Staging can
        # take minutes, so the earlier pre-staging check is not sufficient to
        # protect a collaborator's later update from being overwritten. The
        # same short lock is used by derived-only refreshes, which prevents a
        # check-then-rename race between the two promotion paths.
        with _delivery_promotion_lock(canonical):
            source_drift = _revision_source_drift_problem(state)
            if source_drift:
                raise RevisionSourceDriftError(source_drift)
            canonical.replace(backup)
            moved_original = True
            try:
                candidate.replace(canonical)
            except OSError:
                backup.replace(canonical)
                moved_original = False
                raise
    except (OSError, ValueError) as error:
        if moved_original and backup.exists() and not canonical.exists():
            backup.replace(canonical)
        if isinstance(error, ValueError):
            raise RuntimeError(str(error)) from error
        raise
    finally:
        if publish_root.exists():
            shutil.rmtree(publish_root, ignore_errors=True)
    state["delivery_promoted_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    return backup


def _finalize_deterministic_trace(
    folder: Path, checks: list[dict[str, Any]], runtime_identity: Mapping[str, Any] | None = None,
) -> bool:
    """Close a controller trace only after every real staging check passes.

    A failed first pass is a property of the delivery workspace, not evidence
    that the trace itself is complete.  Keep the trace in its original
    degraded/pending state in that case so a repaired artifact can be checked
    again without claiming a validation result that never happened.
    """
    target = folder / "run-log.yaml"
    if not _is_controller_deterministic_trace(target):
        return False
    passed = bool(checks) and all(item.get("status") == "passed" for item in checks)
    if not passed:
        return False
    try:
        trace = yaml.safe_load(target.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return False
    if not isinstance(trace, dict):
        return False

    validation_results = []
    for item in checks:
        command = str(item.get("command", "")).strip()
        tool_id = command.split()[0] if command else "controller.validation"
        result = _compact_trace_text(item.get("stdout", "") or item.get("stderr", ""), 240)
        validation_results.append({
            "command": command,
            "tool_id": tool_id,
            "tool_version": "active runtime",
            "status": "passed",
            "result": result or "passed",
            "limitation": "",
            "fallback": "not applicable",
        })
    trace["validation_results"] = validation_results
    trace["quality_decision"] = {
        "passed": True,
        "rationale": "All required staging validation commands passed before promotion.",
    }
    trace["review"] = {"status": "passed", "findings": []}
    trace["final_status"] = "validated controller trace"
    _atomic_write_text(
        target,
        yaml.safe_dump(trace, allow_unicode=True, sort_keys=False, default_flow_style=False),
    )
    _normalise_trace_runtime_evidence(target, runtime_identity)
    return True


def _compact_trace_text(value: object, limit: int = 240) -> str:
    """Keep provider diagnostics useful without replaying model transcripts."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _recover_interrupted_delivery(state: dict[str, Any], folder: Path) -> bool:
    """Expose an interrupted pre-checkpoint delivery instead of misreporting it.

    Older controller versions could promote an artifact before recording the
    confirmation and delivery call. Do not infer that a human confirmed it;
    make the integrity break explicit and require a fresh resume confirmation.
    """
    if state.get("status") in {"delivery", "confirmed"} and state.get("termination") == "running":
        raw_pid = state.get("controller_pid")
        alive = False
        try:
            pid = int(raw_pid)
            os.kill(pid, 0)
            alive = True
        except (TypeError, ValueError, ProcessLookupError, PermissionError):
            pass
        if not alive:
            promoted = [name for name in ("confirmed-requirements.md", "prd.md", "prd.html", "run-log.yaml") if (folder / name).is_file()]
            state["status"] = "recovery_required"
            state["termination"] = "interrupted"
            state["last_error"] = "controller process exited during delivery; prior running state was recovered"
            state["recovery"] = {
                "status": "retry_required",
                "detected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "controller_pid": raw_pid,
                "promoted_artifacts": promoted,
                "retry_entry": "--confirm",
            }
            return True
        return False
    if state.get("status") != "awaiting_confirmation" or state.get("user_confirmation"):
        return False
    staged = list(folder.parent.glob(f".{folder.name}.stage-*")) + list(folder.parent.glob(f".{folder.name}.review-*"))
    promoted = [name for name in ("confirmed-requirements.md", "prd.md", "run-log.yaml") if (folder / name).is_file()]
    if not staged or not promoted:
        return False
    state["status"] = "recovery_required"
    state["termination"] = "interrupted"
    state["last_error"] = (
        "检测到旧版控制器在交付阶段中断：已生成 " + "、".join(promoted)
        + "，但确认和阶段检查点未写入。请明确确认恢复交付。"
    )
    state["recovery"] = {
        "status": "confirmation_required",
        "detected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "promoted_artifacts": promoted,
        "staging_traces": [str(path) for path in staged],
    }
    return True


def _controller_pid_alive(state: dict[str, Any]) -> bool:
    """Return whether the controller recorded for an active delivery exists."""
    try:
        os.kill(int(state.get("controller_pid")), 0)
        return True
    except (TypeError, ValueError, ProcessLookupError, PermissionError):
        return False


def _agent_call_has_evidence(result: dict[str, Any]) -> bool:
    """Require attributable runtime evidence before a call can advance a gate."""
    provider = str(result.get("provider", "")).strip()
    model = str(result.get("model", "")).strip()
    if provider == CONTROLLER_TRACE_PROVIDER or model == CONTROLLER_TRACE_MODEL:
        phase = result.get("phase")
        artifact = result.get("artifact")
        execution_mode = result.get("execution_mode")
        return (
            provider == CONTROLLER_TRACE_PROVIDER
            and model == CONTROLLER_TRACE_MODEL
            and result.get("status") == "complete"
            and (
                phase == "delivery"
                and artifact == "run-log.yaml"
                and execution_mode == "deterministic_trace_materialization"
                or phase == "stage_quality_review"
                and artifact == "run-log.yaml"
                and execution_mode == "deterministic_trace_validation"
            )
        )
    if not provider or not model or model in {"configured default", "unknown", "None"}:
        return False
    return result.get("status") == "complete"


def _record_agent_call(
    state: dict[str, Any], result: dict[str, Any], *, phase: str, artifact: str | None = None,
) -> bool:
    result["phase"] = phase
    if artifact:
        result["artifact"] = artifact
    record = dict(result)
    if artifact:
        record["artifact"] = artifact
    state.setdefault("agent_calls", []).append(record)
    return _agent_call_has_evidence(record)


def _mark_attribution_recovery(
    state: dict[str, Any], failed_stage: str, provider: str, model: str | None = None,
) -> None:
    """Keep a confirmed run resumable without replaying a failed transport."""
    completed = []
    for artifact, stage in state.get("delivery_stages", {}).items():
        if stage.get("artifact_status") == "promoted":
            completed.append({"artifact": artifact, "sha256": stage.get("artifact_sha256")})
    state["status"] = "recovery_required"
    state["termination"] = "retry_required"
    state["last_failure_category"] = "attribution_unverified"
    state["recovery"] = {
        "status": "retry_required",
        "failed_stage": failed_stage,
        "completed_artifacts": completed,
        "delivery_workspace": str(_delivery_folder(state)),
        "retry_entry": "--confirm",
        "retry_action": (
            f"python3 scripts/run_interactive_request.py --run-folder {_canonical_folder(state)} "
            "--confirm"
        ),
        "failed_runtime": {
            "provider": provider,
            "model": model,
            "retry_policy": "reselect_from_current_device",
        },
    }


def _required_production_evidence(state: dict[str, Any]) -> tuple[bool, str]:
    """Prove every required production stage used an attributable Agent."""
    calls = state.get("agent_calls", [])
    required = {
        ("intake", None),
        ("clarification_review", None),
        ("delivery", "confirmed-requirements.md"),
        ("delivery", "prd.md"),
        ("delivery", "run-log.yaml"),
        ("stage_quality_review", "confirmed-requirements.md"),
        ("stage_quality_review", "prd.md"),
        ("stage_quality_review", "run-log.yaml"),
    }
    for phase, artifact in required:
        matching = [
            call for call in calls
            if call.get("phase") == phase and (artifact is None or call.get("artifact") == artifact)
        ]
        if not matching:
            return False, f"missing required Agent evidence: {phase}/{artifact or 'request'}"
        if not any(_agent_call_has_evidence(call) for call in matching):
            return False, f"required Agent evidence is not attributable: {phase}/{artifact or 'request'}"
    return True, "all required production Agent stages are attributable"


def _extract_json(text: str) -> dict[str, Any]:
    """Accept plain JSON or a fenced JSON response without hiding failures."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("Agent did not return a JSON intake envelope")
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("Agent intake envelope must be an object")
    return value


def _normalise_intake(value: dict[str, Any]) -> dict[str, Any]:
    status = str(value.get("status", "needs_input"))
    if status not in {"needs_input", "complete", "failed"}:
        status = "needs_input"
    questions = value.get("questions", [])
    if not isinstance(questions, list):
        questions = [str(questions)]
    questions = [str(item).strip() for item in questions if str(item).strip()]
    buckets = value.get("buckets", {})
    if not isinstance(buckets, dict):
        buckets = {}
    must = buckets.get("must_answer_before_generation", value.get("must_answer_before_generation", []))
    if not isinstance(must, list):
        must = [str(must)] if must else []
    # A model may return complete without an empty blocking bucket. The
    # blocking bucket is authoritative: generation is unsafe while it is non-empty.
    must = [str(item).strip() for item in must if str(item).strip()]
    if must:
        status = "needs_input"
    elif status == "needs_input":
        # Only the must-answer bucket is a generation gate. Questions about
        # normal PRD ownership or later development/launch confirmation must
        # not trap the user in intake.
        status = "complete"
        questions = []
    return {
        "status": status,
        "summary": str(value.get("summary", "")).strip(),
        "questions": questions,
        "buckets": {
            "must_answer_before_generation": must,
            "can_draft_with_stated_assumption": buckets.get("can_draft_with_stated_assumption", value.get("can_draft_with_stated_assumption", [])),
            "must_confirm_before_development_or_launch": buckets.get("must_confirm_before_development_or_launch", value.get("must_confirm_before_development_or_launch", [])),
        },
        "scope": value.get("scope", {}),
        "assumptions": value.get("assumptions", []),
        "decisions": value.get("decisions", []),
        "risks": value.get("risks", []),
    }


def _normalise_clarification_review(value: dict[str, Any]) -> dict[str, Any]:
    """Normalise a second-agent gate without letting malformed output pass it."""
    status = str(value.get("status", "needs_input")).strip().lower()
    questions = value.get("questions", [])
    blockers = value.get("blockers", [])
    coverage = value.get("coverage", {})
    if not isinstance(questions, list):
        questions = [questions]
    if not isinstance(blockers, list):
        blockers = [blockers]
    questions = [str(item).strip() for item in questions if str(item).strip()]
    blockers = [str(item).strip() for item in blockers if str(item).strip()]
    if not isinstance(coverage, dict):
        coverage = {}
    missing_coverage = [
        area for area in CLARIFICATION_COVERAGE_AREAS
        if str(coverage.get(area, "")).strip().lower() != "covered"
    ]
    if missing_coverage:
        blockers.append(
            "独立澄清复核未证明以下必要条件已覆盖：" + "、".join(missing_coverage)
        )
    # Only an explicit pass with no undisclosed blocker can advance to the
    # human confirmation checkpoint. A reviewer cannot make an ambiguous
    # request look complete by omitting the status field.
    passed = status == "complete" and not blockers and not questions
    if not passed and not questions:
        questions = ["请补充当前范围中仍会改变方案、验收或风险判断的关键信息。"]
    return {
        "status": "complete" if passed else "needs_input",
        "summary": str(value.get("summary", "")).strip(),
        "questions": questions,
        "blockers": blockers,
        "coverage": coverage,
        "conflicts": value.get("conflicts", []),
    }


def intake_prompt(state: dict[str, Any], answers: str | None) -> str:
    transcript = "\n".join(
        f"Turn {turn['turn']}:\nUser request/answers:\n{turn['user_text']}\nAgent result:\n{turn.get('summary', '')}"
        for turn in state.get("turns", [])
    )
    latest = f"\nLatest user answer:\n{answers}" if answers else ""
    evidence = state.get("implemented_feature_evidence")
    evidence_context = ""
    if _task_mode(state) == "implemented_feature_prd" and isinstance(evidence, Mapping):
        capability = evidence.get("visual_runtime_capability")
        capability = capability if isinstance(capability, Mapping) else {}
        inventory = capability.get("frontend_inventory")
        inventory = inventory if isinstance(inventory, Mapping) else {}
        evidence_context = """
Frozen implementation evidence collected before clarification (use it to ask
about observed behavior; do not treat mocks, fixtures, scaffolding, or test-only
controls as product scope):
%s
""" % json.dumps({
            "branch_name": evidence.get("branch_name"),
            "changed_files": evidence.get("changed_files"),
            "behavior_evidence": evidence.get("behavior_evidence"),
            "validation_evidence": evidence.get("validation_evidence"),
            "frontend": {
                "platform": inventory.get("platform"),
                "preview_surface": inventory.get("preview_surface"),
                "target_matched_files": inventory.get("target_matched_files"),
            },
        }, ensure_ascii=False)
    return f"""You are the PM Orchestrator's production requirement-intake agent.
The user request is ambiguous by default. Work from first principles: identify the
goal, necessary conditions, current blocker, most direct question, and proof needed
to move to the next phase. Ask only questions that materially change scope,
success criteria, platform, permissions, compliance, measurement, or delivery risk.
Never treat silence, a fixture, or your own assumption as user confirmation.

PM Copilot's default product owner is the product manager. Do not ask who owns
ordinary PRD decisions, requirement acceptance, risk trade-offs, or launch
recommendations unless the user identifies a different owner or that ownership
changes a concrete product, permission, compliance, or delivery boundary. Put
development or launch follow-ups in the later-confirmation bucket; do not
promote them to generation blockers unless the PRD would otherwise have to
guess user-visible behavior or acceptance evidence.

Return ONLY one JSON object with this shape:
{{
  "status": "needs_input" | "complete",
  "summary": "what is currently understood",
  "questions": ["branch-changing question with why it matters"],
  "buckets": {{
    "must_answer_before_generation": [],
    "can_draft_with_stated_assumption": [],
    "must_confirm_before_development_or_launch": []
  }},
  "scope": {{"goal":"", "users":[], "in_scope":[], "out_of_scope":[], "platform":""}},
  "assumptions": [], "decisions": [], "risks": []
}}
Put every unresolved material unknown in exactly one bucket. If any
must_answer_before_generation item remains, status MUST be needs_input and the
questions list MUST contain the corresponding questions.

Initial user request:
{state['raw_request']}

Conversation so far:
{transcript or '(no previous turns)'}
{latest}
{evidence_context}
"""


def clarification_review_prompt(state: dict[str, Any], intake: dict[str, Any]) -> str:
    transcript = "\n".join(
        f"Turn {turn['turn']} user input: {turn['user_text']}\n"
        f"Intake conclusion: {turn.get('summary', '')}"
        for turn in state.get("turns", [])
    )
    return f"""You are the independent Clarification Review Agent for a production PM run.
Challenge the Intake Agent's conclusion from first principles. The request may
not advance merely because another model said it is complete. Identify every
unresolved fact that can materially change the user outcome, scope boundary,
non-goal, acceptance evidence, platform/delivery surface, owner/permission,
metric, or material risk. Do not ask preference or implementation questions
that cannot change the next product decision.

PM Copilot's default product owner is the product manager. Do not block merely
because an ordinary PRD decision, acceptance decision, risk trade-off, or
launch recommendation lacks a separately named owner. A fact deliberately
assigned to the development/launch confirmation bucket is covered unless it
would force this PRD to guess user-visible behavior or acceptance evidence.

Return ONLY one JSON object in your final response (UTF-8):
{{
  "status": "needs_input" | "complete",
  "summary": "coverage judgment",
  "questions": ["one next branch-changing question with why it matters"],
  "blockers": ["unresolved material decision"],
  "coverage": {{"goal":"covered|missing", "users":"covered|missing", "scope":"covered|missing", "success_evidence":"covered|missing", "constraints_and_risk":"covered|missing"}},
  "conflicts": []
}}
Use status complete only when every material unknown is either answered by the
user, explicitly accepted as a stated draft assumption, or assigned to the
development/launch confirmation bucket. When status is needs_input, include a
question for each blocker. User silence and model inference are never answers.
For status complete, set every coverage field to exactly covered. Missing,
unknown, or partial coverage is a blocker, not a pass.

Original request:\n{state['raw_request']}

Conversation:\n{transcript or '(no conversation yet)'}

Intake conclusion to challenge:\n{json.dumps(intake, ensure_ascii=False)}
"""


def run_clarification_review(
    state: dict[str, Any], intake: dict[str, Any], provider: str, timeout: int,
    worker: Callable[..., dict[str, Any]] = execute, model: str | None = None,
) -> dict[str, Any]:
    # Clarification review is a bounded, read-only verdict. Its final JSON is
    # preserved in the attributable Agent call instead of masquerading as a
    # staged deliverable that must mutate a temporary file.
    result = worker(provider, clarification_review_prompt(state, intake), ROOT, timeout, model, None, False, 8000)
    result["phase"] = "clarification_review"
    if not _record_agent_call(state, result, phase="clarification_review"):
        return {"status": "failed", "blockers": ["Clarification Review Agent call has no attributable provider/model evidence"]}
    if result.get("status") != "complete":
        return {
            "status": "needs_input",
            "summary": "独立澄清复核未能完成，不能跳过需求澄清。",
            "questions": ["请确认是否继续并补充会影响范围、验收或风险的背景。"],
            "blockers": [result.get("error", "Clarification Review Agent failed")],
            "coverage": {},
            "conflicts": [],
        }
    try:
        raw_review = result.get("output", "")
        return _normalise_clarification_review(_extract_json(raw_review))
    except (ValueError, json.JSONDecodeError) as error:
        return {
            "status": "needs_input",
            "summary": "独立澄清复核没有返回可验证结论。",
            "questions": ["请补充会影响方案边界与验收方式的关键信息。"],
            "blockers": [str(error)],
            "coverage": {},
            "conflicts": [],
        }


def run_intake(
    state: dict[str, Any], provider: str, timeout: int,
    worker: Callable[..., dict[str, Any]] = execute, answers: str | None = None, model: str | None = None,
) -> dict[str, Any]:
    result = worker(provider, intake_prompt(state, answers), ROOT, timeout, model, None, False, 8000)
    result_record = {**result, "turn": len(state.get("turns", [])) + 1}
    if not _record_agent_call(state, result_record, phase="intake"):
        state["status"] = "failed"
        state["termination"] = "failed"
        state["last_error"] = "Intake Agent call has no attributable provider/model evidence"
        return state
    if result.get("status") != "complete":
        state["status"] = "failed"
        state["termination"] = "failed"
        state["last_error"] = result.get("error", "intake Agent failed")
        return state
    try:
        intake = _normalise_intake(_extract_json(result.get("output", "")))
    except (ValueError, json.JSONDecodeError) as error:
        state["status"] = "failed"
        state["termination"] = "failed"
        state["last_error"] = str(error)
        return state
    user_text = answers or state["raw_request"]
    state.setdefault("turns", []).append({
        "turn": len(state.get("turns", [])) + 1,
        "user_text": user_text,
        "summary": intake["summary"],
        "questions": intake["questions"],
        "buckets": intake["buckets"],
        "scope": intake["scope"],
        "assumptions": intake["assumptions"],
        "decisions": intake["decisions"],
        "risks": intake["risks"],
    })
    state["current_intake"] = intake
    if intake["status"] == "needs_input":
        state["status"] = "needs_input"
        state["termination"] = "needs_input"
    else:
        review = run_clarification_review(state, intake, provider, timeout, worker, model)
        state["clarification_review"] = review
        if review["status"] == "failed":
            state["status"] = "failed"
            state["termination"] = "failed"
            state["last_error"] = "Independent clarification review has no attributable Agent evidence"
        elif review["status"] == "needs_input":
            # The independent reviewer owns this gate. Preserve its blockers in
            # the final turn so a resumed run asks the same unresolved branch.
            state["turns"][-1]["questions"] = review["questions"]
            state["turns"][-1]["buckets"]["must_answer_before_generation"] = review["blockers"] or review["questions"]
            state["status"] = "needs_input"
            state["termination"] = "needs_input"
        else:
            state["status"] = "awaiting_confirmation"
            state["termination"] = "human_checkpoint"
    return state


def write_discussion(folder: Path, state: dict[str, Any]) -> None:
    latest = state["turns"][-1]
    lines = ["# 需求讨论记录", "", "## 用户原始需求", state["raw_request"], "", "## 讨论结论", latest["summary"] or "（用户与 PM Copilot 已完成当前轮讨论）", "", "## 已明确范围"]
    scope = latest.get("scope", {})
    for label, key in (("目标", "goal"), ("用户", "users"), ("范围内", "in_scope"), ("范围外", "out_of_scope"), ("平台", "platform")):
        value = scope.get(key, "")
        if isinstance(value, list):
            value = "、".join(str(item) for item in value)
        lines.append(f"- {label}：{value or '未提供'}")
    lines += ["", "## 对话轮次"]
    for turn in state["turns"]:
        lines += [f"### 第 {turn['turn']} 轮", f"用户：{turn['user_text']}", f"PM Copilot：{turn['summary']}", ""]
    folder.joinpath("discussion.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def create_state(
    raw_request: str, folder: Path, *, task_mode: str | None = None,
    delivery_variant: str | None = None,
) -> dict[str, Any]:
    extraction = _request_looks_like_extraction(raw_request)
    variant = delivery_variant or ("compose_to_new" if extraction else "new")
    mode = task_mode or (
        "prd_composition"
        if variant == "compose_to_new"
        else "prd_revision"
        if variant == "in_place_revision"
        else "implemented_feature_prd"
        if _request_looks_like_implemented_feature(raw_request)
        else "new_prd"
    )
    return {
        "schema_version": 1,
        "mode": "interactive",
        "folder": str(folder),
        "raw_request": raw_request,
        "task_mode": mode,
        "delivery_variant": variant,
        "context_source": {
            "mode": (
                "repo-backed"
                if mode == "implemented_feature_prd"
                else "document-backed"
                if variant == "compose_to_new"
                else "brief-only"
            ),
            "files_loaded": [],
            "host_project_root": "",
            "host_project_files_loaded": [],
            "product_documents_loaded": [],
        },
        "status": "new",
        "termination": "running",
        "turns": [],
        "agent_calls": [],
        "artifacts": [],
        "user_confirmation": None,
        "revision_history": [],
        "delivery_stages": {},
        "input_assets": [],
        "input_asset_manifest": None,
    }


def begin_in_place_revision(
    state: dict[str, Any], request: str, selectors: list[str] | None = None,
) -> dict[str, Any]:
    """Reopen one canonical PRD folder without creating a competing delivery."""
    if state.get("mode") != "interactive":
        raise ValueError("run folder is not an interactive production run")
    request = request.strip()
    if not request:
        raise ValueError("a revision request is required")
    for key in ("revision_scope_validation", "revision_stop_reason", "scope_clarification"):
        state.pop(key, None)
    # This is a new revision request, not a resume of the prior confirmed
    # delivery. Its clarification must be frozen from the new turns only.
    state.pop("confirmed_fact_packet", None)
    # A prior delivery's assets are now canonical baseline material. They must
    # not remain implicitly authorized as new input for a later revision.
    state["input_assets"] = []
    state.pop("input_asset_manifest", None)
    folder = Path(str(state["folder"]))
    prd_path = folder / "prd.md"
    known_ids = _trace_requirement_ids(prd_path)
    state.setdefault("revision_history", []).append({
        "at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "request": request,
        "prd_before_sha256": _artifact_digest(prd_path),
        "html_before_sha256": _artifact_digest(folder / "prd.html"),
        "assets_before_sha256": _revision_asset_digests(folder),
        "baseline_requirement_ids": known_ids,
        "mode": "in_place_revision",
    })
    ids = set(_trace_values(selectors))
    ids.update(_extract_requirement_ids(request, known_ids))
    ids.intersection_update(known_ids)
    state["revision_requirement_ids"] = sorted(ids)
    state["revision_scope_manifest"] = {
        "mode": "in_place_revision",
        "request": request,
        "requirement_ids": sorted(ids),
        "selectors": _trace_values(selectors),
        "selector_status": "resolved" if ids else "needs_input",
        "authority": "user-confirmed natural-language scope",
        "allowed_derivatives": {
            # A material selected-behavior revision needs an append-only
            # history row; the scope validator still rejects such a row for
            # a layout- or media-only update.
            "append_only_version_history": bool(re.search(r"(?mi)^###\s+(?:\d+[.、]\s*)?版本(?:记录|历史)\s*$", prd_path.read_text(encoding="utf-8"))),
        },
    }
    state["delivery_variant"] = "in_place_revision"
    state["task_mode"] = "prd_revision"
    state["context_source"] = {
        "mode": "document-backed",
        "files_loaded": ["prd.md", "run-log.yaml"],
        "host_project_root": "",
        "host_project_files_loaded": [],
        "product_documents_loaded": ["prd.md"],
    }
    state["revision_request"] = request
    state["raw_request"] = request
    state["turns"] = []
    state["user_confirmation"] = None
    state["status"] = "new"
    state["termination"] = "running"
    state["artifacts"] = [item for item in state.get("artifacts", []) if item in {"prd.md", "prd.html", "run-log.yaml"}]
    return state


def begin_implemented_feature_append(state: dict[str, Any], request: str) -> dict[str, Any]:
    """Open a completed PRD for append-only implemented-feature delivery."""
    folder = _canonical_folder(state)
    prd_path = folder / "prd.md"
    if state.get("status") != "complete" or not prd_path.is_file() or not (folder / "prd.html").is_file():
        raise ValueError("--append-implemented-feature requires a completed canonical PRD with prd.md and prd.html")
    baseline_ids = _trace_requirement_ids(prd_path)
    if not baseline_ids:
        raise ValueError("current PRD has no requirement IDs to append after")
    state.setdefault("revision_history", []).append({
        "at": dt.datetime.now(dt.timezone.utc).isoformat(), "request": request,
        "prd_before_sha256": _artifact_digest(prd_path), "html_before_sha256": _artifact_digest(folder / "prd.html"),
        "assets_before_sha256": _revision_asset_digests(folder), "baseline_requirement_ids": baseline_ids,
        "mode": "append_implemented_feature",
    })
    state["append_implemented_feature"] = {"baseline_requirement_ids": baseline_ids}
    state["revision_requirement_ids"] = baseline_ids
    state["revision_scope_manifest"] = {"authority": "user-confirmed implemented-feature append", "selectors": []}
    state["append_requirement_ids"] = []
    state["task_mode"] = "implemented_feature_prd"
    state["delivery_variant"] = "in_place_revision"
    state["context_source"] = {
        "mode": "repo-backed", "files_loaded": ["prd.md", "run-log.yaml"],
        "host_project_root": "", "host_project_files_loaded": [], "product_documents_loaded": ["prd.md"],
    }
    state["raw_request"] = request
    state["turns"] = []
    state.pop("confirmed_fact_packet", None)
    state.pop("implemented_feature_evidence", None)
    state.pop("implemented_feature_evidence_source", None)
    state["user_confirmation"] = None
    state["status"] = "new"
    state["termination"] = "running"
    state["artifacts"] = [item for item in state.get("artifacts", []) if item in {"prd.md", "prd.html", "run-log.yaml"}]
    return state


def compact_requirement_numbers(text: str) -> str:
    """Renumber current requirement details consecutively after a deletion.

    Requirement references in the list, detail tables, tracking and handoff
    evidence are rewritten together so an in-place revision cannot leave a gap.
    """
    headings = re.findall(r"(?m)^###\s+(5\.\d+)(?:\s|$)", text)
    unique = list(dict.fromkeys(headings))
    mapping = {old: f"5.{index}" for index, old in enumerate(unique, 1)}
    for old, new in mapping.items():
        text = re.sub(rf"(?<![\d.]){re.escape(old)}(?![\d.])", new, text)
    return text


def _extract_requirement_ids(request: str, known_ids: Sequence[str] | None = None) -> list[str]:
    """Extract requirement references without mistaking CSS values for IDs."""
    known = {str(item) for item in (known_ids or [])}
    candidates = re.findall(r"(?:需求|requirement|PRD|第|修订|修改|更新|删除|新增)\s*#?\s*(\d+\.\d+)\b", request, re.IGNORECASE)
    if known:
        return list(dict.fromkeys(item for item in candidates if item in known))
    return list(dict.fromkeys(candidates))


def _extract_prd_copy_items(text: str) -> list[str]:
    """Collect user-facing copy evidence from the PRD localization section."""
    match = re.search(r"(?ms)^##\s+六、[^\n]*\n(?P<body>.*?)(?=^##\s|\Z)", text)
    body = match.group("body") if match else text
    values = re.findall(r"[“「『]([^”」』\n]{2,80})[”」』]", body)
    values.extend(re.findall(r"(?m)^\s*[-*]\s+([^\n|]{2,80})\s*$", body))
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def _normalise_confirmed_prd_copy(path: Path) -> None:
    """Keep the confirmed failure fallback copy identical across PRD sections."""
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    text = text.replace("节点执行失败，请稍后重试。", "节点执行失败，请稍后重试。")
    text = re.sub(r"节点执行失败，请稍后重试(?!。)", "节点执行失败，请稍后重试。", text)
    _atomic_write_text(path, text)


def _confirmation_packet(state: dict[str, Any]) -> dict[str, Any]:
    """Keep Agent context bounded while preserving the final confirmed facts."""
    latest = state.get("confirmed_fact_packet") or state["turns"][-1]
    return {
        "user_confirmation": state.get("user_confirmation"),
        "final_user_message": latest.get("user_text", ""),
        "summary": latest.get("summary", ""),
        "scope": latest.get("scope", {}),
        "assumptions": latest.get("assumptions", []),
        "decisions": latest.get("decisions", []),
        "risks": latest.get("risks", []),
        "can_draft_with_stated_assumption": latest.get("buckets", {}).get("can_draft_with_stated_assumption", []),
        "must_confirm_before_development_or_launch": latest.get("buckets", {}).get("must_confirm_before_development_or_launch", []),
    }


def _confirmed_fact_source(state: dict[str, Any]) -> dict[str, Any]:
    """Return the immutable fact packet selected at the confirmation gate."""
    return state.get("confirmed_fact_packet") or state["turns"][-1]


def _revision_scope_writer_contract(state: dict[str, Any]) -> str:
    """Project the controller-owned revision contract into actionable writer rules.

    The durable manifest includes baseline hashes for deterministic validation.
    Those hashes do not help an Agent write a bounded revision and can needlessly
    enlarge a delivery prompt, so provide its complete semantic boundary rather
    than replaying integrity implementation details.
    """
    if _is_implemented_feature_append(state):
        baseline = _trace_values(state.get("revision_requirement_ids"))
        next_number = max(int(item.split(".", 1)[1]) for item in baseline if item.startswith("5.")) + 1
        evidence = state.get("implemented_feature_evidence")
        capability = evidence.get("visual_runtime_capability") if isinstance(evidence, Mapping) else {}
        capture = capability.get("real_frontend_capture") if isinstance(capability, Mapping) else {}
        capture_asset = str(capture.get("prd_asset_path") or "").strip() if isinstance(capture, Mapping) else ""
        capture_rule = f"Use the frozen real screenshot at {capture_asset} beside the matching new behavior when it matches the confirmed state." if capture_asset else "No real capture is available; retain a controlled figure placeholder for later reconstruction or manual completion."
        return f"""
This is an append-only implemented-feature PRD update. Preserve every existing
PRD requirement row and detail section byte-for-byte, preserve all existing
assets, and do not rewrite document structure. Add one or more new requirement
rows and matching detail sections only, using contiguous IDs beginning with
5.{next_number}. Append a complete version-history record. Use the frozen
source-material implementation evidence packet; do not inspect host files.
{capture_rule}
"""
    manifest = state.get("revision_scope_manifest")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return """
Controller-owned in-place revision scope contract is unavailable. Do not infer
or broaden a revision boundary from the request; preserve the staged PRD until
the controller supplies a materialized scope contract.
"""

    selected_ids = _trace_values(manifest.get("requirement_ids"))
    baseline = manifest.get("baseline")
    baseline = baseline if isinstance(baseline, dict) else {}
    baseline_sections = baseline.get("requirement_sections")
    baseline_sections = baseline_sections if isinstance(baseline_sections, dict) else {}
    protected_requirement_ids = [
        requirement_id for requirement_id in baseline_sections
        if str(requirement_id) not in selected_ids
    ]
    baseline_assets = baseline.get("assets")
    baseline_assets = baseline_assets if isinstance(baseline_assets, dict) else {}
    allowed_new_assets = manifest.get("allowed_new_assets")
    allowed_new_assets = allowed_new_assets if isinstance(allowed_new_assets, dict) else {}
    derivatives = manifest.get("allowed_derivatives")
    derivatives = derivatives if isinstance(derivatives, dict) else {}
    # Legacy resumptions may predate the explicit derivative field. The PRD
    # scope validator remains authoritative about whether an append is valid.
    derivatives.setdefault("append_only_version_history", True)

    raw_image_contracts = manifest.get("image_contracts")
    raw_image_contracts = raw_image_contracts if isinstance(raw_image_contracts, list) else []
    image_contracts: list[dict[str, Any]] = []
    for raw_contract in raw_image_contracts:
        if not isinstance(raw_contract, dict):
            continue
        image_contracts.append({
            "requirement_ids": _trace_values(raw_contract.get("requirement_ids")),
            "required_image_refs": _trace_values(raw_contract.get("required_image_refs")),
            "exact_count": bool(raw_contract.get("exact_count")),
            "fixed_order": bool(raw_contract.get("fixed_order")),
            "source": str(raw_contract.get("source", "")).strip(),
        })

    semantic_packet = {
        "selected_requirement_ids": selected_ids,
        "protected_requirement_ids": protected_requirement_ids,
        "protected_asset_paths": list(baseline_assets),
        "allowed_new_asset_paths": list(allowed_new_assets),
        "selected_image_contracts": image_contracts,
        "linked_localization_rows_allowed": bool(derivatives.get("linked_localization_rows")),
        "append_only_version_history_allowed": bool(derivatives.get("append_only_version_history")),
    }

    image_rules: list[str] = []
    for contract in image_contracts:
        ids = ", ".join(contract["requirement_ids"]) or "the selected sections"
        refs = list(contract["required_image_refs"])
        refs_text = ", ".join(refs) or "(none)"
        if contract["exact_count"]:
            image_rules.append(
                f"- {ids}: use exactly {len(refs)} local image marker(s), with no extra "
                f"selected-section image; required references are {refs_text}."
            )
        else:
            image_rules.append(
                f"- {ids}: include each required local image reference: {refs_text}."
            )
        if contract["fixed_order"]:
            image_rules.append(
                f"  Keep their marker order exactly: {refs_text}."
            )
    if not image_rules:
        image_rules.append(
            "- No controller-confirmed exact image set applies; do not invent a document-wide image rule."
        )

    if derivatives.get("linked_localization_rows"):
        linked_copy_rule = (
            "Linked localization rows are allowed only when their copy is tied to a selected "
            "requirement. Leave every unrelated localization row unchanged."
        )
    else:
        linked_copy_rule = (
            "No linked-localization allowance exists. Preserve every localization row, including "
            "rows whose wording might look related."
        )

    if derivatives.get("append_only_version_history"):
        version_history_rule = (
            "The existing version-history heading and every prior record are protected. For a "
            "material selected-requirement change, append contiguous complete record row(s) "
            "immediately after the existing records; each row needs version, YYYY-MM-DD date, "
            "material change summary, and owner. Do not add a version record for a layout- or "
            "media-only change."
        )
    else:
        version_history_rule = (
            "There is no controller allowance to change version history. Preserve any existing "
            "history content and do not create, edit, reorder, or append records."
        )

    return f"""
Controller-owned in-place revision scope contract (authoritative):
{json.dumps(semantic_packet, ensure_ascii=False, separators=(",", ":"))}

Apply this contract exactly:
- Change only the selected requirement sections and their matching requirement-list rows. The
  protected requirement sections and all other document structure, headings, field labels, and
  unselected content must remain byte-for-byte equivalent to the staged baseline, except for the
  explicitly allowed linked-localization rows and append-only version-history derivative below.
- Protected assets must remain at the same path with unchanged bytes. Existing baseline assets
  may be retained or referenced, but only the listed controller-copied allowed-new asset paths
  may be added; do not create, replace, or rename assets.
- Selected-section image rules:
{chr(10).join(image_rules)}
- {linked_copy_rule}
- {version_history_rule}
- A material change changes selected requirement prose other than media, a selected
  requirement-list row, or an allowed linked-localization row. A layout/media-only change only
  changes selected-section media markup or media references without changing those product or
  copy semantics. Never use a layout/media-only update to justify a version-history record.
"""


def _materialize_reconstructed_figures(state: dict[str, Any], folder: Path) -> list[dict[str, Any]]:
    """Turn controlled figure placeholders into isolated captures when possible.

    The writer can express the required frontend state without inventing a
    screenshot.  This controller-owned step then makes a real browser capture
    of a disposable reconstruction.  Failure is intentionally non-fatal: the
    original controlled placeholder is retained with the capture report so the
    user never receives an implied real figure.
    """
    prd_path = folder / "prd.md"
    if not prd_path.is_file():
        return []
    text = prd_path.read_text(encoding="utf-8")
    records: list[dict[str, Any]] = []
    script = ROOT / "scripts" / "generate_reconstructed_figure.py"
    for match in list(PLACEHOLDER_DECLARATION_RE.finditer(text)):
        asset_name = match.group("name").strip()
        heading_matches = list(re.finditer(r"(?m)^###\s+(\d+\.\d+)\s+(.+)$", text[:match.start()]))
        requirement_id, title = (heading_matches[-1].group(1), heading_matches[-1].group(2)) if heading_matches else ("", asset_name)
        state_name = Path(asset_name).stem.split("-", 1)[-1] or "默认状态"
        command = [
            sys.executable, str(script), "--run-folder", str(folder), "--asset-name", asset_name,
            "--title", title, "--state", state_name,
        ]
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        report_path = Path("tool-results") / "reconstructed-figures" / f"{Path(asset_name).stem}.json"
        record: dict[str, Any] = {
            "target_ref": requirement_id,
            "asset_name": asset_name,
            "provenance": "reconstructed_figure" if result.returncode == 0 else "required_placeholder",
            "reconstruction_path": (Path("reconstructions") / f"{Path(asset_name).stem}.html").as_posix(),
            "capture_report": report_path.as_posix(),
        }
        asset = folder / "assets" / asset_name
        if result.returncode == 0 and asset.is_file():
            marker = (
                f'[[prd-detail-media src="./assets/{asset_name}" alt="{Path(asset_name).stem}" '
                f'copy="一、{state_name}<br>1. 此还原图示用于核对已确认的用户可见规则与反馈。"]]'
            )
            text = text[:match.start()] + marker + text[match.end():]
            record["path"] = f"assets/{asset_name}"
            record["asset_sha256"] = _artifact_digest(asset)
        else:
            record["replacement_status"] = "pending_manual_completion"
            record["replacement_instruction"] = (
                f"在 {requirement_id or '对应需求'} 的 {state_name} 状态补充真实页面截图，"
                f"替换 {asset_name} 占位图。"
            )
            record["capture_error"] = (result.stderr or result.stdout).strip()[-800:]
        records.append(record)
    if records:
        _atomic_write_text(prd_path, text)
    state["frontend_figure_evidence"] = records
    return records


def _artifact_prompt(state: dict[str, Any], artifact: str, repair_errors: str = "") -> str:
    latest = _confirmed_fact_source(state)
    role = "Requirements"
    target = _delivery_folder(state) / artifact
    available_assets = [
        str(record["name"])
        for record in _input_asset_records(state, _delivery_folder(state))
    ]
    variant = _delivery_variant(state)
    task_mode = _task_mode(state)
    prd_template = "templates/implemented-feature-prd-template.md" if task_mode == "implemented_feature_prd" else "templates/prd-template.md"
    variant_instruction = ""
    if variant == "in_place_revision":
        variant_instruction = """
This is an in-place partial PRD revision. Preserve the staged PRD structure,
unchanged requirement sections, and existing assets. Change only the confirmed
requirement IDs; do not broaden scope from an ambiguous natural-language
request. The controller records revision lineage and evidence separately.
""" + (_revision_scope_writer_contract(state) if artifact == "prd.md" else "")
    elif variant == "compose_to_new":
        sources = [
            {
                "source_id": str(source.get("source_id", "")),
                "display_name": str(source.get("display_name", "")),
                "snapshot_path": str(source.get("snapshot_path", "")),
                "selected_scope": list(source.get("selected_scope", [])),
            }
            for source in _extraction_sources(state)
        ]
        selection = json.dumps(_extraction_selection(state), ensure_ascii=False)
        variant_instruction = f"""
This is a composition into a new independent PRD. Read only these immutable
document-backed source snapshots: {json.dumps(sources, ensure_ascii=False)}.
Create a fresh PRD structure from the confirmed selection {selection}; do not
copy unrelated sections, historical trace text, or source-run status into the
new PRD. The source IDs are provenance labels, not PRD content.
"""
    elif task_mode == "implemented_feature_prd":
        evidence_source = state.get("implemented_feature_evidence_source")
        packet_path = (
            str(evidence_source.get("packet_path", "")).strip()
            if isinstance(evidence_source, dict) else ""
        )
        evidence = state.get("implemented_feature_evidence")
        capability = evidence.get("visual_runtime_capability") if isinstance(evidence, Mapping) else {}
        capture = capability.get("real_frontend_capture") if isinstance(capability, Mapping) else {}
        capture_asset = str(capture.get("prd_asset_path") or "").strip() if isinstance(capture, Mapping) else ""
        capture_rule = (
            f"A frozen real screenshot is available at {capture_asset}; use it only beside the matching observed state."
            if capture_asset else
            "No real capture is available; use controlled placeholder or reconstruction flow for each required state."
        )
        variant_instruction = f"""
This is an implemented-feature PRD. Read the canonical source-material JSON
packet at {packet_path}. Use only that packet as observed implementation
evidence: do not inspect repository files, diffs, external paths, tool output,
or model inference to establish implemented behavior. The confirmed
conversation defines product scope, but any behavior absent from the packet is
unverified product intent and must remain explicit rather than invented.
{capture_rule}
"""
    specialist_evidence = state.get("specialist_evidence")
    specialist_instruction = ""
    if isinstance(specialist_evidence, list) and specialist_evidence:
        evidence_paths = [
            str(item.get("path", "")) for item in specialist_evidence
            if isinstance(item, Mapping) and item.get("path")
        ]
        specialist_instruction = f"""
Independent specialist evidence is available at these run-local paths:
{json.dumps(evidence_paths, ensure_ascii=False)}
It is advisory, may contain failures or uncertainty, and never overrides the confirmed scope. Read only the files relevant to this artifact; PM Copilot makes the final product judgment.
"""
    return f"""You are the accountable PM Copilot {role} Agent in a production interactive run.
    The user explicitly confirmed the clarified requirements below. Treat the
    confirmed conversation as product-scope evidence; do not invent approvals,
    metrics, policy, or regulated decisions. Write one complete artifact at {target}.
Do not modify any other file and do not return until the file exists.

Original request: {state['raw_request']}
Clarified scope: {json.dumps(latest.get('scope', {}), ensure_ascii=False)}
Discussion summary: {latest.get('summary', '')}
Assumptions: {json.dumps(latest.get('assumptions', []), ensure_ascii=False)}
Risks: {json.dumps(latest.get('risks', []), ensure_ascii=False)}
Final user-confirmed evidence packet (authoritative and complete for this run):
{json.dumps(_confirmation_packet(state), ensure_ascii=False)}

Artifact requirements:
- confirmed-requirements.md: facts, explicit user-confirmed scope, non-goals, success criteria, constraints, acceptance evidence, assumptions, risks, and unresolved items. Never call model inference user confirmation.
- prd.md: use {prd_template} and artifacts/prd-contract.md exactly. Create a Chinese H1 of concise requirement title plus YYYY-MM-DD; include document information and version history; use every standard requirement-list field; map one-to-one to 5.x detail IDs; each detail table has only 用户与场景、需求入口、需求详情、设计与交互. When new or changed UI copy exists, include 六、多语言需求. Every localization checklist row must name its matching 5.x requirement ID in 使用位置. Every tracking row must name its matching 5.x requirement ID in 备注; do not put a PRD ID in the event identifier. Every user-facing frontend state must be represented inline by a provided real figure or a controlled `占位图：功能-状态.png`; the controller attempts an isolated reconstructed figure for controlled placeholders and records its provenance. Each real figure must be inside its matching 需求详情 cell using exactly `[[prd-detail-media src="./assets/功能-状态.png" alt="功能-状态" copy="一、状态名称<br>1. 该状态的用户可见规则、边界或反馈"]]`: the screenshot is left and `copy` is its right-column state-specific functional logic. Never use a filename, caption, or generic annotation such as “对应成功状态” in `copy`; never put `<div>` or `<img>` source HTML in a Markdown table, never use a standalone Markdown image, and never add a standalone 图示 row. Translate implementation evidence into user-visible behavior; do not include CSS variables or selectors, color values, gradients, stacking levels, exact dimensions, source field names, component names, interfaces, or implementation plans unless the user explicitly requests an engineering or visual-token specification.
- For the prd.md stage, this Agent writes only prd.md. The controller renders and validates prd.html after prd.md passes review; that required downstream deliverable is not a conflict and must not be used as a reason to refuse the prd.md task.
Provided user visual assets already copied to this delivery workspace: {json.dumps(available_assets, ensure_ascii=False)}. Use each applicable asset inline; do not invent a wireframe in place of it.
{variant_instruction}
{specialist_instruction}
""" + (f"\nRepair these validator findings in this artifact only:\n{repair_errors}" if repair_errors else "")


def _run_artifact_agent(
    state: dict[str, Any], artifact: str, provider: str, timeout: int,
    worker: Callable[..., dict[str, Any]] = _delivery_worker, repair_errors: str = "", state_path: Path | None = None,
    model: str | None = None,
) -> bool:
    target = _delivery_folder(state) / artifact
    target.parent.mkdir(parents=True, exist_ok=True)
    real_folder = _delivery_folder(state)
    with tempfile.TemporaryDirectory(prefix=f".{real_folder.name}.stage-", dir=str(real_folder.parent)) as stage_name:
        stage_folder = Path(stage_name) / real_folder.name
        real_snapshot = Path(stage_name) / ".controller-workspace-before"
        _snapshot_delivery_workspace(real_folder, real_snapshot)
        # Build the worker view from the frozen snapshot so a concurrent or
        # misdirected write cannot become part of the stage by accident.
        shutil.copytree(real_snapshot, stage_folder)
        _discard_non_content_assets(stage_folder)
        stage_state = {**state, "folder": str(stage_folder), "delivery_workspace": str(stage_folder)}
        stage_target = stage_folder / artifact
        stage_before_sha256 = _artifact_digest(stage_target)
        target_before_sha256 = _artifact_digest(target)
        target_snapshot = Path(stage_name) / ".controller-target-before"
        if target.is_file():
            shutil.copy2(target, target_snapshot)
        if artifact == "run-log.yaml":
            try:
                _materialize_controller_trace(stage_state, stage_target)
                # The controller owns the trace for every PRD path: new runs,
                # in-place revisions, and extractions from an existing PRD.
                # Resolve any staged asset hashes before a validator sees it.
                _normalise_trace_runtime_evidence(stage_target, _state_runtime_identity(stage_state))
                result = {
                    "provider": CONTROLLER_TRACE_PROVIDER,
                    "model": CONTROLLER_TRACE_MODEL,
                    "pm_copilot_revision": CONTROLLER_TRACE_REVISION,
                    "status": "complete",
                    "output": "controller materialized run-log trace in isolated stage workspace",
                    "error": "",
                    "execution_mode": "deterministic_trace_materialization",
                    "attempt": 1,
                    "expected_artifact": str(stage_target),
                    "artifact_before_sha256": stage_before_sha256,
                    "artifact_after_sha256": _artifact_digest(stage_target),
                }
                result["artifact_changed_in_workspace"] = (
                    result["artifact_after_sha256"] != stage_before_sha256
                )
                _record_agent_call(state, result, phase="delivery", artifact=artifact)
                result["artifact_after_sha256"] = _artifact_digest(stage_target)
                result["artifact_changed_in_workspace"] = (
                    result["artifact_after_sha256"] != stage_before_sha256
                )
            except (OSError, ValueError, yaml.YAMLError) as error:
                result = {
                    "provider": CONTROLLER_TRACE_PROVIDER,
                    "model": CONTROLLER_TRACE_MODEL,
                    "pm_copilot_revision": CONTROLLER_TRACE_REVISION,
                    "status": "failed",
                    "output": "",
                    "error": str(error),
                    "failure_category": "trace_materialization_failed",
                }
                _record_agent_call(state, result, phase="delivery", artifact=artifact)
        else:
            # Codex workspace-write is scoped to its working directory. Execute
            # from the project staging copy so the promised artifact is writable.
            result = {}
            for attempt in range(1, MAX_ATTRIBUTABLE_AGENT_ATTEMPTS + 1):
                attempt_snapshot = Path(stage_name) / f".controller-workspace-before-{attempt}"
                _snapshot_delivery_workspace(real_folder, attempt_snapshot)
                try:
                    result = worker(
                        provider, _artifact_prompt(stage_state, artifact, repair_errors),
                        stage_folder, timeout, model, None, False, 8000,
                    )
                except BaseException:
                    # A worker exception is still an out-of-stage-write risk.
                    # Restore before propagating the original controller error.
                    _restore_delivery_workspace_snapshot(attempt_snapshot, real_folder)
                    raise
                try:
                    _restore_delivery_workspace_snapshot(attempt_snapshot, real_folder)
                except (OSError, ValueError) as error:
                    result.update({
                        "status": "failed",
                        "error": f"controller could not restore the delivery workspace after Agent execution: {error}",
                        "failure_category": "delivery_workspace_restore_failed",
                    })
                result["attempt"] = attempt
                result["expected_artifact"] = str(stage_target)
                result["artifact_before_sha256"] = stage_before_sha256
                result["artifact_after_sha256"] = _artifact_digest(stage_target)
                result["artifact_changed_in_workspace"] = (
                    result["artifact_after_sha256"] != stage_before_sha256
                )
                attributable = _record_agent_call(state, result, phase="delivery", artifact=artifact)
                if (
                    attributable
                    or result.get("cleanup_blocked")
                    or attempt >= MAX_ATTRIBUTABLE_AGENT_ATTEMPTS
                    or not _is_retryable_agent_failure(result)
                ):
                    break
        try:
            _assert_delivery_tree_has_no_symlinks(stage_folder, label="Agent staging workspace")
        except ValueError as error:
            result.update({
                "status": "failed",
                "error": f"Agent staging workspace integrity check failed: {error}",
                "failure_category": "delivery_workspace_integrity_failed",
            })
        if (
            artifact == "prd.md"
            and stage_target.is_file()
            and _delivery_variant(state) != "in_place_revision"
        ):
            # New documents have no protected baseline. An in-place revision
            # does, so controller-wide cleanup must not rewrite unrelated
            # requirement references or normalize untouched copy.
            _normalise_confirmed_prd_copy(stage_target)
            _atomic_write_text(
                stage_target,
                compact_requirement_numbers(stage_target.read_text(encoding="utf-8")),
            )
        if artifact == "prd.md" and _delivery_variant(state) == "in_place_revision":
            manifest = state.get("revision_scope_manifest")
            if isinstance(manifest, dict) and manifest.get("schema_version") == 1:
                baseline = stage_folder / ".revision-baseline" / "prd.md"
                scope_merge: dict[str, Any] | None = None
                if (
                    result.get("status") == "complete"
                    and stage_target.is_file()
                    and baseline.is_file()
                    and not _is_implemented_feature_append(state)
                ):
                    # The full staged PRD is useful context for the writer, but
                    # its authority ends at the confirmed revision surface.
                    # Rebuild the candidate from the frozen baseline before
                    # validating so a model's unrelated rewrite cannot turn a
                    # narrow confirmed revision into a user-input question.
                    scope_merge = constrain_revision_markdown(
                        manifest,
                        baseline_markdown=baseline.read_text(encoding="utf-8"),
                        candidate_markdown=stage_target.read_text(encoding="utf-8"),
                    )
                    if scope_merge.get("status") == "merged":
                        merged_markdown = str(scope_merge.get("markdown", ""))
                        if merged_markdown != stage_target.read_text(encoding="utf-8"):
                            _atomic_write_text(stage_target, merged_markdown)
                        result["controller_scope_repair"] = {
                            "status": "applied",
                            "preserved": list(scope_merge.get("preserved", [])),
                        }
                    else:
                        result["controller_scope_repair"] = {
                            "status": "failed",
                            "failures": list(scope_merge.get("failures", [])),
                        }
                scope_report = _validate_staged_revision_scope(stage_state, stage_folder)
                state.pop("revision_scope_validation", None)
                precheck = stage_state.get("revision_scope_precheck")
                if isinstance(precheck, Mapping):
                    state["revision_scope_precheck"] = dict(precheck)
                else:
                    state.pop("revision_scope_precheck", None)
                staged_attestation = stage_state.get("revision_asset_attestation")
                if isinstance(staged_attestation, Mapping):
                    state["revision_asset_attestation"] = dict(staged_attestation)
                else:
                    state.pop("revision_asset_attestation", None)
                scope_failures = list(scope_report.get("failures", [])) if isinstance(scope_report, dict) else []
                if scope_merge and scope_merge.get("status") != "merged":
                    scope_failures = [
                        *list(scope_merge.get("failures", [])),
                        *scope_failures,
                    ]
                violation = "\n".join(scope_failures)
            else:
                baseline = stage_folder / ".revision-baseline" / "prd.md"
                violation = _revision_scope_violation(
                    stage_target, baseline, state.get("revision_requirement_ids", []),
                )
            if violation:
                result.update({
                    "status": "failed", "exit_code": 1,
                    "failure_category": "revision_scope_violation", "error": violation,
                })
        stage_after_sha256 = _artifact_digest(stage_target)
        # A changed staged file is necessary but not sufficient: the caller
        # must also be attributable before its bytes can enter the delivery
        # workspace or become reusable on a later recovery attempt.
        attributable = _agent_call_has_evidence(result)
        revision_trace_has_evidence = (
            artifact == "run-log.yaml"
            and _delivery_variant(state) == "in_place_revision"
            and (stage_target.parent / "revision-evidence.json").is_file()
        )
        # A deterministic trace may be byte-identical to a previous trace,
        # while its revision evidence is newly materialized for this staging
        # attempt. Promote that companion proof even when run-log.yaml itself
        # did not change; otherwise its lineage becomes a dangling reference.
        promoted = (
            attributable
            and result.get("status") == "complete"
            and stage_after_sha256 is not None
            and (stage_after_sha256 != stage_before_sha256 or revision_trace_has_evidence)
        )
        if promoted:
            if artifact == "run-log.yaml":
                # Agent tools report their writable staging path. The promoted
                # trace must instead identify the stable canonical run folder.
                text = stage_target.read_text(encoding="utf-8")
                _atomic_write_text(stage_target, text.replace(str(stage_folder), str(real_folder)))
            _atomic_copy(stage_target, target)
            if artifact == "prd.md" and _delivery_variant(state) == "in_place_revision":
                # A PRD change invalidates every final proof copied from a
                # prior canonical run. Promote only the markdown precheck;
                # rendering and final artifact-set attestation happen before
                # the controller-owned trace stage.
                _revision_scope_report_path(real_folder).unlink(missing_ok=True)
                (real_folder / "revision-evidence.json").unlink(missing_ok=True)
                scope_report = _revision_scope_precheck_path(stage_folder)
                if scope_report.is_file():
                    _atomic_copy(scope_report, _revision_scope_precheck_path(real_folder))
            if artifact == "run-log.yaml" and _delivery_variant(state) == "in_place_revision":
                # The in-place trace contract points to controller-created
                # revision evidence. Promote that companion file together with
                # the trace so validation never observes a dangling path from
                # the delivery workspace into the discarded child stage.
                evidence = stage_target.parent / "revision-evidence.json"
                if not evidence.is_file():
                    raise FileNotFoundError("deterministic revision trace did not create revision-evidence.json")
                _atomic_copy(evidence, real_folder / evidence.name)
        elif _artifact_digest(target) != target_before_sha256:
            # An Agent that ignored the stage path may have written into the
            # real delivery workspace. It is not this call's artifact, so put
            # that workspace back before exposing the failure to a reviewer.
            if target_snapshot.is_file():
                _atomic_copy(target_snapshot, target)
            else:
                target.unlink(missing_ok=True)
            result["workspace_target_restored"] = True
        stage_target_for_record = stage_target
        if result.get("cleanup_blocked"):
            quarantined_root = _quarantine_unconfirmed_workspace(
                state, Path(stage_name), artifact, "delivery", result,
            )
            if quarantined_root is not None:
                stage_target_for_record = quarantined_root / real_folder.name / artifact
    result["isolated_workspace"] = True
    result["promoted_artifact"] = artifact if promoted else None
    attributable = _agent_call_has_evidence(result)
    stage = _stage(state, artifact)
    stage["artifact_status"] = "promoted" if promoted else "failed"
    stage["artifact_sha256"] = _artifact_digest(target)
    stage["expected_artifact"] = str(stage_target_for_record)
    stage["source_before_sha256"] = stage_before_sha256
    stage["source_after_sha256"] = stage_after_sha256
    stage["failure_category"] = result.get("failure_category")
    stage["scope_fingerprint"] = _confirmed_scope_fingerprint(state)
    stage["pm_copilot_version"] = _state_runtime_version(state)
    stage["runtime_identity"] = _state_runtime_identity(state)
    stage["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    if stage["artifact_status"] == "promoted" and artifact not in state.setdefault("artifacts", []):
        state["artifacts"].append(artifact)
    if result.get("cleanup_blocked"):
        detail = str(result.get("error") or "unconfirmed detached Agent").strip()
        state["last_error"] = f"{artifact} execution is unconfirmed and was quarantined: {detail}"
    elif not attributable:
        detail = str(result.get("error") or result.get("status") or "unknown Agent failure").strip()
        state["last_error"] = f"{artifact} Agent call has no attributable provider/model evidence: {detail}"
    elif not promoted:
        detail = str(result.get("error", "")).strip()
        state["last_error"] = (
            f"{artifact} was not changed in the project staging directory"
            + (f": {detail}" if detail else "")
        )
    if not promoted:
        state["last_failure_category"] = result.get("failure_category") or state.get("last_error")
    _checkpoint(state, state_path)
    return attributable and promoted


_REVIEW_EVIDENCE_QUOTE_RE = re.compile(
    r'"([^"\n]{3,})"|“([^”\n]{3,})”|`([^`\n]{3,})`|「([^」\n]{3,})」'
)
_ASSET_PROVENANCE_REQUEST_RE = re.compile(
    r"(?:"
    r"(?:asset|image|figure|screenshot|media|图片|图示|截图|资源).{0,56}"
    r"(?:exist(?:ence)?|source|provenance|hash|sha-?256|file|path|存在|来源|哈希|校验|证明)"
    r"|(?:prove|verify|confirm|证明|验证|确认).{0,56}"
    r"(?:asset|image|figure|screenshot|media|图片|图示|截图|资源)"
    r")",
    re.IGNORECASE | re.DOTALL,
)


def _is_in_place_prd_review(state: Mapping[str, Any], artifact: str) -> bool:
    return artifact == "prd.md" and _delivery_variant(dict(state)) == "in_place_revision"


def _revision_asset_attestation_for_review(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return the current controller-owned media attestation for review input."""
    direct = state.get("revision_asset_attestation")
    if isinstance(direct, Mapping):
        return dict(direct)
    validation = state.get("revision_scope_validation")
    if isinstance(validation, Mapping):
        attestation = validation.get("asset_attestation")
        if isinstance(attestation, Mapping):
            return dict(attestation)
    return {}


def _normalise_review_strings(value: object) -> list[str]:
    items = value if isinstance(value, list) else [value]
    return [str(item).strip() for item in items if str(item).strip()]


def _quoted_selected_evidence_is_present(
    state: Mapping[str, Any], requirement_ids: Sequence[str], evidence: str,
) -> bool:
    """Require a reviewer quote that the selected PRD section actually contains."""
    prd_path = _delivery_folder(dict(state)) / "prd.md"
    if not prd_path.is_file():
        return False
    sections = requirement_sections(prd_path.read_text(encoding="utf-8"))
    selected_text = "\n".join(
        str(sections[requirement_id].get("content", ""))
        for requirement_id in requirement_ids
        if requirement_id in sections
    )
    normalized_selected = re.sub(r"\s+", " ", selected_text).strip()
    if not normalized_selected:
        return False
    quotes = [next(part for part in match.groups() if part is not None).strip()
              for match in _REVIEW_EVIDENCE_QUOTE_RE.finditer(evidence)]
    return any(
        re.sub(r"\s+", " ", quote) in normalized_selected
        for quote in quotes
    )


def _revision_review_contract_error(
    state: dict[str, Any], review: Mapping[str, Any], review_status: str,
) -> tuple[list[dict[str, Any]], str | None]:
    """Keep revision reviewer feedback inside the writer-owned selected surface."""
    manifest = state.get("revision_scope_manifest")
    selected = {
        str(item).strip()
        for item in manifest.get("requirement_ids", [])
        if str(item).strip()
    } if isinstance(manifest, Mapping) else set()
    if not selected:
        return [], "controller revision manifest has no selected requirement IDs"
    legacy_findings = _normalise_review_strings(review.get("blocking_findings", []))
    raw_findings = review.get("revision_findings", [])
    if review_status == "pass":
        if legacy_findings or raw_findings:
            return [], "pass must not include blocking_findings or revision_findings"
        return [], None
    if review_status != "needs_revision":
        return [], "status must be pass or needs_revision"
    if legacy_findings:
        return [], "in-place revision findings must use typed revision_findings, not blocking_findings"
    if not isinstance(raw_findings, list) or not raw_findings:
        return [], "needs_revision requires a non-empty typed revision_findings list"
    attestation_passed = _revision_asset_attestation_for_review(state).get("status") == "passed"
    normalized: list[dict[str, Any]] = []
    for index, raw_finding in enumerate(raw_findings, start=1):
        if not isinstance(raw_finding, Mapping):
            return [], f"revision finding {index} must be an object"
        kind = str(raw_finding.get("kind", "")).strip()
        owner = str(raw_finding.get("owner", "")).strip()
        raw_ids = raw_finding.get("requirement_ids")
        if not isinstance(raw_ids, list):
            return [], f"revision finding {index} requirement_ids must be a non-empty list"
        requirement_ids = list(dict.fromkeys(str(item).strip() for item in raw_ids if str(item).strip()))
        evidence = str(raw_finding.get("evidence", "")).strip()
        repair = str(raw_finding.get("repair", "")).strip()
        if kind not in REVISION_REVIEWER_FINDING_TYPES:
            return [], f"revision finding {index} has unsupported kind: {kind or '<empty>'}"
        if owner != "prd_writer":
            return [], f"revision finding {index} owner must be prd_writer"
        if not requirement_ids or any(item not in selected for item in requirement_ids):
            return [], f"revision finding {index} must target only selected requirement IDs"
        if not evidence or not repair:
            return [], f"revision finding {index} requires non-empty evidence and repair"
        if not any(re.search(rf"(?<![0-9.]){re.escape(item)}(?![0-9.])", evidence) for item in requirement_ids):
            return [], f"revision finding {index} evidence must name its selected requirement ID"
        if not _quoted_selected_evidence_is_present(state, requirement_ids, evidence):
            return [], f"revision finding {index} evidence must quote the selected PRD section"
        if attestation_passed and _ASSET_PROVENANCE_REQUEST_RE.search("\n".join((evidence, repair))):
            return [], (
                f"revision finding {index} asks the PRD writer to prove controller-owned asset existence or provenance"
            )
        normalized.append({
            "kind": kind,
            "owner": owner,
            "requirement_ids": requirement_ids,
            "evidence": evidence,
            "repair": repair,
        })
    return normalized, None


def _record_review_contract_rejection(state: dict[str, Any], artifact: str, reason: str) -> None:
    state["review_contract_rejection"] = {
        "artifact": artifact,
        "reason": reason,
        "at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def _reject_revision_review_contract(
    state: dict[str, Any], artifact: str, reason: str, state_path: Path | None,
) -> tuple[bool, str]:
    """Persist only the controller diagnosis for an invalid reviewer response."""
    stage = _stage(state, artifact)
    stage["review_status"] = "failed"
    stage["review_findings"] = []
    stage.pop("revision_findings", None)
    stage["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    stage["scope_fingerprint"] = _confirmed_scope_fingerprint(state)
    stage["pm_copilot_version"] = _state_runtime_version(state)
    _record_review_contract_rejection(state, artifact, reason)
    state["last_error"] = f"Stage Quality Review Agent returned an invalid revision review contract: {reason}"
    _checkpoint(state, state_path)
    return False, state["last_error"]


def _artifact_review_prompt(state: dict[str, Any], artifact: str, review_path: Path) -> str:
    target = _delivery_folder(state) / artifact
    revision_contract = ""
    review_output_contract = f"""Write ONLY one JSON object to {review_path} (UTF-8):
{{"status":"pass"|"needs_revision","summary":"", "blocking_findings":["specific repair"], "acceptance_evidence":["checked condition"]}}
Use pass only when blocking_findings is empty and acceptance_evidence proves
the artifact's required handoff conditions. Empty proof is needs_revision."""
    if _is_in_place_prd_review(state, artifact):
        manifest = state.get("revision_scope_manifest")
        attestation = _revision_asset_attestation_for_review(state)
        correction = state.get("review_contract_correction")
        correction = correction if isinstance(correction, Mapping) and correction.get("artifact") == artifact else {}
        revision_contract = f"""
Controller-owned revision scope contract:
{json.dumps(manifest if isinstance(manifest, dict) else {}, ensure_ascii=False, separators=(",", ":"))}
Controller-owned staged asset attestation:
{json.dumps(attestation, ensure_ascii=False, separators=(",", ":"))}
The revision scope manifest and staged asset attestation are authoritative and
override stale wording in the raw request, prior run history, or any prior
reviewer output. The controller attestation is conclusive for selected-asset
existence, source, bytes, and SHA-256 integrity. Do not ask the PRD writer to
prove, re-check, or change controller-owned asset provenance.

The controller has already checked the frozen baseline. Assess behavior, copy,
acceptance constraints, and selected-section media semantics only inside the
contract's requirement_ids. Do not block the review because an unselected
requirement or its existing image/copy remains in the PRD: it is protected
baseline content, not an extension of this revision.

For each needed repair, use exactly one typed revision_finding object:
{{"kind":"selected_behavior_gap|selected_copy_gap|selected_acceptance_gap|selected_media_semantics_gap","owner":"prd_writer","requirement_ids":["5.1"],"evidence":"5.1: \\"exact quote from the selected PRD section\\"","repair":"specific writer repair"}}
Every finding must target only selected requirement IDs, name those IDs in its
evidence, and include an exact quote from the selected PRD section. The only
permitted owner is prd_writer. Do not emit findings for controller ownership,
unselected content, asset existence, asset source, asset bytes, or hashes.
{("The prior response violated this output contract. Correct only this issue: " + str(correction.get("reason", "")).strip()) if correction else ""}
"""
        review_output_contract = f"""Write ONLY one JSON object to {review_path} (UTF-8):
{{"status":"pass"|"needs_revision","summary":"", "blocking_findings":[], "revision_findings":[{{"kind":"selected_behavior_gap|selected_copy_gap|selected_acceptance_gap|selected_media_semantics_gap","owner":"prd_writer","requirement_ids":["5.1"],"evidence":"5.1: \\"exact quote from selected PRD\\"","repair":"specific writer repair"}}], "acceptance_evidence":["checked condition"]}}
For pass, both blocking_findings and revision_findings must be empty, and
acceptance_evidence must prove the selected revision's handoff conditions. For
needs_revision, blocking_findings must remain empty and revision_findings must
be a non-empty list that obeys the typed contract above."""
    return f"""You are the independent Stage Quality Review Agent in a production PM run.
Read only {target}. Check whether this single artifact is complete, internally
consistent with the user-confirmed scope, and sufficient for its immediate
downstream consumer. Do not edit any file. Do not treat file existence or a
previous Agent's success as acceptance. Reject unsupported approvals, invented
facts, missing scope/non-goals/acceptance evidence, or an artifact that would
force its immediate downstream consumer to guess.

The final user-confirmed evidence packet below is primary evidence. A source
path, source document, asset set, migration instruction, or ownership
statement that appears there is confirmed evidence, not an invented fact. Do
not reject a confirmed-requirements artifact because
it does not itself prove a requested migration has already been executed: its
immediate downstream consumer is the PRD writer, so it must state the required
migration and evidence boundary. Items explicitly deferred to development or
launch (for example concrete port IDs, provider limits, analytics definitions,
or launch approval) must remain visible as later gates; they are not PRD
generation blockers unless the user made them part of the confirmed behavior.
For an in-place revision, evaluate image counts, copy changes, and acceptance
rules only within the revised requirement sections. Existing images and
requirements outside that subset are protected baseline content and must not
be treated as conflicts.

{review_output_contract}

Original request: {state['raw_request']}
Confirmed scope: {json.dumps(_confirmed_fact_source(state).get('scope', {}), ensure_ascii=False)}
Final user-confirmed evidence packet: {json.dumps(_confirmation_packet(state), ensure_ascii=False)}
Artifact under review: {artifact}
{revision_contract}
"""


def _is_controller_deterministic_trace(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        trace = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return False
    return isinstance(trace, dict) and trace.get("pm_copilot_revision") == CONTROLLER_TRACE_REVISION


def _review_controller_trace(
    state: dict[str, Any], artifact: str, state_path: Path | None,
) -> tuple[bool, str]:
    """Review only trace structure locally; final output checks run later."""
    folder = _delivery_folder(state)
    findings = _trace_contract_findings(folder)
    passed = not findings
    result = {
        "provider": CONTROLLER_TRACE_PROVIDER,
        "model": CONTROLLER_TRACE_MODEL,
        "pm_copilot_revision": CONTROLLER_TRACE_REVISION,
        "status": "complete" if passed else "failed",
        "output": "controller validated deterministic run-log structure",
        "error": "" if passed else findings,
        "execution_mode": "deterministic_trace_validation",
        "attempt": 1,
    }
    _record_agent_call(state, result, phase="stage_quality_review", artifact=artifact)
    stage = _stage(state, artifact)
    stage["review_status"] = "passed" if passed else "failed"
    stage["reviewed_sha256"] = _artifact_digest(folder / artifact)
    stage["review_findings"] = [] if passed else [findings]
    stage["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    stage["scope_fingerprint"] = _confirmed_scope_fingerprint(state)
    stage["pm_copilot_version"] = _state_runtime_version(state)
    _checkpoint(state, state_path)
    if passed:
        return True, "controller trace validation passed"
    return False, "deterministic trace validation failed"


def _review_artifact(
    state: dict[str, Any], artifact: str, provider: str, timeout: int,
    worker: Callable[..., dict[str, Any]] = _delivery_worker, state_path: Path | None = None,
    model: str | None = None,
) -> tuple[bool, str]:
    real_folder = _delivery_folder(state)
    if artifact == "run-log.yaml" and _is_controller_deterministic_trace(real_folder / artifact):
        return _review_controller_trace(state, artifact, state_path)
    result: dict[str, Any] = {}
    review_text = ""
    with tempfile.TemporaryDirectory(prefix=f".{real_folder.name}.review-", dir=str(real_folder.parent)) as review_dir:
        review_folder = Path(review_dir) / real_folder.name
        real_snapshot = Path(review_dir) / ".controller-workspace-before"
        _snapshot_delivery_workspace(real_folder, real_snapshot)
        shutil.copytree(real_snapshot, review_folder)
        _discard_non_content_assets(review_folder)
        review_path = review_folder / ".stage-review.json"
        # A prior response can be valid JSON and still be unrelated to this
        # artifact version. Remove it before every independent review call.
        if review_path.exists() or review_path.is_symlink():
            if review_path.is_dir() and not review_path.is_symlink():
                shutil.rmtree(review_path)
            else:
                review_path.unlink()
        for attempt in range(1, MAX_ATTRIBUTABLE_AGENT_ATTEMPTS + 1):
            if review_path.exists() or review_path.is_symlink():
                if review_path.is_dir() and not review_path.is_symlink():
                    shutil.rmtree(review_path)
                else:
                    review_path.unlink()
            review_before_sha256 = _artifact_digest(review_path)
            review_before_mtime = review_path.stat().st_mtime_ns if review_path.is_file() else None
            review_state = {
                **state,
                "folder": str(review_folder),
                "delivery_workspace": str(review_folder),
            }
            attempt_snapshot = Path(review_dir) / f".controller-workspace-before-{attempt}"
            _snapshot_delivery_workspace(real_folder, attempt_snapshot)
            try:
                result = worker(
                    provider, _artifact_review_prompt(review_state, artifact, review_path),
                    review_folder, min(timeout, STAGE_REVIEW_TIMEOUT_MINUTES),
                    model, None, False, 8000,
                )
            except BaseException:
                _restore_delivery_workspace_snapshot(attempt_snapshot, real_folder)
                raise
            try:
                _restore_delivery_workspace_snapshot(attempt_snapshot, real_folder)
            except (OSError, ValueError) as error:
                result.update({
                    "status": "failed",
                    "error": f"controller could not restore the delivery workspace after stage review: {error}",
                    "failure_category": "delivery_workspace_restore_failed",
                })
            try:
                _assert_delivery_tree_has_no_symlinks(review_folder, label="stage review workspace")
            except ValueError as error:
                result.update({
                    "status": "failed",
                    "error": f"stage review workspace integrity check failed: {error}",
                    "failure_category": "review_workspace_integrity_failed",
                })
            review_after_sha256 = _artifact_digest(review_path)
            review_after_mtime = review_path.stat().st_mtime_ns if review_path.is_file() else None
            if result.get("status") == "complete" and (
                not review_path.is_file()
                or review_after_sha256 == review_before_sha256
                or review_after_mtime == review_before_mtime
            ):
                result.update({
                    "status": "failed",
                    "error": "Stage Quality Review Agent did not write a fresh review response in its isolated workspace",
                    "failure_category": "review_response_not_fresh",
                })
            result["attempt"] = attempt
            record = dict(result)
            if _is_in_place_prd_review(state, artifact):
                # The response remains ephemeral until its typed contract is
                # verified below, so invalid free-form repairs cannot leak to
                # a writer through durable controller state.
                record["output"] = "review response held for controller contract validation"
            attributable = _record_agent_call(state, record, phase="stage_quality_review", artifact=artifact)
            if (
                attributable
                or result.get("cleanup_blocked")
                or attempt >= MAX_ATTRIBUTABLE_AGENT_ATTEMPTS
                or not _is_retryable_agent_failure(result)
            ):
                break
        review_text = review_path.read_text(encoding="utf-8") if review_path.is_file() else ""
        if result.get("cleanup_blocked"):
            _quarantine_unconfirmed_workspace(
                state, Path(review_dir), artifact, "review", result,
            )
    result["phase"] = "stage_quality_review"
    result["artifact"] = artifact
    attributable = _agent_call_has_evidence(result)
    if not attributable:
        _stage(state, artifact)["review_status"] = "failed"
        state["last_error"] = "Stage Quality Review Agent call has no attributable provider/model evidence"
        _checkpoint(state, state_path)
        return False, "Stage Quality Review Agent call has no attributable provider/model evidence"
    if result.get("status") != "complete":
        _stage(state, artifact)["review_status"] = "failed"
        _checkpoint(state, state_path)
        return False, result.get("error", "Stage Quality Review Agent failed")
    try:
        review = _extract_json(review_text)
    except (ValueError, json.JSONDecodeError) as error:
        if _is_in_place_prd_review(state, artifact):
            return _reject_revision_review_contract(
                state, artifact, f"review response is not valid JSON: {error}", state_path,
            )
        _stage(state, artifact)["review_status"] = "failed"
        _checkpoint(state, state_path)
        return False, f"Stage Quality Review Agent returned invalid JSON: {error}"
    acceptance_evidence = review.get("acceptance_evidence", [])
    if not isinstance(acceptance_evidence, list):
        acceptance_evidence = [acceptance_evidence]
    acceptance_evidence = [str(item).strip() for item in acceptance_evidence if str(item).strip()]
    review_status = str(review.get("status", "")).strip().lower()
    typed_findings: list[dict[str, Any]] = []
    if _is_in_place_prd_review(state, artifact):
        typed_findings, contract_error = _revision_review_contract_error(state, review, review_status)
        if contract_error:
            return _reject_revision_review_contract(state, artifact, contract_error, state_path)
        findings = [
            "\n".join((
                f"[{finding['kind']}] {', '.join(finding['requirement_ids'])}",
                f"Selected evidence: {finding['evidence']}",
                f"Repair: {finding['repair']}",
            ))
            for finding in typed_findings
        ]
        state.pop("review_contract_rejection", None)
        state.pop("review_contract_correction", None)
    else:
        findings = _normalise_review_strings(review.get("blocking_findings", []))
    if review_status == "needs_revision" and not findings:
        _stage(state, artifact)["review_status"] = "failed"
        _checkpoint(state, state_path)
        return False, "Stage Quality Review Agent returned needs_revision without specific blocking_findings"
    if review_status == "pass" and not acceptance_evidence:
        if _is_in_place_prd_review(state, artifact):
            return _reject_revision_review_contract(
                state, artifact, "pass requires non-empty acceptance_evidence", state_path,
            )
        _stage(state, artifact)["review_status"] = "failed"
        _checkpoint(state, state_path)
        return False, "Stage Quality Review Agent returned pass without acceptance_evidence"
    passed = review_status == "pass" and not findings
    stage = _stage(state, artifact)
    stage["review_status"] = "passed" if passed else "needs_revision"
    stage["reviewed_sha256"] = _artifact_digest(real_folder / artifact)
    stage["review_findings"] = findings
    if _is_in_place_prd_review(state, artifact):
        stage["revision_findings"] = typed_findings
    stage["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    stage["scope_fingerprint"] = _confirmed_scope_fingerprint(state)
    stage["pm_copilot_version"] = _state_runtime_version(state)
    _checkpoint(state, state_path)
    return passed, "\n".join(findings) or str(review.get("summary", "stage review rejected artifact"))


def _trace_contract_findings(folder: Path) -> str:
    """Return trace-validator findings before an incomplete trace reaches review."""
    result = subprocess.run(
        [sys.executable, "scripts/validate_agent_trace.py", str(folder)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if result.returncode == 0:
        return ""
    return "\n".join(part for part in (result.stdout, result.stderr) if part).strip()


def _deliver_artifact_to_quality_gate(
    state: dict[str, Any], artifact: str, provider: str, timeout: int,
    worker: Callable[..., dict[str, Any]] = _delivery_worker, max_revisions: int = DEFAULT_MAX_REVISIONS,
    state_path: Path | None = None, model: str | None = None,
) -> bool:
    target = _delivery_folder(state) / artifact
    stage = _stage(state, artifact)
    if stage.get("review_status") == "passed" and stage.get("reviewed_sha256") == _artifact_digest(target):
        return True
    if stage.get("artifact_status") != "promoted" or not target.is_file():
        if not _run_artifact_agent(state, artifact, provider, timeout, worker, state_path=state_path, model=model):
            return False
    if artifact == "run-log.yaml":
        deterministic_trace = _is_controller_deterministic_trace(target)
        findings = _trace_contract_findings(_delivery_folder(state))
        if findings:
            if not deterministic_trace:
                if not _run_artifact_agent(
                    state, artifact, provider, timeout, worker, findings[-6000:], state_path, model,
                ):
                    state["last_error"] = findings
                    _checkpoint(state, state_path)
                    return False
            findings = _trace_contract_findings(_delivery_folder(state))
            if findings:
                state["last_error"] = findings
                _checkpoint(state, state_path)
                return False
    if _is_in_place_prd_review(state, artifact):
        # A correction prompt is valid for exactly one reviewer retry. Do not
        # let stale output from a previous delivery attempt steer this pass.
        for key in ("review_contract_rejection", "review_contract_correction"):
            value = state.get(key)
            if isinstance(value, Mapping) and value.get("artifact") == artifact:
                state.pop(key, None)
    reviewer_contract_retries = 0
    revision = 0
    while revision <= max_revisions:
        passed, findings = _review_artifact(state, artifact, provider, timeout, worker, state_path, model)
        if passed:
            return True
        rejection = state.get("review_contract_rejection")
        if (
            _is_in_place_prd_review(state, artifact)
            and isinstance(rejection, Mapping)
            and rejection.get("artifact") == artifact
        ):
            reason = str(rejection.get("reason") or "invalid reviewer contract")
            if reviewer_contract_retries >= 1:
                stage["review_status"] = "failed"
                state["revision_stop_reason"] = f"{artifact} stage review contract rejected twice"
                state["last_error"] = (
                    "Stage Quality Review Agent returned invalid revision feedback after one correction retry: "
                    f"{reason}"
                )
                _checkpoint(state, state_path)
                return False
            reviewer_contract_retries += 1
            state["review_contract_correction"] = {
                "artifact": artifact,
                "reason": reason,
                "attempt": reviewer_contract_retries,
            }
            state.pop("review_contract_rejection", None)
            _checkpoint(state, state_path)
            # An invalid reviewer response never reaches the PRD writer or
            # consumes the content-repair budget.
            continue
        if revision >= max_revisions:
            state["revision_stop_reason"] = f"{artifact} stage quality budget exhausted"
            state["last_error"] = findings
            _checkpoint(state, state_path)
            return False
        before = _artifact_digest(target)
        if not _run_artifact_agent(state, artifact, provider, timeout, worker, findings[-6000:], state_path, model):
            state["revision_stop_reason"] = f"{artifact} stage quality repair failed"
            state["last_error"] = findings
            _checkpoint(state, state_path)
            return False
        after = _artifact_digest(target)
        if before == after:
            _record_revision(state, artifact, before, after, "no_progress")
            state["revision_stop_reason"] = f"{artifact} stage quality repair made no artifact change"
            state["last_error"] = findings
            _checkpoint(state, state_path)
            return False
        _record_revision(state, artifact, before, after, "changed")
        state["revision_loops"] = state.get("revision_loops", 0) + 1
        _checkpoint(state, state_path)
        revision += 1
    return False


def _run_validation_command(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(command[1:]),
        "status": "passed" if result.returncode == 0 else "failed",
        "exit_code": result.returncode,
        "stdout": result.stdout[-3000:],
        "stderr": result.stderr[-2000:],
    }


def _render_prd_html_check(folder: Path) -> dict[str, Any]:
    return _run_validation_command([sys.executable, "scripts/render_prd_html.py", str(folder)])


def _prepare_final_revision_scope_attestation(
    state: dict[str, Any], folder: Path,
) -> list[dict[str, Any]]:
    """Render once, then attest the exact revision artifact set for its trace.

    This runs between the accepted PRD stage and controller-owned trace stage.
    It gives a malformed PRD a deterministic repair path before any trace or
    evidence can claim that the selected revision is promotable.
    """
    render_check = _render_prd_html_check(folder)
    checks = [render_check]
    if render_check["status"] != "passed":
        return checks
    report = _validate_staged_revision_scope(state, folder, include_rendered_html=True)
    failures = list(report.get("failures", [])) if isinstance(report, dict) else [
        "final in-place revision scope report is unavailable"
    ]
    _, attestation_problems = _final_revision_scope_attestation_problems(state, folder)
    failures.extend(problem for problem in attestation_problems if problem not in failures)
    checks.append({
        "command": "revision_scope.attest staged prd.md/prd.html/assets",
        "status": "passed" if not failures else "failed",
        "exit_code": 0 if not failures else 1,
        "stdout": "\n".join(report.get("checks", [])) if isinstance(report, dict) else "",
        "stderr": "\n".join(failures),
    })
    return checks


def _refresh_final_revision_derivatives(
    state: dict[str, Any], folder: Path, provider: str, timeout: int,
    worker: Callable[..., dict[str, Any]], state_path: Path | None, model: str | None,
) -> tuple[bool, list[dict[str, Any]], str]:
    """Rebuild every proof derived from repaired in-place PRD bytes.

    A PRD repair invalidates its rendered scope proof and the deterministic
    trace that embeds revision evidence.  Never send those stale derivatives
    into another validation pass: re-render and attest first, then regenerate
    and review the controller-owned trace.
    """
    checks = _prepare_final_revision_scope_attestation(state, folder)
    failed = [check for check in checks if check.get("status") != "passed"]
    if failed:
        reason = "\n\n".join(
            f"{check.get('command', 'final revision attestation')}:\n"
            f"{check.get('stdout', '')}\n{check.get('stderr', '')}"
            for check in failed
        )
        return False, checks, reason
    if not _run_artifact_agent(
        state, "run-log.yaml", provider, timeout, worker, state_path=state_path, model=model,
    ):
        return False, checks, str(state.get("last_error") or "could not regenerate deterministic run-log.yaml")
    passed, findings = _review_artifact(
        state, "run-log.yaml", provider, timeout, worker, state_path, model,
    )
    if not passed:
        return False, checks, findings
    return True, checks, ""


def _validate_delivery(
    folder: Path, staging: bool = False, *, include_render: bool = True, language: str = "zh",
) -> list[dict[str, Any]]:
    commands: list[list[str]] = []
    if include_render:
        commands.append([sys.executable, "scripts/render_prd_html.py", str(folder)])
    commands.extend([
        [sys.executable, "scripts/validate_outputs.py", str(folder), "--language", language] + (["--staging"] if staging else []),
        [sys.executable, "scripts/validate_agent_trace.py", str(folder)],
        [sys.executable, "scripts/run_delivery_checks.py", str(folder), "--language", language] + (["--staging"] if staging else []),
    ])
    return [_run_validation_command(command) for command in commands]


def _validate_staged_delivery(
    state: dict[str, Any], folder: Path, *, language: str | None = None,
) -> list[dict[str, Any]]:
    """Run staged checks without rewriting a trace-bound scope attestation."""
    checks = [_render_prd_html_check(folder)]
    try:
        _assert_delivery_tree_has_no_symlinks(folder, label="staged delivery workspace")
        _validate_input_asset_materialization(state, folder)
        checks.append({
            "command": "controller input-asset materialization validation",
            "status": "passed",
            "exit_code": 0,
            "stdout": "controller snapshots and published input assets match",
            "stderr": "",
        })
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as error:
        checks.append({
            "command": "controller input-asset materialization validation",
            "status": "failed",
            "exit_code": 1,
            "stdout": "",
            "stderr": str(error),
        })
    if _delivery_variant(state) == "in_place_revision":
        report, failures = _final_revision_scope_attestation_problems(state, folder)
        checks.append({
            "command": "revision_scope.verify staged artifact-set attestation",
            "status": "passed" if not failures else "failed",
            "exit_code": 0 if not failures else 1,
            "stdout": "\n".join(report.get("checks", [])) if isinstance(report, dict) else "",
            "stderr": "\n".join(failures),
        })
    effective_language = language or _trace_language(state, folder / "prd.md")
    checks.extend(_validate_delivery(
        folder, staging=True, include_render=False, language=effective_language,
    ))
    return checks


@contextmanager
def _bounded_file_lock(lock_path: Path, label: str, timeout_seconds: float = 30.0) -> Any:
    """Acquire a short-lived process lock without turning a collision into a hang."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as error:
                if error.errno not in {errno.EACCES, errno.EAGAIN}:
                    raise
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"{label} is already active; retry after it reaches a terminal state") from error
                time.sleep(0.05)
        yield
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


@contextmanager
def _delivery_promotion_lock(canonical: Path) -> Any:
    """Serialize the small CAS critical section shared by all delivery paths."""
    lock_path = canonical.parent / f".{canonical.name}.delivery-promotion.lock"
    with _bounded_file_lock(lock_path, "a delivery promotion"):
        yield


@contextmanager
def _derived_refresh_lock(canonical: Path, timeout_seconds: float = 30.0) -> Any:
    """Serialize full derivative refreshes while staging and verifying their inputs."""
    lock_path = canonical.parent / f".{canonical.name}.derived-refresh.lock"
    with _bounded_file_lock(lock_path, "a rendered-derivative refresh", timeout_seconds):
        yield


def _derived_refresh_journal_path(canonical: Path) -> Path:
    return canonical.parent / f".{canonical.name}.derived-refresh-transaction.json"


def _derived_refresh_journal_member(
    canonical: Path, raw_name: object, expected_prefix: str, label: str,
) -> Path:
    if not isinstance(raw_name, str) or not raw_name or Path(raw_name).name != raw_name:
        raise RuntimeError(f"derived refresh transaction has an unsafe {label}")
    if not raw_name.startswith(expected_prefix):
        raise RuntimeError(f"derived refresh transaction has an unexpected {label}")
    return canonical.parent / raw_name


def _recover_derived_refresh_transaction(canonical: Path) -> None:
    """Restore a pre-refresh tree after an interrupted directory replacement.

    POSIX directory replacement takes two renames.  The durable journal makes
    the interval recoverable: unless a refresh recorded its final commit, a
    later controller restores the retained canonical backup rather than
    guessing that a partially promoted candidate is valid.
    """
    journal_path = _derived_refresh_journal_path(canonical)
    if not journal_path.exists():
        return
    if journal_path.is_symlink() or not journal_path.is_file():
        raise RuntimeError("derived refresh transaction journal is not a regular file")
    journal = _read_json_mapping(journal_path, "derived refresh transaction journal")
    if journal.get("schema_version") != DERIVED_REFRESH_TRANSACTION_SCHEMA_VERSION:
        raise RuntimeError("derived refresh transaction journal uses an unsupported schema")
    if journal.get("canonical_name") != canonical.name:
        raise RuntimeError("derived refresh transaction journal targets a different PRD")
    phase = journal.get("phase")
    if phase not in {"prepared", "original_moved", "candidate_promoted", "committed"}:
        raise RuntimeError("derived refresh transaction journal has an unknown phase")
    backup = _derived_refresh_journal_member(
        canonical, journal.get("backup_name"), f".{canonical.name}.derived-refresh-backup-", "backup name",
    )
    publish_root = _derived_refresh_journal_member(
        canonical, journal.get("publish_root_name"), f".{canonical.name}.derived-refresh-publishing-", "publish root name",
    )

    if phase == "committed" and canonical.is_dir():
        _commit_delivery_promotion(backup)
    elif backup.exists():
        if canonical.exists():
            _rollback_delivery_promotion(canonical, backup)
        else:
            backup.replace(canonical)
    elif not canonical.exists():
        raise RuntimeError(
            "interrupted rendered-derivative refresh has neither canonical PRD nor recoverable backup"
        )
    if publish_root.exists():
        if publish_root.is_symlink() or not publish_root.is_dir():
            raise RuntimeError("derived refresh publish workspace is not a regular directory")
        shutil.rmtree(publish_root)
    journal_path.unlink(missing_ok=True)


def _refresh_tree_snapshot(folder: Path, *, protected_only: bool = False) -> dict[str, str]:
    """Digest one run tree for refresh CAS and non-derived-content protection."""
    _assert_delivery_tree_has_no_symlinks(folder, label="derived refresh tree")
    snapshot: dict[str, str] = {}
    for path in sorted(folder.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_dir():
            continue
        relative = path.relative_to(folder)
        relative_name = relative.as_posix()
        if relative.name == ".DS_Store":
            continue
        if not path.is_file():
            raise ValueError(f"derived refresh tree contains a non-regular file: {relative_name}")
        if protected_only and (
            relative_name in DERIVED_REFRESH_MUTABLE_FILES
            or relative.parts[0] == "tool-results"
        ):
            continue
        digest = _artifact_digest(path)
        if digest is None:
            raise ValueError(f"derived refresh tree file cannot be hashed: {relative_name}")
        snapshot[relative_name] = digest
    return snapshot


def _refresh_snapshot_digest(snapshot: Mapping[str, str]) -> str:
    return hashlib.sha256(
        json.dumps(dict(snapshot), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _read_json_mapping(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not readable JSON: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _completed_revision_refresh_problems(state: Mapping[str, Any], canonical: Path) -> list[str]:
    """Reject anything except a fully attested completed in-place revision."""
    problems: list[str] = []
    if state.get("status") != "complete" or state.get("termination") != "complete":
        problems.append("rendered derivative refresh requires a completed PRD run")
    if _delivery_variant(dict(state)) != "in_place_revision":
        problems.append("rendered derivative refresh is only available for completed in-place revisions")
    for name in ("interactive-run.json", "prd.md", "prd.html", "run-log.yaml", "revision-evidence.json"):
        if not (canonical / name).is_file():
            problems.append(f"completed in-place revision is missing {name}")
    if not (canonical / "assets").is_dir():
        problems.append("completed in-place revision is missing assets/")
    manifest = state.get("revision_scope_manifest")
    if not isinstance(manifest, Mapping) or manifest.get("schema_version") != 1:
        problems.append("completed in-place revision has no current controller scope manifest")

    trace_path = canonical / "run-log.yaml"
    if trace_path.is_file():
        try:
            trace = yaml.safe_load(trace_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            problems.append(f"completed run-log.yaml is unreadable: {error}")
            trace = None
        if not isinstance(trace, dict) or trace.get("pm_copilot_revision") != CONTROLLER_TRACE_REVISION:
            problems.append("rendered derivative refresh requires a controller-owned deterministic run-log.yaml")

    evidence_path = canonical / "revision-evidence.json"
    if evidence_path.is_file() and isinstance(manifest, Mapping):
        try:
            evidence = _read_json_mapping(evidence_path, "revision-evidence.json")
        except ValueError as error:
            problems.append(str(error))
        else:
            evidence_manifest = evidence.get("scope_manifest")
            if not isinstance(evidence_manifest, Mapping):
                problems.append("revision-evidence.json is missing the scope manifest")
            elif revision_scope_manifest_digest(evidence_manifest) != revision_scope_manifest_digest(manifest):
                problems.append("revision-evidence.json scope manifest does not match interactive state")
            evidence_validation = evidence.get("scope_validation")
            state_validation = state.get("revision_scope_validation")
            if not isinstance(evidence_validation, Mapping) or not isinstance(state_validation, Mapping):
                problems.append("revision evidence and interactive state must both retain final scope validation")
            else:
                for field in (
                    "status", "report_path", "manifest_sha256", "report_sha256",
                    "artifact_set_sha256", "attestation_schema_version",
                ):
                    if evidence_validation.get(field) != state_validation.get(field):
                        problems.append(
                            f"revision evidence scope_validation.{field} does not match interactive state"
                        )
    if not problems:
        _, attestation_problems = _final_revision_scope_attestation_problems(state, canonical)
        problems.extend(attestation_problems)
        problems.extend(validate_artifact_lineage(canonical / "run-log.yaml"))
    return list(dict.fromkeys(problems))


def _verified_retained_revision_baseline(state: Mapping[str, Any], canonical: Path) -> Path:
    """Return the retained pre-revision Markdown only after hash verification."""
    manifest = state.get("revision_scope_manifest")
    if not isinstance(manifest, Mapping):
        raise ValueError("completed in-place revision is missing its scope manifest")
    baseline_record = manifest.get("baseline")
    if not isinstance(baseline_record, Mapping):
        raise ValueError("completed in-place revision scope manifest is missing its baseline")
    expected_digest = baseline_record.get("prd_sha256")
    if not isinstance(expected_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_digest.lower()):
        raise ValueError("completed in-place revision baseline has no valid prd.md SHA-256")

    raw_workspace = state.get("delivery_workspace")
    if not isinstance(raw_workspace, str) or not raw_workspace.strip():
        raise ValueError("completed in-place revision has no retained delivery workspace baseline")
    expected_workspace = (
        canonical.parent / f".{canonical.name}.delivery-stage" / canonical.name
    ).resolve()
    workspace = Path(raw_workspace).resolve()
    if workspace != expected_workspace:
        raise ValueError("retained revision baseline is outside the controller-owned delivery workspace")
    _assert_delivery_tree_has_no_symlinks(workspace, label="retained revision delivery workspace")
    baseline = workspace / ".revision-baseline" / "prd.md"
    if baseline.is_symlink() or not baseline.is_file():
        raise ValueError("retained revision delivery workspace is missing .revision-baseline/prd.md")
    if _artifact_digest(baseline) != expected_digest:
        raise ValueError("retained revision baseline SHA-256 does not match the attested scope manifest")
    return baseline


def _reload_refresh_state(state: dict[str, Any], canonical: Path) -> None:
    """Bind a refresh to the state that exists after its exclusive lock begins."""
    state_path = canonical / "interactive-run.json"
    persisted = _read_json_mapping(state_path, "interactive-run.json")
    folder_value = persisted.get("folder")
    if not isinstance(folder_value, str) or Path(folder_value).resolve() != canonical:
        raise ValueError("interactive-run.json does not identify this canonical PRD folder")
    state.clear()
    state.update(persisted)


def _refresh_check_failure_reason(checks: Sequence[Mapping[str, Any]]) -> str:
    failures = [
        "{}:\n{}\n{}".format(
            check.get("command", "refresh validation"),
            check.get("stdout", ""),
            check.get("stderr", ""),
        ).strip()
        for check in checks
        if check.get("status") != "passed"
    ]
    return "\n\n".join(failures) or "derived refresh validation failed"


def _replace_derived_refresh_result_files(candidate: Path, workspace: Path) -> None:
    """Refresh referenced validator evidence without deleting unrelated provenance.

    A renderer-only refresh has no authority to discard controller-owned input
    evidence, including implemented-feature packet results that the trace
    validates indirectly.  The candidate starts as a copy of canonical output;
    replace only the reports generated again in this transaction.
    """
    retained: dict[Path, Path] = {
        relative: source
        for relative, source in _trace_result_files(workspace / "run-log.yaml")
    }
    for relative, source in _revision_evidence_result_files(workspace / "revision-evidence.json"):
        retained[relative] = source
    delivery_report = workspace / "tool-results" / "delivery-check-report.json"
    if not delivery_report.is_file():
        raise FileNotFoundError("derived refresh did not produce tool-results/delivery-check-report.json")
    retained[Path("tool-results/delivery-check-report.json")] = delivery_report
    for relative, source in sorted(retained.items(), key=lambda item: item[0].as_posix()):
        _atomic_copy(source, candidate / relative)


def _promote_derived_refresh_workspace(
    state: dict[str, Any], workspace: Path, source_snapshot: Mapping[str, str],
    protected_snapshot: Mapping[str, str], language: str,
    record_candidate_validation: Callable[[Path, list[dict[str, Any]]], None],
    record_canonical_validation: Callable[[list[dict[str, Any]], list[dict[str, Any]]], None],
) -> list[dict[str, Any]]:
    """Publish only verified rendered derivatives through a recoverable CAS transaction."""
    canonical = _canonical_folder(state)
    _assert_delivery_tree_has_no_symlinks(workspace, label="derived refresh workspace")
    if _refresh_tree_snapshot(canonical) != dict(source_snapshot):
        raise DerivedRefreshSourceDriftError(
            "canonical PRD changed while the rendered derivative refresh was staged"
        )

    publish_root = Path(tempfile.mkdtemp(prefix=f".{canonical.name}.derived-refresh-publishing-", dir=canonical.parent))
    candidate = publish_root / canonical.name
    backup = canonical.parent / f".{canonical.name}.derived-refresh-backup-{time.time_ns()}"
    moved_original = False
    journal_path = _derived_refresh_journal_path(canonical)
    journal_written = False
    try:
        shutil.copytree(canonical, candidate, ignore=shutil.ignore_patterns(".DS_Store"))
        for name in ("prd.html", "run-log.yaml", "revision-evidence.json"):
            source = workspace / name
            if not source.is_file():
                raise FileNotFoundError(f"derived refresh artifact is missing: {source}")
            _atomic_copy(source, candidate / name)
        _replace_derived_refresh_result_files(candidate, workspace)
        _write_json(candidate / "interactive-run.json", state)
        _assert_delivery_tree_has_no_symlinks(candidate, label="derived refresh promotion candidate")
        if _refresh_tree_snapshot(candidate, protected_only=True) != dict(protected_snapshot):
            raise RuntimeError("derived refresh changed protected PRD content outside rendered derivatives")

        candidate_checks = _validate_delivery(candidate, include_render=False, language=language)
        if not all(check.get("status") == "passed" for check in candidate_checks):
            raise RuntimeError(_refresh_check_failure_reason(candidate_checks))
        record_candidate_validation(candidate, candidate_checks)
        # Verify the candidate after the preliminary state evidence is written.
        # This is the exact complete tree that will be renamed into canonical.
        candidate_state_checks = _validate_delivery(candidate, include_render=False, language=language)
        if not all(check.get("status") == "passed" for check in candidate_state_checks):
            raise RuntimeError(_refresh_check_failure_reason(candidate_state_checks))
        if _refresh_tree_snapshot(candidate, protected_only=True) != dict(protected_snapshot):
            raise RuntimeError("candidate validation changed protected PRD content")

        with _delivery_promotion_lock(canonical):
            if _refresh_tree_snapshot(canonical) != dict(source_snapshot):
                raise DerivedRefreshSourceDriftError(
                    "canonical PRD changed while the rendered derivative refresh was staged"
                )
            _write_json(journal_path, {
                "schema_version": DERIVED_REFRESH_TRANSACTION_SCHEMA_VERSION,
                "canonical_name": canonical.name,
                "backup_name": backup.name,
                "publish_root_name": publish_root.name,
                "phase": "prepared",
            })
            journal_written = True
            canonical.replace(backup)
            moved_original = True
            _write_json(journal_path, {
                "schema_version": DERIVED_REFRESH_TRANSACTION_SCHEMA_VERSION,
                "canonical_name": canonical.name,
                "backup_name": backup.name,
                "publish_root_name": publish_root.name,
                "phase": "original_moved",
            })
            try:
                candidate.replace(canonical)
            except OSError:
                backup.replace(canonical)
                moved_original = False
                raise
            _write_json(journal_path, {
                "schema_version": DERIVED_REFRESH_TRANSACTION_SCHEMA_VERSION,
                "canonical_name": canonical.name,
                "backup_name": backup.name,
                "publish_root_name": publish_root.name,
                "phase": "candidate_promoted",
            })

            canonical_checks = _validate_delivery(canonical, include_render=False, language=language)
            if not all(check.get("status") == "passed" for check in canonical_checks):
                _rollback_delivery_promotion(canonical, backup)
                moved_original = False
                raise RuntimeError(_refresh_check_failure_reason(canonical_checks))
            # Candidate validation proves the staged bytes; this second pass
            # proves the exact bytes after the CAS directory swap. Persist
            # every pass while the old directory remains recoverable.
            record_canonical_validation(candidate_state_checks, canonical_checks)
            _write_json(journal_path, {
                "schema_version": DERIVED_REFRESH_TRANSACTION_SCHEMA_VERSION,
                "canonical_name": canonical.name,
                "backup_name": backup.name,
                "publish_root_name": publish_root.name,
                "phase": "committed",
            })
            _commit_delivery_promotion(backup)
            moved_original = False
            journal_path.unlink(missing_ok=True)
            journal_written = False
            return canonical_checks
    except BaseException:
        if moved_original and backup.exists():
            _rollback_delivery_promotion(canonical, backup)
            moved_original = False
        if journal_written and canonical.exists():
            journal_path.unlink(missing_ok=True)
        raise
    finally:
        if publish_root.exists():
            shutil.rmtree(publish_root, ignore_errors=True)


def _refresh_completed_revision_derivatives(state: dict[str, Any]) -> tuple[bool, str, list[dict[str, Any]]]:
    """Re-render a completed in-place PRD without reopening product scope or Agents."""
    canonical = _canonical_folder(state)
    checks: list[dict[str, Any]] = []
    try:
        with _derived_refresh_lock(canonical):
            _recover_derived_refresh_transaction(canonical)
            _reload_refresh_state(state, canonical)
            problems = _completed_revision_refresh_problems(state, canonical)
            if problems:
                return False, "; ".join(problems), checks
            baseline = _verified_retained_revision_baseline(state, canonical)
            language = _trace_language(state, canonical / "prd.md")
            checks.extend([
                _run_validation_command([
                    sys.executable, "scripts/validate_outputs.py", str(canonical), "--language", language,
                ]),
                _run_validation_command([
                    sys.executable, "scripts/validate_agent_trace.py", str(canonical),
                ]),
            ])
            if not all(check.get("status") == "passed" for check in checks):
                return False, _refresh_check_failure_reason(checks), checks

            source_snapshot = _refresh_tree_snapshot(canonical)
            protected_snapshot = _refresh_tree_snapshot(canonical, protected_only=True)
            source_report, source_problems = _final_revision_scope_attestation_problems(state, canonical)
            if source_problems or not isinstance(source_report, dict):
                return False, "; ".join(source_problems or ["current revision attestation is unreadable"]), checks
            source_artifact_set = source_report.get("artifact_set", {})
            original_delivery_workspace = state.get("delivery_workspace")
            refresh_state = json.loads(json.dumps(state, ensure_ascii=False))
            _freeze_delivery_runtime_identity(refresh_state)
            refresh_started_at = dt.datetime.now(dt.timezone.utc).isoformat()

            with tempfile.TemporaryDirectory(
                prefix=f".{canonical.name}.derived-refresh-stage-", dir=canonical.parent,
            ) as temporary:
                workspace = Path(temporary) / canonical.name
                shutil.copytree(canonical, workspace, ignore=shutil.ignore_patterns(".DS_Store"))
                if _refresh_tree_snapshot(workspace) != source_snapshot:
                    raise RuntimeError("derived refresh workspace does not match the completed canonical PRD")
                staged_baseline = workspace / ".revision-baseline" / "prd.md"
                _atomic_copy(baseline, staged_baseline)
                refresh_state["delivery_workspace"] = str(workspace)
                refresh_state["derived_artifact_refresh_context"] = {
                    "reason": "renderer implementation update",
                    "started_at": refresh_started_at,
                    "source_artifact_set": source_artifact_set,
                    "protected_content_sha256": _refresh_snapshot_digest(protected_snapshot),
                }

                attestation_checks = _prepare_final_revision_scope_attestation(refresh_state, workspace)
                checks.extend(attestation_checks)
                if not all(check.get("status") == "passed" for check in attestation_checks):
                    return False, _refresh_check_failure_reason(attestation_checks), checks
                if not _run_artifact_agent(
                    refresh_state, "run-log.yaml", CONTROLLER_TRACE_PROVIDER, 1,
                    state_path=None, model=None,
                ):
                    return False, str(refresh_state.get("last_error") or "could not materialize controller trace"), checks
                reviewed, findings = _review_artifact(
                    refresh_state, "run-log.yaml", CONTROLLER_TRACE_PROVIDER, 1,
                    state_path=None, model=None,
                )
                if not reviewed:
                    return False, findings, checks

                first_checks = _validate_staged_delivery(refresh_state, workspace, language=language)
                checks.extend(first_checks)
                if not all(check.get("status") == "passed" for check in first_checks):
                    return False, _refresh_check_failure_reason(first_checks), checks
                if not _finalize_deterministic_trace(
                    workspace, first_checks, _state_runtime_identity(refresh_state),
                ):
                    return False, "could not finalize the deterministic controller trace", checks
                final_checks = _validate_staged_delivery(refresh_state, workspace, language=language)
                checks.extend(final_checks)
                if not all(check.get("status") == "passed" for check in final_checks):
                    return False, _refresh_check_failure_reason(final_checks), checks

                refreshed_report, refreshed_problems = _final_revision_scope_attestation_problems(refresh_state, workspace)
                if refreshed_problems or not isinstance(refreshed_report, dict):
                    return False, "; ".join(refreshed_problems or ["refreshed revision attestation is unreadable"]), checks
                if _refresh_tree_snapshot(canonical) != source_snapshot:
                    raise DerivedRefreshSourceDriftError(
                        "canonical PRD changed while the rendered derivative refresh was staged"
                    )

                refresh_state["delivery_workspace"] = original_delivery_workspace
                refresh_state.pop("derived_artifact_refresh_context", None)
                refresh_state["status"] = "complete"
                refresh_state["termination"] = "complete"
                refresh_state["last_error"] = None
                refresh_state.pop("last_failure_category", None)
                refresh_state["validation"] = checks
                refresh_record = {
                    "mode": "deterministic_rendered_derivative_refresh",
                    "at": refresh_started_at,
                    "source_artifact_set": source_artifact_set,
                    "refreshed_artifact_set": refreshed_report.get("artifact_set", {}),
                    "protected_content_sha256": _refresh_snapshot_digest(protected_snapshot),
                    "runtime_identity": _state_runtime_identity(refresh_state),
                    "validation_commands": [],
                }
                refresh_state.setdefault("derived_artifact_refreshes", []).append(refresh_record)

                def record_candidate_validation(
                    candidate: Path, candidate_checks: list[dict[str, Any]],
                ) -> None:
                    checks.extend(candidate_checks)
                    refresh_state["validation"] = checks
                    refresh_record["validation_commands"] = [
                        {"command": check.get("command", ""), "status": check.get("status", "")}
                        for check in checks
                    ]
                    _write_json(candidate / "interactive-run.json", refresh_state)

                def record_canonical_validation(
                    candidate_state_checks: list[dict[str, Any]], canonical_checks: list[dict[str, Any]],
                ) -> None:
                    checks.extend(candidate_state_checks)
                    checks.extend(canonical_checks)
                    refresh_state["validation"] = checks
                    refresh_record["validation_commands"] = [
                        {"command": check.get("command", ""), "status": check.get("status", "")}
                        for check in checks
                    ]
                    # The candidate carries the preliminary state so the
                    # directory move is atomic.  Replace it with the final,
                    # post-promotion evidence while the old directory remains
                    # available for rollback.
                    _write_json(canonical / "interactive-run.json", refresh_state)

                _promote_derived_refresh_workspace(
                    refresh_state, workspace, source_snapshot, protected_snapshot, language,
                    record_candidate_validation, record_canonical_validation,
                )
            state.clear()
            state.update(refresh_state)
            return True, "", checks
    except (OSError, ValueError, RuntimeError) as error:
        return False, str(error), checks


def _validation_failure_targets_trace(checks: list[dict[str, Any]]) -> bool:
    """Tell a trace-contract failure from a PRD-content failure.

    ``validate_outputs`` and ``run_delivery_checks`` validate a folder rather
    than one filename.  Their trace-specific findings must regenerate the
    controller-owned trace locally, never be handed to the PRD writer.
    """
    # Scope and render failures can cause validate_agent_trace to emit a
    # derived run-log complaint. They still belong to the PRD/HTML artifact,
    # never to deterministic trace regeneration.
    prd_markers = (
        "revision_scope.",
        "revision scope",
        "rendered html images",
        "render_prd_html.py",
        "prd-detail-media",
    )
    trace_markers = (
        "run-log.yaml",
        "run log",
        "agent trace",
        "validate_agent_trace",
        "quality decision",
        "quality_decision",
        "validation_results",
        "specialist_evidence",
        "pm_arbitration",
    )
    for check in checks:
        if check.get("status") == "passed":
            continue
        detail = " ".join(str(check.get(key, "")) for key in ("command", "stdout", "stderr")).lower()
        if any(marker in detail for marker in prd_markers):
            return False
        if any(marker in detail for marker in trace_markers):
            return True
    return False


def _confirmed_delivery_impl(
    state: dict[str, Any], provider: str, timeout: int,
    worker: Callable[..., dict[str, Any]] = _delivery_worker, max_revisions: int = DEFAULT_MAX_REVISIONS,
    state_path: Path | None = None, model: str | None = None,
    interactive_timeout: int = DEFAULT_INTERACTIVE_TIMEOUT_MINUTES,
) -> None:
    confirmation = state.get("user_confirmation")
    if not isinstance(confirmation, dict) or confirmation.get("confirmed") is not True:
        state["status"] = "awaiting_confirmation"
        state["termination"] = "human_checkpoint"
        state["last_error"] = "Explicit user confirmation is required before delivery"
        return
    # A resumed state may describe a controller from an older installation.
    # Freeze the current process before cache snapshot/restore so old reviewed
    # artifacts cannot be relabeled as this attempt's build.
    _freeze_delivery_runtime_identity(state)
    _migrate_stale_internal_scope_clarification(state)
    restart_requested = bool(state.pop("restart_delivery", False))
    _migrate_legacy_confirmed_revision_scope(state)
    _clear_inactive_revision_scope(state)
    asset_problem = _input_asset_problem(state)
    if asset_problem:
        _set_needs_input(
            state,
            "已确认的图片或视频附件无法从控制器快照验证。请重新通过 --asset 附加原始文件；"
            "重新确认后才会继续生成，系统不会用现有图替代或猜测附件内容。",
            reason=asset_problem,
            field="input_assets",
        )
        _checkpoint(state, state_path)
        return
    # A legacy run may have been migrated from raw input paths above. Persist
    # that state before any staging or Agent work so a later interruption never
    # leaves the newly written snapshot orphaned from its manifest descriptor.
    _checkpoint(state, state_path)
    _materialize_revision_scope_manifest(state)
    _record_confirmed_extraction_selection(state)
    input_problem = _delivery_input_problem(state, require_selection=True)
    if input_problem:
        if _delivery_variant(state) == "compose_to_new":
            field = "extraction_source" if _extraction_source_configuration_problem(state) else "extraction_scope"
            question = (
                "请指定要提取的旧 PRD 文件，并为每份来源明确要保留的需求 ID、章节标题或范围。"
                if field == "extraction_source"
                else "请明确每份旧 PRD 中要提取的需求 ID、章节标题或范围；同名需求请用 source-1: 5.1 或文件名.md: 5.1 区分。"
            )
        elif _task_mode(state) == "implemented_feature_prd":
            field = "implementation_evidence"
            question = "请提供已检查的分支、diff、变更文件、行为和验证证据；缺少这些证据不能把已实现功能伪装成普通 PRD。"
        else:
            field = "revision_selector"
            question = "请指定本次原地修改涉及的现有 PRD 需求 ID；范围不明确时不会改写整份文档。"
        _set_needs_input(state, question, reason=input_problem, field=field)
        _checkpoint(state, state_path)
        return
    if restart_requested:
        guard = _retry_failure_guard_decision(state, provider, model)
        if guard.get("blocked"):
            state["status"] = "failed"
            state["termination"] = "needs_maintenance"
            state["last_error"] = (
                "identical delivery failure was already retried without any input, runtime, model, "
                "baseline, or controller-code change; maintenance is required before another Agent call"
            )
            state["recovery"] = {
                "status": "needs_maintenance",
                "failed_stage": guard["context"]["failed_artifact"],
                "failure_category": guard["context"]["failure_category"],
                "failure_fingerprint": guard["fingerprint"],
                "no_progress_attempts": guard["no_progress_attempts"],
                "no_progress_limit": guard["no_progress_limit"],
                "retry_condition": "change controller/runtime/provider/model/input/baseline before retrying",
            }
            _checkpoint(state, state_path)
            return
        _restart_delivery_attempt(state)
    deadline = time.monotonic() + max(1, interactive_timeout) * 60

    def ensure_budget(stage: str) -> bool:
        if time.monotonic() < deadline:
            return True
        state["status"] = "recovery_required"
        state["termination"] = "retry_required"
        state["last_error"] = f"interactive delivery budget exhausted before {stage}"
        state["last_failure_category"] = "interactive_budget_exhausted"
        state["recovery"] = {
            "status": "retry_required", "failed_stage": stage,
            "delivery_workspace": str(_delivery_folder(state)),
            "retry_entry": "--confirm",
        }
        _checkpoint(state, state_path)
        return False
    try:
        folder = _prepare_delivery_workspace(state)
    except (FileNotFoundError, FileExistsError, ValueError) as error:
        reason = str(error)
        if reason == _revision_source_drift_problem(state):
            _set_needs_input(
                state,
                "当前 PRD 在本次修订开始后已被修改。请重新发起原地修订，并基于当前版本确认修改范围。",
                reason=reason,
                field="revision_source_drift",
            )
        else:
            state["status"] = "failed"
            state["termination"] = "failed"
            state["last_error"] = reason
        _checkpoint(state, state_path)
        return
    state["status"] = "delivery"
    state["termination"] = "running"
    state["controller_pid"] = os.getpid()
    state["controller_started_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    state["last_error"] = None
    state.pop("last_failure_category", None)
    # All stage records, reuse decisions, and trace provenance use the
    # process-start snapshot frozen before staging. A disk update while this
    # controller is running cannot make already-loaded code look like a later
    # release.
    state["active_delivery_attempt"] = {
        "started_at": state["controller_started_at"],
        "scope_fingerprint": _confirmed_scope_fingerprint(state),
        "runtime_identity": _state_runtime_identity(state),
    }
    # Specialists answer only independent evidence questions in isolated
    # workspaces. Test workers deliberately skip real model dispatch.
    if worker is _delivery_worker:
        state["specialist_evidence"] = dispatch_specialists(
            state, folder, provider, min(timeout, max(1, int((deadline - time.monotonic() + 59) // 60))), model,
        )
    else:
        state.pop("specialist_evidence", None)
    _checkpoint(state, state_path)

    for artifact in ("confirmed-requirements.md", "prd.md"):
        if not ensure_budget(artifact):
            return
        remaining_minutes = max(1, int((deadline - time.monotonic() + 59) // 60))
        if not _deliver_artifact_to_quality_gate(state, artifact, provider, min(timeout, remaining_minutes), worker, max_revisions, state_path, model):
            if state.get("status") == "needs_input":
                _checkpoint(state, state_path)
                return
            if state.get("status") == "recovery_required":
                _checkpoint(state, state_path)
                return
            reason = str(state.get("last_error") or f"delivery Agent failed to produce {artifact}")
            state["last_error"] = reason
            if "provider/model" in reason:
                _mark_attribution_recovery(state, artifact, provider, model)
            else:
                state["status"] = "failed"
                state["termination"] = "failed"
            _checkpoint(state, state_path)
            return

    # A controlled placeholder is a declaration of a required frontend state,
    # not a finished figure. Attempt an isolated reconstruction before the
    # controller trace and HTML are materialized.
    try:
        _materialize_reconstructed_figures(state, folder)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        state["frontend_figure_evidence"] = [{
            "provenance": "required_placeholder",
            "replacement_status": "pending_manual_completion",
            "replacement_instruction": "补充真实页面截图并重新执行交付。",
            "capture_error": str(error),
        }]

    if _delivery_variant(state) == "in_place_revision":
        scope_revision = 0
        while True:
            if not ensure_budget("final revision scope attestation"):
                return
            scope_checks = _prepare_final_revision_scope_attestation(state, folder)
            state["validation"] = scope_checks
            _checkpoint(state, state_path)
            if all(check["status"] == "passed" for check in scope_checks):
                break
            scope_errors = "\n\n".join(
                f"{check['command']}:\n{check.get('stdout', '')}\n{check.get('stderr', '')}"
                for check in scope_checks if check["status"] != "passed"
            )
            if scope_revision >= max_revisions:
                state["revision_stop_reason"] = "final revision scope attestation budget exhausted"
                state["last_error"] = scope_errors
                state["last_failure_category"] = "revision_scope_attestation_failed"
                state["status"] = "failed"
                state["termination"] = "failed"
                _checkpoint(state, state_path)
                return
            before = _artifact_digest(folder / "prd.md")
            remaining_minutes = max(1, int((deadline - time.monotonic() + 59) // 60))
            if not _run_artifact_agent(
                state, "prd.md", provider, min(timeout, remaining_minutes), worker,
                scope_errors[-6000:], state_path, model,
            ):
                state["revision_stop_reason"] = "final revision scope repair Agent failed"
                _checkpoint(state, state_path)
                return
            after = _artifact_digest(folder / "prd.md")
            if before == after:
                _record_revision(state, "prd.md", before, after, "no_progress")
                state["revision_stop_reason"] = "final revision scope repair made no prd.md change"
                state["last_error"] = scope_errors
                state["status"] = "failed"
                state["termination"] = "failed"
                _checkpoint(state, state_path)
                return
            _record_revision(state, "prd.md", before, after, "changed")
            if not ensure_budget("review for final revision scope repair"):
                return
            remaining_minutes = max(1, int((deadline - time.monotonic() + 59) // 60))
            passed, findings = _review_artifact(
                state, "prd.md", provider, min(timeout, remaining_minutes), worker, state_path, model,
            )
            if not passed:
                state["revision_stop_reason"] = "final revision scope repair was rejected by stage quality review"
                state["last_error"] = findings
                state["status"] = "failed"
                state["termination"] = "failed"
                _checkpoint(state, state_path)
                return
            scope_revision += 1
            state["revision_loops"] = state.get("revision_loops", 0) + 1
            _checkpoint(state, state_path)

    for artifact in ("run-log.yaml",):
        if not ensure_budget(artifact):
            return
        remaining_minutes = max(1, int((deadline - time.monotonic() + 59) // 60))
        if not _deliver_artifact_to_quality_gate(
            state, artifact, provider, min(timeout, remaining_minutes), worker, max_revisions, state_path, model,
        ):
            if state.get("status") == "needs_input":
                _checkpoint(state, state_path)
                return
            if state.get("status") == "recovery_required":
                _checkpoint(state, state_path)
                return
            reason = str(state.get("last_error") or f"delivery Agent failed to produce {artifact}")
            state["last_error"] = reason
            if "provider/model" in reason:
                _mark_attribution_recovery(state, artifact, provider, model)
            else:
                state["status"] = "failed"
                state["termination"] = "failed"
            _checkpoint(state, state_path)
            return
    all_checks: list[dict[str, Any]] = []
    final_checks: list[dict[str, Any]] = []
    for revision in range(max_revisions + 1):
        if not ensure_budget("final validation"):
            return
        checks = _validate_staged_delivery(state, folder)
        all_checks.extend(checks)
        final_checks = checks
        state["validation"] = all_checks
        _checkpoint(state, state_path)
        trace_path = folder / "run-log.yaml"
        deterministic_trace = trace_path.is_file() and "pm_copilot_revision: controller-deterministic-trace" in trace_path.read_text(encoding="utf-8")
        if deterministic_trace:
            # The initial deterministic trace is intentionally pending. Close
            # that state from the controller's actual first-pass results, then
            # rerun validators so pending is never left in a final artifact.
            _finalize_deterministic_trace(folder, checks, _state_runtime_identity(state))
            checks = _validate_staged_delivery(state, folder)
            all_checks.extend(checks)
            final_checks = checks
            state["validation"] = all_checks
            _checkpoint(state, state_path)
        if all(check["status"] == "passed" for check in checks):
            break
        if revision >= max_revisions:
            state["revision_stop_reason"] = "validation budget exhausted"
            break
        artifact = "run-log.yaml" if _validation_failure_targets_trace(checks) else "prd.md"
        errors = "\n\n".join(f"{check['command']}:\n{check.get('stdout', '')}\n{check.get('stderr', '')}" for check in checks if check["status"] != "passed")
        target = folder / artifact
        before = _artifact_digest(target)
        if not ensure_budget(f"validation repair for {artifact}"):
            return
        remaining_minutes = max(1, int((deadline - time.monotonic() + 59) // 60))
        if not _run_artifact_agent(state, artifact, provider, min(timeout, remaining_minutes), worker, errors[-6000:], state_path, model):
            state["revision_stop_reason"] = "repair Agent failed"
            _checkpoint(state, state_path)
            break
        after = _artifact_digest(target)
        if before == after:
            _record_revision(state, artifact, before, after, "no_progress")
            state["revision_stop_reason"] = f"validation repair made no {artifact} change"
            _checkpoint(state, state_path)
            break
        _record_revision(state, artifact, before, after, "changed")
        # A validator repair creates a new artifact version. The review that
        # accepted the prior bytes is no longer evidence for this version.
        if not ensure_budget(f"review for {artifact}"):
            return
        remaining_minutes = max(1, int((deadline - time.monotonic() + 59) // 60))
        passed, findings = _review_artifact(state, artifact, provider, min(timeout, remaining_minutes), worker, state_path, model)
        if not passed:
            state["revision_stop_reason"] = f"validation repair for {artifact} was rejected by stage quality review"
            state["last_error"] = findings
            _checkpoint(state, state_path)
            break
        state["revision_loops"] = revision + 1
        if artifact == "prd.md" and _delivery_variant(state) == "in_place_revision":
            if not ensure_budget("final revision proof refresh"):
                return
            remaining_minutes = max(1, int((deadline - time.monotonic() + 59) // 60))
            refreshed, refresh_checks, refresh_error = _refresh_final_revision_derivatives(
                state, folder, provider, min(timeout, remaining_minutes), worker, state_path, model,
            )
            all_checks.extend(refresh_checks)
            state["validation"] = all_checks
            if not refreshed:
                state["revision_stop_reason"] = "final revision proof refresh failed after prd.md repair"
                state["last_error"] = refresh_error
                _checkpoint(state, state_path)
                # A bad rendered proof still has a valid PRD repair path on
                # the next bounded validation pass. A deterministic trace
                # materialization/review failure does not.
                if any(check.get("status") != "passed" for check in refresh_checks):
                    continue
                break
        _checkpoint(state, state_path)
    state["validation"] = all_checks
    if final_checks and all(check["status"] == "passed" for check in final_checks):
        evidence_ok, evidence_reason = _required_production_evidence(state)
        if evidence_ok:
            promotion_backup: Path | None = None
            try:
                promotion_backup = _promote_delivery_workspace(state)
                canonical_checks = _validate_delivery(_canonical_folder(state))
                state["validation"].extend(canonical_checks)
                if not all(check["status"] == "passed" for check in canonical_checks):
                    _rollback_delivery_promotion(_canonical_folder(state), promotion_backup)
                    promotion_backup = None
                    state.pop("delivery_promoted_at", None)
                    raise RuntimeError("canonical delivery validation failed after promotion")
                _commit_delivery_promotion(promotion_backup)
                promotion_backup = None
                state["status"] = "complete"
                state["termination"] = "complete"
                state["last_error"] = None
                state["artifacts"] = ["discussion.md", "confirmed-requirements.md", "prd.md", "prd.html", "run-log.yaml", "assets/"]
            except RevisionSourceDriftError as error:
                _set_needs_input(
                    state,
                    "当前 PRD 在暂存完成后又被修改。请重新发起原地修订，并基于当前版本重新确认修改范围。",
                    reason=str(error),
                    field="revision_source_drift",
                )
            except (OSError, RuntimeError) as error:
                if promotion_backup is not None:
                    _rollback_delivery_promotion(_canonical_folder(state), promotion_backup)
                    state.pop("delivery_promoted_at", None)
                state["status"] = "failed"
                state["termination"] = "failed"
                state["last_error"] = str(error)
        else:
            state["last_error"] = evidence_reason
            if "not attributable" in evidence_reason or "missing required Agent evidence" in evidence_reason:
                _mark_attribution_recovery(state, "production_evidence", provider, model)
            else:
                state["status"] = "blocked"
                state["termination"] = "blocked"
    else:
        state["status"] = "failed"
        state["termination"] = "failed"
        state["last_failure_category"] = "final_validation_failed"
    if state["status"] not in {"complete", "recovery_required"}:
        state["artifacts"] = [item for item in state.get("artifacts", []) if item not in {"prd.md", "prd.html", "run-log.yaml", "assets/"}]
    _checkpoint(state, state_path)


def _confirmed_delivery(
    state: dict[str, Any], provider: str, timeout: int,
    worker: Callable[..., dict[str, Any]] = _delivery_worker, max_revisions: int = DEFAULT_MAX_REVISIONS,
    state_path: Path | None = None, model: str | None = None,
    interactive_timeout: int = DEFAULT_INTERACTIVE_TIMEOUT_MINUTES,
) -> None:
    """Run delivery behind one terminal-state boundary."""
    previous_handlers = {
        signal.SIGTERM: signal.getsignal(signal.SIGTERM),
        signal.SIGINT: signal.getsignal(signal.SIGINT),
    }

    def _request_terminal_stop(signum: int, _frame: object) -> None:
        raise KeyboardInterrupt(f"controller received {signal.Signals(signum).name}")

    signal.signal(signal.SIGTERM, _request_terminal_stop)
    signal.signal(signal.SIGINT, _request_terminal_stop)
    try:
        _confirmed_delivery_impl(state, provider, timeout, worker, max_revisions, state_path, model, interactive_timeout)
    except BaseException as error:
        if state.get("status") != "complete":
            state["status"] = "failed"
            state["termination"] = "failed"
            state["last_error"] = f"controller terminated during delivery: {type(error).__name__}: {error}".strip()
            state["artifacts"] = [item for item in state.get("artifacts", []) if item in {"discussion.md", "confirmed-requirements.md"}]
        _checkpoint(state, state_path)
        raise
    finally:
        signal.signal(signal.SIGTERM, previous_handlers[signal.SIGTERM])
        signal.signal(signal.SIGINT, previous_handlers[signal.SIGINT])
        if state.get("status") in {"confirmed", "delivery"} or state.get("termination") == "running":
            if state.get("status") != "complete":
                state["status"] = "failed"
                state["termination"] = "failed"
                state["last_error"] = state.get("last_error") or "controller exited before delivery reached a terminal state"
        if state.get("status") in {"failed", "recovery_required"}:
            _record_delivery_failure(state, provider, model)
        else:
            state.pop("active_delivery_attempt", None)
        _checkpoint(state, state_path)


def _build_request_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", help="initial user request")
    parser.add_argument("--request-file")
    parser.add_argument("--run-folder", type=Path)
    parser.add_argument("--new-requirement", action="store_true", help="create one explicitly new independent requirement")
    parser.add_argument("--revise", action="store_true", help="revise the canonical PRD in --run-folder")
    parser.add_argument(
        "--append-implemented-feature", action="store_true",
        help="append newly implemented behavior to the completed PRD in --run-folder",
    )
    parser.add_argument(
        "--extract-from", type=Path, action="append", default=[],
        help="source Markdown/text PRD for a new extraction delivery; repeat for multiple sources",
    )
    parser.add_argument(
        "--revision-requirement-id", action="append", default=[],
        help="existing requirement ID to modify in an in-place revision; repeat for multiple IDs",
    )
    parser.add_argument(
        "--implemented-evidence", type=Path,
        help="JSON file containing the verified implemented-feature evidence packet",
    )
    parser.add_argument("--answers", help="the user's answer for the current needs_input state")
    parser.add_argument("--confirm", action="store_true", help="explicitly confirm the clarified scope")
    parser.add_argument("--asset", action="append", default=[], help="user-provided screenshot or video to copy into canonical assets/")
    parser.add_argument(
        "--provider", choices=("auto", "codex"), default="auto",
        help="local Codex runtime; auto selects the configured local Codex route",
    )
    parser.add_argument("--model", help="explicitly select a model reported by the chosen runtime")
    parser.add_argument("--timeout-minutes", type=int, default=DEFAULT_EXECUTION_TIMEOUT_MINUTES)
    parser.add_argument("--interactive-timeout-minutes", type=int, default=DEFAULT_INTERACTIVE_TIMEOUT_MINUTES,
                        help="aggregate budget for the confirmed delivery workflow")
    parser.add_argument("--max-revisions", type=int, default=DEFAULT_MAX_REVISIONS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--refresh-rendered-derivatives",
        action="store_true",
        help="re-render and re-attest only deterministic derived artifacts for a completed in-place revision",
    )
    return parser


def _resolve_request_plan(
    args: argparse.Namespace, parser: argparse.ArgumentParser, *,
    entrypoint: Literal["interactive", "natural"],
) -> PrdRequestPlan:
    """Normalize shared entry arguments before any run folder is touched.

    Both the natural-language facade and the interactive resume surface use
    this one validation path. The facade differs only by requiring PRD-shaped
    request text when it receives new user text and by defaulting an initial
    request to a new canonical folder.
    """
    if args.timeout_minutes < 1:
        parser.error("--timeout-minutes must be at least 1")
    if args.interactive_timeout_minutes < 1:
        parser.error("--interactive-timeout-minutes must be at least 1")
    if args.max_revisions < 0:
        parser.error("--max-revisions cannot be negative")
    if args.refresh_rendered_derivatives:
        incompatible: list[str] = []
        if args.new_requirement:
            incompatible.append("--new-requirement")
        if args.revise:
            incompatible.append("--revise")
        if args.extract_from:
            incompatible.append("--extract-from")
        if args.implemented_evidence:
            incompatible.append("--implemented-evidence")
        if args.revision_requirement_id:
            incompatible.append("--revision-requirement-id")
        if args.answers:
            incompatible.append("--answers")
        if args.confirm:
            incompatible.append("--confirm")
        if args.asset:
            incompatible.append("--asset")
        if args.dry_run:
            incompatible.append("--dry-run")
        if args.model:
            incompatible.append("--model")
        if args.request and args.request.strip():
            incompatible.append("--request")
        if args.request_file:
            incompatible.append("--request-file")
        if not args.run_folder:
            parser.error("--refresh-rendered-derivatives requires --run-folder")
        if incompatible:
            parser.error(
                "--refresh-rendered-derivatives cannot be combined with " + ", ".join(incompatible)
            )
    if args.request_file:
        raw_request = Path(args.request_file).expanduser().read_text(encoding="utf-8").strip()
    else:
        raw_request = (args.request or "").strip()
    if entrypoint == "natural":
        if raw_request and not is_prd_request(raw_request):
            parser.error("request is not classified as a PRD request")
        # The natural facade starts a new canonical requirement by default.
        # A supplied folder is a resume target; it must not be silently
        # converted into an in-place revision because extraction/evidence
        # pauses resume through that same folder.
        if raw_request and not args.run_folder:
            args.new_requirement = True
        resume_input_supplied = bool(
            args.extract_from
            or args.implemented_evidence
            or args.revision_requirement_id
            or args.answers
            or args.confirm
            or args.asset
            or args.append_implemented_feature
            or args.refresh_rendered_derivatives
        )
        if args.run_folder and not args.revise and raw_request and not resume_input_supplied:
            parser.error(
                "--run-folder identifies an existing canonical PRD; add --revise for an in-place update"
            )
    if sum(bool(value) for value in (args.new_requirement, args.revise, args.append_implemented_feature)) > 1:
        parser.error("--new-requirement, --revise, and --append-implemented-feature are mutually exclusive")
    if args.extract_from and args.revise:
        parser.error("--extract-from creates a new PRD and cannot be combined with --revise")
    if args.extract_from and args.append_implemented_feature:
        parser.error("--extract-from cannot be combined with --append-implemented-feature")
    if args.implemented_evidence and args.revise:
        parser.error("--implemented-evidence creates an implemented-feature PRD and cannot be combined with --revise")
    if args.extract_from and args.implemented_evidence:
        parser.error("--extract-from and --implemented-evidence select different PRD delivery modes")
    if args.revision_requirement_id and args.new_requirement:
        parser.error("--revision-requirement-id is only valid for an existing in-place revision")
    if args.revision_requirement_id and args.append_implemented_feature:
        parser.error("--revision-requirement-id cannot be combined with append-only implemented-feature delivery")
    if args.revision_requirement_id and (args.extract_from or args.implemented_evidence):
        parser.error("--revision-requirement-id cannot be combined with a new extraction or implemented-feature PRD")
    if args.revision_requirement_id and not args.run_folder:
        parser.error("--revision-requirement-id requires --run-folder")
    if args.new_requirement and args.run_folder:
        parser.error("--new-requirement creates its own canonical folder; do not pass --run-folder")
    if args.revise and not args.run_folder:
        parser.error("--revise requires --run-folder for the canonical PRD")
    if args.append_implemented_feature and not args.run_folder:
        parser.error("--append-implemented-feature requires --run-folder for the current canonical PRD")
    folder = args.run_folder
    if folder is None and raw_request and args.new_requirement:
        try:
            folder = new_requirement_folder(raw_request, resolved_output_root(Path.cwd()))
        except FileExistsError as error:
            parser.error(str(error))
    if folder is None:
        parser.error("provide --run-folder for an existing canonical PRD, or use --new-requirement for a new independent requirement")
    folder = folder.resolve()
    delivery_variant = (
        "in_place_revision"
        if args.revise or args.append_implemented_feature
        else "compose_to_new"
        if args.extract_from or _request_looks_like_extraction(raw_request)
        else "new"
    )
    task_mode = (
        "implemented_feature_prd"
        if args.append_implemented_feature
        else "prd_revision"
        if delivery_variant == "in_place_revision"
        else "prd_composition"
        if delivery_variant == "compose_to_new"
        else "implemented_feature_prd"
        if args.implemented_evidence or _request_looks_like_implemented_feature(raw_request)
        else "new_prd"
    )
    return PrdRequestPlan(
        args=args,
        raw_request=raw_request,
        folder=folder,
        task_mode=task_mode,
        delivery_variant=delivery_variant,
        entrypoint=entrypoint,
    )


def _execute_request_plan(plan: PrdRequestPlan, parser: argparse.ArgumentParser) -> int:
    """Execute a normalized request plan using the existing persisted-state controller."""
    args = plan.args
    raw_request = plan.raw_request
    folder = plan.folder
    # A hard stop during a renderer-only refresh can occur between the two
    # directory renames. Recover its journal before applying the ordinary
    # existence gate, so a later normal controller cannot mistake a missing
    # canonical folder for a request to create a new run.
    if not args.new_requirement and _derived_refresh_journal_path(folder).exists():
        try:
            with _derived_refresh_lock(folder, timeout_seconds=0):
                _recover_derived_refresh_transaction(folder)
        except (OSError, RuntimeError, ValueError) as error:
            parser.error(str(error))
    if args.new_requirement and folder.exists():
        parser.error(f"canonical PRD folder already exists: {folder}")
    if not args.new_requirement and not folder.exists():
        parser.error(f"canonical PRD folder not found: {folder}; only --new-requirement may create a PRD folder")
    if args.revise and not folder.is_dir():
        parser.error(f"canonical PRD folder not found: {folder}")
    folder.mkdir(parents=True, exist_ok=True)
    state_path = folder / "interactive-run.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else create_state(
        raw_request,
        folder,
        task_mode=plan.task_mode,
        delivery_variant=plan.delivery_variant,
    )
    if state.get("mode") != "interactive":
        parser.error("run folder is not an interactive production run")
    if args.append_implemented_feature:
        try:
            state = begin_implemented_feature_append(state, raw_request)
        except ValueError as error:
            parser.error(str(error))
    if (
        _task_mode(state) == "implemented_feature_prd"
        and not args.implemented_evidence
        and not isinstance(state.get("implemented_feature_evidence"), dict)
    ):
        try:
            workspace = resolve_project_workspace(Path.cwd().resolve(), ensure=True)
            register_automatic_implemented_feature_evidence(state, Path(workspace["project_root"]))
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            parser.error(f"could not collect host implementation evidence: {error}")
    if _normalise_persisted_prd_mode(state):
        _write_json(state_path, state)
    if args.refresh_rendered_derivatives:
        if state.get("status") != "complete" or state.get("termination") != "complete":
            print(json.dumps({
                "status": "failed",
                "run_folder": str(folder),
                "refresh": {
                    "status": "rejected",
                    "error": "rendered derivative refresh requires an already completed PRD run",
                },
                "validation": [],
            }, ensure_ascii=False, indent=2))
            return 1
        refreshed, error, checks = _refresh_completed_revision_derivatives(state)
        print(json.dumps({
            "status": "complete" if refreshed else "failed",
            "run_folder": str(folder),
            "refresh": {
                "status": "complete" if refreshed else "failed",
                "error": error,
            },
            "validation": checks,
        }, ensure_ascii=False, indent=2))
        # Successful promotion already atomically wrote interactive-run.json
        # with the canonical post-promotion validation evidence.
        return 0 if refreshed else 1
    if _recover_interrupted_delivery(state, folder):
        _write_json(state_path, state)
    if _migrate_stale_internal_scope_clarification(state):
        _write_json(state_path, state)
    delivery_needs_input_field = _confirmed_delivery_needs_input_field(state)
    cli_delivery_input_provided = bool(
        args.extract_from or args.implemented_evidence or args.revision_requirement_id or args.asset
    )
    if args.revise:
        required_input = state.get("required_input")
        can_rebase_after_drift = (
            state.get("status") == "needs_input"
            and isinstance(required_input, dict)
            and required_input.get("field") == "revision_source_drift"
        )
        if state.get("status") not in {"complete", "failed"} and not can_rebase_after_drift:
            parser.error("canonical PRD is already active; resume it without --revise")
        try:
            state = begin_in_place_revision(state, raw_request, args.revision_requirement_id)
            apply_revision_requirement_ids(state, args.revision_requirement_id)
        except ValueError as error:
            parser.error(str(error))
    elif args.revision_requirement_id:
        if delivery_needs_input_field != "revision_selector":
            parser.error("--revision-requirement-id may only resume a matching revision-selector needs_input state")
        if _delivery_variant(state) != "in_place_revision":
            parser.error("--revision-requirement-id can only resume an in-place revision")
        try:
            apply_revision_requirement_ids(state, args.revision_requirement_id)
        except ValueError as error:
            parser.error(str(error))
    if args.extract_from:
        if (
            not args.new_requirement
            and delivery_needs_input_field not in {"extraction_source", "extraction_scope"}
        ):
            parser.error("--extract-from may only resume a matching extraction needs_input state")
        if not args.new_requirement and _delivery_variant(state) != "compose_to_new":
            parser.error("--extract-from may only start or resume an extraction PRD run")
        try:
            for source in args.extract_from:
                register_extraction_source(state, source)
        except (FileNotFoundError, ValueError) as error:
            parser.error(str(error))
    if args.implemented_evidence:
        if not args.new_requirement and not args.append_implemented_feature and delivery_needs_input_field != "implementation_evidence":
            parser.error("--implemented-evidence may only resume a matching implementation-evidence needs_input state")
        if not args.new_requirement and _task_mode(state) != "implemented_feature_prd":
            parser.error("--implemented-evidence may only start or resume an implemented-feature PRD run")
        try:
            register_implemented_feature_evidence(state, args.implemented_evidence)
        except (FileNotFoundError, ValueError) as error:
            parser.error(str(error))
    if args.asset:
        try:
            register_input_assets(state, [Path(value).expanduser().resolve() for value in args.asset])
        except (FileNotFoundError, FileExistsError, ValueError) as error:
            parser.error(str(error))
    if cli_delivery_input_provided:
        _resume_confirmed_delivery_after_cli_input(state, delivery_needs_input_field)
        _write_json(state_path, state)
    if args.answers and _submit_confirmed_delivery_answer(state, args.answers):
        _write_json(state_path, state)
        if state["status"] == "awaiting_confirmation":
            print("已记录交付所需输入；请使用 --confirm 重新确认后进入 PRD 生成。")
        else:
            print(json.dumps({"status": "needs_input", "questions": _needs_input_questions(state), "run_folder": str(folder)}, ensure_ascii=False, indent=2))
        return 3
    if args.dry_run:
        state["status"] = "planned"
        _write_json(state_path, state)
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0
    if state["status"] in {"new", "needs_input"}:
        if state["status"] == "needs_input" and not args.answers:
            print(json.dumps({"status": "needs_input", "questions": _needs_input_questions(state)}, ensure_ascii=False, indent=2))
            return 3
        state = run_intake(state, args.provider, args.timeout_minutes, answers=args.answers, model=args.model)
        if state["status"] == "awaiting_confirmation":
            write_discussion(folder, state)
            state["artifacts"] = ["discussion.md"]
            print("需求已澄清，请检查 discussion.md；确认无误后使用 --confirm 进入 PRD 生成。")
        elif state["status"] == "needs_input":
            print(json.dumps({"status": "needs_input", "questions": _needs_input_questions(state), "run_folder": str(folder)}, ensure_ascii=False, indent=2))
        _write_json(state_path, state)
        return 3 if state["status"] == "needs_input" else 0
    if state["status"] in {"awaiting_confirmation", "recovery_required", "confirmed", "delivery", "failed"}:
        if not args.confirm:
            if state["status"] == "recovery_required":
                print(json.dumps({"status": "recovery_required", "last_error": state.get("last_error"), "recovery": state.get("recovery"), "run_folder": str(folder)}, ensure_ascii=False, indent=2))
            elif state["status"] in {"confirmed", "delivery", "failed"}:
                print("交付已中断但确认已持久化；请使用 --confirm 恢复未完成阶段。")
            else:
                print("仍在等待用户明确确认；未生成 PRD。请使用 --confirm。")
            return 3
        if state["status"] == "delivery" and state.get("termination") == "running" and _controller_pid_alive(state):
            print(json.dumps({
                "status": "delivery",
                "termination": "running",
                "controller_pid": state.get("controller_pid"),
                "message": "delivery is already running; refusing a second controller",
                "run_folder": str(folder),
            }, ensure_ascii=False, indent=2))
            return 2
        prior_status = state["status"]
        state["user_confirmation"] = {
            "confirmed": True, "at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source": "explicit --confirm" if prior_status == "awaiting_confirmation" else "explicit --confirm resume",
        }
        # Freeze the complete clarified turn at the human confirmation gate.
        # Downstream artifact/review Agents must not reconstruct scope from a
        # later, abbreviated turn summary.
        packet = state.get("confirmed_fact_packet")
        if not isinstance(packet, dict) or not packet:
            confirmed_turn = state["turns"][-1] if state.get("turns") else {}
            state["confirmed_fact_packet"] = json.loads(json.dumps(confirmed_turn, ensure_ascii=False))
            state["confirmed_fact_packet"]["confirmed_at"] = state["user_confirmation"]["at"]
        state["resume_from_status"] = prior_status
        state["restart_delivery"] = prior_status in {"recovery_required", "failed"}
        state["status"] = "confirmed"
        state["termination"] = "running"
        _write_json(state_path, state)
        _confirmed_delivery(state, args.provider, args.timeout_minutes, max_revisions=args.max_revisions, state_path=state_path, model=args.model, interactive_timeout=args.interactive_timeout_minutes)
        print(json.dumps({"status": state["status"], "run_folder": str(folder), "artifacts": state.get("artifacts", []), "validation": state.get("validation", []), "recovery": state.get("recovery")}, ensure_ascii=False, indent=2))
        return 0 if state["status"] == "complete" else 1
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def _run_request_entry(
    argv: Sequence[str] | None = None, *,
    entrypoint: Literal["interactive", "natural"],
) -> int:
    request_argv = tuple(sys.argv[1:] if argv is None else argv)
    # A renderer-only refresh intentionally does not load Agents or new
    # controller behavior, so retain its existing no-sync exception. Every
    # other public entry synchronizes before argument parsing: an older copied
    # runtime must not reject a flag added by the newer source it is about to
    # load.
    if "--refresh-rendered-derivatives" not in request_argv:
        _ensure_runtime_current(request_argv, entrypoint=entrypoint)
    parser = _build_request_parser()
    args = parser.parse_args(request_argv)
    plan = _resolve_request_plan(args, parser, entrypoint=entrypoint)
    return _execute_request_plan(plan, parser)


def run_prd_request_entry(argv: Sequence[str] | None = None) -> int:
    """Run the natural-language PRD facade without rewriting process arguments."""
    return _run_request_entry(argv, entrypoint="natural")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the resumable interactive controller entry point."""
    return _run_request_entry(argv, entrypoint="interactive")


if __name__ == "__main__":
    raise SystemExit(main())
