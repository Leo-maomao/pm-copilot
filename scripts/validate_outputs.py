#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the PRD, rendered HTML, figures, and compact delivery evidence."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

import yaml

from prd_visual_contract import PLACEHOLDER_DECLARATION_RE
from validate_agent_trace import (
    validate_artifact_lineage,
    validate_implemented_feature_evidence_packet,
    validate_run_log,
)


REQUIRED_PRD_SECTIONS_ZH = ("文档说明", "需求背景", "需求清单", "需求详情")
DETAIL_FIELDS_ZH = ("用户与场景", "需求入口", "需求详情", "设计与交互")
RETIRED_DELIVERY_NAMES = {"prototype", "handoff", "prototype-web.html", "catalog.md", "dev-tasks.yaml", "launch-decision.yaml"}
DETAIL_MEDIA_MARKER_RE = re.compile(r"\[\[prd-detail-media\s+(?P<attributes>.*?)\]\]", re.I | re.S)
DETAIL_MEDIA_ATTRIBUTE_RE = re.compile(r'\b(?P<name>src|alt|copy)\s*=\s*"(?P<value>[^"]*)"', re.I | re.S)
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\((?P<path>[^)]+)\)")
REQUIREMENT_HEADING_RE = re.compile(r"^#{2,4}\s*5\.(?P<id>\d+)\s+", re.M)
SENSITIVE_TRACKING_RE = re.compile(r"(?:手机号|身份证|邮箱|email|phone|password|token|cookie)", re.I)


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _trace(folder: Path) -> dict:
    try:
        payload = yaml.safe_load(read(folder / "run-log.yaml"))
    except (OSError, yaml.YAMLError):
        return {}
    return payload if isinstance(payload, dict) else {}


def extract_yaml_block(text: str, key: str) -> str:
    payload = yaml.safe_load(text) if text.strip() else {}
    value = payload.get(key) if isinstance(payload, dict) else None
    return yaml.safe_dump({key: value}, allow_unicode=True, sort_keys=False) if value is not None else ""


def yaml_list_field_has_values(block: str, key: str) -> bool:
    try:
        payload = yaml.safe_load(block)
    except yaml.YAMLError:
        return False
    return isinstance(payload, dict) and isinstance(payload.get(key), list) and bool(payload[key])


def _safe_local_file(folder: Path, reference: str) -> Path | None:
    reference = unquote(reference).split("#", 1)[0].split("?", 1)[0]
    if not reference or re.match(r"^[a-z]+:", reference, re.I):
        return None
    candidate = (folder / reference).resolve()
    try:
        candidate.relative_to(folder.resolve())
    except ValueError:
        return None
    return candidate


def _asset_references(markdown: str) -> list[str]:
    refs = [match.group("path").strip() for match in MARKDOWN_IMAGE_RE.finditer(markdown)]
    for marker in DETAIL_MEDIA_MARKER_RE.finditer(markdown):
        fields = {item.group("name").lower(): item.group("value").strip() for item in DETAIL_MEDIA_ATTRIBUTE_RE.finditer(marker.group("attributes"))}
        if fields.get("src"):
            refs.append(fields["src"])
    return refs


class PRDHTMLInspectionParser(HTMLParser):
    """Small structural parser used for local PRD HTML validation."""

    def __init__(self) -> None:
        super().__init__()
        self.images: list[dict[str, object]] = []
        self.videos: list[dict[str, object]] = []
        self.scripts: list[str] = []
        self.stylesheets: list[str] = []
        self._video: dict[str, object] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "img":
            self.images.append({"src": values.get("src", ""), "alt": values.get("alt", "")})
        elif tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        elif tag == "link" and values.get("href"):
            self.stylesheets.append(values["href"])
        elif tag == "video":
            self._video = {"src": values.get("src", ""), "controls": "controls" in values, "playsinline": "playsinline" in values, "sources": []}
            self.videos.append(self._video)
        elif tag == "source" and self._video is not None:
            sources = self._video["sources"]
            assert isinstance(sources, list)
            sources.append({"src": values.get("src", ""), "type": values.get("type", "")})

    def handle_endtag(self, tag: str) -> None:
        if tag == "video":
            self._video = None


def check_folder(path: Path, require_run_log: bool = True, staging: bool = False) -> None:
    if not path.is_dir():
        fail(f"output folder does not exist: {path}")
    for retired in RETIRED_DELIVERY_NAMES:
        if (path / retired).exists():
            fail(f"retired non-PRD delivery artifact is not allowed: {retired}")
    if require_run_log and not (path / "run-log.yaml").is_file():
        fail("missing run-log.yaml")
    if not staging:
        for name in ("prd.md", "prd.html", "assets"):
            if not (path / name).exists():
                fail(f"missing canonical PRD delivery artifact: {name}")


def check_pre_clarification(path: Path) -> None:
    if (path / "prd.md").exists() or (path / "prd.html").exists():
        fail("PRD artifacts cannot exist before scope confirmation")


def check_stale_validation(path: Path) -> None:
    for name in ("prd.md", "prd.html"):
        target = path / name
        if target.is_file() and re.search(r"\b(?:to be verified|should run)\b|待执行|待运行", read(target), re.I):
            fail(f"{name} contains stale validation status")


def check_readiness_trace(path: Path, staging: bool = False) -> None:
    trace = _trace(path)
    decision = trace.get("quality_decision") if isinstance(trace, dict) else None
    if not isinstance(decision, dict):
        fail("run-log.yaml requires quality_decision")
    passed = decision.get("passed") is True
    if staging:
        return
    if not passed:
        fail("canonical output requires quality_decision.passed: true")
    validation = trace.get("validation_results")
    if not isinstance(validation, list) or not validation or any(not isinstance(item, dict) or item.get("status") != "passed" for item in validation):
        fail("canonical output requires passed validation_results")


def check_artifact_lineage_trace(path: Path) -> None:
    for message in validate_artifact_lineage(path / "run-log.yaml"):
        fail(message)


def check_implemented_feature_prd_trace(path: Path) -> None:
    for message in validate_implemented_feature_evidence_packet(path / "run-log.yaml"):
        fail(message)


def check_run_log_agent_evidence(path: Path) -> None:
    # Provider/model details belong to specialist evidence, not a generic Agent ledger.
    result = validate_run_log(path / "run-log.yaml")
    for message in result["failures"]:
        fail(message)


def _section_present(text: str, names: tuple[str, ...]) -> bool:
    return any(re.search(rf"^#+\s*.*(?:{re.escape(name)}).*", text, re.M) for name in names)


def check_requirement_detail_structure(text: str, language: str | None = None) -> None:
    if language == "en":
        if not _section_present(text, ("Requirement Details",)):
            fail("English PRD requires Requirement Details")
        return
    if not _section_present(text, ("需求详情",)):
        fail("PRD requires 需求详情")
    for field in DETAIL_FIELDS_ZH:
        if field not in text:
            fail(f"PRD requirement details require {field}")


def check_requirement_figure_rows(text: str) -> None:
    for marker in DETAIL_MEDIA_MARKER_RE.finditer(text):
        fields = {item.group("name").lower(): item.group("value").strip() for item in DETAIL_MEDIA_ATTRIBUTE_RE.finditer(marker.group("attributes"))}
        if not all(fields.get(name) for name in ("src", "alt", "copy")):
            fail("prd-detail-media requires src, alt, and copy")
    for value in PLACEHOLDER_DECLARATION_RE.findall(text):
        if not value.lower().endswith(".png"):
            fail("controlled figure placeholder must use the 功能-状态.png format")


def check_requirement_detail_media_blocks(text: str, preserved_legacy_requirement_ids: set[str] | None = None) -> None:
    # Detail figures must use the renderer's single semantic marker. Historical
    # untouched sections are intentionally outside this new-document constraint.
    details = re.split(r"^#{2,4}\s*5\.\d+\s+", text, flags=re.M)[1:]
    for detail in details:
        if re.search(r"<img\b|!\[[^\]]*\]\(", detail, re.I) and "[[prd-detail-media" not in detail:
            fail("requirement detail figures must use prd-detail-media")
    check_requirement_figure_rows(text)


def check_prd_flow_sections(text: str) -> None:
    if "```mermaid" in text and not re.search(r"```mermaid\s*\n\s*(?:flowchart|graph|sequenceDiagram)", text, re.I):
        fail("Mermaid figure requires a valid flow declaration")


def check_prd_output_contract(path: Path, language: str | None = None) -> None:
    markdown = read(path / "prd.md")
    if not markdown.lstrip().startswith("#"):
        fail("prd.md requires a title")
    if language != "en":
        for section in REQUIRED_PRD_SECTIONS_ZH:
            if section not in markdown:
                fail(f"Chinese PRD missing required section: {section}")
    check_requirement_detail_structure(markdown, language)
    check_requirement_detail_media_blocks(markdown)
    for reference in _asset_references(markdown):
        asset = _safe_local_file(path, reference)
        if asset is None or not asset.is_file():
            fail(f"PRD figure reference must remain inside assets and exist: {reference}")


def _contains_unlocalized_english_copy(value: str) -> bool:
    cleaned = re.sub(r"\b(?:[A-Z][A-Za-z0-9_-]*\s+)?(?:ID|URL|URI|API|SKU)\b", "", value, flags=re.I)
    return bool(re.search(r"\b[A-Za-z]{3,}(?:\s+[A-Za-z]{3,})+\b", cleaned))


def probable_english_copy_lines(block: str) -> list[str]:
    return [line.strip() for line in block.splitlines() if _contains_unlocalized_english_copy(line) and not re.search(r"[\u3400-\u9fff]", line)]


def check_chinese_prd(path: Path) -> None:
    markdown = read(path / "prd.md")
    for section in REQUIRED_PRD_SECTIONS_ZH:
        if section not in markdown:
            fail(f"Chinese PRD missing required section: {section}")
    check_requirement_detail_structure(markdown, "zh")
    check_requirement_detail_media_blocks(markdown)


def check_tracking_context(path: Path) -> None:
    markdown = read(path / "prd.md") if (path / "prd.md").is_file() else ""
    if "埋点需求" not in markdown:
        return
    for row in markdown.splitlines():
        if row.startswith("|") and SENSITIVE_TRACKING_RE.search(row):
            fail("tracking requirements must not include raw sensitive identifiers")


def check_mermaid(path: Path) -> None:
    if (path / "prd.md").is_file():
        check_prd_flow_sections(read(path / "prd.md"))


def check_prd_html_documents(path: Path) -> None:
    html_path = path / "prd.html"
    if not html_path.is_file():
        fail("missing prd.html")
    html = read(html_path)
    if "<!doctype html" not in html[:300].lower() or "<body" not in html.lower():
        fail("prd.html is not a complete HTML document")
    parser = PRDHTMLInspectionParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception as error:
        fail(f"prd.html parse failed: {error}")
    for source in [*parser.scripts, *parser.stylesheets, *(str(item.get("src") or "") for item in parser.images)]:
        if source and re.match(r"^(?:https?:)?//", source, re.I):
            fail(f"prd.html may not depend on remote runtime asset: {source}")
        if source and not source.startswith("data:") and not re.match(r"^[a-z]+:", source, re.I):
            target = _safe_local_file(path, source)
            if target is None or not target.is_file():
                fail(f"prd.html references missing local asset: {source}")
    for video in parser.videos:
        if not video.get("controls") or not video.get("playsinline"):
            fail("inline PRD video requires controls and playsinline")


def resolve_output_language(folder: Path, explicit_language: str | None) -> str | None:
    if explicit_language:
        return explicit_language
    language = _trace(folder).get("language")
    return str(language).lower() if str(language).lower() in {"zh", "en"} else None


def _proven_preserved_legacy_requirement_ids(folder: Path, run_log: str, text: str) -> set[str]:
    # Legacy media exemptions were part of the old revision validator. New
    # revisions prove preservation through revision-evidence.json instead.
    return set()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_folder", type=Path)
    parser.add_argument("--language", choices=["zh", "en"], default=None)
    parser.add_argument("--pre-clarification", action="store_true")
    parser.add_argument("--staging", action="store_true")
    args = parser.parse_args()
    folder = args.output_folder
    check_folder(folder, staging=args.staging)
    if args.pre_clarification:
        check_pre_clarification(folder)
        print(f"PM Copilot pre-clarification output validation passed: {folder}")
        return
    check_stale_validation(folder)
    check_readiness_trace(folder, staging=args.staging)
    check_run_log_agent_evidence(folder)
    check_artifact_lineage_trace(folder)
    check_implemented_feature_prd_trace(folder)
    check_prd_output_contract(folder, resolve_output_language(folder, args.language))
    check_tracking_context(folder)
    check_mermaid(folder)
    check_prd_html_documents(folder)
    print(f"PM Copilot output validation passed: {folder}")


if __name__ == "__main__":
    main()
