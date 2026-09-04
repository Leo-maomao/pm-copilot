#!/usr/bin/env python3
"""Run the production, user-driven PM Copilot clarification gate.

This entry point deliberately does not use ``evals/scenario-confirmations.json``.
It persists a resumable conversation, asks the local Agent for only the next
branch-changing questions, and refuses downstream generation until the user
has explicitly confirmed the clarified scope.
"""

from __future__ import annotations

import argparse
import datetime as dt
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
from pathlib import Path
from typing import Any, Callable, Sequence

import yaml

from agent_runtime import execute
from delivery_failure_guard import (
    build_delivery_failure_fingerprint,
    decide_delivery_failure_attempt,
    failure_attempt_record,
)
from ensure_runtime_current import ensure_current
from project_workspace import resolve as resolve_project_workspace
from runtime_limits import (
    DEFAULT_EXECUTION_TIMEOUT_MINUTES, DEFAULT_INTERACTIVE_IDENTICAL_FAILURE_LIMIT,
    DEFAULT_INTERACTIVE_MAX_REVISIONS, DEFAULT_INTERACTIVE_TIMEOUT_MINUTES,
)
from revision_scope import (
    asset_digests as _revision_asset_digests,
    build_revision_scope_manifest,
    validate_rendered_html_scope,
    validate_revision_scope,
)
from validate_agent_trace import (
    validate_artifact_lineage,
    validate_implemented_feature_evidence_packet,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAX_REVISIONS = DEFAULT_INTERACTIVE_MAX_REVISIONS
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
TRACE_TEMPLATE = ROOT / "templates" / "agent-run-log-template.yaml"
CLARIFICATION_COVERAGE_AREAS = (
    "goal", "users", "scope", "success_evidence", "constraints_and_risk",
)
DELIVERY_VARIANTS = {"new", "in_place_revision", "extract_to_new"}
IMPLEMENTED_EVIDENCE_PACKET_PATH = Path("source-material") / "implemented-feature-evidence.json"

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
NUMERIC_REQUIREMENT_RANGE_RE = re.compile(
    r"(?<![\d.])(\d+)\.(\d+)\s*(?:-|~|–|—|至|到|to|through|until)\s*(\d+)\.(\d+)(?![\d.])",
    re.IGNORECASE,
)
SOURCE_REQUIREMENT_ID_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:\d+(?:\.\d+)+|[A-Za-z][A-Za-z0-9_]*-\d+)(?![A-Za-z0-9_.-])"
)


class RevisionSourceDriftError(RuntimeError):
    """A confirmed in-place revision can no longer safely replace its source."""


def _ensure_runtime_current() -> None:
    """Synchronize a copied global runtime before it can run an old controller.

    Plugin activation already performs this check, but direct invocation of the
    global controller bypasses the plugin. Source checkouts have no install
    metadata and deliberately skip the check.
    """
    if not (ROOT / "install-state.json").is_file():
        return
    result = ensure_current(ROOT, Path.home() / ".agents" / "skills", require_current=True)
    status = str(result.get("status", ""))
    if status == "up_to_date":
        return
    if status == "synced":
        os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]])
        return
    reason = str(result.get("reason") or result.get("action_required") or "runtime synchronization failed")
    raise RuntimeError(f"PM Copilot global runtime is not current: {reason}")


def _artifact_digest(path: Path) -> str | None:
    """Return a content digest so a repair loop cannot mistake no-op work for progress."""
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _request_looks_like_extraction(raw_request: str) -> bool:
    """Recognize an extraction request without mistaking an edit for a new PRD."""
    text = unicodedata.normalize("NFKC", raw_request or "").casefold()
    if not EXTRACTION_DOCUMENT_RE.search(text) or not EXTRACTION_NEW_TARGET_RE.search(text):
        return False
    has_source = bool(EXTRACTION_SOURCE_CONTEXT_RE.search(text))
    has_extraction_action = bool(EXTRACTION_ACTION_RE.search(text))
    has_construction_action = bool(EXTRACTION_CONSTRUCTION_RE.search(text))
    return has_source and (has_extraction_action or has_construction_action)


def _delivery_variant(state: dict[str, Any]) -> str:
    """Return a persisted delivery shape, preserving compatibility with old runs."""
    variant = str(state.get("delivery_variant", "")).strip()
    if variant in DELIVERY_VARIANTS:
        return variant
    return "in_place_revision" if state.get("revision_history") else "new"


def _task_mode(state: dict[str, Any]) -> str:
    """Keep ordinary PRD delivery as the only backwards-compatible default."""
    value = str(state.get("task_mode", "")).strip()
    return value or "prd_delivery"


def _context_source_mode(state: dict[str, Any]) -> str:
    source = state.get("context_source")
    if isinstance(source, dict):
        value = str(source.get("mode", "")).strip()
        if value in {"brief-only", "document-backed", "repo-backed"}:
            return value
    if _delivery_variant(state) == "extract_to_new":
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


def _extraction_snapshot_path(state: dict[str, Any]) -> Path | None:
    descriptor = state.get("extraction_source")
    if not isinstance(descriptor, dict):
        return None
    relative = str(descriptor.get("snapshot_path", "")).strip()
    if not relative:
        return None
    root = _canonical_folder(state)
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _extraction_selection(state: dict[str, Any]) -> list[str]:
    descriptor = state.get("extraction_source")
    if isinstance(descriptor, dict):
        selected = _trace_values(descriptor.get("selected_scope"))
        if selected:
            return selected
    packet = state.get("confirmed_fact_packet")
    if not isinstance(packet, dict):
        turns = state.get("turns")
        packet = turns[-1] if isinstance(turns, list) and turns and isinstance(turns[-1], dict) else {}
    scope = packet.get("scope") if isinstance(packet, dict) else {}
    return _trace_values(scope.get("in_scope") if isinstance(scope, dict) else [])


def _normalise_source_selector(value: str) -> str:
    """Compare user selectors to source text without punctuation or case noise."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^\w\u3400-\u9fff]+", "", normalized)


def _source_requirement_ids(source_text: str) -> list[str]:
    """Read IDs from source PRD headings and requirement-list rows only."""
    candidates: list[str] = []
    for line in source_text.splitlines():
        if not re.match(r"\s*(?:#{1,6}\s+|\|)", line):
            continue
        candidates.extend(SOURCE_REQUIREMENT_ID_RE.findall(line))
    return list(dict.fromkeys(candidates))


def _source_headings(source_text: str) -> list[tuple[str, str]]:
    """Return stable heading labels, both with and without a leading ID."""
    headings: list[tuple[str, str]] = []
    for raw_heading in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*$", source_text):
        heading = raw_heading.strip()
        body = re.sub(
            r"^(?:(?:需求|requirement)\s*)?(?:\d+(?:\.\d+)+|[A-Za-z][A-Za-z0-9_-]*-\d+)[.、:：\-\s]*",
            "",
            heading,
            flags=re.IGNORECASE,
        ).strip()
        for candidate in (heading, body):
            normalized = _normalise_source_selector(candidate)
            if normalized:
                headings.append((normalized, heading))
    return headings


def _source_text_spans(source_text: str) -> list[str]:
    """Collect source prose fragments that may be a uniquely cited scope."""
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


def _is_substantive_free_text(selector: str) -> bool:
    """Avoid treating a generic one-word fragment as a safe source selector."""
    cjk_count = len(re.findall(r"[\u3400-\u9fff]", selector))
    latin_words = re.findall(r"[a-z0-9]+", selector, flags=re.IGNORECASE)
    return cjk_count >= 3 or len("".join(latin_words)) >= 8 or len(latin_words) >= 2


def _resolve_extraction_selection(
    source_text: str, selected_scope: Sequence[str],
) -> tuple[list[dict[str, object]], str | None]:
    """Resolve every extraction selector to one unambiguous source location.

    A nonempty free-form scope is not enough to create a new canonical PRD:
    each selected item must anchor to a requirement ID, a unique heading, or a
    unique source phrase. Numeric ranges are accepted only when every ID in the
    stated range exists in the immutable snapshot.
    """
    source_ids = set(_source_requirement_ids(source_text))
    headings = _source_headings(source_text)
    text_spans = _source_text_spans(source_text)
    resolutions: list[dict[str, object]] = []

    for raw_selector in selected_scope:
        selector = str(raw_selector).strip()
        normalized = _normalise_source_selector(selector)
        if not normalized:
            return [], "提取范围包含空选择；请提供需求 ID、完整章节标题或可唯一匹配的原文范围。"

        ranges = list(NUMERIC_REQUIREMENT_RANGE_RE.finditer(selector))
        if ranges:
            for match in ranges:
                start_major, start_minor, end_major, end_minor = map(int, match.groups())
                if start_major != end_major or start_minor > end_minor:
                    return [], f"提取范围“{selector}”不是可解析的同级需求 ID 范围。"
                expected = [f"{start_major}.{minor}" for minor in range(start_minor, end_minor + 1)]
                missing = [item for item in expected if item not in source_ids]
                if missing:
                    return [], (
                        f"提取范围“{selector}”未完整匹配旧 PRD 快照中的需求 ID；"
                        f"缺少 {', '.join(missing)}。"
                    )
                resolutions.append({"selector": selector, "kind": "requirement_id_range", "matches": expected})
                continue
            continue

        selected_ids = list(dict.fromkeys(SOURCE_REQUIREMENT_ID_RE.findall(selector)))
        if selected_ids:
            unknown = [item for item in selected_ids if item not in source_ids]
            if unknown:
                return [], (
                    f"提取范围“{selector}”引用的需求 ID 不在旧 PRD 快照中：{', '.join(unknown)}。"
                )
            resolutions.append({"selector": selector, "kind": "requirement_id", "matches": selected_ids})
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
            return [], f"提取范围“{selector}”匹配多个旧 PRD 章节；请提供完整章节标题或需求 ID。"

        if _is_substantive_free_text(selector):
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
                return [], f"提取范围“{selector}”匹配多个旧 PRD 文本位置；请改用需求 ID 或章节标题。"

        return [], (
            f"提取范围“{selector}”无法在旧 PRD 快照中唯一定位；"
            "请提供存在的需求 ID、完整章节标题或可唯一匹配的原文范围。"
        )
    return resolutions, None


def _extraction_selection_problem(state: dict[str, Any]) -> str | None:
    """Return a stable input stop when the requested source subset is unclear."""
    snapshot = _extraction_snapshot_path(state)
    if snapshot is None or not snapshot.is_file():
        return "未提供可验证的旧 PRD 来源。请指定要提取的源文档。"
    selected = _extraction_selection(state)
    if not selected:
        return "未明确要从旧 PRD 提取哪些内容；请提供需求 ID、章节标题或可核验的范围。"
    _, problem = _resolve_extraction_selection(
        snapshot.read_text(encoding="utf-8"), selected,
    )
    return problem


def register_extraction_source(state: dict[str, Any], source: Path) -> None:
    """Snapshot an explicitly identified source PRD before it can influence delivery.

    The snapshot is the immutable document-backed context for this run. The
    source's original path stays in controller state for drift detection; the
    human-readable trace cites only the local snapshot and its content hash.
    """
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Extraction source PRD not found: {source}")
    if source.suffix.lower() not in {".md", ".markdown", ".mdown", ".txt"}:
        raise ValueError("Extraction source must be a Markdown or text PRD")
    canonical = _canonical_folder(state)
    snapshot = canonical / "source-material" / "source-prd.md"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    _atomic_copy(source, snapshot)
    digest = _artifact_digest(snapshot)
    if not digest:
        raise ValueError("Extraction source PRD is empty")
    state["delivery_variant"] = "extract_to_new"
    state["context_source"] = {
        "mode": "document-backed",
        "files_loaded": ["source-material/source-prd.md"],
    }
    state["extraction_source"] = {
        "source_path": str(source),
        "display_name": source.name,
        "snapshot_path": "source-material/source-prd.md",
        "sha256": digest,
        # A replacement snapshot needs a fresh confirmation. Retaining a prior
        # selector could silently apply an old source boundary to new bytes.
        "selected_scope": [],
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
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
    state["delivery_variant"] = "new"
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
    """Allow only controller-copied user assets to be new during a revision."""
    assets: dict[str, str] = {}
    for raw_source in state.get("input_assets", []):
        source = Path(str(raw_source)).expanduser()
        digest = _artifact_digest(source)
        if digest:
            assets[f"assets/{source.name}"] = digest
    return assets


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
    if _delivery_variant(state) == "extract_to_new":
        descriptor = state.get("extraction_source")
        if not isinstance(descriptor, dict):
            return (
                "extraction_source",
                "请指定要提取的旧 PRD 文件并明确要保留的需求 ID、章节标题或范围。",
            )
        return (
            "extraction_scope",
            "请明确旧 PRD 中要提取的需求 ID、章节标题或范围；确认后才会创建新的独立 PRD。",
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
        and field in {"extraction_source", "extraction_scope", "implementation_evidence", "revision_selector"}
    ):
        return field
    return None


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
    if _delivery_variant(state) != "extract_to_new":
        return None
    descriptor = state.get("extraction_source")
    snapshot = _extraction_snapshot_path(state)
    if not isinstance(descriptor, dict) or snapshot is None or not snapshot.is_file():
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
    if _delivery_variant(state) == "in_place_revision" and not _trace_values(state.get("revision_requirement_ids")):
        return "未明确原地修改的 PRD 需求 ID；请指定一个或多个现有需求 ID，或明确确认整份 PRD 都可重写。"
    return _extraction_source_problem(state, require_selection=require_selection) or _implemented_evidence_problem(state)


def _record_confirmed_extraction_selection(state: dict[str, Any]) -> None:
    """Freeze the source selection alongside the user's delivery confirmation."""
    if _delivery_variant(state) != "extract_to_new":
        return
    descriptor = state.get("extraction_source")
    if not isinstance(descriptor, dict):
        return
    selected = _extraction_selection(state)
    if not selected:
        return
    snapshot = _extraction_snapshot_path(state)
    if snapshot is None or not snapshot.is_file():
        return
    resolutions, problem = _resolve_extraction_selection(
        snapshot.read_text(encoding="utf-8"), selected,
    )
    if problem:
        # Keep an unresolved selection in the current clarification packet, not
        # in immutable source state. A later user answer can then replace it.
        descriptor.pop("selected_scope", None)
        descriptor.pop("selection_resolution", None)
        return
    descriptor["selected_scope"] = selected
    descriptor["selection_resolution"] = resolutions
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

    A Seawork launch without a trustworthy Agent ID may still have been
    accepted by the daemon. Moving its private stage aside preserves that
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


def _canonical_folder(state: dict[str, Any]) -> Path:
    return Path(str(state["folder"])).resolve()


def _is_retryable_agent_failure(result: dict[str, Any]) -> bool:
    detail = " ".join(str(result.get(key, "")) for key in ("status", "error", "output")).lower()
    return (
        "stream disconnected" in detail
        or "stream_disconnected" in detail
        or result.get("failure_category") == "agent_no_output"
        or result.get("failure_category") == "seawork_agent_error"
        or result.get("failure_category") in {"agent_no_progress", "agent_timeout", "seawork_launch_error"}
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


def _normalise_trace_runtime_evidence(run_log: Path) -> int:
    """Keep controller-owned runtime provenance and figure hashes tied to promoted bytes."""
    try:
        trace = yaml.safe_load(run_log.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        # Keep an invalid Agent-written trace available to the trace validator;
        # normalisation must not hide the original parsing failure.
        return 0
    if not isinstance(trace, dict):
        return 0

    trace["pm_copilot_version"] = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
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

    implemented = trace.get("implemented_feature_prd")
    if isinstance(implemented, dict):
        coverage = implemented.get("screenshots_and_placeholders")
        if isinstance(coverage, list):
            for item in coverage:
                if not isinstance(item, dict) or item.get("coverage_decision") != "real_figure":
                    continue
                refresh_asset(item)
                additional_assets = item.get("additional_assets")
                if isinstance(additional_assets, list):
                    for asset in additional_assets:
                        refresh_asset(asset)

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
    text = prd_path.read_text(encoding="utf-8")
    ids = re.findall(r"(?m)^\|\s*(\d+\.\d+)\s*\|", text)
    ids.extend(re.findall(r"(?m)^###\s+(\d+\.\d+)(?:\s|$)", text))
    return list(dict.fromkeys(ids))


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
    extraction = state.get("extraction_source") if variant == "extract_to_new" else None
    if variant == "extract_to_new":
        snapshot = _extraction_snapshot_path(state)
        if not isinstance(extraction, dict) or snapshot is None:
            raise ValueError("extraction trace requires an immutable source PRD snapshot")
        source_sha256 = str(extraction.get("sha256", "")).strip()
        if not source_sha256 or _artifact_digest(snapshot) != source_sha256:
            raise ValueError("extraction trace source PRD snapshot hash is not current")
        selected_scope = _extraction_selection(state)
        selection_problem = _extraction_selection_problem(state)
        if selection_problem:
            raise ValueError(selection_problem)
        source_scope_resolution, resolution_problem = _resolve_extraction_selection(
            snapshot.read_text(encoding="utf-8"), selected_scope,
        )
        if resolution_problem:
            raise ValueError(resolution_problem)
        return {
            "mode": "extraction_run",
            "target_prd_path": "",
            "target_html_path": "",
            "revision_evidence_path": "",
            "revised_requirement_ids": [],
            "deleted_requirement_ids": [],
            "source_snapshot_path": str(extraction["snapshot_path"]),
            "source_prd_display_name": str(extraction.get("display_name", "")),
            "source_prd_sha256": source_sha256,
            "selected_source_scope": selected_scope,
            "source_scope_resolution": source_scope_resolution,
            "historical_artifacts": [{
                "path": str(extraction["snapshot_path"]),
                "role": "user_provided_input",
                "excluded_from_current_facts": False,
            }],
            "output_folder_reset": True,
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
        "historical_artifacts": (
            [{"path": "prd.md", "role": "comparison_only", "excluded_from_current_facts": True}]
            if revision else []
        ),
        "output_folder_reset": not revision,
    }


def _materialize_revision_evidence(state: dict[str, Any], target: Path) -> None:
    """Persist the before-state proof for any in-place update before promotion."""
    if _delivery_variant(state) != "in_place_revision":
        return
    history = state.get("revision_history") or []
    if not history:
        return
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
    """Create a controller-owned trace from current staged facts.

    The run log is execution provenance, not a creative deliverable.  Keeping
    it controller-owned removes an entire model/stream dependency while still
    requiring the same staging hashes, trace contract, and final validators.
    """
    try:
        trace = yaml.safe_load(TRACE_TEMPLATE.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"could not load the controller trace template: {error}") from error
    if not isinstance(trace, dict):
        raise ValueError("controller trace template must contain a YAML mapping")

    problem = _delivery_input_problem(state, require_selection=True)
    if problem:
        raise ValueError(problem)
    prd_path = target.parent / "prd.md"
    latest = _confirmed_fact_source(state) if state.get("turns") or state.get("confirmed_fact_packet") else {}
    scope = latest.get("scope", {}) if isinstance(latest, dict) else {}
    if not isinstance(scope, dict):
        scope = {}
    language = _trace_language(state, prd_path)
    lineage = _trace_lineage(state, prd_path)
    revision = lineage["mode"] == "in_place_revision"
    extraction = lineage["mode"] == "extraction_run"
    task_mode = _task_mode(state)
    context_mode = _context_source_mode(state)
    context_descriptor = state.get("context_source") if isinstance(state.get("context_source"), dict) else {}
    raw_request = str(state.get("raw_request", "")).strip()
    goal = str(scope.get("goal", "")).strip() or raw_request or "Produce the confirmed PRD delivery"
    in_scope = _trace_values(scope.get("in_scope"))
    out_of_scope = _trace_values(scope.get("out_of_scope"))
    assumptions = _trace_values(latest.get("assumptions") if isinstance(latest, dict) else [])
    risks = _trace_values(latest.get("risks") if isinstance(latest, dict) else [])
    assets = sorted(
        item.relative_to(target.parent).as_posix()
        for item in (target.parent / "assets").glob("*")
        if item.is_file()
    ) if (target.parent / "assets").is_dir() else []
    active_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    request_kind = (
        "in-place revision" if revision else "extraction into a new PRD" if extraction else "new PRD delivery"
    )
    facts = [
        {"fact": "The PRD scope was explicitly confirmed before delivery.", "source": "interactive confirmation", "confidence": "high"},
        {"fact": "The controller generated this trace from the staged delivery workspace.", "source": "controller state", "confidence": "high"},
    ]
    if in_scope:
        facts.append({"fact": "Confirmed in-scope items: " + "; ".join(in_scope), "source": "interactive confirmation", "confidence": "high"})
    if extraction:
        facts.append({
            "fact": "The new PRD is limited to the user-confirmed selection from the immutable source snapshot.",
            "source": lineage["source_snapshot_path"], "confidence": "high",
        })
    if task_mode == "implemented_feature_prd":
        supplied_evidence = state.get("implemented_feature_evidence")
        evidence_source = state.get("implemented_feature_evidence_source")
        packet = _implemented_evidence_packet_path(state)
        if not isinstance(supplied_evidence, dict) or not isinstance(evidence_source, dict) or packet is None:
            raise ValueError("implemented-feature trace requires a verified implementation evidence packet")
        implemented_trace = json.loads(json.dumps(supplied_evidence, ensure_ascii=False))
        implemented_trace["active"] = True
        implemented_trace["mode"] = str(implemented_trace.get("mode") or "implemented_feature_prd")
        implemented_trace["evidence_packet"] = {
            "path": str(evidence_source.get("packet_path", "")),
            "sha256": str(evidence_source.get("packet_sha256", "")),
            "imported_result_refs": _trace_values(evidence_source.get("imported_result_refs")),
        }
    else:
        implemented_trace = {
            "active": False, "mode": "not_applicable", "branch_name": "", "diff_commands": [],
            "changed_files": [], "nearby_context_files": [], "ui_surfaces": [],
            "visual_runtime_capability": {"runtime_discovery": []}, "visual_capture_recovery": [],
            "behavior_evidence": [], "screenshots_and_placeholders": [], "validation_evidence": [],
            "completeness_check": {"implementation_behaviors_checked": [], "represented_in_prd": [], "unresolved_product_intent": [], "omitted_as_non_goal": []},
        }

    trace.update({
        "run_id": target.parent.name,
        "date": dt.datetime.now(dt.timezone.utc).date().isoformat(),
        "scenario": request_kind,
        "language": language,
        "agent_platform": "pm-copilot-controller",
        "model": CONTROLLER_TRACE_MODEL,
        "pm_copilot_version": active_version,
        "pm_copilot_revision": CONTROLLER_TRACE_REVISION,
        "task": {
            "request_source": "conversation",
            "brief_path": "",
            "raw_request": raw_request,
            "requested_artifacts": ["prd.md", "prd.html", "run-log.yaml", "assets/"],
        },
        "agent_strategy": {
            "task_mode": task_mode,
            "secondary_modes": [],
            "autonomy_level": "full-loop",
            "goal": goal,
            "success_criteria": [
                "The staged PRD and HTML reflect the explicitly confirmed scope.",
                "Every required final validator passes against the staged bytes.",
                "The canonical output is promoted only after staging validation succeeds.",
            ],
            "effort_budget": "standard-loop",
            "user_value": "A validated PRD can be reviewed and handed off without reconstructing execution history.",
            "selected_path": [
                "confirmed interactive scope",
                "isolated staging delivery",
                "independent artifact review",
                "controller-owned trace and final validation",
            ],
            "skipped_path": [{
                "state": "remote trace writer",
                "reason": "Run-log provenance is deterministic controller state and does not require a model call.",
                "readiness_impact": "none",
            }],
            "rejected_alternatives": [{
                "option": "Generate the run log through a remote Agent stream",
                "reason": "It adds a transport dependency without adding product judgment.",
                "risk_avoided": "An interrupted stream cannot leave a stale trace marked as current.",
            }],
            "final_delivery_contract": {
                "artifacts_required": ["prd.md", "prd.html", "run-log.yaml", "assets/"],
                "judgment_required": True,
                "blockers_required": True,
                "validation_required": True,
                "next_actions_required": True,
                "memory_candidates_required": False,
            },
        },
        "delegation_plan": {"active": False, "pattern": "direct", "workers": []},
        "agent_task_ledger": {
            "path": "", "status": "not_applicable", "evidence_ledger_paths": [],
            "resume_count": len(state.get("delivery_attempts", [])), "execution_boundary": "not_applicable",
        },
        "collaboration_protocol": {
            "required": False, "trigger": "not_required",
            "reason": "This delivery has no controller-managed multi-agent conflict.",
            "claims": [], "cross_reviews": [], "arbitrations": [],
        },
        "resume_checkpoint": {
            "last_reliable_state": "staged artifacts accepted before final validation",
            "task_mode": task_mode, "autonomy_level": "full-loop",
            "artifacts_ready": [name for name in ("confirmed-requirements.md", "prd.md", "prd.html") if (target.parent / name).is_file()],
            "artifacts_omitted": [], "blocking_questions": [],
            "decisions_made": ["Use a controller-owned run log for deterministic execution provenance."],
            "rejected_alternatives": ["Remote trace generation"],
            "validation_completed": ["requirements and PRD stage reviews"],
            "validation_required": ["render_prd_html.py", "validate_outputs.py", "validate_agent_trace.py", "run_delivery_checks.py"],
            "next_safe_action": "run final validation in the isolated staging workspace",
        },
        "termination_condition": {
            "status": "degraded",
            "evidence": "The controller trace is materialized; final validators have not yet all passed.",
            "pm_usefulness": "The trace is ready for deterministic validation, not for canonical promotion.",
            "remaining_limitation": "Canonical delivery remains blocked until final staging validation passes.",
        },
        "tool_plan": {
            "required_tools": [
                {"tool_id": "render_prd_html.py", "purpose": "render the staged PRD HTML", "trigger": "before final validation", "fallback": "fail the delivery"},
                {"tool_id": "validate_outputs.py", "purpose": "validate staged output bytes", "trigger": "before promotion", "fallback": "repair the rejected artifact"},
                {"tool_id": "validate_agent_trace.py", "purpose": "validate execution provenance", "trigger": "before promotion", "fallback": "regenerate controller trace"},
            ],
            "optional_tools": [], "unavailable_or_skipped": [],
        },
        "decision_record": [{
            "id": "D1", "decision": "Use the confirmed scope and staged artifacts as the only delivery source of truth.",
            "owner": "PM Orchestrator", "confidence": "high",
            "evidence": ["explicit user confirmation", "staged artifact hashes"],
            "alternatives_considered": ["reuse an unverified historical staging directory"],
            "tradeoff": "Fresh validation costs local execution time but prevents stale artifact promotion.",
            "readiness_impact": "prd",
        }],
        "replan_triggers": [{
            "trigger": "validation_failure", "observed_at_state": "delivery",
            "action_taken": "Keep canonical output unchanged and repair only the rejected staged artifact.",
            "affected_artifacts": ["prd.md", "run-log.yaml"], "readiness_impact": "prd",
        }],
        "review_loop": {"iterations": 0, "critical_or_high_findings": [], "finding_closures": [], "unresolved_findings": [], "final_recommendation": "revise"},
        "loop_policy": {
            "enabled": False, "loop_type": "direct",
            "disabled_reason": "Run-log materialization is deterministic controller work, not an autonomous model loop.",
            "max_iterations": 1, "max_tool_calls": 4, "max_elapsed_minutes": 5,
            "max_consecutive_no_progress": 1, "min_progress_score_delta": 1,
            "stop_conditions": ["success_criteria_met", "failed"],
            "human_checkpoint": {"required_after_iteration": 0, "status": "not_required", "required_before_actions": []},
        },
        "loop_state": {
            "current_iteration": 0, "tool_calls_used": 0, "elapsed_minutes": 0,
            "consecutive_no_progress": 0, "last_progress_score": 0,
            "success_criteria_met": False, "conflict_resolution_status": "clear",
        },
        "iteration_trace": [],
        "loop_summary": {"iterations_completed": 0, "stop_reason": "not_applicable", "final_progress_score": 0, "unresolved_items": []},
        "memory_candidates": {"none": True, "product_memory": [], "user_preferences": [], "decision_log": []},
        "next_actions": {
            "product": [], "design": [],
            "engineering": ["Review the promoted PRD against the confirmed scope before implementation."],
            "qa": ["Use the PRD acceptance evidence during downstream verification."],
            "analytics": [], "launch": [],
        },
        "action_closure": {"critical_path": [{
            "action_id": "A1", "action": "Complete final staging validation and promote only the verified delivery.",
            "owner": "PM Orchestrator", "due_phase": "now", "source_decision_ids": ["D1"],
            "source_blocker_ids": [], "completion_evidence": "canonical validation passes after promotion", "status": "ready",
        }]},
        "context": {
            "source_mode": context_mode,
            "files_loaded": ["discussion.md", "confirmed-requirements.md", "prd.md", *list(context_descriptor.get("files_loaded", []))],
            "host_project_root": str(context_descriptor.get("host_project_root", "")),
            "host_project_files_loaded": list(context_descriptor.get("host_project_files_loaded", [])),
            "product_documents_loaded": [
                *list(context_descriptor.get("product_documents_loaded", [])),
                *([lineage["source_snapshot_path"]] if extraction else []),
            ],
            "current_state_summary": str(latest.get("summary", "")) if isinstance(latest, dict) else "",
            "current_state_facts": facts,
            "analytics_taxonomy_source": {"status": "not checked", "source": "", "implication": "tracking is evaluated in the PRD contract when applicable"},
            "context_excluded": ["unverified historical delivery workspaces"], "conflicts_found": [], "conflict_resolution": [],
        },
        "artifact_lineage": lineage,
        "external_research": {"status": "not_applicable", "question": "", "competitor_flows": [], "sources": [], "limitations": [], "recommendation_impact": ""},
        "readiness": {
            "prd_status": "ready for review", "engineering_handoff_status": "not applicable", "launch_status": "not applicable",
            "status_rationale": "The delivery remains in staging until every final validator passes.",
            "engineering_blockers": [], "launch_blockers": [],
        },
        "workflow": {
            "states_completed": ["discussion", "clarification", "confirmation", "requirements delivery", "PRD stage review"],
            "states_skipped": [], "skip_reasons": [], "last_reliable_state": "delivery",
            "resume_source": "existing run-log" if revision else "source PRD snapshot" if extraction else "new run",
            "clarification_gate": {
                "required": True, "status": "confirmed", "stopped_before_generation": False,
                "assumption_risk_accepted": False, "confirmation_risk_accepted": False,
                "evidence": "explicit interactive confirmation",
            },
            "revision_loops": int(state.get("revision_loops", 0)),
        },
        "implemented_feature_prd": implemented_trace,
        "requirement_coverage_review": [],
        "agent_transitions": [{
            "state": "delivery", "agent": "PM Orchestrator", "status": "complete", "confidence": "high",
            "input_evidence": ["confirmed scope", "staged artifact hashes"],
            "artifact_delta": {"files_created": ["run-log.yaml"], "files_changed": ["run-log.yaml"], "files_unchanged": assets},
            "validation_delta": {"commands_run": [], "commands_skipped": [], "required_later": ["render_prd_html.py", "validate_outputs.py", "validate_agent_trace.py", "run_delivery_checks.py"]},
            "readiness_impact": "prd", "conflict": "", "resolution": "", "next_expected_output": "final validation result",
        }],
        "agents_used": [{"name": "PM Orchestrator", "purpose": "controller-owned provenance", "inputs": ["controller state"], "outputs": ["run-log.yaml"], "handoff_to": "final validator"}],
        "skills_used": [],
        "tools_used": [{"tool_id": "controller.trace", "name": "controller trace materializer", "purpose": "write deterministic run-log.yaml", "trigger": "after PRD stage review", "command": "internal controller", "status": "passed", "result": "staged trace materialized", "artifacts_created": ["run-log.yaml"], "limitation": "final validation pending", "fallback_used": "not applicable"}],
        "tool_preflight": {"command": "not required for controller trace materialization", "status": "skipped", "report_path": "", "available_tools": [], "setup_required_tools": [], "unavailable_tools": []},
        "external_integrations": [],
        "human_inputs": {
            "clarification_questions": [],
            "answers_received": _trace_values(latest.get("user_text") if isinstance(latest, dict) else []),
            "default_options_selected": [], "unanswered_questions": [], "confirmations_required": [],
        },
        "assumptions": [{"id": "A1", "assumption": item, "reason": "recorded during clarification", "risk": "tracked in the confirmed scope", "source": "user confirmed", "blocks_generation": False} for item in assumptions],
        "scope_decisions": {"confirmed_mvp": in_scope or [goal], "optional_or_conditional": [], "future_scope": [], "non_goals": out_of_scope},
        "surface_decisions": {"entry_points": [], "navigation_visibility": "not specified", "eligible_user_state": "not specified", "ineligible_user_state": "not specified", "fallback_states": risks},
        "host_frontend_inventory": {"platform": "not_applicable", "entry_files": [], "route_or_screen_files": [], "component_files": [], "style_files": [], "icon_asset_sources": [], "data_or_mock_sources": [], "render_entrypoint": "not applicable", "preview_surface": "", "preview_url": "", "source_rendering_decision": "not_required", "source_rendering_limitation": ""},
        "style_evidence": {"source_files": [], "reused_components": [], "reused_tokens_or_classes": [], "icon_asset_sources": [], "ui_delta": "not applicable", "limitations": []},
        "ui_delivery_trace": {"mode": "not_applicable", "host_mutation_policy": "not_applicable", "target_surface": "", "preview_files_changed": [], "implementation_files_changed": [], "baseline_import": {"imported_sources": [], "render_method": "not_applicable", "baseline_modification_policy": "not_applicable"}, "delta_patch": {"patch_files": [], "patch_strategy": "not_applicable", "mock_state_sources": [], "multi_turn_change_log": [], "next_delta_anchor": ""}, "source_to_demo_mapping": [], "backend_simulation": {"method": "not_applicable", "data_contract_source": "", "states_represented": [], "limitations": []}, "parity_claim": "not_applicable", "source_extract": {"source_target": "", "selector": "", "extraction_command": "", "extracted_html_path": "", "source_region_screenshot": "", "extracted_region_screenshot": "", "region_diff": "", "interaction_scope": "", "interaction_checks": [], "style_capture_method": "", "asset_handling": "", "annotation_layer": "", "annotation_config": "", "source_change_scope": "not_applicable", "validation_report": "", "limitations": []}, "limitations": []},
        "existing_ui_visual_baseline": {"status": "not_applicable", "source": "unavailable", "target": "", "screenshots": [], "comparison_method": "not_run", "limitation": ""},
        "image_reference_reconstruction": {"status": "not_applicable", "references": [], "visual_inventory_summary": [], "asset_handling": {"reused_assets": [], "generated_assets": [], "placeholders": []}, "comparison": {"method": "not_run", "implementation_screenshots": [], "mismatches_fixed": [], "remaining_mismatches": [], "skipped_reason": ""}, "fidelity_claim": "not_applicable"},
        "design_calibration": {"visual_density": "not_applicable", "layout_variance": "not_applicable", "motion_intensity": "not_applicable", "anti_generic_choices": []},
        "content_sources": [{"content_area": "confirmed product scope", "source_status": "user supplied", "source_reference": "interactive conversation", "review_owner": "PM Orchestrator", "review_status": "approved", "disclaimer_status": "not applicable", "launch_impact": "not applicable"}],
        "structured_catalog": {"catalog_type": "not_applicable", "primary_artifact": "", "html_artifact": "", "source_status": "not_applicable", "review_status": "not_applicable", "owner": "", "row_count": 0, "required_fields": [], "source_freshness_limitations": [], "blocked_rows": []},
        "structured_reference": {"delivery_class": "not_applicable", "catalog_type": "not_applicable", "primary_artifact": "", "html_artifact": "", "source_status": "not_applicable", "review_status": "not_applicable", "owner": "", "entities": [], "fields": [], "rules": [], "decisions": [], "attention_points": [], "calibration": {"workflow": "not_applicable", "patch_scope": "not_applicable", "protected_objects": [], "conflicts_detected": []}, "change_log": [], "completeness_check": {"entity_count": 0, "field_coverage": [], "defaults_checked": [], "enums_checked": [], "limits_checked": [], "sources_checked": [], "pending_confirmations": [], "conflicts": []}},
        "open_questions": [],
        "artifacts": {"prd": "prd.md", "catalog": "", "ui_deliverable": "", "run_log": "run-log.yaml", "tool_results_dir": "", "optional_exports": [], "omitted_split_files": []},
        "visual_validation": {"required": False, "command": "", "status": "skipped", "preview_target": "", "screenshots": [], "baseline_dir": "", "diff_status": "not_applicable", "max_diff_ratio": None, "observed_diff_ratio": None, "non_blank_ratio": None, "report_path": "", "source_preview_report_path": "", "limitation": "not applicable"},
        "handoff_artifacts": {"dev_tasks": "", "launch_decision": "", "generation_mode": "not_requested", "status": "not_requested"},
        "guardrail_events": [],
        "security_and_audit": {"boundary": "PM artifact generation only; no host product mutation", "audit_visibility": "interactive controller state and final trace", "identity_confirmation_expectation": "explicit user confirmation before delivery", "redaction_expectation": "do not record secrets or raw sensitive data", "retention_or_deletion_assumption": "retain the canonical PRD trace under the project output folder", "unresolved_approval_owner": "not applicable"},
        "review_findings": [],
        "review_scores": {
            "delivery": {"score": 0, "max_score": 32, "status": "not_scored_pending_validation"},
            "prd": {"score": 0, "max_score": 40, "status": "not_scored_pending_validation"},
            "metrics_and_tracking": {"score": 0, "max_score": 28, "status": "not_scored_pending_validation"},
            "ui_delivery": {"score": 0, "max_score": 32, "status": "not_scored_pending_validation"},
            "review_checklist": {"score": 0, "max_score": 20, "status": "not_scored_pending_validation"},
        },
        "quality_thresholds": {"delivery": 23, "prd": 31, "metrics_and_tracking": 21, "ui_delivery": 24, "review_checklist": 15},
        "quality_decision": {"passed": False, "score_delta": 0, "rationale": "Final validation is pending."},
        "validation_results": [
            {"command": "render_prd_html.py", "tool_id": "render_prd_html.py", "tool_version": "active runtime", "status": "pending", "result": "controller validation pending", "limitation": "", "fallback": ""},
            {"command": "validate_outputs.py", "tool_id": "validate_outputs.py", "tool_version": "active runtime", "status": "pending", "result": "controller validation pending", "limitation": "", "fallback": ""},
            {"command": "validate_agent_trace.py", "tool_id": "validate_agent_trace.py", "tool_version": "active runtime", "status": "pending", "result": "controller validation pending", "limitation": "", "fallback": ""},
            {"command": "run_delivery_checks.py", "tool_id": "run_delivery_checks.py", "tool_version": "active runtime", "status": "pending", "result": "controller validation pending", "limitation": "", "fallback": ""},
        ],
        "self_iteration": {"triggered": False, "source_run_id": "", "source_run_ids": [], "failure_evidence": [], "user_corrections": [], "generalized_failures": [], "selected_fix_surfaces": [], "regression_updates": [], "generalization_boundary": "", "validation_commands": [], "version_change": "", "embedded_copy_sync": []},
        "failures": [],
        "final_status": "deterministic trace ready for validation",
    })
    if revision:
        _materialize_revision_evidence(state, target)
    _atomic_write_text(target, yaml.safe_dump(trace, allow_unicode=True, sort_keys=False, default_flow_style=False))
    _normalise_trace_runtime_evidence(target)


def _copy_input_assets(state: dict[str, Any], destination: Path) -> None:
    assets = destination / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for raw_source in state.get("input_assets", []):
        source = Path(str(raw_source)).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Input screenshot asset not found: {source}")
        if source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".mov", ".m4v", ".ogv", ".ogg"}:
            raise ValueError(f"Unsupported PRD visual asset: {source.name}")
        target = assets / source.name
        if target.exists() and hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(source.read_bytes()).digest():
            raise FileExistsError(f"Input screenshot asset name conflicts with an existing canonical asset: {source.name}")
        shutil.copy2(source, target)


def _active_runtime_version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _confirmed_scope_fingerprint(state: dict[str, Any]) -> str:
    """Fingerprint only the facts that make an accepted stage reusable."""
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
    revisions = state.get("revision_history") if _delivery_variant(state) == "in_place_revision" else []
    latest_revision = revisions[-1] if isinstance(revisions, list) and revisions else {}
    revision_evidence = {
        key: value
        for key, value in latest_revision.items()
        if key != "at"
    } if isinstance(latest_revision, dict) else {}
    input_assets = []
    for raw_asset in state.get("input_assets", []):
        asset = Path(str(raw_asset)).expanduser()
        input_assets.append({
            "name": asset.name,
            "sha256": _artifact_digest(asset),
        })
    payload = {
        "raw_request": str(state.get("raw_request", "")).strip(),
        "task_mode": _task_mode(state),
        "delivery_variant": _delivery_variant(state),
        "context_source": state.get("context_source", {}),
        "confirmed_fact_packet": packet_copy,
        "revision": revision_evidence,
        "revision_scope_manifest": state.get("revision_scope_manifest", {}),
        "revision_requirement_ids": sorted(_trace_values(state.get("revision_requirement_ids"))),
        "extraction_source": state.get("extraction_source", {}),
        "implemented_feature_evidence": state.get("implemented_feature_evidence", {}),
        "input_assets": sorted(input_assets, key=lambda item: (item["name"], str(item["sha256"]))),
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
    payload = {
        "prd_sha256": _artifact_digest(canonical / "prd.md"),
        "html_sha256": _artifact_digest(canonical / "prd.html"),
        "scope_manifest": state.get("revision_scope_manifest", {}),
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
    return {
        "scope_fingerprint": _confirmed_scope_fingerprint(state),
        "baseline_digest": _revision_baseline_fingerprint(state),
        "runtime_version": _active_runtime_version(),
        "controller_version": _artifact_digest(Path(__file__).resolve()),
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
    version = _active_runtime_version()
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
        "artifacts": reusable,
    }
    _write_json(cache / "manifest.json", manifest)
    state["retry_reuse"] = {
        "status": "available",
        "scope_fingerprint": fingerprint,
        "pm_copilot_version": version,
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
    version = _active_runtime_version()
    if (
        not isinstance(manifest, dict)
        or manifest.get("scope_fingerprint") != fingerprint
        or manifest.get("pm_copilot_version") != version
        or reuse.get("scope_fingerprint") != fingerprint
        or reuse.get("pm_copilot_version") != version
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
    return None


def _prepare_delivery_workspace(state: dict[str, Any]) -> Path:
    canonical = _canonical_folder(state)
    source_drift = _revision_source_drift_problem(state)
    if source_drift:
        raise ValueError(source_drift)
    workspace = canonical.parent / f".{canonical.name}.delivery-stage" / canonical.name
    if workspace.exists():
        shutil.rmtree(workspace.parent)
    workspace.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(canonical, workspace, ignore=shutil.ignore_patterns(".delivery-stage", ".DS_Store"))
    if _delivery_variant(state) == "in_place_revision" and (workspace / "prd.md").is_file():
        baseline = workspace / ".revision-baseline"
        baseline.mkdir(parents=True, exist_ok=True)
        shutil.copy2(workspace / "prd.md", baseline / "prd.md")
    _copy_input_assets(state, workspace)
    state["delivery_workspace"] = str(workspace)
    _restore_reusable_delivery_artifacts(state, workspace)
    return workspace


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
    baseline_assets = manifest.get("baseline", {}).get("assets", {})
    baseline_assets = baseline_assets if isinstance(baseline_assets, dict) else {}
    report = validate_revision_scope(
        manifest,
        baseline_markdown=baseline.read_text(encoding="utf-8"),
        candidate_markdown=candidate.read_text(encoding="utf-8"),
        baseline_assets={str(path): str(digest) for path, digest in baseline_assets.items()},
        candidate_assets=_revision_asset_digests(folder),
    )
    if include_rendered_html and report.get("status") == "passed":
        html_path = folder / "prd.html"
        if not html_path.is_file():
            report.setdefault("failures", []).append("rendered prd.html is missing for revision scope validation")
        else:
            report.setdefault("failures", []).extend(
                validate_rendered_html_scope(report, html_path.read_text(encoding="utf-8"))
            )
        if report.get("failures"):
            report["status"] = "failed"
    report["validated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    report["manifest_sha256"] = hashlib.sha256(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    _write_json(_revision_scope_report_path(folder), report)
    state["revision_scope_validation"] = {
        "status": report.get("status"),
        "report_path": "tool-results/revision-scope-validation.json",
        "manifest_sha256": report["manifest_sha256"],
        "failures": list(report.get("failures", [])),
    }
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
    revision_evidence = workspace / "revision-evidence.json"
    retained_result_files = {
        relative: source
        for relative, source in _trace_result_files(workspace / "run-log.yaml")
    }
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

        if revision_evidence.is_file():
            _atomic_copy(revision_evidence, candidate / revision_evidence.name)
        _promote_trace_result_files(candidate, referenced_result_files)
        (candidate / ".DS_Store").unlink(missing_ok=True)
        (candidate / "assets" / ".DS_Store").unlink(missing_ok=True)

        # Verify the candidate after all staged provenance and retained result
        # files are copied, but before the directory swap.  This prevents a
        # source-material mutation during the delivery window from ever being
        # visible in canonical output under the old trace hash.
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
        # protect a collaborator's later update from being overwritten.
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
    except OSError:
        if moved_original and backup.exists() and not canonical.exists():
            backup.replace(canonical)
        raise
    finally:
        if publish_root.exists():
            shutil.rmtree(publish_root, ignore_errors=True)
    state["delivery_promoted_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    return backup


def _write_trace_agent_evidence(run_log: Path, state: dict[str, Any]) -> None:
    """Store one concise, structured evidence record for every accepted stage."""
    if not run_log.is_file():
        return
    try:
        trace = yaml.safe_load(run_log.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return
    if not isinstance(trace, dict):
        return
    trace["agent_execution_evidence"] = _trace_agent_evidence(state)
    _atomic_write_text(
        run_log,
        yaml.safe_dump(trace, allow_unicode=True, sort_keys=False, default_flow_style=False),
    )
    _normalise_trace_runtime_evidence(run_log)


def _append_controller_agent_evidence(state: dict[str, Any]) -> None:
    """Make controller-observed provider/model evidence durable in run-log.yaml."""
    _write_trace_agent_evidence(_delivery_folder(state) / "run-log.yaml", state)


def _finalize_deterministic_trace(folder: Path, checks: list[dict[str, Any]]) -> bool:
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
    trace["termination_condition"] = {
        "status": "complete",
        "evidence": "Every controller-observed staging validator passed against the final staged bytes.",
        "pm_usefulness": "The validated PRD is ready for its stated review and handoff path.",
        "remaining_limitation": "Product decisions and implementation approvals remain owned by their named reviewers.",
    }
    trace["quality_decision"] = {
        "passed": True,
        "score_delta": 0,
        "rationale": "All required staging validation commands passed before promotion.",
    }
    trace["review_loop"] = {
        "iterations": 1,
        "critical_or_high_findings": [],
        "finding_closures": [],
        "unresolved_findings": [],
        "final_recommendation": "proceed",
    }
    action_closure = trace.get("action_closure")
    if isinstance(action_closure, dict):
        critical_path = action_closure.get("critical_path")
        if isinstance(critical_path, list):
            for action in critical_path:
                if isinstance(action, dict) and action.get("status") == "ready":
                    action["status"] = "complete"
    trace["final_status"] = "validated controller trace"
    _atomic_write_text(
        target,
        yaml.safe_dump(trace, allow_unicode=True, sort_keys=False, default_flow_style=False),
    )
    _normalise_trace_runtime_evidence(target)
    return True


_TRACE_EVIDENCE_PHASES = (
    ("intake", None),
    ("clarification_review", None),
    ("delivery", "confirmed-requirements.md"),
    ("stage_quality_review", "confirmed-requirements.md"),
    ("delivery", "prd.md"),
    ("stage_quality_review", "prd.md"),
    ("delivery", "run-log.yaml"),
    ("stage_quality_review", "run-log.yaml"),
)


def _compact_trace_text(value: object, limit: int = 240) -> str:
    """Keep provider diagnostics useful without replaying model transcripts."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _trace_agent_evidence(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return one current attributable completion per required production stage.

    Agent-call records are durable controller state and can retain verbose
    historical provider output across recovery attempts. A trace needs an
    evidence index, not that transcript: replaying it into the final Agent
    prompt has repeatedly caused the small YAML write to lose its stream.
    """
    latest: dict[tuple[str, str | None], dict[str, Any]] = {}
    calls = state.get("agent_calls", [])
    for call in reversed(calls if isinstance(calls, list) else []):
        if not isinstance(call, dict) or call.get("status") != "complete":
            continue
        key = (str(call.get("phase", "")), call.get("artifact"))
        if key not in _TRACE_EVIDENCE_PHASES or key in latest:
            continue
        if not _agent_call_has_evidence(call):
            continue
        latest[key] = {
            "phase": key[0],
            "artifact": key[1] or "request",
            "provider": call.get("provider"),
            "model": call.get("model"),
            "status": "complete",
            "attempt": call.get("attempt", 1),
            "agent_id": call.get("agent_id"),
            "execution_mode": call.get("execution_mode"),
            "error": _compact_trace_text(call.get("error", ""), 160),
        }
    return [latest[key] for key in _TRACE_EVIDENCE_PHASES if key in latest]


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


def create_state(raw_request: str, folder: Path) -> dict[str, Any]:
    extraction = _request_looks_like_extraction(raw_request)
    return {
        "schema_version": 1,
        "mode": "interactive",
        "folder": str(folder),
        "raw_request": raw_request,
        "task_mode": "prd_delivery",
        "delivery_variant": "extract_to_new" if extraction else "new",
        "context_source": {
            "mode": "document-backed" if extraction else "brief-only",
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
    folder = Path(str(state["folder"]))
    prd_path = folder / "prd.md"
    known_ids = _trace_requirement_ids(prd_path)
    state.setdefault("revision_history", []).append({
        "at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "request": request,
        "prd_before_sha256": _artifact_digest(prd_path),
        "html_before_sha256": _artifact_digest(folder / "prd.html"),
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
    }
    state["delivery_variant"] = "in_place_revision"
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


def _artifact_prompt(state: dict[str, Any], artifact: str, repair_errors: str = "") -> str:
    latest = _confirmed_fact_source(state)
    role = "Requirements" if artifact != "run-log.yaml" else "Orchestrator Trace"
    target = _delivery_folder(state) / artifact
    available_assets = [Path(item).name for item in state.get("input_assets", [])]
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
"""
    elif variant == "extract_to_new":
        descriptor = state.get("extraction_source") if isinstance(state.get("extraction_source"), dict) else {}
        snapshot = str(descriptor.get("snapshot_path", "source-material/source-prd.md"))
        selection = json.dumps(_extraction_selection(state), ensure_ascii=False)
        variant_instruction = f"""
This is an extraction into a new independent PRD. Read only the immutable
document-backed source snapshot at {snapshot}. Create a fresh PRD structure
from the confirmed selection {selection}; do not copy unrelated sections,
historical trace text, or source-run status into the new PRD.
"""
    elif task_mode == "implemented_feature_prd":
        evidence_source = state.get("implemented_feature_evidence_source")
        packet_path = (
            str(evidence_source.get("packet_path", "")).strip()
            if isinstance(evidence_source, dict) else ""
        )
        variant_instruction = f"""
This is an implemented-feature PRD. Read the canonical source-material JSON
packet at {packet_path}. Use only that packet as observed implementation
evidence: do not inspect repository files, diffs, external paths, tool output,
or model inference to establish implemented behavior. The confirmed
conversation defines product scope, but any behavior absent from the packet is
unverified product intent and must remain explicit rather than invented.
"""
    if artifact == "run-log.yaml":
        # A trace consists of controller-observable evidence, so avoid
        # repeating the complete product brief and every unrelated artifact
        # contract. The old prompt caused the Agent to load them again, making
        # the final, mechanical stage disproportionately prone to a stream
        # interruption before it ever opened the target file.
        trace_calls = _trace_agent_evidence(state)
        revision = variant == "in_place_revision"
        revision_history = state.get("revision_history", []) if revision else []
        revision_ids = list(state.get("revision_requirement_ids") or [])
        if not revision_ids and revision_history:
            revision_ids = _extract_requirement_ids(str(revision_history[-1].get("request", "")))
        lineage = {
            "mode": "in_place_revision" if revision else "extraction_run" if variant == "extract_to_new" else "new_delivery",
            "revised_requirement_ids": revision_ids if revision else [],
        }
        trace_packet = {
            "confirmation": state.get("user_confirmation"),
            "task_mode": task_mode,
            "summary": _compact_trace_text(latest.get("summary", ""), 1200),
            "scope_goal": _compact_trace_text(latest.get("scope", {}).get("goal", ""), 1000),
            "in_scope": [_compact_trace_text(item, 280) for item in latest.get("scope", {}).get("in_scope", [])[:12]],
            "out_of_scope": [_compact_trace_text(item, 280) for item in latest.get("scope", {}).get("out_of_scope", [])[:12]],
            "assumptions": [_compact_trace_text(item, 240) for item in latest.get("assumptions", [])[:8]],
            "risks": [_compact_trace_text(item, 240) for item in latest.get("risks", [])[:8]],
            "artifact_lineage": lineage,
            "agent_calls": trace_calls,
            "input_assets": available_assets,
        }
        return f"""Write one complete artifact at {target}.
You are the PM Copilot Trace Agent. Create only that YAML file and do not
modify any other path. Do not read PM_COPILOT.md, prior run-log.yaml, or other
project artifacts: the controller evidence below is authoritative and
sufficient. Start by copying templates/agent-run-log-template.yaml to the
target, then replace every placeholder. Do not omit or rename any top-level
template section. Write the file before any explanatory response.

The log must pass validate_agent_trace.py and validate_outputs.py. In
particular it requires agent_strategy, delegation_plan, resume_checkpoint,
termination_condition, tool_plan, decision_record, replan_triggers,
review_loop, loop_policy, loop_state, iteration_trace, loop_summary,
memory_candidates, next_actions, action_closure, quality_thresholds,
quality_decision, failures, and readiness.prd_status,
readiness.engineering_handoff_status, readiness.launch_status,
readiness.engineering_blockers, readiness.launch_blockers. Record the explicit
confirmation, real Agent calls, separate PRD/engineering/launch readiness and
validation commands. It must be a compact trace under 24 KiB. For an in-place
revision, set artifact_lineage.mode to in_place_revision and include only its
changed requirement IDs. Do not claim human engineering or launch approval.

Controller evidence:
{json.dumps(trace_packet, ensure_ascii=False, separators=(",", ":"))}
  """ + (f"\nRepair only these trace-validator findings:\n{repair_errors}" if repair_errors else "")
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
- prd.md: use {prd_template} and artifacts/prd-contract.md exactly. Create a Chinese H1 of concise requirement title plus YYYY-MM-DD; include document information and version history; use every standard requirement-list field; map one-to-one to 5.x detail IDs; each detail table has only 用户与场景、需求入口、需求详情、设计与交互. When new or changed UI copy exists, include 六、多语言需求. Each provided screenshot must be inside its matching 需求详情 cell using exactly `[[prd-detail-media src="./assets/功能-状态.png" alt="功能-状态" copy="对应状态、规则和反馈"]]`; never put `<div>` or `<img>` source HTML in a Markdown table, never use a standalone Markdown image, and never add a standalone 图示 row.
- run-log.yaml: use templates/agent-run-log-template.yaml, fill concrete fields, record this interactive user confirmation, real Agent calls, validation commands, separate PRD/engineering/launch readiness, and truthful termination state.
- For the prd.md stage, this Agent writes only prd.md. The controller renders and validates prd.html after prd.md passes review; that required downstream deliverable is not a conflict and must not be used as a reason to refuse the prd.md task.
Provided user visual assets already copied to this delivery workspace: {json.dumps(available_assets, ensure_ascii=False)}. Use each applicable asset inline; do not invent a wireframe in place of it. Record visual coverage decisions as real_figure, required_placeholder, or not_required in run-log.yaml.
{variant_instruction}
""" + ("""
For run-log.yaml, overwrite the target immediately with a compact trace under 24 KiB. Do not read, summarize, or preserve the prior run-log.yaml. Use concise field values and file paths instead of embedded command output or Agent transcripts.
""" if artifact == "run-log.yaml" else "") + (f"\nRepair these validator findings in this artifact only:\n{repair_errors}" if repair_errors else "")


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
        shutil.copytree(real_folder, stage_folder)
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
                _normalise_trace_runtime_evidence(stage_target)
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
                _write_trace_agent_evidence(stage_target, state)
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
                result = worker(provider, _artifact_prompt(stage_state, artifact, repair_errors), stage_folder, timeout, model, None, False, 8000)
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
                scope_report = _validate_staged_revision_scope(stage_state, stage_folder)
                state["revision_scope_validation"] = stage_state.get("revision_scope_validation", {})
                scope_failures = list(scope_report.get("failures", [])) if isinstance(scope_report, dict) else []
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
                question = (
                    "检测到 PRD 修改超出当前确认范围。请确认是否允许这些额外章节一并修改；"
                    "若不允许，控制器将恢复未授权内容。"
                )
                state["status"] = "needs_input"
                state["termination"] = "needs_input"
                state["last_error"] = violation
                state["scope_clarification"] = {"artifact": artifact, "question": question, "violation": violation}
                if state.get("turns"):
                    state["turns"][-1]["questions"] = [question]
                    state["turns"][-1].setdefault("buckets", {})["must_answer_before_generation"] = [question]
        stage_after_sha256 = _artifact_digest(stage_target)
        # A changed staged file is necessary but not sufficient: the caller
        # must also be attributable before its bytes can enter the delivery
        # workspace or become reusable on a later recovery attempt.
        attributable = _agent_call_has_evidence(result)
        promoted = (
            attributable
            and
            result.get("status") == "complete"
            and stage_after_sha256 is not None
            and stage_after_sha256 != stage_before_sha256
        )
        if promoted:
            if artifact == "run-log.yaml":
                # Agent tools report their writable staging path. The promoted
                # trace must instead identify the stable canonical run folder.
                text = stage_target.read_text(encoding="utf-8")
                _atomic_write_text(stage_target, text.replace(str(stage_folder), str(real_folder)))
            _atomic_copy(stage_target, target)
            if artifact == "prd.md" and _delivery_variant(state) == "in_place_revision":
                scope_report = _revision_scope_report_path(stage_folder)
                if scope_report.is_file():
                    _atomic_copy(scope_report, _revision_scope_report_path(real_folder))
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
    stage["pm_copilot_version"] = _active_runtime_version()
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


def _artifact_review_prompt(state: dict[str, Any], artifact: str, review_path: Path) -> str:
    target = _delivery_folder(state) / artifact
    revision_contract = ""
    if artifact == "prd.md" and _delivery_variant(state) == "in_place_revision":
        manifest = state.get("revision_scope_manifest")
        validation = state.get("revision_scope_validation")
        revision_contract = f"""
Controller-owned revision scope contract:
{json.dumps(manifest if isinstance(manifest, dict) else {}, ensure_ascii=False, separators=(",", ":"))}
Controller scope-validation summary:
{json.dumps(validation if isinstance(validation, dict) else {}, ensure_ascii=False, separators=(",", ":"))}
The controller has already checked the frozen baseline. Assess image count,
order, copy, and acceptance constraints only inside the contract's
requirement_ids. Do not block the review because an unselected requirement or
its existing image/copy remains in the PRD: it is protected baseline content,
not an extension of this revision. Every blocking finding must cite at least
one selected requirement ID and quote its evidence from that selected section.
"""
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

Write ONLY one JSON object to {review_path} (UTF-8):
{{"status":"pass"|"needs_revision","summary":"", "blocking_findings":["specific repair"], "acceptance_evidence":["checked condition"]}}
Use pass only when blocking_findings is empty and acceptance_evidence proves
the artifact's required handoff conditions. Empty proof is needs_revision.

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
    stage["pm_copilot_version"] = _active_runtime_version()
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
    with tempfile.TemporaryDirectory(prefix=f".{real_folder.name}.review-", dir=str(real_folder.parent)) as review_dir:
        review_folder = Path(review_dir) / real_folder.name
        shutil.copytree(real_folder, review_folder)
        review_path = review_folder / ".stage-review.json"
        result = {}
        for attempt in range(1, MAX_ATTRIBUTABLE_AGENT_ATTEMPTS + 1):
            result = worker(provider, _artifact_review_prompt({**state, "folder": str(review_folder)}, artifact, review_path), review_folder, min(timeout, STAGE_REVIEW_TIMEOUT_MINUTES), model, None, False, 8000)
            result["attempt"] = attempt
            attributable = _record_agent_call(state, result, phase="stage_quality_review", artifact=artifact)
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
        review = _extract_json(review_text or result.get("output", ""))
    except (ValueError, json.JSONDecodeError) as error:
        _stage(state, artifact)["review_status"] = "failed"
        _checkpoint(state, state_path)
        return False, f"Stage Quality Review Agent returned invalid JSON: {error}"
    findings = review.get("blocking_findings", [])
    if not isinstance(findings, list):
        findings = [findings]
    findings = [str(item).strip() for item in findings if str(item).strip()]
    acceptance_evidence = review.get("acceptance_evidence", [])
    if not isinstance(acceptance_evidence, list):
        acceptance_evidence = [acceptance_evidence]
    acceptance_evidence = [str(item).strip() for item in acceptance_evidence if str(item).strip()]
    review_status = str(review.get("status", "")).strip().lower()
    if review_status == "needs_revision" and not findings:
        _stage(state, artifact)["review_status"] = "failed"
        _checkpoint(state, state_path)
        return False, "Stage Quality Review Agent returned needs_revision without specific blocking_findings"
    if review_status == "pass" and not acceptance_evidence:
        _stage(state, artifact)["review_status"] = "failed"
        _checkpoint(state, state_path)
        return False, "Stage Quality Review Agent returned pass without acceptance_evidence"
    passed = review_status == "pass" and not findings
    stage = _stage(state, artifact)
    stage["review_status"] = "passed" if passed else "needs_revision"
    stage["reviewed_sha256"] = _artifact_digest(real_folder / artifact)
    stage["review_findings"] = findings
    stage["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    stage["scope_fingerprint"] = _confirmed_scope_fingerprint(state)
    stage["pm_copilot_version"] = _active_runtime_version()
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
    for revision in range(max_revisions + 1):
        passed, findings = _review_artifact(state, artifact, provider, timeout, worker, state_path, model)
        if passed:
            return True
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
    return False


def _validate_delivery(folder: Path, staging: bool = False) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    commands = [
        [sys.executable, "scripts/render_prd_html.py", str(folder)],
        [sys.executable, "scripts/validate_outputs.py", str(folder), "--language", "zh"] + (["--staging"] if staging else []),
        [sys.executable, "scripts/validate_agent_trace.py", str(folder)],
        [sys.executable, "scripts/run_delivery_checks.py", str(folder), "--language", "zh"] + (["--staging"] if staging else []),
    ]
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        checks.append({
            "command": " ".join(command[1:]),
            "status": "passed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "stdout": result.stdout[-3000:],
            "stderr": result.stderr[-2000:],
        })
    return checks


def _validate_staged_delivery(state: dict[str, Any], folder: Path) -> list[dict[str, Any]]:
    """Run global validators plus the semantic contract for an in-place revision."""
    checks = _validate_delivery(folder, staging=True)
    report = _validate_staged_revision_scope(state, folder, include_rendered_html=True)
    if report is not None:
        failures = list(report.get("failures", [])) if isinstance(report, dict) else ["revision scope report is unavailable"]
        checks.append({
            "command": "revision_scope.validate staged prd.md/prd.html",
            "status": "passed" if not failures else "failed",
            "exit_code": 0 if not failures else 1,
            "stdout": "\n".join(report.get("checks", [])) if isinstance(report, dict) else "",
            "stderr": "\n".join(failures),
        })
    return checks


def _validation_failure_targets_trace(checks: list[dict[str, Any]]) -> bool:
    """Tell a trace-contract failure from a PRD-content failure.

    ``validate_outputs`` and ``run_delivery_checks`` validate a folder rather
    than one filename.  Their trace-specific findings must regenerate the
    controller-owned trace locally, never be handed to the PRD writer.
    """
    trace_markers = (
        "run-log.yaml",
        "run log",
        "agent trace",
        "validate_agent_trace",
        "quality decision",
        "quality_decision",
        "validation_results",
        "agent_execution_evidence",
        "termination_condition",
    )
    for check in checks:
        if check.get("status") == "passed":
            continue
        detail = " ".join(str(check.get(key, "")) for key in ("command", "stdout", "stderr")).lower()
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
    restart_requested = bool(state.pop("restart_delivery", False))
    _migrate_legacy_confirmed_revision_scope(state)
    _materialize_revision_scope_manifest(state)
    _record_confirmed_extraction_selection(state)
    input_problem = _delivery_input_problem(state, require_selection=True)
    if input_problem:
        if _delivery_variant(state) == "extract_to_new":
            field = "extraction_source" if not isinstance(state.get("extraction_source"), dict) else "extraction_scope"
            question = (
                "请指定要提取的旧 PRD 文件并明确要保留的需求 ID、章节标题或范围。"
                if field == "extraction_source"
                else "请明确旧 PRD 中要提取的需求 ID、章节标题或范围；确认后才会创建新的独立 PRD。"
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
    state["active_delivery_attempt"] = {
        "started_at": state["controller_started_at"],
        "scope_fingerprint": _confirmed_scope_fingerprint(state),
    }
    _checkpoint(state, state_path)

    for artifact in ("confirmed-requirements.md", "prd.md", "run-log.yaml"):
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
    _append_controller_agent_evidence(state)
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
            _finalize_deterministic_trace(folder, checks)
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


def main() -> int:
    _ensure_runtime_current()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", help="initial user request")
    parser.add_argument("--request-file")
    parser.add_argument("--run-folder", type=Path)
    parser.add_argument("--new-requirement", action="store_true", help="create one explicitly new independent requirement")
    parser.add_argument("--revise", action="store_true", help="revise the canonical PRD in --run-folder")
    parser.add_argument("--extract-from", type=Path, help="source Markdown/text PRD for a new extraction delivery")
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
        "--provider", default="auto",
        help="Agent runtime; default auto selects the current device's ready route",
    )
    parser.add_argument("--model", help="explicitly select a model reported by the chosen runtime")
    parser.add_argument("--timeout-minutes", type=int, default=DEFAULT_EXECUTION_TIMEOUT_MINUTES)
    parser.add_argument("--interactive-timeout-minutes", type=int, default=DEFAULT_INTERACTIVE_TIMEOUT_MINUTES,
                        help="aggregate budget for the confirmed delivery workflow")
    parser.add_argument("--max-revisions", type=int, default=DEFAULT_MAX_REVISIONS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.timeout_minutes < 1:
        parser.error("--timeout-minutes must be at least 1")
    if args.interactive_timeout_minutes < 1:
        parser.error("--interactive-timeout-minutes must be at least 1")
    if args.max_revisions < 0:
        parser.error("--max-revisions cannot be negative")
    if args.request_file:
        raw_request = Path(args.request_file).expanduser().read_text(encoding="utf-8").strip()
    else:
        raw_request = (args.request or "").strip()
    if args.new_requirement and args.revise:
        parser.error("--new-requirement and --revise cannot be used together")
    if args.extract_from and args.revise:
        parser.error("--extract-from creates a new PRD and cannot be combined with --revise")
    if args.implemented_evidence and args.revise:
        parser.error("--implemented-evidence creates an implemented-feature PRD and cannot be combined with --revise")
    if args.extract_from and args.implemented_evidence:
        parser.error("--extract-from and --implemented-evidence select different PRD delivery modes")
    if args.revision_requirement_id and args.new_requirement:
        parser.error("--revision-requirement-id is only valid for an existing in-place revision")
    if args.revision_requirement_id and (args.extract_from or args.implemented_evidence):
        parser.error("--revision-requirement-id cannot be combined with a new extraction or implemented-feature PRD")
    if args.revision_requirement_id and not args.run_folder:
        parser.error("--revision-requirement-id requires --run-folder")
    if args.new_requirement and args.run_folder:
        parser.error("--new-requirement creates its own canonical folder; do not pass --run-folder")
    if args.revise and not args.run_folder:
        parser.error("--revise requires --run-folder for the canonical PRD")
    folder = args.run_folder
    if folder is None and raw_request and args.new_requirement:
        try:
            folder = new_requirement_folder(raw_request, resolved_output_root(Path.cwd()))
        except FileExistsError as error:
            parser.error(str(error))
    if folder is None:
        parser.error("provide --run-folder for an existing canonical PRD, or use --new-requirement for a new independent requirement")
    folder = folder.resolve()
    if args.new_requirement and folder.exists():
        parser.error(f"canonical PRD folder already exists: {folder}")
    if not args.new_requirement and not folder.exists():
        parser.error(f"canonical PRD folder not found: {folder}; only --new-requirement may create a PRD folder")
    if args.revise and not folder.is_dir():
        parser.error(f"canonical PRD folder not found: {folder}")
    folder.mkdir(parents=True, exist_ok=True)
    state_path = folder / "interactive-run.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else create_state(raw_request, folder)
    if args.asset:
        resolved_assets = [str(Path(value).expanduser().resolve()) for value in args.asset]
        state["input_assets"] = list(dict.fromkeys([*state.get("input_assets", []), *resolved_assets]))
    if state.get("mode") != "interactive":
        parser.error("run folder is not an interactive production run")
    if _recover_interrupted_delivery(state, folder):
        _write_json(state_path, state)
    delivery_needs_input_field = _confirmed_delivery_needs_input_field(state)
    cli_delivery_input_provided = bool(
        args.extract_from or args.implemented_evidence or args.revision_requirement_id
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
        if not args.new_requirement and _delivery_variant(state) != "extract_to_new":
            parser.error("--extract-from may only start or resume an extraction PRD run")
        try:
            register_extraction_source(state, args.extract_from)
        except (FileNotFoundError, ValueError) as error:
            parser.error(str(error))
    if args.implemented_evidence:
        if not args.new_requirement and delivery_needs_input_field != "implementation_evidence":
            parser.error("--implemented-evidence may only resume a matching implementation-evidence needs_input state")
        if not args.new_requirement and _task_mode(state) != "implemented_feature_prd":
            parser.error("--implemented-evidence may only start or resume an implemented-feature PRD run")
        try:
            register_implemented_feature_evidence(state, args.implemented_evidence)
        except (FileNotFoundError, ValueError) as error:
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


if __name__ == "__main__":
    raise SystemExit(main())
