#!/usr/bin/env python3
"""Validate one generated PM Copilot output folder."""

from __future__ import annotations

import argparse
import re
import sys
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


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
    )
    for marker in required:
        if marker not in run_log:
            fail(f"Run log missing context marker: {marker}")


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
    if not generated_prototypes(path):
        return
    run_log = read(path / "run-log.yaml")
    if "visual_validation:" not in run_log and "validate_prototype_visual.py" not in run_log:
        fail("Run log missing visual_validation marker for prototype delivery")


def check_prototype_agent_and_style_trace(path: Path) -> None:
    prototypes = generated_prototypes(path)
    if not prototypes:
        return

    run_log = read(path / "run-log.yaml")
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
        check_annotation_marker_contract(read(prototype), prototype.name)

    if "source_mode: repo-backed" in run_log:
        for marker in (
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

        for prototype in prototypes:
            text = read(prototype)
            if "style-source-summary" not in text and "data-style-source" not in text:
                fail(
                    f"Repo-backed prototype missing style-source-summary or data-style-source: "
                    f"{prototype.name}"
                )


def check_annotation_marker_contract(text: str, prototype_name: str) -> None:
    if "annotation-marker" not in text:
        fail(f"{prototype_name} missing red annotation-marker badges")
    if "data-annotation-id" not in text:
        fail(f"{prototype_name} missing data-annotation-id mapping for annotation markers")
    if 'data-annotation-placement="top-right"' not in text and "data-annotation-placement='top-right'" not in text:
        fail(f"{prototype_name} missing top-right annotation placement metadata")
    if "annotation-target" not in text:
        fail(f"{prototype_name} missing annotation-target wrappers for component-corner markers")

    annotation_ids = set(re.findall(r"data-annotation-id=[\"']([0-9]+)[\"']", text))
    if not annotation_ids:
        fail(f"{prototype_name} missing annotation ID values")
    if not ANNOTATION_NUMERAL_RE.search(text):
        fail(f"{prototype_name} missing circled annotation numbers in side-panel notes")
    if len(annotation_ids) >= 2 and "②" not in text:
        fail(f"{prototype_name} missing matching side-panel ② note for the second marker")


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


def check_mini_program_prototype(path: Path) -> None:
    prototypes = sorted(path.glob("prototype-mini-program.html"))
    if not prototypes:
        return

    text = read(prototypes[0])
    check_annotation_marker_contract(text, prototypes[0].name)
    required = [
        "mini-capsule",
        "tabbar",
        "page-header",
        "note-group-title",
        "showScreen(",
        "onclick=",
    ]
    for marker in required:
        if marker not in text:
            fail(f"Mini Program prototype missing marker: {marker}")
    if "不是生产代码" not in text and "not production code" not in text.lower():
        fail("Prototype missing not-production-code label")
    if "待产包" in text:
        for marker in ("待审核", "免责声明"):
            if marker not in text:
                fail(f"Content-backed prototype missing marker: {marker}")
    external_refs = ("http://", "https://", "cdn.", "unpkg.com", "cdnjs.")
    if any(ref in text for ref in external_refs):
        fail("Prototype should be self-contained and avoid external network references")


def check_web_prototype(path: Path) -> None:
    prototypes = sorted(path.glob("prototype-web.html"))
    if not prototypes:
        return

    text = read(prototypes[0])
    check_annotation_marker_contract(text, prototypes[0].name)
    required = [
        "prototype-shell",
        "desktop-nav",
        "annotation-panel",
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
    check_default_option_trace(folder)
    check_scope_and_surface_trace(folder)
    check_visual_validation_trace(folder)
    check_prototype_agent_and_style_trace(folder)
    if args.language == "zh":
        check_chinese_prd(folder)
    check_tracking_context(folder)
    check_content_source(folder)
    check_mini_program_prototype(folder)
    check_web_prototype(folder)
    check_mermaid(folder)
    check_handoff_artifacts(folder)
    print(f"PM Copilot output validation passed: {folder}")


if __name__ == "__main__":
    main()
