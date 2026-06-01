#!/usr/bin/env python3
"""Validate one generated PM Copilot output folder."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import re
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path


FORBIDDEN_DEFAULT_FILES = {
    "task-brief.md",
    "clarifying-questions.md",
    "assumptions.md",
    "pm-package.md",
    "metrics-tree.md",
    "tracking-plan.md",
    "user-flow.md",
    "review-checklist.md",
    "final-package-summary.md",
}

STALE_VALIDATION_RE = re.compile(
    r"\b(should run|to be verified)\b|待执行|待运行|应运行",
    re.IGNORECASE,
)

CHINESE_STATUS_LEAK_RE = re.compile(
    r"Ready for review|Ready for engineering|Blocked before launch|"
    r"\|\s*(Critical|High|Medium|Low|Open|Accepted)\s*\|"
)

REQUIRED_PRD_SECTIONS_ZH = [
    "版本记录",
    "需求输入",
    "就绪摘要",
    "背景",
    "调研",
    "目标",
    "需求范围",
    "需求列表",
    "需求详情",
    "埋点",
    "UI 交付",
    "风险",
    "验收标准",
    "交付评审",
    "验证结果",
]

PROTOTYPE_FILE_NAMES = (
    "index.html",
    "prototype-mini-program.html",
    "prototype-web.html",
    "prototype-h5.html",
    "prototype-app.html",
)
CATALOG_FILE_NAMES = (
    "catalog.md",
    "catalog.html",
    "reference.md",
    "reference.html",
)
CATALOG_REQUIRED_COLUMNS = {
    "item_id",
    "display_name",
    "source_status",
    "review_status",
    "owner",
    "access_date",
    "implementation_notes",
}
MODEL_CATALOG_REQUIRED_COLUMNS = {
    "provider",
    "model_id",
    "version_or_release",
    "input_modalities",
    "output_modalities",
    "context_window",
    "required_parameters",
    "optional_parameters",
    "rate_limits",
    "pricing_source",
    "deprecation_status",
}
ALLOWED_CATALOG_SOURCE_STATUSES = {
    "source_backed",
    "user_supplied",
    "mixed",
    "draft",
    "blocked",
}
ALLOWED_CATALOG_REVIEW_STATUSES = {
    "unreviewed",
    "pm_reviewed",
    "engineering_reviewed",
    "approved",
    "blocked",
}
DOCUMENT_ATTENTION_TYPES = {
    "source_gap",
    "pm_override",
    "conflict",
    "engineering_must_read",
    "launch_blocker",
    "cost_or_quota_risk",
    "security_or_compliance",
    "change_marker",
}

CIRCLED_ANNOTATION_NUMERAL_RE = re.compile(r"[①②③④⑤⑥⑦⑧⑨]")
BACKEND_BOUNDARY_RE = re.compile(
    r"\b(BFF|API\s+contract|backend\s+contract|service\s+boundary)\b|后端|接口|契约",
    re.IGNORECASE,
)
HOST_SERVICE_TERM_RE = re.compile(
    r"\b[A-Za-z][A-Za-z0-9_-]*(?:bff|api|service|server|backend)[A-Za-z0-9_-]*\b",
    re.IGNORECASE,
)

EXPECTED_REVIEW_SCORES = {
    "delivery": 32,
    "prd": 40,
    "metrics_and_tracking": 28,
    "prototype": 32,
    "review_checklist": 20,
}

EXPECTED_QUALITY_THRESHOLDS = {
    "delivery": 23,
    "prd": 31,
    "metrics_and_tracking": 21,
    "prototype": 24,
    "review_checklist": 15,
}

ALLOWED_TASK_TYPES = {
    "frontend",
    "backend",
    "data",
    "analytics",
    "qa",
    "docs",
    "release",
    "design",
}

ALLOWED_HANDOFF_STATUSES = {"ready", "blocked", "draft"}
ALLOWED_HANDOFF_MODES = {"human_confirmed", "unattended_candidate"}
ALLOWED_LAUNCH_DECISIONS = {
    "launch_blocked",
    "ready_for_engineering",
    "ready_for_staging",
    "ready_for_release_review",
    "ready_to_launch",
    "not_applicable",
}
ALLOWED_LAUNCH_MODES = {"human_confirmed", "unattended_candidate"}
ALLOWED_GATE_STATUSES = {
    "passed",
    "passed_with_blockers",
    "passed_with_required_skips",
    "failed",
    "blocked",
    "skipped",
    "not_applicable",
}
BLOCKING_GATE_STATUSES = {"failed", "blocked"}
PRODUCTION_DECISIONS = {
    "launch_blocked",
    "ready_for_staging",
    "ready_for_release_review",
    "ready_to_launch",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def visible_html_text(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def html_has_state(text: str, *names: str) -> bool:
    visible = visible_html_text(text).lower()
    state_attr = "\n".join(re.findall(r"data-ui-state=[\"']([^\"']+)[\"']", text, re.IGNORECASE)).lower()
    joined = visible + "\n" + state_attr
    return any(name.lower() in joined for name in names)


def check_compatibility_html_boundary(text: str, prototype_name: str) -> None:
    if not re.search(r"data-delivery-boundary|delivery-boundary|compatibility_html_review_artifact", text, re.IGNORECASE):
        fail(f"{prototype_name} missing compatibility UI delivery boundary metadata")
    visible = visible_html_text(text)
    if re.search(r"不是生产代码|not\s+production\s+code|prototype\s+only", visible, re.IGNORECASE):
        fail(f"{prototype_name} must not show not-production/example labels in product UI")
    generic_label_count = len(re.findall(r"示例|演示|\bdemo\b|\bsample\b|\bplaceholder\b|占位", visible, re.IGNORECASE))
    if generic_label_count >= 3:
        fail(f"{prototype_name} contains repeated visible example/demo/placeholder labels")


def extract_yaml_block(text: str, key: str) -> str:
    match = re.search(rf"^(?P<indent>\s*){re.escape(key)}:\s*(?:#.*)?$", text, re.MULTILINE)
    if not match:
        return ""
    indent = len(match.group("indent"))
    lines: list[str] = []
    for line in text[match.end():].splitlines():
        if line.strip() and len(line) - len(line.lstrip(" ")) <= indent:
            break
        lines.append(line)
    return "\n".join(lines)


def yaml_list_field_has_values(block: str, key: str) -> bool:
    match = re.search(rf"^(?P<indent>\s*){re.escape(key)}:\s*(?P<inline>.*)$", block, re.MULTILINE)
    if not match:
        return False
    inline = match.group("inline").strip()
    if inline in ("[]", '""', "''"):
        return False
    if inline and not inline.startswith("#"):
        return True
    indent = len(match.group("indent"))
    child_lines: list[str] = []
    for line in block[match.end():].splitlines():
        if line.strip() and len(line) - len(line.lstrip(" ")) <= indent:
            break
        child_lines.append(line)
    child_block = "\n".join(child_lines)
    return bool(re.search(r"^\s*-\s*(?!\"\"\s*$|''\s*$|#|\s*$).+", child_block, re.MULTILINE))


def yaml_mapping_field_has_value(block: str, key: str) -> bool:
    return bool(
        re.search(
            rf"^\s*(?:-\s*)?{re.escape(key)}:\s*(?!\"\"\s*$|''\s*$|#|\s*$).+",
            block,
            re.MULTILINE,
        )
    )


def yaml_scalar_field_value(block: str, key: str) -> str:
    match = re.search(rf"^\s*{re.escape(key)}:\s*(?P<value>.+?)\s*(?:#.*)?$", block, re.MULTILINE)
    if not match:
        return ""
    value = match.group("value").strip()
    if value in ("[]", "{}", '""', "''"):
        return ""
    return value.strip("\"'")


def yaml_field_value(block: str, key: str) -> str:
    match = re.search(
        rf"^\s*(?:-\s*)?{re.escape(key)}:\s*(?P<value>.*?)\s*(?:#.*)?$",
        block,
        re.MULTILINE,
    )
    if not match:
        return ""
    value = match.group("value").strip()
    if value in ("", "[]", "{}", '""', "''"):
        return ""
    return value.strip("\"'")


def yaml_bool_field_value(block: str, key: str) -> bool | None:
    value = yaml_field_value(block, key).lower()
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def yaml_list_item_blocks(block: str) -> list[str]:
    items: list[list[str]] = []
    current: list[str] = []
    base_indent: int | None = None
    for line in block.splitlines():
        match = re.match(r"^(?P<indent>\s*)-\s+", line)
        if match and base_indent is None:
            base_indent = len(match.group("indent"))
        if match and len(match.group("indent")) == base_indent:
            if current:
                items.append(current)
            current = [line]
            continue
        if current:
            current.append(line)
    if current:
        items.append(current)
    return ["\n".join(item) for item in items]


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def markdown_table_headers(text: str) -> list[list[str]]:
    lines = text.splitlines()
    headers: list[list[str]] = []
    for index, line in enumerate(lines[:-1]):
        if not line.lstrip().startswith("|"):
            continue
        separator = lines[index + 1]
        if not re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", separator):
            continue
        cells = [
            normalize_table_cell(cell)
            for cell in line.strip().strip("|").split("|")
        ]
        headers.append([cell for cell in cells if cell])
    return headers


def normalize_table_cell(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("`", "")
    value = re.sub(r"\s+", "_", value.strip().lower())
    return value


def headers_include_columns(headers: set[str], required_columns: set[str]) -> bool:
    return all(
        any(header == column or column in header for header in headers)
        for column in required_columns
    )


def missing_columns(headers: set[str], required_columns: set[str]) -> list[str]:
    return sorted(
        column
        for column in required_columns
        if not any(header == column or column in header for header in headers)
    )


def table_cell_has_value(cell: str) -> bool:
    value = cell.strip()
    normalized = value.lower()
    if not value or value in {"-", "—"}:
        return False
    if normalized in {"tbd", "todo", "to do", "待定", "待补充", "待填写"}:
        return False
    if re.fullmatch(r"<[^>|]+>", value):
        return False
    return True


def column_index_map(headers: list[str], required_columns: set[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for column in required_columns:
        for index, header in enumerate(headers):
            if header == column or column in header:
                mapping[column] = index
                break
    return mapping


def markdown_table_has_data_for(text: str, required_columns: set[str]) -> bool:
    lines = text.splitlines()
    for index, line in enumerate(lines[:-2]):
        if not line.lstrip().startswith("|"):
            continue
        separator = lines[index + 1]
        if not re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", separator):
            continue
        headers = [normalize_table_cell(cell) for cell in line.strip().strip("|").split("|")]
        header_set = {header for header in headers if header}
        if not headers_include_columns(header_set, required_columns):
            continue
        required_indexes = column_index_map(headers, required_columns)
        for data_line in lines[index + 2:]:
            if not data_line.lstrip().startswith("|"):
                break
            if "---" in data_line:
                continue
            cells = [cell.strip() for cell in data_line.strip().strip("|").split("|")]
            if all(
                column in required_indexes
                and required_indexes[column] < len(cells)
                and table_cell_has_value(cells[required_indexes[column]])
                for column in required_columns
            ):
                return True
    return False


def strip_yaml_comments(block: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in block.splitlines())


def raw_request_allows_standalone_html(run_log: str) -> bool:
    raw_request = yaml_scalar_field_value(run_log, "raw_request")
    return bool(
        re.search(
            r"(standalone|self[-_ ]contained|portable|independent\s+html|prototype-web\.html|"
            r"html\s*(file|artifact|prototype)|"
            r"独立\s*HTML|单文件\s*HTML|静态\s*HTML|便携|本地\s*HTML|HTML\s*文件|"
            r"HTML\s*原型|只要\s*HTML|输出\s*HTML|生成\s*HTML|导出\s*HTML)",
            raw_request,
            re.IGNORECASE,
        )
    )


def raw_request_allows_greenfield_ui(run_log: str) -> bool:
    raw_request = yaml_scalar_field_value(run_log, "raw_request")
    return bool(
        re.search(
            r"(greenfield|redesign|from scratch|start over|new visual design|freeform|freestyle|"
            r"rebuild\s+(the\s+)?ui|ignore existing (ui|design)|discard existing (ui|design)|"
            r"do not reuse existing (ui|design)|"
            r"重新设计|全新设计|自由发挥|从零(?:开始)?(?:设计|做|搭|构建)|"
            r"(?:UI|界面|视觉|设计).*?重构|重构.*?(?:UI|界面|视觉|设计)|"
            r"抛弃.*(?:原|现有).*?(?:设计|样式|UI)|"
            r"不(?:沿用|复用|参考).*?(?:原|现有).*?(?:设计|样式|UI)|"
            r"(?:不要|不用).*?(?:原|现有).*?(?:设计|样式|UI)|"
            r"重做.*?(?:视觉|设计|UI)|彻底改造.*?(?:UI|界面|视觉|设计)|大改版)",
            raw_request,
            re.IGNORECASE,
        )
    )


def source_rendering_was_blocked(run_log: str) -> bool:
    inventory_block = extract_yaml_block(run_log, "host_frontend_inventory")
    isolated_block = extract_yaml_block(run_log, "isolated_ui_prototype")
    limitation = yaml_scalar_field_value(inventory_block, "source_rendering_limitation")
    context = "\n".join(
        (
            limitation,
            yaml_scalar_field_value(isolated_block, "parity_claim"),
            yaml_scalar_field_value(isolated_block, "host_mutation_policy"),
        )
    )
    return bool(
        re.search(
            r"(failed|unavailable|setup failed|browser failed|dev server failed|"
            r"build failed|command failed|missing render command|missing preview surface|"
            r"dependency|simulator|devtools|preview surface|无法|失败|不可用|缺少|缺失|"
            r"未找到|找不到|依赖|模拟器|开发者工具|预览面)",
            context,
            re.IGNORECASE,
        )
    )


def check_repo_backed_style_evidence_quality(run_log: str) -> None:
    style_block = extract_yaml_block(run_log, "style_evidence")
    inventory_block = extract_yaml_block(run_log, "host_frontend_inventory")
    visual_baseline_block = extract_yaml_block(run_log, "existing_ui_visual_baseline")
    isolated_block = extract_yaml_block(run_log, "isolated_ui_prototype")
    source_map_block = extract_yaml_block(isolated_block, "source_to_demo_mapping")
    baseline_import_block = extract_yaml_block(isolated_block, "baseline_import")
    delta_patch_block = extract_yaml_block(isolated_block, "delta_patch")

    for field in ("source_files", "reused_components", "reused_tokens_or_classes", "icon_asset_sources"):
        if not yaml_list_field_has_values(style_block, field):
            fail(f"Repo-backed UI delivery style_evidence.{field} must list concrete host evidence")

    if not yaml_scalar_field_value(inventory_block, "platform"):
        fail("Repo-backed UI delivery host_frontend_inventory.platform must identify the host frontend type")
    for field in ("entry_files", "route_or_screen_files", "component_files", "style_files", "icon_asset_sources"):
        if not yaml_list_field_has_values(inventory_block, field):
            fail(f"Repo-backed UI delivery host_frontend_inventory.{field} must list inspected host sources")

    source_files_block = extract_yaml_block(style_block, "source_files")
    if not re.search(
        r"\b(src|app|pages|components|features|public|assets|styles|tailwind|theme|storybook|stories|lib|miniapp|"
        r"miniprogram|android|ios)/|"
        r"\.(tsx|ts|jsx|js|vue|svelte|css|scss|less|html|wxml|wxss|axml|acss|ttml|ttss|dart|kt|swift|xml|"
        r"png|jpg|jpeg|webp|svg)\b",
        source_files_block,
        re.IGNORECASE,
    ):
        fail("Repo-backed UI delivery style_evidence.source_files must name real host files or assets")

    if not yaml_mapping_field_has_value(source_map_block, "source"):
        fail("Repo-backed UI delivery source_to_demo_mapping must include non-empty source entries")
    if not yaml_mapping_field_has_value(source_map_block, "prototype_representation"):
        fail(
            "Repo-backed UI delivery source_to_demo_mapping must describe how each source appears "
            "in the UI deliverable"
        )

    mode = yaml_scalar_field_value(isolated_block, "mode")
    allowed_modes = {
        "self_contained_html_from_host_code",
        "source_extract_html",
        "source_delta_patch",
        "source_rendered_preview",
        "code_preview_route",
        "storybook_or_demo",
        "mini_program_preview",
        "app_preview_screen",
        "document_or_screenshot_only",
        "not_applicable",
    }
    if mode not in allowed_modes:
        fail("Repo-backed UI delivery isolated_ui_prototype.mode must name a supported artifact mode")
    recommended_mode = yaml_scalar_field_value(inventory_block, "recommended_artifact_mode")
    render_entrypoint = yaml_scalar_field_value(inventory_block, "render_entrypoint")
    preview = yaml_scalar_field_value(inventory_block, "preview_surface")
    visual_baseline_status = yaml_scalar_field_value(visual_baseline_block, "status")
    frontend_source_available = any(
        yaml_list_field_has_values(inventory_block, field)
        for field in ("entry_files", "route_or_screen_files", "component_files", "style_files")
    )
    source_rendering_decision = yaml_scalar_field_value(inventory_block, "source_rendering_decision")
    allowed_source_rendering_decisions = {
        "required",
        "used",
        "blocked",
        "user_explicit_portable",
        "user_explicit_greenfield",
        "not_required",
    }
    if source_rendering_decision and source_rendering_decision not in allowed_source_rendering_decisions:
        fail(
            "Repo-backed UI delivery host_frontend_inventory.source_rendering_decision must be one of "
            "required, used, blocked, user_explicit_portable, user_explicit_greenfield, or not_required"
        )
    if source_rendering_decision == "user_explicit_portable" and not raw_request_allows_standalone_html(run_log):
        fail("Repo-backed UI delivery cannot record user_explicit_portable unless the raw request asks for HTML/portable output")
    if source_rendering_decision == "user_explicit_greenfield" and not raw_request_allows_greenfield_ui(run_log):
        fail(
            "Repo-backed UI delivery cannot record user_explicit_greenfield unless the raw request asks to "
            "redesign, rebuild, or stop reusing the original UI"
        )
    if source_rendering_decision == "blocked" and not source_rendering_was_blocked(run_log):
        fail("Repo-backed UI delivery source_rendering_decision blocked requires a concrete source-rendering limitation")
    explicit_portable_or_blocked = (
        raw_request_allows_standalone_html(run_log)
        or raw_request_allows_greenfield_ui(run_log)
        or source_rendering_was_blocked(run_log)
    )
    source_rendered_modes = {
        "source_delta_patch",
        "source_rendered_preview",
        "code_preview_route",
        "storybook_or_demo",
        "mini_program_preview",
        "app_preview_screen",
    }
    source_derived_html_modes = {"source_extract_html"}
    non_source_rendered_modes = allowed_modes - source_rendered_modes
    if (
        mode in non_source_rendered_modes
        and frontend_source_available
        and mode not in source_derived_html_modes
        and not explicit_portable_or_blocked
    ):
        fail(
            "Repo-backed frontend source exists, so UI delivery must use source-rendered preview/delta "
            "unless the raw request explicitly asks for standalone/greenfield UI or source rendering was "
            "attempted and blocked"
        )
    if (
        mode == "self_contained_html_from_host_code"
        and recommended_mode in source_rendered_modes
        and render_entrypoint
        and preview
        and not explicit_portable_or_blocked
    ):
        fail(
            "Repo-backed renderable frontend should not fall back to standalone HTML unless the user "
            "explicitly requested portable/standalone HTML, requested greenfield/redesign UI, or source rendering was attempted and blocked"
        )
    if (
        mode == "self_contained_html_from_host_code"
        and recommended_mode in source_rendered_modes
        and render_entrypoint
        and preview
        and visual_baseline_status in {"not_captured", "none", "missing", ""}
        and not explicit_portable_or_blocked
    ):
        fail(
            "Repo-backed standalone HTML fallback must capture an existing UI visual baseline or record a "
            "concrete source-rendering/browser limitation"
        )
    exact_fidelity_requested = re.search(
        r"(1:1|pixel|exact|source-level|near-online|as if added in source code|"
        r"一模一样|真实\s*UI|线上一致|源码|源代码|完全一致)",
        run_log,
        re.IGNORECASE,
    )
    if exact_fidelity_requested and mode == "self_contained_html_from_host_code":
        fail(
            "Repo-backed exact/source-level UI fidelity must use source_delta_patch, source_rendered_preview, "
            "code_preview_route, storybook_or_demo, mini_program_preview, or app_preview_screen; "
            "not standalone HTML"
        )
    isolated_values = strip_yaml_comments(isolated_block)
    parity_claim = yaml_scalar_field_value(isolated_values, "parity_claim")
    if mode == "self_contained_html_from_host_code" and not re.search(
        r"(limited|fidelity[-_ ]limited|not source-rendered|degraded|有限|非源码渲染|降级)",
        parity_claim + "\n" + isolated_values,
        re.IGNORECASE,
    ):
        fail("Repo-backed standalone HTML mode must explicitly mark source-rendered fidelity as limited")
    if mode in source_rendered_modes:
        if not yaml_list_field_has_values(isolated_block, "preview_files_changed"):
            fail("Host-rendered UI delivery mode must record preview_files_changed")
        if not yaml_scalar_field_value(inventory_block, "render_entrypoint"):
            fail("Host-rendered UI delivery mode must record host_frontend_inventory.render_entrypoint")
        if not yaml_list_field_has_values(baseline_import_block, "imported_sources"):
            fail("Source-rendered UI delivery mode must record baseline_import.imported_sources")
        baseline_policy = yaml_scalar_field_value(baseline_import_block, "baseline_modification_policy")
        if baseline_policy not in {"no_rewrite", "read_only_import", "production_change_requested"}:
            fail("Source-rendered UI delivery mode must record a valid baseline_import.baseline_modification_policy")
        rewrite_scan_block = isolated_block.replace("no_rewrite", "")
        if baseline_policy != "production_change_requested" and re.search(
            r"(rewrite|recreate|redraw|manual baseline|手写\s*baseline|重写|重画)",
            rewrite_scan_block,
            re.IGNORECASE,
        ):
            fail("Source-rendered UI delivery mode must import/render the baseline, not rewrite it")
        if not yaml_list_field_has_values(delta_patch_block, "patch_files"):
            fail("Source-rendered UI delivery mode must record delta_patch.patch_files")
        if not yaml_scalar_field_value(delta_patch_block, "patch_strategy"):
            fail("Source-rendered UI delivery mode must record delta_patch.patch_strategy")
        if not yaml_scalar_field_value(delta_patch_block, "next_delta_anchor"):
            fail("Source-rendered UI delivery mode must record delta_patch.next_delta_anchor for multi-turn continuation")
    if mode == "source_extract_html":
        has_preview_files = yaml_list_field_has_values(isolated_block, "preview_files_changed")
        has_user_approved_implementation = yaml_list_field_has_values(
            isolated_block,
            "implementation_files_changed",
        ) or re.search(
            r"source_change_scope\s*:\s*(user_approved_implementation|production_oriented_implementation)",
            isolated_block,
        )
        if not has_preview_files and not has_user_approved_implementation:
            fail(
                "source_extract_html must record preview_files_changed or "
                "user-approved implementation_files_changed for the source-rendered UI"
            )
        if not yaml_scalar_field_value(inventory_block, "render_entrypoint"):
            fail("source_extract_html must record host_frontend_inventory.render_entrypoint")
        if not yaml_list_field_has_values(baseline_import_block, "imported_sources") and not has_user_approved_implementation:
            fail("source_extract_html must record baseline_import.imported_sources")
        if not yaml_list_field_has_values(delta_patch_block, "patch_files") and not has_user_approved_implementation:
            fail("source_extract_html must record delta_patch.patch_files")
        source_extract_block = extract_yaml_block(isolated_block, "source_extract")
        if not source_extract_block:
            fail("source_extract_html must record isolated_ui_prototype.source_extract")
        for field in (
            "source_target",
            "selector",
            "extraction_command",
            "extracted_html_path",
            "source_region_screenshot",
            "extracted_region_screenshot",
            "region_diff",
            "interaction_scope",
            "interaction_checks",
            "style_capture_method",
            "asset_handling",
            "annotation_layer",
            "annotation_config",
            "source_change_scope",
            "validation_report",
            "limitations",
        ):
            if not yaml_mapping_field_has_value(source_extract_block, field):
                fail(f"source_extract_html must record source_extract.{field}")


class PrototypeScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_script = False
        self._current_is_js = False
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        attr_map = {name.lower(): value or "" for name, value in attrs}
        script_type = attr_map.get("type", "").strip().lower()
        self._current_is_js = script_type in ("", "text/javascript", "application/javascript", "module")
        self._in_script = True
        if self._current_is_js:
            self.scripts.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script":
            self._in_script = False
            self._current_is_js = False

    def handle_data(self, data: str) -> None:
        if self._in_script and self._current_is_js and self.scripts:
            self.scripts[-1] += data


def section_text(text: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}:\s*(?:[^#\n]*)?(?:#.*)?$", text, re.MULTILINE)
    if not match:
        return ""
    next_match = re.search(
        r"^[A-Za-z_][A-Za-z0-9_-]*:\s*(?:[^#\n]*)?(?:#.*)?$",
        text[match.end():],
        re.MULTILINE,
    )
    end = match.end() + next_match.start() if next_match else len(text)
    return text[match.start():end]


def generated_prototypes(path: Path) -> list[Path]:
    return [path / name for name in PROTOTYPE_FILE_NAMES if (path / name).is_file()]


def generated_catalogs(path: Path) -> list[Path]:
    return [path / name for name in CATALOG_FILE_NAMES if (path / name).is_file()]


def is_document_prototype_html(text: str) -> bool:
    return bool(
        re.search(
            r"<meta[^>]+name=[\"']pm-copilot-artifact[\"'][^>]+content=[\"']document_prototype[\"']",
            text,
            re.IGNORECASE,
        )
        or "data-document-prototype" in text
    )


def check_folder(path: Path) -> None:
    if not path.is_dir():
        fail(f"Output folder not found: {path}")
    if path.parent.name == "outputs" and not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*-\d{4}-\d{2}-\d{2}(?:-\d+)?",
        path.name,
    ):
        fail(
            "Output folder names under outputs/ must use "
            "requirement-slug-YYYY-MM-DD with an optional numeric collision suffix"
        )

    forbidden = sorted(name for name in FORBIDDEN_DEFAULT_FILES if (path / name).exists())
    if forbidden:
        fail(f"Forbidden default split files present: {', '.join(forbidden)}")

    if not (path / "run-log.yaml").is_file():
        fail("Missing run-log.yaml")
    allowed = {
        "prd.md",
        "run-log.yaml",
        "tracking-plan.csv",
        "user-flow.mmd",
        "dev-tasks.yaml",
        "launch-decision.yaml",
    } | set(PROTOTYPE_FILE_NAMES) | set(CATALOG_FILE_NAMES)
    unexpected = sorted(item.name for item in path.iterdir() if item.is_file() and item.name not in allowed)
    if unexpected:
        fail(f"Unexpected output files present: {', '.join(unexpected)}")


def check_pre_clarification(path: Path) -> None:
    allowed = {"run-log.yaml"}
    files = {item.name for item in path.iterdir() if item.is_file()}
    extra = sorted(files - allowed)
    if extra:
        fail(f"Pre-clarification output contains downstream artifacts: {', '.join(extra)}")

    run_log = read(path / "run-log.yaml")
    required_markers = (
        "stopped_before_generation:",
        "unanswered_questions:",
    )
    for marker in required_markers:
        if marker not in run_log:
            fail(f"Pre-clarification run log missing marker: {marker}")
    if (
        "must_answer_before_generation:" not in run_log
        and "must answer before generation" not in run_log
    ):
        fail("Pre-clarification run log missing must-answer classification evidence")


def check_stale_validation(path: Path) -> None:
    for file_name in ("prd.md", "run-log.yaml", "catalog.md", "catalog.html"):
        file_path = path / file_name
        if file_path.exists() and STALE_VALIDATION_RE.search(read(file_path)):
            fail(f"Stale validation placeholder found in {file_name}")


def check_readiness_trace(path: Path) -> None:
    run_log = read(path / "run-log.yaml")
    required = (
        "readiness:",
        "prd_status:",
        "engineering_handoff_status:",
        "launch_status:",
        "engineering_blockers:",
        "launch_blockers:",
    )
    for marker in required:
        if marker not in run_log:
            fail(f"Run log missing readiness marker: {marker}")
    for marker in ("review_scores:", "quality_thresholds:", "quality_decision:"):
        if marker not in run_log:
            fail(f"Run log missing quality marker: {marker}")
    if "quality_decision:" in run_log and "passed: true" not in run_log:
        fail("Quality decision must explicitly pass for final generated artifacts")
    if "failures:" not in run_log:
        fail("Run log missing failures section")
    if "category:" not in run_log and "failures: []" not in run_log and "none" not in run_log.lower():
        fail("Run log failures section must include category or explicit no-failure marker")


def check_context_trace(path: Path) -> None:
    run_log = read(path / "run-log.yaml")
    required = (
        "pm_copilot_version:",
        "pm_copilot_revision:",
        "agents_used:",
        "skills_used:",
        "tools_used:",
        "source_mode:",
        "host_project_files_loaded:",
        "current_state_facts:",
        "analytics_taxonomy_source:",
        "external_research:",
    )
    for marker in required:
        if marker not in run_log:
            fail(f"Run log missing context marker: {marker}")


def check_structured_run_log_trace(path: Path) -> None:
    run_log = read(path / "run-log.yaml")
    check_external_research_shape(run_log)
    check_agent_transition_shape(run_log)
    check_handoff_artifact_shape(run_log)
    check_content_source_shape(run_log)
    check_guardrail_event_shape(run_log)
    check_security_and_audit_shape(run_log)
    check_review_score_shape(run_log)
    check_quality_threshold_shape(run_log)


def check_external_research_shape(run_log: str) -> None:
    section = section_text(run_log, "external_research")
    if not section:
        fail("Run log missing external_research section")
    for marker in ("status:", "question:", "sources:", "limitations:", "recommendation_impact:"):
        if marker not in section:
            fail(f"external_research missing marker: {marker}")
    if re.search(r"^\s*status:\s*(completed|degraded)\b", section, re.MULTILINE):
        for marker in ("title:", "url:", "observed_fact:", "product_implication:", "confidence:"):
            if marker not in section:
                fail(f"source-backed external_research missing marker: {marker}")


def check_agent_transition_shape(run_log: str) -> None:
    section = section_text(run_log, "agent_transitions")
    if not section:
        fail("Run log missing agent_transitions section")
    if re.search(r"^\s+artifact_delta:\s*(none|\"none\"|'none')\s*$", section, re.MULTILINE):
        fail("agent_transitions artifact_delta must be structured, not raw none")
    if re.search(r"^\s+validation_delta:\s*(none|\"none\"|'none')\s*$", section, re.MULTILINE):
        fail("agent_transitions validation_delta must be structured, not raw none")
    if re.search(r"^\s+artifact_delta:\s*\n\s+-\s+", section, re.MULTILINE):
        fail("agent_transitions artifact_delta must use files_created/files_changed/files_unchanged")
    if re.search(r"^\s+validation_delta:\s*\n\s+-\s+", section, re.MULTILINE):
        fail("agent_transitions validation_delta must use commands_run/commands_skipped/required_later")
    for marker in ("files_created:", "files_changed:", "files_unchanged:"):
        if marker not in section:
            fail(f"agent_transitions artifact_delta missing marker: {marker}")
    for marker in ("commands_run:", "commands_skipped:", "required_later:"):
        if marker not in section:
            fail(f"agent_transitions validation_delta missing marker: {marker}")

    for scalar_name in ("artifact_delta", "validation_delta"):
        scalar_re = re.compile(rf"^[^\S\r\n]+{scalar_name}:[^\S\r\n]+.+$", re.MULTILINE)
        for match in scalar_re.finditer(section):
            fail(f"agent_transitions {scalar_name} must not be a prose scalar")


def check_handoff_artifact_shape(run_log: str) -> None:
    section = section_text(run_log, "handoff_artifacts")
    if not section:
        fail("Run log missing handoff_artifacts section")
    for marker in ("dev_tasks:", "launch_decision:", "generation_mode:", "status:"):
        if marker not in section:
            fail(f"handoff_artifacts missing marker: {marker}")


def check_content_source_shape(run_log: str) -> None:
    section = section_text(run_log, "content_sources")
    if not section:
        fail("Run log missing content_sources section")
    if re.search(r"^content_sources:\s*\[\]\s*$", section, re.MULTILINE):
        return
    if "- content_area:" not in section:
        fail("content_sources must be a list with content_area entries or []")
    for marker in (
        "source_status:",
        "source_reference:",
        "review_owner:",
        "review_status:",
        "disclaimer_status:",
        "launch_impact:",
    ):
        if marker not in section:
            fail(f"content_sources missing marker: {marker}")


def check_guardrail_event_shape(run_log: str) -> None:
    section = section_text(run_log, "guardrail_events")
    if not section or re.search(r"^guardrail_events:\s*\[\]\s*$", section, re.MULTILINE):
        return
    for marker in ("type:", "decision:", "rationale:"):
        if marker not in section:
            fail(f"guardrail_events missing marker: {marker}")


def check_security_and_audit_shape(run_log: str) -> None:
    section = section_text(run_log, "security_and_audit")
    if not section:
        fail("Run log missing security_and_audit section")
    for marker in (
        "boundary:",
        "audit_visibility:",
        "identity_confirmation_expectation:",
        "redaction_expectation:",
        "retention_or_deletion_assumption:",
        "unresolved_approval_owner:",
    ):
        if marker not in section:
            fail(f"security_and_audit missing canonical marker: {marker}")
    for stale_marker in ("security_boundary:", "retention_deletion_assumption:"):
        if stale_marker in section:
            fail(f"security_and_audit uses stale marker: {stale_marker}")


def check_review_score_shape(run_log: str) -> None:
    section = section_text(run_log, "review_scores")
    if not section:
        fail("Run log missing review_scores section")
    for key, max_score in EXPECTED_REVIEW_SCORES.items():
        pattern = (
            rf"^\s+{re.escape(key)}:\s*\n"
            rf"(?:\s+[A-Za-z_][A-Za-z0-9_-]*:\s*[^\n]*\n)*?"
            rf"\s+score:\s*\d+\s*\n"
            rf"(?:\s+[A-Za-z_][A-Za-z0-9_-]*:\s*[^\n]*\n)*?"
            rf"\s+max_score:\s*{max_score}\b"
        )
        if not re.search(pattern, section, re.MULTILINE):
            fail(f"review_scores must include numeric {key}.score and max_score {max_score}")
        if not re.search(
            rf"^\s+{re.escape(key)}:\s*\n(?:\s+[A-Za-z_][A-Za-z0-9_-]*:\s*[^\n]*\n)*?\s+status:\s*.+$",
            section,
            re.MULTILINE,
        ):
            fail(f"review_scores {key} missing status")


def check_quality_threshold_shape(run_log: str) -> None:
    section = section_text(run_log, "quality_thresholds")
    if not section:
        fail("Run log missing quality_thresholds section")
    for key, threshold in EXPECTED_QUALITY_THRESHOLDS.items():
        if not re.search(rf"^\s+{re.escape(key)}:\s+{threshold}\b", section, re.MULTILINE):
            fail(f"quality_thresholds must include {key}: {threshold}")
    for stale_marker in ("minimum_score_per_category:", "blocking_findings_allowed:"):
        if stale_marker in section:
            fail(f"quality_thresholds uses non-rubric marker: {stale_marker}")


def check_external_research_trace(path: Path) -> None:
    if not (path / "prd.md").is_file():
        return
    run_log = read(path / "run-log.yaml")
    for marker in (
        "external_research:",
        "status:",
        "question:",
        "sources:",
        "limitations:",
        "recommendation_impact:",
    ):
        if marker not in run_log:
            fail(f"Run log missing external research marker: {marker}")


def check_default_option_trace(path: Path) -> None:
    run_log = read(path / "run-log.yaml")
    if "defaults_applied" in run_log or "推荐默认" in run_log:
        for marker in ("default_options_selected:", "selected_option:", "rationale:", "residual_risk:"):
            if marker not in run_log:
                fail(f"Default-option run log missing marker: {marker}")


def check_scope_and_surface_trace(path: Path) -> None:
    run_log = read(path / "run-log.yaml")
    required = ("scope_decisions:", "future_scope:", "non_goals:", "surface_decisions:")
    alternatives = (
        ("confirmed_mvp:", "confirmed_mvp_scope:"),
        ("optional_or_conditional:", "optional_scope:"),
        ("entry_points:", "entry_point:"),
        ("eligible_user_state:", "eligibility:"),
        ("fallback_states:", "fallback:"),
    )
    for marker in required:
        if marker not in run_log:
            fail(f"Run log missing scope/surface marker: {marker}")
    for canonical, legacy in alternatives:
        if canonical not in run_log and legacy not in run_log:
            fail(f"Run log missing scope/surface marker: {canonical} or {legacy}")
    if "navigation_visibility:" not in run_log:
        fail("Run log missing scope/surface marker: navigation_visibility:")


def check_visual_validation_trace(path: Path) -> None:
    run_log = read(path / "run-log.yaml")
    ui_html_prototypes = [
        prototype
        for prototype in generated_prototypes(path)
        if not is_document_prototype_html(read(prototype))
    ]
    has_html_prototype = bool(ui_html_prototypes)
    has_source_rendered_prototype = "isolated_ui_prototype:" in run_log and re.search(
        r"^\s*mode:\s*(source_delta_patch|source_rendered_preview|code_preview_route|storybook_or_demo|mini_program_preview|app_preview_screen)\b",
        run_log,
        re.MULTILINE,
    )
    if not has_html_prototype and not has_source_rendered_prototype:
        return
    if "visual_validation:" not in run_log and "validate_prototype_visual.py" not in run_log:
        fail("Run log missing visual_validation marker for UI delivery")
    section = section_text(run_log, "visual_validation")
    for marker in ("command:", "status:", "screenshots:", "report_path:", "limitation:"):
        if marker not in section:
            fail(f"visual_validation missing marker: {marker}")
    status = yaml_scalar_field_value(section, "status")
    if status == "passed":
        if not yaml_scalar_field_value(section, "command"):
            fail("visual_validation passed requires command")
        if not yaml_scalar_field_value(section, "report_path") and "source_preview_report_path:" not in section:
            fail("visual_validation passed requires report_path or source_preview_report_path")
    if has_source_rendered_prototype and "validate_ui_preview.py" not in section:
        if not re.search(r"(storybook|preview|simulator|browser|screenshot|截图)", section, re.IGNORECASE):
            fail("Source-backed UI delivery needs validate_ui_preview.py or equivalent preview/simulator evidence")


def check_prototype_agent_and_style_trace(path: Path, language: str | None = None) -> None:
    prototypes = generated_prototypes(path)
    run_log = read(path / "run-log.yaml")
    if not prototypes and "isolated_ui_prototype:" not in run_log:
        return

    document_prototypes = [
        prototype
        for prototype in prototypes
        if is_document_prototype_html(read(prototype))
    ]
    ui_prototypes = [
        prototype
        for prototype in prototypes
        if prototype not in document_prototypes
    ]
    for prototype in document_prototypes:
        check_document_prototype_html(prototype)

    if not ui_prototypes and "isolated_ui_prototype:" not in run_log:
        return

    if "UI Delivery Agent" not in run_log and "Prototype Agent" not in run_log:
        fail("Run log missing UI Delivery Agent/Prototype Agent for UI delivery")
    if "multi-platform-prototype" not in run_log:
        fail("Run log missing multi-platform-prototype skill for UI delivery")
    for marker in (
        "design_calibration:",
        "visual_density:",
        "layout_variance:",
        "motion_intensity:",
    ):
        if marker not in run_log:
            fail(f"UI delivery missing design calibration marker: {marker}")

    if "source_mode: repo-backed" in run_log:
        for marker in (
            "host_frontend_inventory:",
            "entry_files:",
            "route_or_screen_files:",
            "component_files:",
            "style_files:",
            "icon_asset_sources:",
            "render_entrypoint:",
            "style_evidence:",
            "source_files:",
            "reused_components:",
            "reused_tokens_or_classes:",
            "prototype_delta:",
            "limitations:",
        ):
            if marker not in run_log:
                fail(f"Repo-backed UI delivery missing style evidence marker: {marker}")
        for marker in (
            "existing_ui_visual_baseline:",
            "source:",
            "target:",
            "screenshots:",
            "comparison_method:",
        ):
            if marker not in run_log:
                fail(f"Repo-backed UI delivery missing existing UI visual baseline marker: {marker}")
        for marker in (
            "isolated_ui_prototype:",
            "host_mutation_policy:",
            "mode:",
            "target_surface:",
            "baseline_import:",
            "delta_patch:",
            "source_to_demo_mapping:",
            "backend_simulation:",
            "parity_claim:",
        ):
            if marker not in run_log:
                fail(f"Repo-backed UI delivery missing isolated UI delivery marker: {marker}")

        check_repo_backed_style_evidence_quality(run_log)

        for prototype in ui_prototypes:
            text = read(prototype)
            if "style-source-summary" not in text and "data-style-source" not in text:
                fail(
                    f"Repo-backed UI delivery missing style-source-summary or data-style-source: "
                    f"{prototype.name}"
                )

    for prototype in ui_prototypes:
        text = read(prototype)
        check_compatibility_html_boundary(text, prototype.name)
        check_annotation_marker_contract(text, prototype.name, language)


def css_rule_body(text: str, selector: str) -> str:
    for match in re.finditer(r"(?P<selectors>[^{}]+)\{(?P<body>[^{}]*)\}", text, re.MULTILINE | re.DOTALL):
        selectors = [item.strip() for item in match.group("selectors").split(",")]
        if selector in selectors:
            return match.group("body")
    return ""


def css_property_value(body: str, property_name: str) -> str:
    match = re.search(
        rf"\b{re.escape(property_name)}\s*:\s*([^;]+)",
        body,
        re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", match.group(1).strip().lower()) if match else ""


def css_rule_uses_nonzero_border(body: str) -> bool:
    border_matches = re.findall(r"\bborder(?!-radius)(?:-[a-z-]+)?\s*:\s*([^;]+)", body, re.IGNORECASE)
    for value in border_matches:
        normalized = value.strip().lower()
        if normalized.startswith("0") or normalized == "none":
            continue
        if "transparent" in normalized and re.search(r"\b0(?:px|rem|em)?\b", normalized):
            continue
        return True
    return False


def css_rule_has_red_badge_colors(body: str) -> bool:
    return bool(
        re.search(r"(#ff3b30|rgb\(\s*255\s*,\s*59\s*,\s*48\s*\)|--annotation-red|\bred\b)", body, re.IGNORECASE)
        and re.search(r"(color\s*:\s*(#fff|#ffffff|white|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\)))", body, re.IGNORECASE)
    )


def css_rule_centers_badge_content(body: str) -> bool:
    has_flex_or_grid_center = (
        re.search(r"\balign-items\s*:\s*center\b", body, re.IGNORECASE)
        and re.search(r"\bjustify-content\s*:\s*center\b", body, re.IGNORECASE)
    )
    has_place_center = re.search(r"\bplace-items\s*:\s*center\b", body, re.IGNORECASE)
    return bool(has_flex_or_grid_center or has_place_center)


def check_annotation_marker_contract(text: str, prototype_name: str, language: str | None = None) -> None:
    if "annotation-marker" not in text:
        fail(f"{prototype_name} missing red annotation-marker badges")
    if "data-annotation-id" not in text:
        fail(f"{prototype_name} missing data-annotation-id mapping for annotation markers")
    if not re.search(r"annotationConfig\s*=\s*\{", text) or "notes:" not in text:
        fail(f"{prototype_name} missing editable annotationConfig.notes mapping")
    if "renderAnnotationMarkers" not in text:
        fail(f"{prototype_name} must render annotation markers from the editable annotation config")
    if "data-annotation-anchor" not in text and "selector:" not in text:
        fail(f"{prototype_name} missing editable annotation anchor or selector mapping")
    has_top_right_placement = (
        'data-annotation-placement="top-right"' in text
        or "data-annotation-placement='top-right'" in text
        or re.search(
            r"setAttribute\(\s*['\"]data-annotation-placement['\"]\s*,\s*['\"]top-right['\"]\s*\)",
            text,
        )
    )
    if not has_top_right_placement:
        fail(f"{prototype_name} missing top-right annotation placement metadata")
    if "annotation-target" not in text:
        fail(f"{prototype_name} missing annotation-target wrappers for component-corner markers")
    for marker in ("annotation-toggle", "annotation-dialog", "annotation-list"):
        if marker not in text:
            fail(f"{prototype_name} missing marker-dialog annotation control: {marker}")
    if 'data-draggable="true"' not in text and "data-draggable='true'" not in text:
        fail(f"{prototype_name} missing draggable annotation-toggle metadata")
    if not re.search(r"(pointerdown|mousedown|touchstart)", text):
        fail(f"{prototype_name} missing drag interaction handlers for annotation-toggle")
    if re.search(r"class=[\"'][^\"']*(?:note-panel|annotation-panel)[^\"']*[\"']", text):
        fail(f"{prototype_name} should not use a persistent side annotation panel")
    if "annotation-backdrop" in text:
        fail(f"{prototype_name} should not use a global annotation backdrop for marker notes")
    if re.search(r"\.annotation-marker(?:\.|\s+)(?:active|is-active)\b", text):
        fail(f"{prototype_name} annotation markers should not change visual color when selected")
    if language == "zh" and not re.search(
        r"<button[^>]*class=[\"'][^\"']*annotation-toggle[^\"']*[\"'][^>]*>\s*注释\s*</button>",
        text,
        re.MULTILINE | re.DOTALL,
    ):
        fail(f"{prototype_name} annotation toggle label must be exactly 注释 for Chinese prototypes")
    for marker in ("prototype-viewport", "data-prototype-state"):
        if marker not in text:
            fail(f"{prototype_name} missing full-surface state/viewport marker: {marker}")
    dialog_rule = re.search(
        r"\.annotation-dialog\s*\{(?P<body>[^}]*)\}",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if dialog_rule:
        body = dialog_rule.group("body")
        if re.search(r"\binset\s*:\s*0\b", body):
            fail(f"{prototype_name} annotation-dialog must not be a full-screen marker modal")
        if (
            re.search(r"\btop\s*:\s*50%", body)
            and re.search(r"\bleft\s*:\s*50%", body)
            and "translate(-50%, -50%)" in body
        ):
            fail(f"{prototype_name} annotation-dialog must be positioned beside the marker, not centered")
    if "getBoundingClientRect" not in text or not re.search(r"\.style\.(left|top)\s*=", text):
        fail(f"{prototype_name} marker annotation dialog must calculate local position near the marker")
    if not re.search(r"data-active-annotation-id", text) or not re.search(r"classList\.contains\(['\"]active['\"]\)", text):
        fail(f"{prototype_name} marker annotation dialog must toggle closed when clicking the same marker again")
    marker_body = css_rule_body(text, ".annotation-marker")
    dialog_body = css_rule_body(text, ".annotation-dialog")
    if dialog_body:
        overflow_x = css_property_value(dialog_body, "overflow-x")
        if overflow_x and overflow_x not in {"hidden", "clip"}:
            fail(f"{prototype_name} annotation-dialog must not allow horizontal scrolling")
        if not overflow_x and css_property_value(dialog_body, "overflow") == "auto":
            fail(f"{prototype_name} annotation-dialog must use overflow-x hidden instead of overflow auto")
    show_annotation_match = re.search(
        r"function\s+showAnnotation\s*\([^)]*\)\s*\{(?P<body>.*?)\n\s*function\s+showAnnotationList\b",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if show_annotation_match:
        show_annotation_body = show_annotation_match.group("body")
        if re.search(r"<\s*(?:header|h[1-6])\b|annotation-number|annotation-close", show_annotation_body):
            fail(
                f"{prototype_name} marker annotation popover must render only annotation body text, "
                "without number, title, or close button"
            )
        if not re.search(r"<p\b", show_annotation_body):
            fail(f"{prototype_name} marker annotation popover should render body text in a paragraph")
    if "annotation-list-panel" in text:
        has_outside_click = (
            "document.addEventListener('click'" in text or 'document.addEventListener(\"click\"' in text
        ) and (
            "closest('#annotation-list-panel')" in text
            or 'closest("#annotation-list-panel")' in text
            or ".contains(event.target)" in text
        ) and "closeAnnotationPanel()" in text
        if not has_outside_click:
            fail(f"{prototype_name} annotation list panel must close when clicking outside the side panel")
    if marker_body:
        if css_rule_uses_nonzero_border(marker_body):
            fail(f"{prototype_name} annotation-marker must be red fill with white text and no border line")
        if not css_rule_has_red_badge_colors(marker_body):
            fail(f"{prototype_name} annotation-marker must use red background and white text")
        if not css_rule_centers_badge_content(marker_body):
            fail(f"{prototype_name} annotation-marker must center the digit inside the badge")
        body = marker_body
        if re.search(r"\b(top|right):\s*-\d", body):
            fail(f"{prototype_name} annotation-marker uses negative offsets that can be clipped")
    number_body = css_rule_body(text, ".annotation-number")
    if number_body:
        if css_rule_uses_nonzero_border(number_body):
            fail(f"{prototype_name} annotation-number must match marker style with no border line")
        if not css_rule_has_red_badge_colors(number_body):
            fail(f"{prototype_name} annotation-number must use the same red background and white text style")
        if not css_rule_centers_badge_content(number_body):
            fail(f"{prototype_name} annotation-number must center the digit inside the badge")
    if marker_body and number_body:
        for property_name in ("width", "height", "font-size", "font-weight", "line-height"):
            marker_value = css_property_value(marker_body, property_name)
            number_value = css_property_value(number_body, property_name)
            if not marker_value or not number_value:
                fail(
                    f"{prototype_name} annotation-marker and annotation-number must both define "
                    f"{property_name} so panel/dialog badges cannot inherit mismatched sizing"
                )
            if marker_value != number_value:
                fail(
                    f"{prototype_name} annotation-number {property_name} must match "
                    f"annotation-marker {property_name}"
                )
    list_body = css_rule_body(text, ".annotation-list")
    list_active_body = css_rule_body(text, ".annotation-list.active")
    if list_body:
        if not (re.search(r"\btop\s*:\s*0\b", list_body) and re.search(r"\bright\s*:\s*0\b", list_body)):
            fail(f"{prototype_name} annotation-list must slide from the right edge")
        if not (re.search(r"\bbottom\s*:\s*0\b", list_body) or re.search(r"\bheight\s*:\s*100d?vh\b", list_body)):
            fail(f"{prototype_name} annotation-list must use full viewport height")
        if "translateX(100%)" not in list_body or "translateX(0)" not in list_active_body:
            fail(f"{prototype_name} annotation-list must slide in from the right")
    if "annotation-toggle" in text and ".annotation-toggle.hidden" not in text:
        fail(f"{prototype_name} annotation toggle must hide while the annotation panel is open")
    if "prototype-state-tabs" in text:
        fail(f"{prototype_name} must not use legacy prominent prototype-state-tabs")
    if "reviewer-state-switcher" in text and 'data-reviewer-only="true"' not in text and "data-reviewer-only='true'" not in text:
        fail(f"{prototype_name} reviewer state switcher must be marked data-reviewer-only")
    target_rule = re.search(r"\.annotation-target\s*\{(?P<body>[^}]*)\}", text, re.MULTILINE | re.DOTALL)
    if target_rule and re.search(r"overflow:\s*(hidden|clip|auto|scroll)", target_rule.group("body")):
        fail(f"{prototype_name} annotation-target must not clip annotation markers")
    if not re.search(r"white-space:\s*nowrap", text):
        fail(f"{prototype_name} missing nowrap protection for compact controls and annotation toggles")

    annotation_ids = set(re.findall(r"data-annotation-id=[\"']([0-9]+)[\"']", text))
    annotation_ids.update(re.findall(r"\bid\s*:\s*['\"]([0-9]+)['\"]", text))
    if not annotation_ids:
        fail(f"{prototype_name} missing annotation ID values")
    if CIRCLED_ANNOTATION_NUMERAL_RE.search(text):
        fail(f"{prototype_name} annotation number badges must use plain digits, not circled numerals")
    if re.search(
        r"<span[^>]+class=[\"'][^\"']*annotation-number[^\"']*[\"'][^>]*>(?:(?!</span>).)*"
        r"<(?:span|button)[^>]+class=[\"'][^\"']*annotation-(?:marker|number)[^\"']*[\"']",
        text,
        re.MULTILINE | re.DOTALL,
    ):
        fail(f"{prototype_name} annotation number badges must not contain nested annotation badges")
    for annotation_id in sorted(annotation_ids, key=int):
        has_plain_number_source = re.search(rf"number:\s*['\"]{annotation_id}['\"]", text)
        has_plain_number_badge = re.search(
            rf"<span[^>]+class=[\"'][^\"']*annotation-number[^\"']*[\"'][^>]*>\s*{annotation_id}\s*</span>",
            text,
            re.MULTILINE | re.DOTALL,
        )
        if not has_plain_number_source and not has_plain_number_badge:
            fail(f"{prototype_name} missing plain digit annotation number badge for marker {annotation_id}")
    check_prototype_script_syntax(text, prototype_name)


def check_prototype_script_syntax(text: str, prototype_name: str) -> None:
    parser = PrototypeScriptParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as error:
        fail(f"{prototype_name} script extraction failed: {error}")
    if not parser.scripts:
        fail(f"{prototype_name} missing executable prototype script")
    scripts = "\n;\n".join(parser.scripts)
    node = shutil.which("node")
    if node:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".js", delete=False) as temp_file:
            temp_file.write(scripts)
            temp_path = Path(temp_file.name)
        try:
            result = subprocess.run(
                [node, "--check", str(temp_path)],
                text=True,
                capture_output=True,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            fail(f"{prototype_name} script syntax check timed out")
        finally:
            temp_path.unlink(missing_ok=True)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip().splitlines()
            fail(f"{prototype_name} contains JavaScript syntax errors: {' | '.join(detail[:3])}")
        return

    if "\\'" in scripts or '\\"' in scripts:
        fail(f"{prototype_name} contains suspicious escaped quotes in script; install node for full syntax check")


def check_chinese_prd(path: Path) -> None:
    prd_path = path / "prd.md"
    if not prd_path.exists():
        return

    text = read(prd_path)
    for section in REQUIRED_PRD_SECTIONS_ZH:
        if section not in text:
            fail(f"Chinese PRD missing expected section keyword: {section}")
    if CHINESE_STATUS_LEAK_RE.search(text):
        fail("Chinese PRD contains raw English readiness/review status labels")
    if "Mini Program" in text:
        fail("Chinese PRD should localize platform label as 微信小程序")
    for marker in ("MVP", "可选", "未来", "非目标"):
        if marker not in text:
            fail(f"Chinese PRD missing scope partition marker: {marker}")
    for marker in ("加载", "空", "错误"):
        if marker not in text:
            fail(f"Chinese PRD missing state coverage marker: {marker}")
    has_mini_program = (path / "prototype-mini-program.html").is_file()
    state_markers = ("无家庭",) if has_mini_program else ("未登录", "游客", "无权限")
    if not any(marker in text for marker in state_markers):
        fail(
            "Chinese PRD missing access/setup state marker: "
            + " or ".join(state_markers)
        )
    if "source_mode: repo-backed" in read(path / "run-log.yaml"):
        if "工程实施" not in text and "实施路径" not in text:
            fail("Repo-backed Chinese PRD missing engineering implementation map")
    ac_count = len(re.findall(r"\|\s*AC\d+\s*\|", text))
    if ac_count < 4:
        fail("PRD must include at least four acceptance criteria for this scenario")
    prototype_refs = re.findall(r"`(prototype-[a-z-]+\.html)`", text)
    for ref in prototype_refs:
        if not (path / ref).is_file():
            fail(f"PRD references missing compatibility UI HTML file: {ref}")


def check_tracking_context(path: Path) -> None:
    prd_path = path / "prd.md"
    if not prd_path.exists():
        return

    text = read(prd_path)
    if "event_name" not in text:
        return
    if "proposed taxonomy" not in text and "拟议" not in text and "未发现既有" not in text:
        fail("Tracking section missing proposed-taxonomy or taxonomy-source disclosure")

    sensitive_terms = ("预产期", "孕周", "医院", "病历", "身份证号", "手机号")
    event_lines = [line for line in text.splitlines() if line.startswith("| public_")]
    property_row_re = re.compile(r"^\|\s*[a-z][a-z0-9_]*\s*\|")
    property_lines = [
        line for line in text.splitlines()
        if property_row_re.match(line) and any(term in line for term in sensitive_terms)
    ]
    for line in event_lines:
        if any(term in line for term in sensitive_terms):
            fail("Tracking event row contains sensitive property text")
    if property_lines:
        fail("Tracking property table contains sensitive property text")


def check_content_source(path: Path) -> None:
    prd_path = path / "prd.md"
    if not prd_path.exists():
        return

    text = read(prd_path)
    content_markers = ("待产包", "清单", "内容来源")
    if all(marker in text for marker in content_markers):
        for marker in ("审核", "免责声明", "发布"):
            if marker not in text:
                fail(f"Content-backed PRD missing marker: {marker}")

        run_log_path = path / "run-log.yaml"
        run_log = read(run_log_path)
        for marker in (
            "content_sources:",
            "source_status:",
            "review_owner:",
            "review_status:",
            "disclaimer_status:",
            "launch_impact:",
        ):
            if marker not in run_log:
                fail(f"Content-backed run log missing marker: {marker}")


def check_mini_program_prototype(path: Path, language: str | None = None) -> None:
    prototypes = sorted(path.glob("prototype-mini-program.html"))
    if not prototypes:
        return

    text = read(prototypes[0])
    check_compatibility_html_boundary(text, prototypes[0].name)
    check_annotation_marker_contract(text, prototypes[0].name, language)
    required = [
        "mini-capsule",
        "tabbar",
        "page-header",
        "annotation-toggle",
        "annotation-dialog",
        "annotation-list",
        "onclick=",
    ]
    for marker in required:
        if marker not in text:
            fail(f"Mini Program UI HTML missing marker: {marker}")
    if "showScreen(" not in text and "showView(" not in text:
        fail("Mini Program UI HTML missing screen/state switching function")
    if "待产包" in text:
        for marker in ("待审核", "免责声明"):
            if marker not in text:
                fail(f"Content-backed UI HTML missing marker: {marker}")
    external_refs = ("http://", "https://", "cdn.", "unpkg.com", "cdnjs.")
    if any(ref in text for ref in external_refs):
        fail("Compatibility UI HTML should be self-contained and avoid external network references")


def check_web_prototype(path: Path, language: str | None = None) -> None:
    prototypes = sorted(path.glob("prototype-web.html"))
    if not prototypes:
        return

    text = read(prototypes[0])
    if is_document_prototype_html(text):
        return
    check_compatibility_html_boundary(text, prototypes[0].name)
    check_annotation_marker_contract(text, prototypes[0].name, language)
    required = [
        "prototype-shell",
        "desktop-nav",
        "prototype-viewport",
        "annotation-toggle",
        "annotation-dialog",
        "annotation-list",
        "note-group-title",
        "showView(",
        "onclick=",
        "@media",
    ]
    for marker in required:
        if marker not in text:
            fail(f"Web UI HTML missing marker: {marker}")
    state_requirements = (
        ("signed-out", ("未登录", "游客", "signed-out", "logged-out", "guest")),
        ("permission", ("无权限", "permission", "forbidden", "denied")),
        ("error", ("错误", "error")),
        ("loading", ("加载", "loading")),
    )
    for label, aliases in state_requirements:
        if not html_has_state(text, *aliases):
            fail(f"Web UI HTML missing real state coverage marker: {label}")
    prd_text = read(path / "prd.md") if (path / "prd.md").is_file() else ""
    if (HOST_SERVICE_TERM_RE.search(prd_text) or BACKEND_BOUNDARY_RE.search(prd_text)) and not (
        HOST_SERVICE_TERM_RE.search(text) or BACKEND_BOUNDARY_RE.search(visible_html_text(text))
    ):
        fail("Repo-backed Web UI HTML missing backend/API boundary annotation")
    external_refs = ("http://", "https://", "cdn.", "unpkg.com", "cdnjs.")
    if any(ref in text for ref in external_refs):
        fail("Web UI HTML should be self-contained and avoid external network references")


def check_mermaid(path: Path) -> None:
    prd_path = path / "prd.md"
    if not prd_path.exists():
        return
    text = read(prd_path)
    if "```mermaid" in text and "flowchart" not in text:
        fail("Mermaid block missing flowchart declaration")


def check_structured_catalog(path: Path) -> None:
    catalogs = generated_catalogs(path)
    if not catalogs:
        return

    run_log = read(path / "run-log.yaml")
    run_log_section_name = "structured_reference" if "structured_reference:" in run_log else "structured_catalog"
    if f"{run_log_section_name}:" not in run_log:
        fail("Run log missing structured_reference or structured_catalog section for reference delivery")
    section = extract_yaml_block(run_log, run_log_section_name)
    for marker in ("catalog_type:", "primary_artifact:", "source_status:", "review_status:", "owner:"):
        if marker not in section:
            fail(f"{run_log_section_name} run-log section missing marker: {marker}")
    if run_log_section_name == "structured_reference":
        for marker in ("entities:", "fields:", "rules:", "decisions:", "attention_points:"):
            if marker not in section:
                fail(f"structured_reference run-log section missing marker: {marker}")

    for catalog_md in (path / "catalog.md", path / "reference.md"):
        if catalog_md.exists():
            check_catalog_markdown(catalog_md)

    for catalog_html in (path / "catalog.html", path / "reference.html"):
        if catalog_html.exists():
            check_catalog_html(catalog_html)


def check_catalog_markdown(catalog_path: Path) -> None:
    text = read(catalog_path)
    frontmatter = parse_frontmatter(text)
    artifact_type = frontmatter.get("artifact_type")
    if artifact_type not in {"structured_catalog", "structured_reference"}:
        fail(f"{catalog_path.name} frontmatter must set artifact_type: structured_catalog or structured_reference")

    source_status = frontmatter.get("source_status", "")
    if source_status not in ALLOWED_CATALOG_SOURCE_STATUSES:
        fail("catalog.md source_status has unsupported value")

    review_status = frontmatter.get("review_status", "")
    if review_status not in ALLOWED_CATALOG_REVIEW_STATUSES:
        fail("catalog.md review_status has unsupported value")

    for key in ("catalog_type", "language", "owner", "last_updated"):
        if not frontmatter.get(key):
            fail(f"{catalog_path.name} frontmatter missing non-empty {key}")

    if not re.search(r"(catalog summary|清单摘要|目录摘要|目录概述|清单概述)", text, re.IGNORECASE):
        fail(f"{catalog_path.name} missing catalog summary section")
    if not re.search(r"(field dictionary|字段字典|字段说明)", text, re.IGNORECASE):
        fail(f"{catalog_path.name} missing field dictionary section")
    if not re.search(r"(source and review|来源.*审核|来源.*评审|source status)", text, re.IGNORECASE | re.DOTALL):
        fail(f"{catalog_path.name} missing source and review status section")
    if not re.search(r"(engineering handoff|研发交付|工程交付|工程说明)", text, re.IGNORECASE):
        fail(f"{catalog_path.name} missing engineering handoff notes section")
    if not re.search(r"(validation results|验证结果|校验结果|检查结果)", text, re.IGNORECASE):
        fail(f"{catalog_path.name} missing validation results section")

    header_union = {
        header
        for headers in markdown_table_headers(text)
        for header in headers
    }
    missing = missing_columns(header_union, CATALOG_REQUIRED_COLUMNS)
    if missing:
        fail(f"{catalog_path.name} missing required catalog columns: " + ", ".join(missing))
    if not markdown_table_has_data_for(text, CATALOG_REQUIRED_COLUMNS):
        fail(f"{catalog_path.name} must contain at least one data row with required catalog columns")

    if artifact_type == "structured_reference" or "attention_points" in text:
        check_attention_points_text(text, catalog_path.name)
        for marker in (
            "source_facts",
            "product_decisions",
            "change_log",
            "completeness_check",
        ):
            if marker not in text:
                fail(f"{catalog_path.name} structured reference missing {marker}")

    is_model_catalog = (
        "model" in frontmatter.get("catalog_type", "").lower()
        or any("model_id" in header for header in header_union)
        or "模型" in text
    )
    if is_model_catalog:
        missing_model = missing_columns(header_union, MODEL_CATALOG_REQUIRED_COLUMNS)
        if missing_model:
            fail(f"{catalog_path.name} model catalog missing columns: " + ", ".join(missing_model))


def check_catalog_html(catalog_path: Path) -> None:
    text = read(catalog_path)
    if "<!doctype html" not in text[:200].lower():
        fail(f"{catalog_path.name} missing doctype")
    if not re.search(
        r"<meta[^>]+name=[\"']pm-copilot-artifact[\"'][^>]+content=[\"'](?:structured_catalog|structured_reference)[\"']",
        text,
        re.IGNORECASE,
    ):
        fail(f"{catalog_path.name} missing structured catalog/reference meta marker")
    if "<table" not in text.lower():
        fail(f"{catalog_path.name} must include at least one table")
    if re.search(r"https?://|cdn\.|unpkg\.com|cdnjs\.", text, re.IGNORECASE):
        fail(f"{catalog_path.name} must be self-contained and avoid external network references")

    normalized = normalize_table_cell(visible_html_text(text) + " " + text)
    for column in CATALOG_REQUIRED_COLUMNS:
        if column not in normalized:
            fail(f"{catalog_path.name} missing required catalog column token: {column}")
    if "model_id" in normalized or "model" in normalized or "模型" in visible_html_text(text):
        for column in MODEL_CATALOG_REQUIRED_COLUMNS:
            if column not in normalized:
                fail(f"{catalog_path.name} model catalog missing column token: {column}")
    if "structured_reference" in normalized or "attention_points" in text or "attention-point" in text:
        check_attention_points_text(text, catalog_path.name)


def check_attention_points_text(text: str, artifact_name: str) -> None:
    normalized = normalize_table_cell(visible_html_text(text) + " " + text)
    attention_hits = sorted(attention_type for attention_type in DOCUMENT_ATTENTION_TYPES if attention_type in normalized)
    if not attention_hits:
        fail(f"{artifact_name} missing structured document attention_points")
    if not re.search(r"(target_ref|scope|field|rule|entity|字段|规则|对象)", normalized, re.IGNORECASE):
        fail(f"{artifact_name} attention_points must identify the target object, field, or rule")


def check_document_prototype_html(prototype_path: Path) -> None:
    text = read(prototype_path)
    if "<!doctype html" not in text[:200].lower():
        fail(f"{prototype_path.name} missing doctype")
    if not is_document_prototype_html(text):
        fail(f"{prototype_path.name} missing document_prototype meta marker")
    if re.search(r"https?://|cdn\.|unpkg\.com|cdnjs\.", text, re.IGNORECASE):
        fail(f"{prototype_path.name} must be self-contained and avoid external network references")
    for marker in ("document-nav", "data-document-section", "attention-point", "data-attention-type"):
        if marker not in text:
            fail(f"{prototype_path.name} missing document prototype marker: {marker}")
    for marker in ("source_status", "review_status"):
        if marker not in text:
            fail(f"{prototype_path.name} missing source/review status token: {marker}")
    if "<table" not in text.lower():
        fail(f"{prototype_path.name} document prototype must include structured tables")
    if "annotation-marker" in text and "attention-point" not in text:
        fail(f"{prototype_path.name} document prototype must use semantic attention points, not only UI annotations")
    check_attention_points_text(text, prototype_path.name)
    check_prototype_script_syntax(text, prototype_path.name)


def check_handoff_artifacts(path: Path) -> None:
    dev_tasks = path / "dev-tasks.yaml"
    if dev_tasks.exists():
        text = read(dev_tasks)
        for marker in (
            "run_id:",
            "source_prd:",
            "handoff_status:",
            "generation_mode:",
            "tasks:",
            "source_requirements:",
            "acceptance_criteria:",
            "validation_commands:",
            "ready_for_issue:",
        ):
            if marker not in text:
                fail(f"dev-tasks.yaml missing marker: {marker}")
        check_dev_tasks_contract(text)

    launch_decision = path / "launch-decision.yaml"
    if launch_decision.exists():
        text = read(launch_decision)
        for marker in (
            "run_id:",
            "source_prd:",
            "decision:",
            "decision_mode:",
            "decision_owner_required:",
            "gates:",
            "visual_validation:",
            "blockers:",
            "required_human_approvals:",
            "allowed_next_actions:",
            "disallowed_actions:",
            "rollback_plan:",
        ):
            if marker not in text:
                fail(f"launch-decision.yaml missing marker: {marker}")
        if re.search(r"decision:\s*ready_to_launch", text) and not re.search(
            r"decision_mode:\s*human_confirmed",
            text,
        ):
            fail("launch-decision.yaml cannot mark ready_to_launch without human_confirmed mode")
        check_launch_decision_contract(text)


def check_dev_tasks_contract(text: str) -> None:
    handoff_status = yaml_field_value(text, "handoff_status")
    if handoff_status not in ALLOWED_HANDOFF_STATUSES:
        fail("dev-tasks.yaml handoff_status must be ready, blocked, or draft")

    generation_mode = yaml_field_value(text, "generation_mode")
    if generation_mode not in ALLOWED_HANDOFF_MODES:
        fail("dev-tasks.yaml generation_mode must be human_confirmed or unattended_candidate")

    tasks_block = extract_yaml_block(text, "tasks")
    task_blocks = yaml_list_item_blocks(tasks_block)
    if not task_blocks:
        fail("dev-tasks.yaml must contain at least one task")

    blocked_task_count = 0
    ready_task_count = 0
    for index, task in enumerate(task_blocks, start=1):
        task_id = yaml_field_value(task, "id") or f"task {index}"
        for field in ("id", "title", "type", "owner_role", "description"):
            if not yaml_field_value(task, field):
                fail(f"dev-tasks.yaml {task_id} missing non-empty {field}")

        task_type = yaml_field_value(task, "type")
        if task_type not in ALLOWED_TASK_TYPES:
            fail(f"dev-tasks.yaml {task_id} has unsupported task type: {task_type}")

        for field in ("source_requirements", "acceptance_criteria", "validation_commands"):
            if not yaml_list_field_has_values(task, field):
                fail(f"dev-tasks.yaml {task_id} must include non-empty {field}")

        has_blockers = yaml_list_field_has_values(task, "blocked_by")
        if has_blockers:
            blocked_task_count += 1

        ready_for_issue = yaml_bool_field_value(task, "ready_for_issue")
        if ready_for_issue is None:
            fail(f"dev-tasks.yaml {task_id} ready_for_issue must be true or false")
        if ready_for_issue:
            ready_task_count += 1
            if has_blockers:
                fail(f"dev-tasks.yaml {task_id} cannot be ready_for_issue while blocked_by is non-empty")
            if not (
                yaml_list_field_has_values(task, "affected_surfaces")
                or yaml_list_field_has_values(task, "likely_files")
            ):
                fail(
                    f"dev-tasks.yaml {task_id} ready_for_issue true requires affected_surfaces "
                    "or likely_files"
                )
            if not yaml_list_field_has_values(task, "dependencies"):
                fail(f"dev-tasks.yaml {task_id} ready_for_issue true requires dependencies")

    if handoff_status in {"blocked", "draft"} and not (
        yaml_list_field_has_values(text, "blocking_summary") or blocked_task_count
    ):
        fail("dev-tasks.yaml blocked or draft handoff must expose blocking_summary or task blocked_by")

    if handoff_status == "ready" and ready_task_count == 0:
        fail("dev-tasks.yaml ready handoff must include at least one ready_for_issue task")


def check_launch_decision_contract(text: str) -> None:
    decision = yaml_field_value(text, "decision")
    if decision not in ALLOWED_LAUNCH_DECISIONS:
        fail("launch-decision.yaml decision has unsupported value")

    decision_mode = yaml_field_value(text, "decision_mode")
    if decision_mode not in ALLOWED_LAUNCH_MODES:
        fail("launch-decision.yaml decision_mode must be human_confirmed or unattended_candidate")

    owner_required = yaml_bool_field_value(text, "decision_owner_required")
    if owner_required is None:
        fail("launch-decision.yaml decision_owner_required must be true or false")

    gates_block = extract_yaml_block(text, "gates")
    gate_statuses: dict[str, str] = {}
    for gate in (
        "prd_complete",
        "engineering_handoff",
        "validation",
        "visual_validation",
        "content_approval",
        "analytics_approval",
        "privacy_security_legal",
        "rollout_and_rollback",
    ):
        gate_block = extract_yaml_block(gates_block, gate)
        if not gate_block:
            fail(f"launch-decision.yaml gates.{gate} missing")
        status = yaml_field_value(gate_block, "status")
        evidence = yaml_field_value(gate_block, "evidence")
        if status not in ALLOWED_GATE_STATUSES:
            fail(f"launch-decision.yaml gates.{gate}.status has unsupported value: {status}")
        if not evidence:
            fail(f"launch-decision.yaml gates.{gate}.evidence must be non-empty")
        gate_statuses[gate] = status

    if any(status in BLOCKING_GATE_STATUSES for status in gate_statuses.values()):
        if decision != "launch_blocked":
            fail("launch-decision.yaml must use launch_blocked when any gate is failed or blocked")

    if decision == "launch_blocked":
        for field in ("blockers", "required_human_approvals", "disallowed_actions"):
            if not yaml_list_field_has_values(text, field):
                fail(f"launch-decision.yaml launch_blocked requires non-empty {field}")

    if decision == "ready_to_launch":
        if decision_mode != "human_confirmed":
            fail("launch-decision.yaml ready_to_launch requires human_confirmed mode")
        if yaml_list_field_has_values(text, "blockers"):
            fail("launch-decision.yaml ready_to_launch cannot have blockers")
        if any(
            status not in {"passed", "not_applicable"}
            for status in gate_statuses.values()
        ):
            fail("launch-decision.yaml ready_to_launch requires all gates passed or not_applicable")

    if decision in {"ready_for_staging", "ready_for_release_review", "ready_to_launch"}:
        if gate_statuses["validation"] not in {"passed", "passed_with_required_skips"}:
            fail("launch-decision.yaml ready decisions require validation gate evidence")

    rollback_block = extract_yaml_block(text, "rollback_plan")
    if decision in PRODUCTION_DECISIONS:
        for field in ("owner", "trigger", "steps"):
            has_value = (
                yaml_list_field_has_values(rollback_block, field)
                if field == "steps"
                else bool(yaml_field_value(rollback_block, field))
            )
            if not has_value:
                fail(f"launch-decision.yaml production-facing decision requires rollback_plan.{field}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_folder", type=Path)
    parser.add_argument("--language", choices=["zh", "en"], default=None)
    parser.add_argument("--pre-clarification", action="store_true")
    args = parser.parse_args()

    folder = args.output_folder
    check_folder(folder)
    if args.pre_clarification:
        check_pre_clarification(folder)
        print(f"PM Copilot pre-clarification output validation passed: {folder}")
        return

    check_stale_validation(folder)
    check_readiness_trace(folder)
    check_context_trace(folder)
    check_structured_run_log_trace(folder)
    check_default_option_trace(folder)
    check_scope_and_surface_trace(folder)
    check_visual_validation_trace(folder)
    check_prototype_agent_and_style_trace(folder, args.language)
    if args.language == "zh":
        check_chinese_prd(folder)
    check_tracking_context(folder)
    check_content_source(folder)
    check_mini_program_prototype(folder, args.language)
    check_web_prototype(folder, args.language)
    check_mermaid(folder)
    check_structured_catalog(folder)
    check_handoff_artifacts(folder)
    print(f"PM Copilot output validation passed: {folder}")


if __name__ == "__main__":
    main()
