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
    "原型",
    "风险",
    "验收标准",
    "交付评审",
    "验证结果",
]

PROTOTYPE_FILE_NAMES = (
    "prototype-mini-program.html",
    "prototype-web.html",
    "prototype-h5.html",
    "prototype-app.html",
)

ANNOTATION_NUMERAL_RE = re.compile(r"[①②③④⑤⑥⑦⑧⑨]")

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


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def strip_yaml_comments(block: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in block.splitlines())


def check_repo_backed_style_evidence_quality(run_log: str) -> None:
    style_block = extract_yaml_block(run_log, "style_evidence")
    inventory_block = extract_yaml_block(run_log, "host_frontend_inventory")
    isolated_block = extract_yaml_block(run_log, "isolated_ui_prototype")
    source_map_block = extract_yaml_block(isolated_block, "source_to_demo_mapping")
    baseline_import_block = extract_yaml_block(isolated_block, "baseline_import")
    delta_patch_block = extract_yaml_block(isolated_block, "delta_patch")

    for field in ("source_files", "reused_components", "reused_tokens_or_classes", "icon_asset_sources"):
        if not yaml_list_field_has_values(style_block, field):
            fail(f"Repo-backed prototype style_evidence.{field} must list concrete host evidence")

    if not yaml_scalar_field_value(inventory_block, "platform"):
        fail("Repo-backed prototype host_frontend_inventory.platform must identify the host frontend type")
    for field in ("entry_files", "route_or_screen_files", "component_files", "style_files", "icon_asset_sources"):
        if not yaml_list_field_has_values(inventory_block, field):
            fail(f"Repo-backed prototype host_frontend_inventory.{field} must list inspected host sources")

    source_files_block = extract_yaml_block(style_block, "source_files")
    if not re.search(
        r"\b(src|app|pages|components|features|public|assets|styles|tailwind|theme|storybook|stories|lib|miniapp|"
        r"miniprogram|android|ios)/|"
        r"\.(tsx|ts|jsx|js|vue|svelte|css|scss|less|html|wxml|wxss|axml|acss|ttml|ttss|dart|kt|swift|xml|"
        r"png|jpg|jpeg|webp|svg)\b",
        source_files_block,
        re.IGNORECASE,
    ):
        fail("Repo-backed prototype style_evidence.source_files must name real host files or assets")

    if not yaml_mapping_field_has_value(source_map_block, "source"):
        fail("Repo-backed prototype source_to_demo_mapping must include non-empty source entries")
    if not yaml_mapping_field_has_value(source_map_block, "prototype_representation"):
        fail(
            "Repo-backed prototype source_to_demo_mapping must describe how each source appears "
            "in the prototype"
        )

    mode = yaml_scalar_field_value(isolated_block, "mode")
    allowed_modes = {
        "self_contained_html_from_host_code",
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
        fail("Repo-backed prototype isolated_ui_prototype.mode must name a supported artifact mode")
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
    source_rendered_modes = {
        "source_delta_patch",
        "source_rendered_preview",
        "code_preview_route",
        "storybook_or_demo",
        "mini_program_preview",
        "app_preview_screen",
    }
    if mode in source_rendered_modes:
        if not yaml_list_field_has_values(isolated_block, "preview_files_changed"):
            fail("Host-rendered prototype mode must record preview_files_changed")
        if not yaml_scalar_field_value(inventory_block, "render_entrypoint"):
            fail("Host-rendered prototype mode must record host_frontend_inventory.render_entrypoint")
        if not yaml_list_field_has_values(baseline_import_block, "imported_sources"):
            fail("Source-rendered prototype mode must record baseline_import.imported_sources")
        baseline_policy = yaml_scalar_field_value(baseline_import_block, "baseline_modification_policy")
        if baseline_policy not in {"no_rewrite", "read_only_import", "production_change_requested"}:
            fail("Source-rendered prototype mode must record a valid baseline_import.baseline_modification_policy")
        rewrite_scan_block = isolated_block.replace("no_rewrite", "")
        if baseline_policy != "production_change_requested" and re.search(
            r"(rewrite|recreate|redraw|manual baseline|手写\s*baseline|重写|重画)",
            rewrite_scan_block,
            re.IGNORECASE,
        ):
            fail("Source-rendered prototype mode must import/render the baseline, not rewrite it")
        if not yaml_list_field_has_values(delta_patch_block, "patch_files"):
            fail("Source-rendered prototype mode must record delta_patch.patch_files")
        if not yaml_scalar_field_value(delta_patch_block, "patch_strategy"):
            fail("Source-rendered prototype mode must record delta_patch.patch_strategy")
        if not yaml_scalar_field_value(delta_patch_block, "next_delta_anchor"):
            fail("Source-rendered prototype mode must record delta_patch.next_delta_anchor for multi-turn continuation")


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


def check_folder(path: Path) -> None:
    if not path.is_dir():
        fail(f"Output folder not found: {path}")

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
    } | set(PROTOTYPE_FILE_NAMES)
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
        "must_answer_before_generation:",
        "unanswered_questions:",
    )
    for marker in required_markers:
        if marker not in run_log:
            fail(f"Pre-clarification run log missing marker: {marker}")


def check_stale_validation(path: Path) -> None:
    for file_name in ("prd.md", "run-log.yaml"):
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
        scalar_re = re.compile(rf"^\s+{scalar_name}:\s+.+$", re.MULTILINE)
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
    required = (
        "scope_decisions:",
        "confirmed_mvp_scope:",
        "optional_scope:",
        "future_scope:",
        "non_goals:",
        "surface_decisions:",
        "entry_point:",
        "navigation_visibility:",
        "eligibility:",
        "fallback:",
    )
    for marker in required:
        if marker not in run_log:
            fail(f"Run log missing scope/surface marker: {marker}")


def check_visual_validation_trace(path: Path) -> None:
    run_log = read(path / "run-log.yaml")
    has_html_prototype = bool(generated_prototypes(path))
    has_source_rendered_prototype = "isolated_ui_prototype:" in run_log and re.search(
        r"^\s*mode:\s*(source_delta_patch|source_rendered_preview|code_preview_route|storybook_or_demo|mini_program_preview|app_preview_screen)\b",
        run_log,
        re.MULTILINE,
    )
    if not has_html_prototype and not has_source_rendered_prototype:
        return
    if "visual_validation:" not in run_log and "validate_prototype_visual.py" not in run_log:
        fail("Run log missing visual_validation marker for prototype delivery")


def check_prototype_agent_and_style_trace(path: Path, language: str | None = None) -> None:
    prototypes = generated_prototypes(path)
    run_log = read(path / "run-log.yaml")
    if not prototypes and "isolated_ui_prototype:" not in run_log:
        return

    if "Prototype Agent" not in run_log:
        fail("Run log missing Prototype Agent for prototype delivery")
    if "multi-platform-prototype" not in run_log:
        fail("Run log missing multi-platform-prototype skill for prototype delivery")
    for marker in (
        "design_calibration:",
        "visual_density:",
        "layout_variance:",
        "motion_intensity:",
    ):
        if marker not in run_log:
            fail(f"Prototype delivery missing design calibration marker: {marker}")

    for prototype in prototypes:
        check_annotation_marker_contract(read(prototype), prototype.name, language)

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
                fail(f"Repo-backed prototype missing style evidence marker: {marker}")
        for marker in (
            "existing_ui_visual_baseline:",
            "source:",
            "target:",
            "screenshots:",
            "comparison_method:",
        ):
            if marker not in run_log:
                fail(f"Repo-backed prototype missing existing UI visual baseline marker: {marker}")
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
                fail(f"Repo-backed prototype missing isolated UI prototype marker: {marker}")

        check_repo_backed_style_evidence_quality(run_log)

        for prototype in prototypes:
            text = read(prototype)
            if "style-source-summary" not in text and "data-style-source" not in text:
                fail(
                    f"Repo-backed prototype missing style-source-summary or data-style-source: "
                    f"{prototype.name}"
                )


def css_rule_body(text: str, selector: str) -> str:
    match = re.search(
        rf"{re.escape(selector)}\s*\{{(?P<body>[^}}]*)\}}",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group("body") if match else ""


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


def check_annotation_marker_contract(text: str, prototype_name: str, language: str | None = None) -> None:
    if "annotation-marker" not in text:
        fail(f"{prototype_name} missing red annotation-marker badges")
    if "data-annotation-id" not in text:
        fail(f"{prototype_name} missing data-annotation-id mapping for annotation markers")
    if 'data-annotation-placement="top-right"' not in text and "data-annotation-placement='top-right'" not in text:
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
    if "note-panel" in text or "annotation-panel" in text:
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
    if marker_body:
        if css_rule_uses_nonzero_border(marker_body):
            fail(f"{prototype_name} annotation-marker must be red fill with white text and no border line")
        if not css_rule_has_red_badge_colors(marker_body):
            fail(f"{prototype_name} annotation-marker must use red background and white text")
        body = marker_body
        if re.search(r"\b(top|right):\s*-\d", body):
            fail(f"{prototype_name} annotation-marker uses negative offsets that can be clipped")
    number_body = css_rule_body(text, ".annotation-number")
    if number_body:
        if css_rule_uses_nonzero_border(number_body):
            fail(f"{prototype_name} annotation-number must match marker style with no border line")
        if not css_rule_has_red_badge_colors(number_body):
            fail(f"{prototype_name} annotation-number must use the same red background and white text style")
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
    state_tabs_body = css_rule_body(text, ".prototype-state-tabs")
    if "prototype-state-tabs" in text and not re.search(r"\bposition\s*:\s*fixed\b", state_tabs_body):
        fail(f"{prototype_name} prototype state tabs must use a fixed position")
    target_rule = re.search(r"\.annotation-target\s*\{(?P<body>[^}]*)\}", text, re.MULTILINE | re.DOTALL)
    if target_rule and re.search(r"overflow:\s*(hidden|clip|auto|scroll)", target_rule.group("body")):
        fail(f"{prototype_name} annotation-target must not clip annotation markers")
    if not re.search(r"white-space:\s*nowrap", text):
        fail(f"{prototype_name} missing nowrap protection for compact controls and annotation toggles")

    annotation_ids = set(re.findall(r"data-annotation-id=[\"']([0-9]+)[\"']", text))
    if not annotation_ids:
        fail(f"{prototype_name} missing annotation ID values")
    if not ANNOTATION_NUMERAL_RE.search(text):
        fail(f"{prototype_name} missing circled annotation numbers in annotation dialogs or list")
    if len(annotation_ids) >= 2 and "②" not in text:
        fail(f"{prototype_name} missing matching ② note for the second marker")
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
            fail(f"PRD references missing prototype file: {ref}")


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
            fail(f"Mini Program prototype missing marker: {marker}")
    if "showScreen(" not in text and "showView(" not in text:
        fail("Mini Program prototype missing screen/state switching function")
    if "不是生产代码" not in text and "not production code" not in text.lower():
        fail("Prototype missing not-production-code label")
    if "待产包" in text:
        for marker in ("待审核", "免责声明"):
            if marker not in text:
                fail(f"Content-backed prototype missing marker: {marker}")
    external_refs = ("http://", "https://", "cdn.", "unpkg.com", "cdnjs.")
    if any(ref in text for ref in external_refs):
        fail("Prototype should be self-contained and avoid external network references")


def check_web_prototype(path: Path, language: str | None = None) -> None:
    prototypes = sorted(path.glob("prototype-web.html"))
    if not prototypes:
        return

    text = read(prototypes[0])
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
            fail(f"Web prototype missing marker: {marker}")
    if "不是生产代码" not in text and "not production code" not in text.lower():
        fail("Web prototype missing not-production-code label")
    for marker in ("未登录", "无权限", "错误", "加载"):
        if marker not in text:
            fail(f"Web prototype missing state marker: {marker}")
    if "fund-bff" in read(path / "prd.md") and "fund-bff" not in text:
        fail("Repo-backed Web prototype missing BFF boundary marker")
    external_refs = ("http://", "https://", "cdn.", "unpkg.com", "cdnjs.")
    if any(ref in text for ref in external_refs):
        fail("Web prototype should be self-contained and avoid external network references")


def check_mermaid(path: Path) -> None:
    prd_path = path / "prd.md"
    if not prd_path.exists():
        return
    text = read(prd_path)
    if "```mermaid" in text and "flowchart" not in text:
        fail("Mermaid block missing flowchart declaration")


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
    check_handoff_artifacts(folder)
    print(f"PM Copilot output validation passed: {folder}")


if __name__ == "__main__":
    main()
