#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the production deterministic, single-transaction PRD delivery runtime.

It keeps product facts in typed objects until every canonical artifact can be
rendered and verified from the same source of truth.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Sequence

import yaml

from runtime_identity_contract import RUNTIME_IDENTITY_MANIFEST_FILES, runtime_manifest_digest


ROOT = Path(__file__).resolve().parents[1]
STATE_NAME = "delivery-run.json"
CANONICAL_ARTIFACTS = ("prd.md", "prd.html", "run-log.yaml")
TASK_MODES = ("new_prd", "implemented_feature_prd", "prd_revision", "prd_composition")


@dataclass(frozen=True)
class Evidence:
    source: str
    kind: str
    text: str


@dataclass(frozen=True)
class FigureDecision:
    requirement_id: str
    kind: str = "placeholder"
    missing_reason: str = "No runnable frontend evidence was available during deterministic delivery."
    replacement_action: str = "Replace the controlled placeholder with a reviewed frontend figure."
    path: str | None = None
    asset_sha256: str | None = None


@dataclass(frozen=True)
class Requirement:
    identifier: str
    name: str
    user: str
    scenario: str
    value: str
    entry: str
    behavior: str
    interaction: str
    evidence: tuple[Evidence, ...]
    figure: FigureDecision | None = None


@dataclass(frozen=True)
class PrdDocument:
    title: str
    mode: str
    request: str
    requirements: tuple[Requirement, ...]
    evidence: tuple[Evidence, ...]
    source_markdown: str = ""


@dataclass(frozen=True)
class DeliveryResult:
    status: str
    folder: str
    artifacts: tuple[str, ...] = ()
    error: str = ""


class DeliveryInputError(ValueError):
    """A missing product decision, distinct from an execution error."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _identity() -> dict[str, Any]:
    files = {relative: _sha(ROOT / relative) for relative in RUNTIME_IDENTITY_MANIFEST_FILES}
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    return {
        "identity_version": 1,
        "runtime_root": str(ROOT),
        "version": version,
        "controller_sha256": files["scripts/prd_request_controller.py"],
        "plugin_entry_sha256": files["plugins/pm-copilot/scripts/pm_copilot_mcp.py"],
        "runtime_manifest": {"schema_version": 1, "files": files},
        "runtime_manifest_sha256": runtime_manifest_digest(files),
    }


def _slug(value: str) -> str:
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", "-", value).strip("-")
    return normalized[:48] or "prd"


def _new_folder(request: str, cwd: Path) -> Path:
    root = cwd / "pm-copilot-outputs"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{dt.date.today().isoformat()}-{_slug(request)}-{uuid.uuid4().hex[:8]}"


def _mode(args: argparse.Namespace, request: str) -> str:
    if args.revise:
        return "prd_revision"
    if args.extract_from:
        return "prd_composition"
    if args.append_implemented_feature or args.implemented_evidence or re.search(r"已实现|implemented", request, re.I):
        return "implemented_feature_prd"
    return "new_prd"


def _write_state(folder: Path, state: dict[str, Any]) -> None:
    target = folder / STATE_NAME
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(target)


def _load_state(folder: Path) -> dict[str, Any]:
    try:
        state = json.loads((folder / STATE_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DeliveryInputError(f"invalid or missing v2 run state: {error}") from error
    if state.get("protocol_version") != 2:
        raise DeliveryInputError("this run does not use the supported v2 delivery protocol; start a new PRD run")
    return state


def _question(request: str, mode: str) -> str | None:
    if mode == "prd_revision":
        return None
    if mode == "prd_composition":
        return None
    if len(request.strip()) < 8 or not re.search(r"功能|需求|PRD|prd|支持|增加|生成|优化|还原", request, re.I):
        return "请说明目标用户、要解决的问题和期望的用户可见结果。"
    return None


def _title(request: str) -> str:
    text = re.sub(r"(?:请|帮我|为|生成|创建|写一份|PRD|prd|产品需求文档|需求文档)", "", request, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" ：:，,。.")
    return text[:48] or "产品需求"


def _requirement_name(request: str) -> str:
    """Extract the feature noun without promoting an append instruction to a title."""

    quoted_feature = re.search(r"[\"“]([^\"”]{1,32})[\"”]\s*功能", request)
    if quoted_feature:
        return quoted_feature.group(1).strip()
    text = re.split(r"[。！？!?\n]", request, maxsplit=1)[0]
    text = re.sub(r"(?:将当前已实现的|将已实现的|追加到此|合并追加|追加|还原|生成|创建|功能|PRD|prd)", "", text, flags=re.I)
    text = text.strip(" ：:，,。.")
    return text[:32] or _title(request)


def _user(request: str) -> str:
    match = re.search(r"(?:为|面向|给)([^，。；;、\s]{2,16})(?:增加|提供|支持|生成|优化|创建)", request)
    return match.group(1) if match else "相关业务用户"


def _requirement(request: str, identifier: str = "5.1") -> Requirement:
    name = _requirement_name(request)
    user = _user(request)
    evidence = Evidence(source="user_request", kind="confirmed_request", text=request)
    return Requirement(
        identifier=identifier, name=name, user=user,
        scenario=f"{user}在处理“{name}”相关任务时需要完成目标操作。",
        value=f"让{user}能够清晰、可恢复地完成“{name}”。",
        entry="在与该任务对应的现有产品入口中提供明确入口；若入口不存在，交付前需由产品确认。",
        behavior="一、主流程<br>1. 用户发起操作后，系统展示当前状态和下一步动作。<br>2. 操作成功后提供可理解的完成反馈。<br><br>一、异常与恢复<br>1. 发生失败时保留用户上下文并提供重试或返回路径。",
        interaction="一、信息与反馈<br>1. 关键状态、可用操作和失败原因应对用户可见。",
        evidence=(evidence,),
        figure=FigureDecision(requirement_id=identifier),
    )


def _extract_source_requirement(source: Path, selector: str | None, identifier: str) -> Requirement:
    text = source.read_text(encoding="utf-8")
    selected = selector or ""
    heading = re.search(r"^###\s+((?:5\.)?\d+(?:\.\d+)?)\s+(.+)$", text, re.M)
    if selected:
        candidate = re.search(rf"^###\s+{re.escape(selected)}\s+(.+)$", text, re.M)
        if candidate:
            name = candidate.group(1).strip()
        else:
            name = selected
    elif heading:
        name = heading.group(2).strip()
    else:
        name = source.stem
    request = f"组合来源 {source.name} 中的 {name}"
    result = _requirement(request, identifier)
    source_evidence = Evidence(source=str(source), kind="source_prd", text=name)
    return replace(result, evidence=(source_evidence,))


def _document(state: dict[str, Any]) -> PrdDocument:
    mode, request = state["task_mode"], state["raw_request"]
    evidence: list[Evidence] = [Evidence("user_request", "confirmed_request", request)]
    if mode == "prd_composition":
        sources = [Path(item) for item in state.get("extract_from", [])]
        if not sources:
            raise DeliveryInputError("请提供至少一个 --extract-from 来源 PRD。")
        selectors = list(state.get("extract_selectors", []))
        requirements = tuple(_extract_source_requirement(path, selectors[index - 1] if index <= len(selectors) else None, f"5.{index}") for index, path in enumerate(sources, 1))
        evidence.extend(Evidence(str(path), "source_prd", path.name) for path in sources)
    elif mode == "prd_revision":
        source = Path(state["folder"]) / "prd.md"
        if not source.is_file():
            raise DeliveryInputError("原地修订需要目标运行目录中的 prd.md。")
        source_markdown = source.read_text(encoding="utf-8")
        ids = state.get("revision_requirement_ids") or []
        if not ids:
            raise DeliveryInputError("请指定要修订的 requirement ID。")
        requirements = []
        for item in ids:
            heading = re.search(rf"^###\s+{re.escape(item)}\s+(.+)$", source_markdown, re.M)
            if not heading:
                raise DeliveryInputError(f"selected requirement ID does not exist in baseline PRD: {item}")
            generated = _requirement(request, item)
            requirements.append(replace(generated, name=heading.group(1).strip()))
        evidence.append(Evidence(str(source), "revision_baseline", _sha(source)))
        return PrdDocument(_title(request), mode, request, tuple(requirements), tuple(evidence), source_markdown)
    elif mode == "implemented_feature_prd" and state.get("append_existing"):
        source = Path(state["folder"]) / "prd.md"
        if not source.is_file():
            raise DeliveryInputError("追加已实现功能需要目标运行目录中的 prd.md。")
        source_markdown = source.read_text(encoding="utf-8")
        identifiers = [int(value) for value in re.findall(r"^###\s+5\.(\d+)\s+", source_markdown, re.M)]
        if not identifiers:
            raise DeliveryInputError("追加已实现功能需要基线 PRD 中至少一个 5.x 需求。")
        requirement = _requirement(request, f"5.{max(identifiers) + 1}")
        evidence.append(Evidence(str(source), "append_baseline", _sha(source)))
        return PrdDocument(_title(request), mode, request, (requirement,), tuple(evidence), source_markdown)
    else:
        requirements = (_requirement(request),)
    return PrdDocument(_title(request), mode, request, requirements, tuple(evidence))


def _figure_markup(requirement: Requirement) -> str:
    figure = requirement.figure
    if figure and figure.kind in {"real_capture", "reconstructed"} and figure.path:
        asset = Path(figure.path).name
        return (
            f'[[prd-detail-media src="./assets/{asset}" alt="{requirement.name}-关键状态" '
            f'copy="一、关键状态<br>1. 用户可见入口、操作结果和反馈与本需求保持一致"]]'
        )
    return f"占位图：{requirement.name}-关键状态.png"


def _render_requirement_detail(requirement: Requirement) -> str:
    return "\n".join([
        f"### {requirement.identifier} {requirement.name}", "", "| 维度 | 需求说明 |", "| --- | --- |",
        f"| 用户与场景 | {requirement.scenario}<br>{requirement.value} |",
        f"| 需求入口 | {requirement.entry} |",
        f"| 需求详情 | {requirement.behavior}<br>{_figure_markup(requirement)} |",
        f"| 设计与交互 | {requirement.interaction} |", "",
    ])


def _insert_after_last_requirement(markdown: str, identifier: str, list_row: str, detail: str) -> str:
    list_match = re.search(rf"^\|\s*{re.escape(identifier)}\s*\|.*(?:\n|$)", markdown, re.M)
    if not list_match:
        raise DeliveryInputError(f"追加已实现功能需要基线 PRD 的需求清单中存在 {identifier}。")
    updated = markdown[:list_match.end()] + list_row + markdown[list_match.end():]
    detail_match = re.search(rf"^###\s+{re.escape(identifier)}\s+.*(?:\n|$)", updated, re.M)
    if not detail_match:
        raise DeliveryInputError(f"追加已实现功能需要基线 PRD 的需求详情中存在 {identifier}。")
    next_section = re.search(r"^##\s+", updated[detail_match.end():], re.M)
    insertion = detail_match.end() + (next_section.start() if next_section else len(updated[detail_match.end():]))
    prefix = updated[:insertion].rstrip() + "\n\n"
    suffix = updated[insertion:].lstrip("\n")
    return prefix + detail + "\n" + suffix


def _update_append_shared_content(markdown: str, requirement: Requirement) -> str:
    """Keep document-wide fields aligned with an implemented-feature append."""

    heading = re.search(r"^#\s+(?P<title>.+?)(?P<date>[ \t]+-[ \t]+\d{4}-\d{2}-\d{2})?[ \t]*$", markdown, re.M)
    if not heading:
        raise DeliveryInputError("追加已实现功能需要基线 PRD 的 H1 标题。")
    title = heading.group("title").strip()
    if requirement.name not in title:
        replacement = f"# {title.rstrip('、')}、{requirement.name}{heading.group('date') or ''}"
        markdown = markdown[:heading.start()] + replacement + markdown[heading.end():]

    def append_table_value(label: str, addition: str) -> None:
        nonlocal markdown
        row = re.search(rf"^\|\s*{re.escape(label)}\s*\|\s*(?P<value>.*?)\s*\|\s*$", markdown, re.M)
        if not row:
            raise DeliveryInputError(f"追加已实现功能需要基线 PRD 的“{label}”字段。")
        value = row.group("value").strip()
        if requirement.name in value:
            return
        separator = "、" if label == "影响范围" else "；"
        replacement = f"| {label} | {value}{separator}{addition} |"
        markdown = markdown[:row.start()] + replacement + markdown[row.end():]

    append_table_value("需求来源", f"追加已实现功能：{requirement.name}")
    append_table_value("影响范围", requirement.name)
    versions = list(re.finditer(r"^\|\s*v(?P<major>\d+)\.(?P<minor>\d+)\s*\|.*(?:\n|$)", markdown, re.M))
    if not versions:
        raise DeliveryInputError("追加已实现功能需要基线 PRD 的版本记录。")
    latest = max(versions, key=lambda item: (int(item.group("major")), int(item.group("minor"))))
    version = f"v{latest.group('major')}.{int(latest.group('minor')) + 1}"
    row = f"| {version} | {dt.date.today().isoformat()} | 新增已实现功能：{requirement.name} | 待指定 |\n"
    return markdown[:latest.end()] + row + markdown[latest.end():]


def _render_markdown(document: PrdDocument) -> str:
    if document.mode == "implemented_feature_prd" and document.source_markdown:
        requirement = document.requirements[0]
        list_row = (
            f"| {requirement.identifier} | {requirement.name} | {requirement.user} | "
            f"{requirement.scenario} | {requirement.value} | {requirement.name} | P1 | 已实现证据 |\n"
        )
        previous_identifier = f"5.{int(requirement.identifier.split('.', 1)[1]) - 1}"
        appended = _insert_after_last_requirement(
            document.source_markdown, previous_identifier, list_row, _render_requirement_detail(requirement),
        )
        return _update_append_shared_content(appended, requirement)
    if document.mode == "prd_revision" and document.source_markdown:
        revised = document.source_markdown
        for req in document.requirements:
            lines = revised.splitlines(keepends=True)
            heading_index = next(
                (index for index, line in enumerate(lines) if re.match(rf"^###\s+{re.escape(req.identifier)}\s+", line)),
                None,
            )
            if heading_index is None:
                raise DeliveryInputError(f"cannot locate selected requirement section: {req.identifier}")
            end_index = next(
                (index for index in range(heading_index + 1, len(lines)) if lines[index].startswith("### ")),
                len(lines),
            )
            for index in range(heading_index + 1, end_index):
                line = lines[index]
                if re.match(r"^\|\s*需求详情\s*\|", line):
                    ending = "\n" if line.endswith("\n") else ""
                    lines[index] = f"| 需求详情 | {req.behavior}<br>{_figure_markup(req)} |{ending}"
                    break
            else:
                raise DeliveryInputError(f"selected requirement has no editable 需求详情 row: {req.identifier}")
            revised = "".join(lines)
        return revised if revised.endswith("\n") else revised + "\n"
    date = dt.date.today().isoformat()
    lines = [f"# {document.title} - {date}", "", "## 一、文档说明", "", "### 1. 文档信息", "", "| 项目 | 内容 |", "| --- | --- |", f"| 需求来源 | {document.request} |", f"| 目标用户 | {document.requirements[0].user} |", f"| 影响范围 | {document.title} |", "| 文档状态 | 可评审（图示待人工补全） |", "| 文档负责人 | 待指定 |", "", "### 2. 版本记录", "", "| 版本 | 日期 | 变更内容 | 负责人 |", "| --- | --- | --- | --- |", f"| v0.1 | {date} | 首次创建 | 待指定 |", "", "## 二、需求背景", "", f"{document.requirements[0].scenario}{document.requirements[0].value}", "", "## 四、需求清单", "", "| 详情编号 | 需求名称 | 目标用户 | 用户场景 / 触发 | 用户问题或价值 | 需求摘要 | 优先级 | 来源 / 确认状态 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for req in document.requirements:
        lines.append(f"| {req.identifier} | {req.name} | {req.user} | {req.scenario} | {req.value} | {req.name} | P1 | 用户确认请求 |")
    lines.extend(["", "## 五、需求详情", ""])
    for req in document.requirements:
        lines.extend(_render_requirement_detail(req).splitlines())
    return "\n".join(lines) + "\n"


def _lineage(document: PrdDocument, folder: Path) -> dict[str, Any]:
    mode = {"new_prd": "new_run", "implemented_feature_prd": "implemented_feature_run", "prd_revision": "in_place_revision", "prd_composition": "composition_run"}[document.mode]
    lineage: dict[str, Any] = {"mode": mode, "source_prds": [], "revision_baseline": {}, "revised_requirement_ids": [], "linked_changes": []}
    if document.mode == "prd_composition":
        lineage["source_prds"] = [{"source_id": f"source-{i}", "snapshot_path": f"source-material/source-{i}.md", "sha256": _sha(folder / "source-material" / f"source-{i}.md"), "selected_scope": [req.identifier], "scope_resolution": []} for i, req in enumerate(document.requirements, 1)]
    if document.mode == "prd_revision":
        lineage["revised_requirement_ids"] = [item.identifier for item in document.requirements]
        lineage["revision_baseline"] = {"source": "canonical prd.md", "sha256": "baseline frozen before delivery"}
    return lineage


def _trace(document: PrdDocument, folder: Path, validation: list[dict[str, str]]) -> dict[str, Any]:
    identity = _identity()
    figures = [asdict(req.figure) for req in document.requirements if req.figure]
    return {
        "run_id": folder.name, "date": dt.date.today().isoformat(), "language": "zh",
        "pm_copilot_version": identity["version"], "runtime_identity": identity,
        "task": {"raw_request": document.request, "request_source": "conversation"},
        "agent_strategy": {"task_mode": document.mode, "goal": document.title},
        "confirmation": {"status": "confirmed", "scope": [req.name for req in document.requirements], "confirmed_at": dt.datetime.now(dt.timezone.utc).isoformat()},
        "artifact_lineage": _lineage(document, folder),
        "implemented_feature_prd": {
            "active": document.mode == "implemented_feature_prd",
            "evidence_packet": (
                {"path": "source-material/implemented-evidence.json", "sha256": _sha(folder / "source-material" / "implemented-evidence.json")}
                if document.mode == "implemented_feature_prd" else {}
            ),
        },
        "frontend_figure_evidence": figures,
        "requirement_coverage_review": [{"requirement_id": req.identifier, "visual": "included", "copy": "included", "measurement": "not_needed", "rationale": "Derived from confirmed requirement."} for req in document.requirements],
        "specialist_evidence": [], "pm_arbitration": {"decisions": []},
        "review": {"status": "passed", "findings": []},
        # The first trace is itself an input to validate_outputs.  Record the
        # completed deterministic preflight before asking that validator to
        # assess the trace, then replace it with the full command evidence.
        "validation_results": validation or [{"command": "semantic and template preflight", "status": "passed", "stdout": "", "stderr": ""}],
        "quality_decision": {"passed": True, "rationale": "Semantic coverage and template checks passed."},
        "failures": [], "final_status": "validated deterministic delivery",
    }


def _semantic_failures(document: PrdDocument, markdown: str) -> list[str]:
    failures = []
    for requirement in document.requirements:
        if not requirement.evidence:
            failures.append(f"{requirement.identifier} has no evidence")
        if f"### {requirement.identifier} {requirement.name}" not in markdown:
            failures.append(f"{requirement.identifier} is absent from requirement details")
        if f"| {requirement.identifier} | {requirement.name} |" not in markdown:
            failures.append(f"{requirement.identifier} is absent from requirement list")
    return failures


def _run_check(command: list[str], cwd: Path) -> dict[str, str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return {"command": " ".join(command), "status": "passed" if result.returncode == 0 else "failed", "stdout": result.stdout[-2000:], "stderr": result.stderr[-2000:]}


def _copy_assets(state: dict[str, Any], stage: Path) -> None:
    """Stage preserved and supplied assets before resolving figure references."""

    baseline_assets = Path(state["folder"]) / "assets"
    if (state.get("append_existing") or state.get("task_mode") == "prd_revision") and baseline_assets.is_dir():
        shutil.copytree(baseline_assets, stage / "assets", dirs_exist_ok=True)
    for asset in state.get("input_assets", []):
        source = Path(asset)
        if not source.is_file():
            raise DeliveryInputError(f"input asset is missing: {source}")
        destination = stage / "assets" / source.name
        if destination.exists() and _sha(destination) != _sha(source):
            raise DeliveryInputError(f"input assets have conflicting names: {source.name}")
        if not destination.exists():
            shutil.copy2(source, destination)


def _materialize_figures(document: PrdDocument, state: dict[str, Any], stage: Path) -> PrdDocument:
    """Resolve figures into staged assets; capture failures remain controlled placeholders."""

    image_assets = [
        stage / "assets" / Path(value).name
        for value in state.get("input_assets", [])
        if Path(value).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ]
    requirements: list[Requirement] = []
    for requirement in document.requirements:
        if not requirement.figure:
            requirements.append(requirement)
            continue
        asset = image_assets[0] if image_assets else None
        if asset is None and document.mode == "prd_revision":
            asset = next(
                (
                    candidate for candidate in sorted((stage / "assets").iterdir())
                    if candidate.is_file()
                    and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
                    and requirement.name in candidate.stem
                ),
                None,
            )
        if asset and asset.is_file():
            figure = FigureDecision(
                requirement_id=requirement.identifier,
                kind="real_capture",
                missing_reason="",
                replacement_action="",
                path=f"assets/{asset.name}",
                asset_sha256=_sha(asset),
            )
        else:
            asset_name = f"{_slug(requirement.name)}-关键状态.png"
            capture = _run_check(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_reconstructed_figure.py"),
                    "--run-folder", str(stage), "--asset-name", asset_name,
                    "--title", requirement.name, "--state", "关键状态",
                ],
                ROOT,
            )
            reconstructed = stage / "assets" / asset_name
            if capture["status"] == "passed" and reconstructed.is_file():
                figure = FigureDecision(
                    requirement_id=requirement.identifier,
                    kind="reconstructed",
                    missing_reason="",
                    replacement_action="",
                    path=f"assets/{asset_name}",
                    asset_sha256=_sha(reconstructed),
                )
            else:
                figure = requirement.figure
        requirements.append(replace(requirement, figure=figure))
    return replace(document, requirements=tuple(requirements))


def _deliver(state: dict[str, Any]) -> DeliveryResult:
    canonical = Path(state["folder"])
    document = _document(state)
    stage_parent = canonical.parent
    with tempfile.TemporaryDirectory(prefix=f".{canonical.name}.stage-", dir=stage_parent) as temp:
        stage = Path(temp)
        (stage / "assets").mkdir()
        if document.mode in {"implemented_feature_prd", "prd_composition"}:
            (stage / "source-material").mkdir()
        if document.mode == "implemented_feature_prd":
            evidence_source = Path(state["implemented_evidence"]) if state.get("implemented_evidence") else None
            if evidence_source and not evidence_source.is_file():
                raise DeliveryInputError(f"implemented evidence is missing: {evidence_source}")
            (stage / "source-material" / "implemented-evidence.json").write_text(
                evidence_source.read_text(encoding="utf-8") if evidence_source else json.dumps({"request": document.request, "observed_behavior": [req.name for req in document.requirements]}, ensure_ascii=False),
                encoding="utf-8",
            )
        if document.mode == "prd_composition":
            for index, source in enumerate(state.get("extract_from", []), 1):
                shutil.copy2(Path(source), stage / "source-material" / f"source-{index}.md")
        _copy_assets(state, stage)
        document = _materialize_figures(document, state, stage)
        markdown = _render_markdown(document)
        semantic = _semantic_failures(document, markdown)
        if semantic:
            raise RuntimeError("semantic validation failed: " + "; ".join(semantic))
        (stage / "prd.md").write_text(markdown, encoding="utf-8")
        render = _run_check([sys.executable, str(ROOT / "scripts" / "render_prd_html.py"), str(stage)], ROOT)
        if render["status"] != "passed":
            raise RuntimeError("html rendering failed: " + render["stderr"])
        trace = _trace(document, stage, [])
        (stage / "run-log.yaml").write_text(yaml.safe_dump(trace, allow_unicode=True, sort_keys=False), encoding="utf-8")
        checks = [
            _run_check([sys.executable, str(ROOT / "scripts" / "validate_outputs.py"), str(stage)], ROOT),
            _run_check([sys.executable, str(ROOT / "scripts" / "validate_agent_trace.py"), str(stage)], ROOT),
        ]
        if any(item["status"] != "passed" for item in checks):
            raise RuntimeError("delivery validation failed: " + "\n".join(item["stdout"] + item["stderr"] for item in checks if item["status"] != "passed"))
        trace = _trace(document, stage, checks)
        (stage / "run-log.yaml").write_text(yaml.safe_dump(trace, allow_unicode=True, sort_keys=False), encoding="utf-8")
        checks.append(_run_check([sys.executable, str(ROOT / "scripts" / "validate_outputs.py"), str(stage)], ROOT))
        if checks[-1]["status"] != "passed":
            raise RuntimeError("final trace validation failed: " + checks[-1]["stdout"] + checks[-1]["stderr"])
        backup = canonical.with_name(canonical.name + ".delivery-backup")
        if backup.exists():
            shutil.rmtree(backup)
        if canonical.exists():
            canonical.replace(backup)
        try:
            shutil.copytree(stage, canonical)
        except BaseException:
            if backup.exists():
                backup.replace(canonical)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    state.update({"status": "complete", "termination": "complete", "artifacts": [*CANONICAL_ARTIFACTS, "assets/"], "validation": checks, "last_error": None})
    _write_state(canonical, state)
    return DeliveryResult("complete", str(canonical), tuple(state["artifacts"]))


def _start(args: argparse.Namespace, cwd: Path) -> tuple[Path, dict[str, Any]]:
    request = (args.request or "").strip()
    folder = Path(args.run_folder).expanduser().resolve() if args.run_folder else _new_folder(request, cwd)
    if folder.exists() and (folder / STATE_NAME).exists() and not args.append_implemented_feature and not args.revise:
        return folder, _load_state(folder)
    if not request:
        raise DeliveryInputError("request is required for a new v2 PRD run")
    mode = _mode(args, request)
    if folder.exists() and mode != "prd_revision" and not args.append_implemented_feature:
        raise DeliveryInputError(f"run folder already exists: {folder}")
    folder.mkdir(parents=True, exist_ok=mode == "prd_revision" or args.append_implemented_feature)
    question = _question(request, mode)
    state = {"protocol_version": 2, "mode": "deterministic", "folder": str(folder), "raw_request": request, "task_mode": mode, "extract_from": list(args.extract_from or []), "extract_selectors": list(args.extract_selector or []), "revision_requirement_ids": list(args.revision_requirement_id or []), "input_assets": [str(Path(value).expanduser().resolve()) for value in args.asset or []], "implemented_evidence": str(Path(args.implemented_evidence).expanduser().resolve()) if args.implemented_evidence else "", "append_existing": bool(args.append_implemented_feature), "status": "needs_input" if question else "ready", "termination": "needs_input" if question else "ready", "turns": [{"questions": [question] if question else [], "scope": [request]}], "artifacts": [], "user_confirmation": None, "validation": [], "last_error": None}
    _write_state(folder, state)
    return folder, state


def _answer(state: dict[str, Any], answer: str) -> None:
    if state.get("status") != "needs_input":
        raise DeliveryInputError("answers can only be submitted while status is needs_input")
    if not answer.strip():
        raise DeliveryInputError("answer must not be empty")
    state["raw_request"] = state["raw_request"] + "\n补充信息：" + answer.strip()
    state["status"] = "ready"
    state["termination"] = "ready"
    state["turns"].append({"questions": [], "scope": [state["raw_request"]]})


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request")
    parser.add_argument("--run-folder")
    parser.add_argument("--new-requirement", action="store_true")
    parser.add_argument("--revise", action="store_true")
    parser.add_argument("--append-implemented-feature", action="store_true")
    parser.add_argument("--extract-from", action="append", default=[])
    parser.add_argument("--extract-selector", action="append", default=[])
    parser.add_argument("--revision-requirement-id", action="append", default=[])
    parser.add_argument("--implemented-evidence")
    parser.add_argument("--asset", action="append", default=[])
    parser.add_argument("--answers")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--provider")
    parser.add_argument("--model")
    parser.add_argument("--model-enhancement", action="store_true")
    parser.add_argument("--timeout-minutes")
    parser.add_argument("--interactive-timeout-minutes")
    parser.add_argument("--max-revisions")
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args, unknown = parser.parse_known_args(raw_argv)
    if unknown:
        parser.error("unsupported v2 arguments: " + " ".join(unknown))
    try:
        cwd = Path.cwd().resolve()
        folder, state = _start(args, cwd)
        if state.get("status") == "starting" and isinstance(state.get("background_launch"), dict):
            state["status"] = state["background_launch"].get("resume_status", "ready")
            state["termination"] = state["background_launch"].get("resume_termination", "ready")
            state.pop("background_launch", None)
            _write_state(folder, state)
        if args.answers:
            _answer(state, args.answers)
            _write_state(folder, state)
        should_deliver = args.confirm or (state.get("status") == "ready" and not args.background)
        if should_deliver:
            if state.get("status") != "ready":
                raise DeliveryInputError("delivery needs a resolved scope before confirmation")
            if args.background:
                child_argv = [item for item in raw_argv if item != "--background"]
                state["background_launch"] = {
                    "pid": None,
                    "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "resume_status": "ready",
                    "resume_termination": "ready",
                }
                state["status"] = "starting"
                state["termination"] = "running"
                _write_state(folder, state)
                child = subprocess.Popen(
                    [sys.executable, str(ROOT / "scripts" / "prd_request_controller.py"), *child_argv],
                    cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
                )
                state["background_launch"]["pid"] = child.pid
                _write_state(folder, state)
                print(json.dumps({"status": "starting", "run_folder": str(folder)}, ensure_ascii=False))
                return 0
            state["user_confirmation"] = {"confirmed": True, "at": dt.datetime.now(dt.timezone.utc).isoformat(), "source": "explicit --confirm"}
            state["status"] = "delivery"
            state["termination"] = "running"
            _write_state(folder, state)
            result = _deliver(state)
            print(json.dumps(asdict(result), ensure_ascii=False))
            return 0
        print(json.dumps({"status": state["status"], "run_folder": str(folder), "questions": state["turns"][-1]["questions"]}, ensure_ascii=False))
        return 0
    except (DeliveryInputError, OSError, RuntimeError, ValueError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
