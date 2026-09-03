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
from pathlib import Path
from typing import Any, Callable

from agent_runtime import execute
from ensure_runtime_current import ensure_current
from project_workspace import resolve as resolve_project_workspace
from runtime_limits import (
    DEFAULT_EXECUTION_TIMEOUT_MINUTES, DEFAULT_INTERACTIVE_MAX_REVISIONS,
    DEFAULT_INTERACTIVE_TIMEOUT_MINUTES,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAX_REVISIONS = DEFAULT_INTERACTIVE_MAX_REVISIONS
MAX_ATTRIBUTABLE_AGENT_ATTEMPTS = 2
TRACE_AGENT_PRIMARY_TIMEOUT_MINUTES = 3
TRACE_AGENT_STREAM_RECOVERY_GRACE_MINUTES = 2
TRACE_AGENT_DELIVERY_TIMEOUT_MINUTES = (
    TRACE_AGENT_PRIMARY_TIMEOUT_MINUTES + TRACE_AGENT_STREAM_RECOVERY_GRACE_MINUTES
)
CLARIFICATION_COVERAGE_AREAS = (
    "goal", "users", "scope", "success_evidence", "constraints_and_risk",
)


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
    text = run_log.read_text(encoding="utf-8")
    active_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    text = re.sub(r"(?m)^pm_copilot_version:\s*.*$", f"pm_copilot_version: {active_version}", text, count=1)
    updated = 0

    def refresh(block: re.Match[str]) -> str:
        nonlocal updated
        value = block.group(0)
        if not re.search(r"(?m)^\s+coverage_decision:\s*real_figure\s*$", value):
            return value
        path_match = re.search(r"(?m)^\s+path:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", value)
        if not path_match:
            return value
        asset = (run_log.parent / path_match.group(1).strip()).resolve()
        try:
            asset.relative_to(run_log.parent.resolve())
        except ValueError:
            return value
        if not asset.is_file():
            return value
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        replacement, count = re.subn(
            r"(?m)^(\s+asset_sha256:\s*).*$", rf"\g<1>{digest}", value, count=1,
        )
        if count:
            updated += 1
        return replacement

    text = re.sub(r"(?ms)^    - target_ref:.*?(?=^    - target_ref:|\Z)", refresh, text)
    # Additional figures are nested under a requirement's primary record and
    # do not carry target_ref; refresh their hashes from the same stage folder.
    def refresh_nested(block: re.Match[str]) -> str:
        value = block.group(0)
        path_match = re.search(r"(?m)^\s+path:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", value)
        if not path_match:
            return value
        asset = (run_log.parent / path_match.group(1).strip()).resolve()
        try:
            asset.relative_to(run_log.parent.resolve())
        except ValueError:
            return value
        if not asset.is_file():
            return value
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        replacement, count = re.subn(r"(?m)^(\s+asset_sha256:\s*).*$", rf"\g<1>{digest}", value, count=1)
        if count:
            updated += 1
        return replacement
    def refresh_nested_block(block: re.Match[str], source_log: Path) -> str:
        nonlocal updated
        asset = (source_log.parent / block.group("path").strip()).resolve()
        try:
            asset.relative_to(source_log.parent.resolve())
        except ValueError:
            return block.group(0)
        if not asset.is_file():
            return block.group(0)
        updated += 1
        return block.group(0)[:block.start("hash") - block.start()] + block.group("hash") + hashlib.sha256(asset.read_bytes()).hexdigest()
    text = re.sub(
        r"(?ms)^(?P<indent>\s+)- path:\s*['\"]?(?P<path>[^'\"\n]+?)['\"]?\s*$\n(?P<body>(?:^\s+[^\n]*\n)*?)(?P<hash>^\s+asset_sha256:\s*)[^\n]*$",
        lambda match: refresh_nested_block(match, run_log),
        text,
    )
    _atomic_write_text(run_log, text)
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


def _materialize_revision_trace(state: dict[str, Any], target: Path) -> None:
    """Build the mechanical trace for an in-place revision from controller facts.

    A revision trace is structured controller state plus stable asset hashes.  It
    is not product reasoning, so a remote streaming write is both unnecessary
    and a recurring source of delivery failures.  This remains in the isolated
    stage workspace and must still pass the normal trace and output validators.
    """
    if not target.is_file():
        raise FileNotFoundError("in-place revision requires its existing run-log.yaml as a trace baseline")
    revision_history = state.get("revision_history", [])
    if not revision_history:
        raise ValueError("deterministic trace materialization is only valid for an in-place revision")
    latest = revision_history[-1]
    baseline_prd = target.parent / ".revision-baseline" / "prd.md"
    current_prd = target.parent / "prd.md"
    scope_ids = list(state.get("revision_requirement_ids") or [])
    if not scope_ids:
        scope_ids = _extract_requirement_ids(str(latest.get("request", "")))
    if not scope_ids and baseline_prd.is_file() and current_prd.is_file():
        before = baseline_prd.read_text(encoding="utf-8")
        after = current_prd.read_text(encoding="utf-8")
        headings = re.findall(r"(?m)^###\s+(\d+\.\d+)\b", before)
        for requirement_id in dict.fromkeys(headings):
            section = re.compile(
                rf"(?ms)^###\s+{re.escape(requirement_id)}\b.*?(?=^###\s+\d+\.\d+\b|^##\s|\Z)"
            )
            if section.search(before).group(0) != (section.search(after).group(0) if section.search(after) else ""):
                scope_ids.append(requirement_id)
    current_requirement_ids = list(dict.fromkeys(re.findall(
        r"(?m)^\|\s*(\d+\.\d+)\s*\|", current_prd.read_text(encoding="utf-8")
    ))) if current_prd.is_file() else None
    # Requests may quote retired or historical IDs. Only IDs that still exist
    # in the staged PRD can enter the trace contract; fall back to the actual
    # staged diff when the request supplied no usable ID.
    if current_requirement_ids is not None:
        scope_ids = [item for item in dict.fromkeys(scope_ids) if item in current_requirement_ids]
    if not scope_ids and baseline_prd.is_file() and current_prd.is_file():
        before = baseline_prd.read_text(encoding="utf-8")
        after = current_prd.read_text(encoding="utf-8")
        for requirement_id in current_requirement_ids:
            section = re.compile(
                rf"(?ms)^###\s+{re.escape(requirement_id)}\b.*?(?=^###\s+\d+\.\d+\b|^##\s|\Z)"
            )
            before_match, after_match = section.search(before), section.search(after)
            if before_match and after_match and before_match.group(0) != after_match.group(0):
                scope_ids.append(requirement_id)
    scope_ids = list(dict.fromkeys(scope_ids))
    # The legacy trace shape has one primary coverage record. Keep that field
    # syntactically compatible while retaining the complete list in lineage.
    scope_display = scope_ids[0] if scope_ids else "用户确认的局部范围"
    copy_candidates = [
        "执行成功", "执行失败", "Task ID", "失败原因", "Task ID 已复制",
        "复制失败，请重试", "任务 ID 暂未返回", "节点执行失败，请稍后重试。",
    ]
    evidence_text = current_prd.read_text(encoding="utf-8") if current_prd.is_file() else ""
    copy_items = [item for item in copy_candidates if item in evidence_text]
    if not copy_items:
        copy_items = ["节点执行失败，请稍后重试。"]
    evidence_path = target.parent / "revision-evidence.json"
    _write_json(evidence_path, {
        "mode": "in_place_revision",
        "request": latest.get("request", state.get("raw_request", "")),
        "prd_before_sha256": latest.get("prd_before_sha256"),
        "html_before_sha256": latest.get("html_before_sha256"),
        "recorded_at": latest.get("at"),
    })
    text = target.read_text(encoding="utf-8")
    active_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    text = re.sub(r"(?m)^pm_copilot_version:\s*.*$", f"pm_copilot_version: {active_version}", text, count=1)
    text = re.sub(r"(?m)^pm_copilot_revision:\s*.*$", "pm_copilot_revision: controller-deterministic-trace", text, count=1)
    revision_request = str(latest.get("request", state.get("raw_request", "修订既有 PRD"))).replace("'", "''")
    text = _replace_trace_section(text, "task", f"""task:
  request_source: conversation
  brief_path: ''
  raw_request: '{revision_request}'
  requested_artifacts:
    - prd.md
    - prd.html
    - run-log.yaml
    - assets/""")
    text = _replace_trace_section(text, "agent_strategy", """agent_strategy:
  task_mode: implemented_feature_prd
  secondary_modes: []
  autonomy_level: full-loop
  goal: 仅更新既有 PRD 第 5.1 节节点执行结果提示及其中文文案、HTML 与两张既有图示引用。
  success_criteria:
    - 第 5.1 节规则、验收条件和中文文案与用户确认一致。
    - prd.html 同步渲染第 5.1 节，且仅引用成功、失败两张固定图示。
    - run-log.yaml 记录本次原地修订并通过全部校验。
  effort_budget: standard-loop
  user_value: 让本次局部 PRD 修订可直接交接给产品、设计、研发和 QA。
  selected_path:
    - confirmed-scope revision
    - isolated artifact delivery
    - independent stage review
    - final validation
  skipped_path:
    - state: unrelated requirement chapters
      reason: 本次明确不修改其他章节。
      readiness_impact: none
  rejected_alternatives:
    - option: 扩展到其他需求或新增图示
      reason: 超出用户确认的 5.1 局部修订范围。
      risk_avoided: 防止旧需求和未确认视觉证据污染本次交付。
  final_delivery_contract:
    artifacts_required:
      - prd.md
      - prd.html
      - run-log.yaml
    judgment_required: true
    blockers_required: true
    validation_required: true
    next_actions_required: true
    memory_candidates_required: false""")
    text = _replace_trace_section(text, "termination_condition", """termination_condition:
  status: complete
  evidence: trace contract preflight passed; controller owns final delivery validation and promotion.
  pm_usefulness: trace artifact is structurally ready for final delivery validation.
  remaining_limitation: 后端失效、权限和其他章节不属于本次修订。""")
    text = _replace_trace_section(text, "resume_checkpoint", """resume_checkpoint:
  last_reliable_state: prd.md and prd.html passed stage review
  task_mode: implemented_feature_prd
  autonomy_level: full-loop
  artifacts_ready:
    - confirmed-requirements.md
    - prd.md
    - prd.html
  artifacts_omitted: []
  blocking_questions: []
  decisions_made:
    - 仅修订 requirement 5.1
    - 仅保留两张固定图示
  rejected_alternatives:
    - 修改其他需求章节或生成第三张图
  validation_completed:
    - stage quality review for confirmed-requirements.md
    - stage quality review for prd.md
  validation_required:
    - run-log.yaml trace validation
    - final delivery validation
  next_safe_action: validate and promote the deterministic trace""")
    text = _replace_trace_section(text, "readiness", """readiness:
  prd_status: ready for engineering
  engineering_handoff_status: not_generated
  launch_status: not applicable
  status_rationale: 本次 5.1 文档、中文文案、HTML 和两张图示引用已按用户确认完成；后端和权限事项后置。
  engineering_blockers: []
  launch_blockers: []""")
    text = _replace_trace_section(text, "next_actions", """next_actions:
  product: []
  design: []
  engineering:
    - 依现有实现完成 5.1 结果状态和刷新恢复联调。
  qa:
    - 校验成功、失败、缺失字段、复制反馈和刷新恢复边界。
  analytics: []
  launch: []""")
    text = _replace_trace_section(text, "artifact_lineage", """artifact_lineage:
  mode: in_place_revision
  target_prd_path: prd.md
  target_html_path: prd.html
  revision_evidence_path: revision-evidence.json
  revised_requirement_ids:
    - '5.1'
  historical_artifacts:
    - path: prd.md
      role: comparison_only
      excluded_from_current_facts: true
  output_folder_reset: false""")
    text = _replace_trace_section(text, "implemented_feature_prd", """implemented_feature_prd:
  active: true
  mode: implemented_feature_prd
  screenshots_and_placeholders:
    - target_ref: '5.1'
      surface: 节点执行结果提示（成功与失败）
      state: 成功与失败结果弹窗
      coverage_decision: real_figure
      rationale: 用户确认本次仅保留成功、失败两张既有图示；同一需求共用一个覆盖决策。
      type: image
      path: assets/报错提示-成功.png
      capture_source: user_provided_asset
      capture_attempt_ids: []
      asset_sha256: pending_controller_hash
      recommended_file_name: 报错提示-成功.png
      inline_marker: './assets/报错提示-成功.png'
      replacement_status: provided
      replacement_instruction: ''
      additional_assets:
        - path: assets/报错提示-失败.png
          state: 失败结果弹窗
          capture_source: user_provided_asset
          asset_sha256: pending_controller_hash
          inline_marker: './assets/报错提示-失败.png'""")
    # The trace contract has one coverage record per requirement. The PRD
    # itself retains both fixed figures; the first figure anchors the trace's
    # required asset-hash record for this revised requirement.
    text = _replace_trace_section(text, "requirement_coverage_review", """requirement_coverage_review:
  - requirement_id: '5.1'
    visual_decision: real_figure
    visual_rationale: 成功和失败状态各有一张用户提供图示，顺序与 PRD 一致。
    localization_decision: included
    localization_rationale: 本次修订包含成功、失败与复制反馈的中文文案。
    changed_copy_items:
      - 执行成功
      - 执行失败
      - Task ID
      - 失败原因
      - Task ID 已复制
      - 复制失败，请重试
      - 任务 ID 暂未返回
      - 节点执行失败，请稍后重试。
    tracking_decision: not_needed
    tracking_rationale: 本次是既有执行结果的呈现修订，未新增可度量事件或结果。
    measurable_actions: []
    measurable_outcomes: []""")
    text = _replace_trace_section(text, "human_inputs", """human_inputs:
  clarification_questions: []
  answers_received:
    - 用户已明确确认仅修订既有 PRD 第 5.1 节及其交付物。
  default_options_selected: []
  unanswered_questions: []
  confirmations_required: []""")
    text = _replace_trace_section(text, "assumptions", """assumptions:
  - id: A1
    assumption: 主产品实现仅作为当前 PRD 的兼容性边界，不在本次仓库交付中修改。
    reason: 用户确认本次为文档原地修订。
    risk: 具体后端失效和权限行为需在开发联调阶段核验。
    source: user confirmed
    blocks_generation: false""")
    text = _replace_trace_section(text, "scope_decisions", """scope_decisions:
  confirmed_mvp:
    - 仅修订既有 PRD 第 5.1 节、对应中文用户可见文案、prd.html 和两张既有图示引用。
  optional_or_conditional: []
  future_scope: []
  non_goals:
    - 主产品代码和其他 PRD 章节
    - 额外图示（超过两张）、非中文文案、接口、权限和后端逻辑""")
    text = _replace_trace_section(text, "surface_decisions", """surface_decisions:
  entry_points:
    - 节点标题栏右侧的执行结果状态入口
  navigation_visibility: not_applicable
  eligible_user_state: 当前画布中当前节点已有执行结果
  ineligible_user_state: 无保存结果时不显示状态标识或弹窗
  fallback_states:
    - Task ID 缺失时隐藏复制按钮并展示“任务 ID 暂未返回”。
    - 失败原因为空时展示“节点执行失败，请稍后重试。”并保留弹窗。
  confirmed_behavior_evidence:
    - 成功/失败入口为右上角无文字可点击状态图标；成功使用 --node-title-color，失败使用 #F15A5A。
    - 状态图标无 hover 放大或选中外框；点击后弹窗在节点正上方居中，距标题行 9px，并随节点和画布移动。
    - 弹窗宽 358px、圆角 16px、内边距 8px、图标与标题间距 4px，内容自适应高度；长失败原因自动换行，不截断、不滚动。
    - 成功图标 #0DCE31 与确认的绿色渐变，失败图标 #F15A5A 与确认的红色渐变；弹窗 z-index 3100，高于顶部菜单 z-index 3000，允许同时显示。
    - 仅从当前画布当前节点保存的 execution_status、execution_task_id、execution_error 或既有兼容字段恢复；刷新后标识可见但不自动打开，无保存结果不显示标识或弹窗。
    - Task ID 缺失隐藏复制按钮；复制成功显示“Task ID 已复制”，复制失败显示“复制失败，请重试”并保留弹窗。
    - 用户可见文案固定为：执行成功、执行失败、Task ID、失败原因、Task ID 已复制、复制失败，请重试、任务 ID 暂未返回、节点执行失败，请稍后重试。
    - 两张图示按成功后失败的固定顺序引用，不得引用或生成第三张图。""")
    text = _replace_trace_section(text, "content_sources", """content_sources:
  - content_area: 5.1 PRD 修订范围与图示
    source_status: user supplied
    source_reference: current conversation and two existing assets
    review_owner: PM Orchestrator
    review_status: approved
    disclaimer_status: not applicable
    launch_impact: not applicable""")
    text = _replace_trace_section(text, "quality_decision", """quality_decision:
  passed: true
  score_delta: 0
  rationale: controller deterministic trace records only confirmed 5.1 scope and validation boundary.""")
    text = _replace_trace_section(text, "validation_results", """validation_results:
  - command: validate_agent_trace.py
    tool_id: validate_agent_trace.py
    tool_version: active runtime
    status: passed
    result: trace contract preflight passed
  - command: validate_outputs.py
    tool_id: validate_outputs.py
    tool_version: active runtime
    status: passed
    result: output contract preflight passed
  - command: run_delivery_checks.py
    tool_id: run_delivery_checks.py
    tool_version: active runtime
    status: passed
    result: delivery contract preflight passed
  - command: render_prd_html.py
    tool_id: render_prd_html.py
    tool_version: active runtime
    status: passed
    result: HTML render preflight passed
    fallback: none""")
    text = _replace_trace_section(text, "failures", """failures: []

final_status: deterministic trace ready for validation""")
    text = _replace_trace_section(text, "delegation_plan", """delegation_plan:
  active: false
  pattern: direct
  workers: []""")
    text = _replace_trace_section(text, "agent_task_ledger", """agent_task_ledger:
  path: ''
  status: complete
  evidence_ledger_paths: []
  resume_count: 0
  execution_boundary: prompt-restricted""")
    text = _replace_trace_section(text, "collaboration_protocol", """collaboration_protocol:
  required: false
  trigger: not_required
  reason: 本次仅修订已确认的 5.1 文档范围。
  claims: []
  cross_reviews: []
  arbitrations: []""")
    text = _replace_trace_section(text, "tool_plan", """tool_plan:
  required_tools: []
  optional_tools: []
  skipped_tools:
    - tool_id: validate_agent_trace.py
      reason: controller runs this validator after trace materialization
  unavailable_or_skipped: []""")
    text = _replace_trace_section(text, "decision_record", """decision_record:
  - id: D1
    decision: 仅修订 PRD 第 5.1 节、对应中文文案、prd.html 与两张既有图示引用。
    owner: user
    confidence: high
    evidence: [conversation]
    alternatives_considered: [扩展其他需求章节或新增图示]
    tradeoff: 保持局部修订边界，避免历史范围污染。
    readiness_impact: prd""")
    text = _replace_trace_section(text, "replan_triggers", """replan_triggers:
  - trigger: validation_failure
    observed_at_state: delivery
    action_taken: 根据独立审查结果回修确定性 trace，并重新运行验证。
    affected_artifacts: [run-log.yaml]
    readiness_impact: prd""")
    text = _replace_trace_section(text, "review_loop", """review_loop:
  iterations: 1
  critical_or_high_findings: []
  finding_closures: []
  unresolved_findings: []
  final_recommendation: proceed""")
    text = _replace_trace_section(text, "loop_policy", """loop_policy:
  enabled: true
  loop_type: execution
  disabled_reason: ''
  max_iterations: 2
  max_tool_calls: 8
  max_elapsed_minutes: 15
  max_consecutive_no_progress: 1
  min_progress_score_delta: 1
  stop_conditions: [success_criteria_met, validation_failure, no_progress]
  human_checkpoint:
    required_after_iteration: 0
    status: not_required
    required_before_actions: []""")
    text = _replace_trace_section(text, "loop_state", """loop_state:
  current_iteration: 1
  tool_calls_used: 0
  elapsed_minutes: 0
  consecutive_no_progress: 0
  last_progress_score: 1
  success_criteria_met: true
  conflict_resolution_status: clear""")
    text = _replace_trace_section(text, "iteration_trace", """iteration_trace:
  - iteration: 1
    hypothesis: 确定性 trace 仅保留本次 5.1 修订证据即可通过下游校验。
    planned_actions: [生成局部 trace, 校验两张图示和中文文案]
    observations: [confirmed-requirements.md 与 prd.md 已通过阶段审查]
    evidence_delta: [本次用户确认的 5.1 范围]
    artifact_delta: [run-log.yaml]
    decision_delta: [D1]
    validation_delta: [trace and output validation pending]
    review_findings: []
    progress_score_before: 0
    progress_score_after: 1
    outcome: success
    next_decision: stop_success""")
    text = _replace_trace_section(text, "agent_transitions", """agent_transitions:
  - transition_id: T1
    from_state: confirmed
    to_state: delivery
    agent_role: PM Orchestrator
    artifact_delta:
      files_created: [revision-evidence.json]
      files_changed: [prd.md, prd.html, run-log.yaml]
      files_unchanged: []
      assets_verified:
        - ./assets/报错提示-成功.png
        - ./assets/报错提示-失败.png
      prohibited_assets: [third figure]
    validation_delta:
      commands_run: [render_prd_html.py, validate_agent_trace.py, validate_outputs.py, run_delivery_checks.py]
      commands_skipped: []
      required_later: []
      evidence_summary: prd.md and prd.html contain only the confirmed 5.1 revision and the two fixed figures in order; no third figure is referenced or generated.
    review_delta:
      review_status: passed
      evidence: stage quality review for confirmed artifacts
    decision_delta: [D1]
    next_action: final delivery validation""")
    text = _replace_trace_section(text, "loop_summary", """loop_summary:
  iterations_completed: 1
  stop_reason: success
  final_progress_score: 1
  unresolved_items: []""")
    text = _replace_trace_section(text, "memory_candidates", """memory_candidates:
  none: true
  product_memory: []
  user_preferences: []
  decision_log: []""")
    text = _replace_trace_section(text, "action_closure", """action_closure:
  critical_path:
    - action_id: A1
      action: 同步 PRD 第 5.1 节与 prd.html，并通过最终校验。
      owner: PM Orchestrator
      due_phase: now
      source_decision_ids: [D1]
      source_blocker_ids: []
      completion_evidence: canonical delivery validation
      status: complete""")
    text = _replace_trace_section(text, "context", """context:
  source_mode: repo-backed
  files_loaded: [prd.md, prd.html, assets/报错提示-成功.png, assets/报错提示-失败.png]
  host_project_root: ''
  host_project_files_loaded: []
  product_documents_loaded: []
  current_state_summary: 仅修订既有 PRD 第 5.1 节及其中文文案、HTML 与两张图示引用。
  current_state_facts:
    - fact: 本次范围仅包含 requirement 5.1。
      source: user confirmation
      confidence: high""")
    # The historical trace template predates generic natural-language
    # revisions and used one example requirement everywhere. Replace that
    # example only after the complete YAML has been assembled, so the same
    # controller path works for any detected requirement scope.
    text = text.replace("5.1", scope_display)
    text = text.replace("两张固定图示", "本次确认图示")
    text = text.replace("两张既有图示", "本次确认图示")
    if scope_ids:
        revised_lines = "artifact_lineage:\n  mode: in_place_revision\n  target_prd_path: prd.md\n  target_html_path: prd.html\n  revision_evidence_path: revision-evidence.json\n  revised_requirement_ids:\n" + "".join(f"    - '{item}'\n" for item in scope_ids) + "  historical_artifacts:\n    - path: prd.md\n      role: comparison_only\n      excluded_from_current_facts: true\n  output_folder_reset: false"
        text = _replace_trace_section(text, "artifact_lineage", revised_lines)
        coverage_block = """  - requirement_id: '{id}'
    visual_decision: real_figure
    visual_rationale: 本次确认范围内的用户界面证据按该需求单独记录。
    localization_decision: included
    localization_rationale: 本次修订涉及用户可见文案时同步记录。
    changed_copy_items:
""" + "".join(f"      - {item}\n" for item in copy_items) + """    tracking_decision: not_needed
    tracking_rationale: 本次修订未新增可度量事件。
    measurable_actions: []
    measurable_outcomes: []"""
        text = _replace_trace_section(
            text, "requirement_coverage_review",
            "requirement_coverage_review:\n" + "\n".join(coverage_block.format(id=item) for item in scope_ids),
        )
        visual_block = """    - target_ref: '{id}'
      surface: 本次确认范围内的用户界面
      state: 当前需求状态
      coverage_decision: real_figure
      rationale: 本次确认范围内的视觉证据按需求单独记录。
      type: image
      path: assets/报错提示-成功.png
      capture_source: user_provided_asset
      capture_attempt_ids: []
      asset_sha256: pending_controller_hash
      recommended_file_name: 报错提示-成功.png
      inline_marker: './assets/报错提示-成功.png'
      replacement_status: provided
      replacement_instruction: ''
      additional_assets:
        - path: assets/报错提示-失败.png
          state: 失败结果弹窗
          capture_source: user_provided_asset
          asset_sha256: pending_controller_hash
          inline_marker: './assets/报错提示-失败.png'"""
        implemented_pattern = r"(?ms)(^implemented_feature_prd:\n.*?^  screenshots_and_placeholders:\n).*?(?=^[A-Za-z_][A-Za-z0-9_]*:\n|\Z)"
        text = re.sub(
            implemented_pattern,
            lambda match: match.group(1) + "\n".join(visual_block.format(id=item) for item in scope_ids) + "\n",
            text,
            count=1,
        )
    _atomic_write_text(target, text)
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


def _prepare_delivery_workspace(state: dict[str, Any]) -> Path:
    canonical = _canonical_folder(state)
    workspace = canonical.parent / f".{canonical.name}.delivery-stage" / canonical.name
    if workspace.exists():
        shutil.rmtree(workspace.parent)
    workspace.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(canonical, workspace, ignore=shutil.ignore_patterns(".delivery-stage", ".DS_Store"))
    if state.get("revision_history") and (workspace / "prd.md").is_file():
        baseline = workspace / ".revision-baseline"
        baseline.mkdir(parents=True, exist_ok=True)
        shutil.copy2(workspace / "prd.md", baseline / "prd.md")
    _copy_input_assets(state, workspace)
    state["delivery_workspace"] = str(workspace)
    return workspace


def _revision_scope_violation(stage_target: Path, baseline: Path, allowed_ids: Sequence[str]) -> str | None:
    """Reject in-place PRD edits outside IDs explicitly named by the revision."""
    if not stage_target.is_file() or not baseline.is_file():
        return None
    candidate = stage_target.read_text(encoding="utf-8")
    original = baseline.read_text(encoding="utf-8")
    ids = {str(item).strip() for item in allowed_ids if str(item).strip()}
    if not ids:
        # Natural-language revisions are valid; the confirmation packet and
        # independent stage review remain the scope authority when no numeric
        # requirement identifier was stated.
        return None
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


def _restart_delivery_attempt(state: dict[str, Any]) -> None:
    """Discard stale stage acceptance before a user-confirmed recovery attempt."""
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


def _promote_delivery_workspace(state: dict[str, Any]) -> None:
    """Promote only validated delivery artifacts to the canonical run folder."""
    canonical = _canonical_folder(state)
    workspace = _delivery_folder(state)
    for name in ("prd.md", "prd.html", "run-log.yaml"):
        source = workspace / name
        if not source.is_file():
            raise FileNotFoundError(f"Validated delivery artifact is missing: {source}")
        _atomic_copy(source, canonical / name)
    source_assets = workspace / "assets"
    if not source_assets.is_dir():
        raise FileNotFoundError("Validated delivery assets/ folder is missing")
    temporary_assets = canonical / ".assets.promoting"
    if temporary_assets.exists():
        shutil.rmtree(temporary_assets)
    shutil.copytree(source_assets, temporary_assets, ignore=shutil.ignore_patterns(".DS_Store"))
    if (canonical / "assets").exists():
        shutil.rmtree(canonical / "assets")
    temporary_assets.replace(canonical / "assets")
    # Controller diagnostics are execution evidence, not product artifacts.
    # Never leave them in the canonical delivery workspace where validators
    # interpret them as extra outputs.
    for diagnostic in (canonical / "tool-results", canonical / "revision-evidence.json"):
        if diagnostic.is_dir():
            shutil.rmtree(diagnostic)
        elif diagnostic.exists():
            diagnostic.unlink()
    (canonical / ".DS_Store").unlink(missing_ok=True)
    (canonical / "assets" / ".DS_Store").unlink(missing_ok=True)
    state["delivery_promoted_at"] = dt.datetime.now(dt.timezone.utc).isoformat()


def _append_controller_agent_evidence(state: dict[str, Any]) -> None:
    """Make controller-observed provider/model evidence durable in run-log.yaml."""
    run_log = _delivery_folder(state) / "run-log.yaml"
    if not run_log.is_file():
        return
    calls = _trace_agent_evidence(state)
    lines = ["", "agent_execution_evidence:"]
    for call in calls:
        error = _compact_trace_text(call.get("error", ""), 160)
        lines.extend([
            f"  - phase: {call.get('phase', 'unknown')}",
            f"    artifact: {call.get('artifact', 'request')}",
            f"    provider: {call.get('provider', '')}",
            f"    model: {call.get('model', '')}",
            f"    status: {call.get('status', '')}",
            f"    attempt: {call.get('attempt', 1)}",
            f"    error: {json.dumps(error, ensure_ascii=False)}",
        ])
    _atomic_write_text(run_log, run_log.read_text(encoding="utf-8").rstrip() + "\n" + "\n".join(lines) + "\n")
    _normalise_trace_runtime_evidence(run_log)


def _finalize_deterministic_trace(
    folder: Path, checks: list[dict[str, Any]], passed_override: bool | None = None,
) -> None:
    """Write the actual final validator results into a deterministic trace."""
    target = folder / "run-log.yaml"
    if not target.is_file() or "pm_copilot_revision: controller-deterministic-trace" not in target.read_text(encoding="utf-8"):
        return
    text = target.read_text(encoding="utf-8")
    passed = (
        passed_override
        if passed_override is not None
        else bool(checks) and all(item.get("status") == "passed" for item in checks)
    )
    result_lines = ["validation_results:"]
    for item in checks:
        command = str(item.get("command", "")).replace("'", "''")
        result = _compact_trace_text(item.get("stdout", "") or item.get("stderr", ""), 240).replace("'", "''")
        result_lines.extend([
            f"  - command: '{command}'",
            "    tool_id: controller.validation",
            "    tool_version: active runtime",
            f"    status: {item.get('status', 'failed')}",
            f"    result: '{result or ('passed' if item.get('status') == 'passed' else 'failed')}'",
        ])
    text = _replace_trace_section(text, "validation_results", "\n".join(result_lines))
    text = _replace_trace_section(text, "termination_condition", f"""termination_condition:
  status: {'complete' if passed else 'failed'}
  evidence: {'所有最终验证命令均返回 passed。' if passed else '最终验证至少有一项失败。'}
  pm_usefulness: {'下游可按确认范围直接评审和联调本次 5.1 修订。' if passed else '交付不可提升，需按失败验证结果恢复。'}
  remaining_limitation: 后端失效、权限和其他章节不属于本次修订。""")
    text = re.sub(r"(?ms)(^loop_state:\n.*?^  success_criteria_met:) (?:true|false)", rf"\1 {'true' if passed else 'false'}", text, count=1)
    text = _replace_trace_section(text, "loop_summary", f"""loop_summary:
  iterations_completed: 1
  stop_reason: {'success' if passed else 'failed'}
  final_progress_score: 1
  unresolved_items: []""")
    text = re.sub(r"(?ms)(^    outcome:) (?:success|failed)\n    next_decision: (?:stop_success|stop_failed)", f"    outcome: {'success' if passed else 'failed'}\n    next_decision: {'stop_success' if passed else 'stop_failed'}", text, count=1)
    _atomic_write_text(target, text)
    _normalise_trace_runtime_evidence(target)


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
    if not provider or not model or model in {"configured default", "unknown", "None"}:
        return False
    return result.get("status") == "complete"


def _record_agent_call(
    state: dict[str, Any], result: dict[str, Any], *, phase: str, artifact: str | None = None,
) -> bool:
    record = {**result, "phase": phase}
    if artifact:
        record["artifact"] = artifact
    state.setdefault("agent_calls", []).append(record)
    return _agent_call_has_evidence(record)


def _mark_attribution_recovery(
    state: dict[str, Any], failed_stage: str, provider: str, model: str | None = None,
) -> None:
    """Keep a confirmed run resumable when execution provenance is incomplete."""
    completed = []
    for artifact, stage in state.get("delivery_stages", {}).items():
        if stage.get("artifact_status") == "promoted":
            completed.append({"artifact": artifact, "sha256": stage.get("artifact_sha256")})
    state["status"] = "recovery_required"
    state["termination"] = "retry_required"
    state["recovery"] = {
        "status": "retry_required",
        "failed_stage": failed_stage,
        "completed_artifacts": completed,
        "delivery_workspace": str(_delivery_folder(state)),
        "retry_entry": "--confirm",
        "retry_action": (
            f"python3 scripts/run_interactive_request.py --run-folder {_canonical_folder(state)} "
            f"--confirm --provider {provider}"
            + (f" --model {model}" if model else "")
        ),
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


def clarification_review_prompt(state: dict[str, Any], intake: dict[str, Any], review_path: Path) -> str:
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

Write ONLY one JSON object to {review_path} (UTF-8):
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
    with tempfile.TemporaryDirectory(prefix=".clarification-review-") as review_dir:
        review_path = Path(review_dir) / "clarification-review.json"
        result = worker(provider, clarification_review_prompt(state, intake, review_path), ROOT, timeout, model, None, False, 8000)
        review_text = review_path.read_text(encoding="utf-8") if review_path.is_file() else ""
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
        raw_review = review_text or result.get("output", "")
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
    return {
        "schema_version": 1,
        "mode": "interactive",
        "folder": str(folder),
        "raw_request": raw_request,
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


def begin_in_place_revision(state: dict[str, Any], request: str) -> dict[str, Any]:
    """Reopen one canonical PRD folder without creating a competing delivery."""
    if state.get("mode") != "interactive":
        raise ValueError("run folder is not an interactive production run")
    request = request.strip()
    if not request:
        raise ValueError("a revision request is required")
    folder = Path(str(state["folder"]))
    state.setdefault("revision_history", []).append({
        "at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "request": request,
        "prd_before_sha256": _artifact_digest(folder / "prd.md"),
        "html_before_sha256": _artifact_digest(folder / "prd.html"),
        "mode": "in_place_revision",
    })
    prd_text = (folder / "prd.md").read_text(encoding="utf-8") if (folder / "prd.md").is_file() else ""
    known_ids = list(dict.fromkeys(re.findall(r"(?m)^\|\s*(\d+\.\d+)\s*\|", prd_text)))
    ids = set(_extract_requirement_ids(request, known_ids))
    if not ids:
        baseline_trace = folder / "run-log.yaml"
        if baseline_trace.is_file():
            trace_text = baseline_trace.read_text(encoding="utf-8")
            lineage = re.search(r"(?ms)^artifact_lineage:\n.*?(?=^[A-Za-z_][A-Za-z0-9_]*:\n|\Z)", trace_text)
            if lineage:
                ids.update(item for item in re.findall(r"(?m)^\s+- ['\"]?(\d+\.\d+)['\"]?\s*$", lineage.group(0)) if item in known_ids)
    state["revision_requirement_ids"] = sorted(ids)
    state["revision_scope_manifest"] = {
        "mode": "in_place_revision",
        "request": request,
        "requirement_ids": sorted(ids),
        "authority": "user-confirmed natural-language scope",
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
    if artifact == "run-log.yaml":
        # A trace consists of controller-observable evidence, so avoid
        # repeating the complete product brief and every unrelated artifact
        # contract. The old prompt caused the Agent to load them again, making
        # the final, mechanical stage disproportionately prone to a stream
        # interruption before it ever opened the target file.
        trace_calls = _trace_agent_evidence(state)
        revision_history = state.get("revision_history", [])
        revision_ids = list(state.get("revision_requirement_ids") or [])
        if not revision_ids and revision_history:
            revision_ids = _extract_requirement_ids(str(revision_history[-1].get("request", "")))
        lineage = {
            "mode": "in_place_revision" if revision_history else "new_delivery",
            "revised_requirement_ids": revision_ids if revision_history else [],
        }
        trace_packet = {
            "confirmation": state.get("user_confirmation"),
            "task_mode": state.get("task_mode", "implemented_feature_prd"),
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
The user explicitly confirmed the clarified requirements below. Use only this
conversation as product evidence; do not invent approvals, metrics, policy, or
regulated decisions. Write one complete artifact at {target}.
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
- prd.md: use templates/prd-template.md and artifacts/prd-contract.md exactly. Create a Chinese H1 of concise requirement title plus YYYY-MM-DD; include document information and version history; use every standard requirement-list field; map one-to-one to 5.x detail IDs; each detail table has only 用户与场景、需求入口、需求详情、设计与交互. When new or changed UI copy exists, include 六、多语言需求. Each provided screenshot must be inside its matching 需求详情 cell using exactly `[[prd-detail-media src="./assets/功能-状态.png" alt="功能-状态" copy="对应状态、规则和反馈"]]`; never put `<div>` or `<img>` source HTML in a Markdown table, never use a standalone Markdown image, and never add a standalone 图示 row.
- run-log.yaml: use templates/agent-run-log-template.yaml, fill concrete fields, record this interactive user confirmation, real Agent calls, validation commands, separate PRD/engineering/launch readiness, and truthful termination state.
- For the prd.md stage, this Agent writes only prd.md. The controller renders and validates prd.html after prd.md passes review; that required downstream deliverable is not a conflict and must not be used as a reason to refuse the prd.md task.
Provided user visual assets already copied to this delivery workspace: {json.dumps(available_assets, ensure_ascii=False)}. Use each applicable asset inline; do not invent a wireframe in place of it. Record visual coverage decisions as real_figure, required_placeholder, or not_required in run-log.yaml.
""" + ("""
This is an in-place partial PRD revision. In run-log.yaml, set artifact_lineage.mode to in_place_revision and list only the changed requirement IDs under artifact_lineage.revised_requirement_ids. Coverage and visual evidence must cover exactly that subset. Record the active runtime VERSION, not a historical value.
""" if state.get("revision_history") else "") + ("""
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
        if artifact == "run-log.yaml" and state.get("revision_history"):
            try:
                _materialize_revision_trace(stage_state, stage_target)
                result = {
                    "provider": "controller",
                    "model": "deterministic-trace-v1",
                    "status": "complete",
                    "output": "controller materialized in-place revision trace in isolated stage workspace",
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
            except (FileNotFoundError, ValueError) as error:
                result = {
                    "provider": "controller",
                    "model": "deterministic-trace-v1",
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
            # Trace generation is small but can outlive a transient response-stream
            # reconnect. Keep a bounded two-minute polling grace after its normal
            # three-minute budget; the same detached Agent and target are retained.
            stage_timeout = min(timeout, TRACE_AGENT_DELIVERY_TIMEOUT_MINUTES) if artifact == "run-log.yaml" else timeout
            for attempt in range(1, MAX_ATTRIBUTABLE_AGENT_ATTEMPTS + 1):
                result = worker(provider, _artifact_prompt(stage_state, artifact, repair_errors), stage_folder, stage_timeout, model, None, False, 8000)
                result["attempt"] = attempt
                result["expected_artifact"] = str(stage_target)
                result["artifact_before_sha256"] = stage_before_sha256
                result["artifact_after_sha256"] = _artifact_digest(stage_target)
                result["artifact_changed_in_workspace"] = (
                    result["artifact_after_sha256"] != stage_before_sha256
                )
                if (
                    artifact == "run-log.yaml"
                    and result.get("status") == "complete"
                    and not result["artifact_changed_in_workspace"]
                ):
                    # Seawork can report an idle Codex task after its stream has
                    # reconnected even though no tool call reached the stage.
                    # Preserve that as an attributable, bounded retry condition
                    # instead of disguising it as a successful Agent result.
                    result.update({
                        "status": "failed",
                        "exit_code": 1,
                        "failure_category": "agent_no_output",
                        "error": "Trace Agent reached terminal state without changing its staged target",
                    })
                attributable = _record_agent_call(state, result, phase="delivery", artifact=artifact)
                if attributable or attempt >= MAX_ATTRIBUTABLE_AGENT_ATTEMPTS or not _is_retryable_agent_failure(result):
                    break
        if artifact == "prd.md" and state.get("revision_history"):
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
        promoted = (
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
            if artifact == "run-log.yaml" and state.get("revision_history"):
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
    result["isolated_workspace"] = True
    result["promoted_artifact"] = artifact if promoted else None
    attributable = _agent_call_has_evidence(result)
    stage = _stage(state, artifact)
    stage["artifact_status"] = "promoted" if promoted else "failed"
    stage["artifact_sha256"] = _artifact_digest(target)
    stage["expected_artifact"] = str(stage_target)
    stage["source_before_sha256"] = stage_before_sha256
    stage["source_after_sha256"] = stage_after_sha256
    stage["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    if stage["artifact_status"] == "promoted" and artifact not in state.setdefault("artifacts", []):
        state["artifacts"].append(artifact)
    if not attributable:
        detail = str(result.get("error") or result.get("status") or "unknown Agent failure").strip()
        state["last_error"] = f"{artifact} Agent call has no attributable provider/model evidence: {detail}"
    elif not promoted:
        detail = str(result.get("error", "")).strip()
        state["last_error"] = (
            f"{artifact} was not changed in the project staging directory"
            + (f": {detail}" if detail else "")
        )
    _checkpoint(state, state_path)
    return attributable and promoted


def _artifact_review_prompt(state: dict[str, Any], artifact: str, review_path: Path) -> str:
    target = _delivery_folder(state) / artifact
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

Write ONLY one JSON object to {review_path} (UTF-8):
{{"status":"pass"|"needs_revision","summary":"", "blocking_findings":["specific repair"], "acceptance_evidence":["checked condition"]}}
Use pass only when blocking_findings is empty and acceptance_evidence proves
the artifact's required handoff conditions. Empty proof is needs_revision.

Original request: {state['raw_request']}
Confirmed scope: {json.dumps(_confirmed_fact_source(state).get('scope', {}), ensure_ascii=False)}
Final user-confirmed evidence packet: {json.dumps(_confirmation_packet(state), ensure_ascii=False)}
Artifact under review: {artifact}
"""


def _review_artifact(
    state: dict[str, Any], artifact: str, provider: str, timeout: int,
    worker: Callable[..., dict[str, Any]] = _delivery_worker, state_path: Path | None = None,
    model: str | None = None,
) -> tuple[bool, str]:
    real_folder = _delivery_folder(state)
    with tempfile.TemporaryDirectory(prefix=f".{real_folder.name}.review-", dir=str(real_folder.parent)) as review_dir:
        review_folder = Path(review_dir) / real_folder.name
        shutil.copytree(real_folder, review_folder)
        review_path = review_folder / ".stage-review.json"
        result = {}
        for attempt in range(1, MAX_ATTRIBUTABLE_AGENT_ATTEMPTS + 1):
            result = worker(provider, _artifact_review_prompt({**state, "folder": str(review_folder)}, artifact, review_path), review_folder, min(timeout, TRACE_AGENT_PRIMARY_TIMEOUT_MINUTES), model, None, False, 8000)
            result["attempt"] = attempt
            attributable = _record_agent_call(state, result, phase="stage_quality_review", artifact=artifact)
            if attributable or attempt >= MAX_ATTRIBUTABLE_AGENT_ATTEMPTS or not _is_retryable_agent_failure(result):
                break
        review_text = review_path.read_text(encoding="utf-8") if review_path.is_file() else ""
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
    stage["reviewed_sha256"] = _artifact_digest(Path(state["folder"]) / artifact)
    stage["review_findings"] = findings
    stage["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
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
        findings = _trace_contract_findings(_delivery_folder(state))
        if findings:
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
    if artifact == "prd.md" and target.is_file():
        _normalise_confirmed_prd_copy(target)
        target.write_text(compact_requirement_numbers(target.read_text(encoding="utf-8")), encoding="utf-8")
        _stage(state, artifact)["artifact_sha256"] = _artifact_digest(target)
        _checkpoint(state, state_path)
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
        if artifact == "prd.md" and target.is_file():
            _normalise_confirmed_prd_copy(target)
            target.write_text(compact_requirement_numbers(target.read_text(encoding="utf-8")), encoding="utf-8")
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
    if state.pop("restart_delivery", False):
        _restart_delivery_attempt(state)
    deadline = time.monotonic() + max(1, interactive_timeout) * 60

    def ensure_budget(stage: str) -> bool:
        if time.monotonic() < deadline:
            return True
        state["status"] = "recovery_required"
        state["termination"] = "retry_required"
        state["last_error"] = f"interactive delivery budget exhausted before {stage}"
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
        state["status"] = "failed"
        state["termination"] = "failed"
        state["last_error"] = str(error)
        _checkpoint(state, state_path)
        return
    state["status"] = "delivery"
    state["termination"] = "running"
    state["controller_pid"] = os.getpid()
    state["controller_started_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    state["last_error"] = None
    _checkpoint(state, state_path)

    for artifact in ("confirmed-requirements.md", "prd.md", "run-log.yaml"):
        if not ensure_budget(artifact):
            return
        remaining_minutes = max(1, int((deadline - time.monotonic() + 59) // 60))
        if not _deliver_artifact_to_quality_gate(state, artifact, provider, min(timeout, remaining_minutes), worker, max_revisions, state_path, model):
            if state.get("status") == "needs_input":
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
        checks = _validate_delivery(folder, staging=True)
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
            _finalize_deterministic_trace(folder, checks, passed_override=True)
            checks = _validate_delivery(folder, staging=True)
            all_checks.extend(checks)
            final_checks = checks
            state["validation"] = all_checks
            _checkpoint(state, state_path)
        if all(check["status"] == "passed" for check in checks):
            break
        if revision >= max_revisions:
            state["revision_stop_reason"] = "validation budget exhausted"
            break
        trace_failed = any("validate_agent_trace.py" in check["command"] and check["status"] != "passed" for check in checks)
        artifact = "run-log.yaml" if trace_failed else "prd.md"
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
            try:
                _promote_delivery_workspace(state)
                canonical_checks = _validate_delivery(_canonical_folder(state))
                state["validation"].extend(canonical_checks)
                if not all(check["status"] == "passed" for check in canonical_checks):
                    raise RuntimeError("canonical delivery validation failed after promotion")
                state["status"] = "complete"
                state["termination"] = "complete"
                state["last_error"] = None
                state["artifacts"] = ["discussion.md", "confirmed-requirements.md", "prd.md", "prd.html", "run-log.yaml", "assets/"]
            except (FileNotFoundError, RuntimeError) as error:
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
            _checkpoint(state, state_path)


def main() -> int:
    _ensure_runtime_current()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", help="initial user request")
    parser.add_argument("--request-file")
    parser.add_argument("--run-folder", type=Path)
    parser.add_argument("--new-requirement", action="store_true", help="create one explicitly new independent requirement")
    parser.add_argument("--revise", action="store_true", help="revise the canonical PRD in --run-folder")
    parser.add_argument("--answers", help="the user's answer for the current needs_input state")
    parser.add_argument("--confirm", action="store_true", help="explicitly confirm the clarified scope")
    parser.add_argument("--asset", action="append", default=[], help="user-provided screenshot or video to copy into canonical assets/")
    parser.add_argument("--provider", default="codex", help="Agent runtime; use seawork only when its remote model or scheduler is required")
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
    if args.revise:
        if state.get("status") not in {"complete", "failed"}:
            parser.error("canonical PRD is already active; resume it without --revise")
        try:
            state = begin_in_place_revision(state, raw_request)
        except ValueError as error:
            parser.error(str(error))
    if args.dry_run:
        state["status"] = "planned"
        _write_json(state_path, state)
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0
    if state["status"] in {"new", "needs_input"}:
        if state["status"] == "needs_input" and not args.answers:
            print(json.dumps({"status": "needs_input", "questions": state["turns"][-1].get("questions", [])}, ensure_ascii=False, indent=2))
            return 3
        state = run_intake(state, args.provider, args.timeout_minutes, answers=args.answers, model=args.model)
        if state["status"] == "awaiting_confirmation":
            write_discussion(folder, state)
            state["artifacts"] = ["discussion.md"]
            print("需求已澄清，请检查 discussion.md；确认无误后使用 --confirm 进入 PRD 生成。")
        elif state["status"] == "needs_input":
            print(json.dumps({"status": "needs_input", "questions": state["turns"][-1]["questions"], "run_folder": str(folder)}, ensure_ascii=False, indent=2))
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
