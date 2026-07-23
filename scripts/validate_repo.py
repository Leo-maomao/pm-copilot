#!/usr/bin/env python3
"""Lightweight repository validator for PM Copilot."""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRS = [
    "adapters",
    "agents",
    "skills",
    "context",
    "indexes",
    "policies",
    "prompts",
    "workflow",
    "artifacts",
    "tools",
    "guardrails",
    "templates",
    "docs",
    "scripts",
]

REQUIRED_FILES = [
    "README.md",
    "README.en.md",
    "PM_COPILOT.md",
    ".gitattributes",
    "LICENSE",
    "VERSION",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "requirements-dev.txt",
    "workflow/main-workflow.md",
    "workflow/context-loading.md",
    "workflow/execution-handoff-workflow.md",
    "workflow/delivery-check-workflow.md",
    "artifacts/artifact-contracts.md",
    "artifacts/dev-task-contract.md",
    "artifacts/launch-decision-contract.md",
    "artifacts/prd-contract.md",
    "artifacts/ui-delivery-contract.md",
    "artifacts/structured-catalog-contract.md",
    "artifacts/tool-result-contract.md",
    "artifacts/trace-contract.md",
    "artifacts/tracking-plan-contract.md",
    "tools/tool-registry.yaml",
    "tools/handoff-tooling.md",
    "tools/launch-tooling.md",
    "tools/repo-context-tooling.md",
    "tools/research-tooling.md",
    "tools/ui-delivery-tooling.md",
    "tools/tool-use-protocol.md",
    "tools/validation-tooling.md",
    "guardrails/guardrails.md",
    "guardrails/failover.md",
    "context/product-context.example.yaml",
    "context/product-memory.example.yaml",
    "context/user-preferences.example.yaml",
    "context/decision-log.example.yaml",
    "context/memory-model.md",
    "indexes/runtime-routing.yaml",
    "policies/role-boundary.md",
    "policies/rule-governance.md",
    "prompts/prompt-system.md",
    "docs/direct-use.md",
    "docs/embedded-use.md",
    "docs/use-cases.md",
    "docs/output-gallery.md",
    "docs/agent-modes.md",
    "docs/agent-system-references.md",
    "docs/optimization-playbook.md",
    "docs/practice-self-iteration.md",
    "docs/self-improvement-system.md",
    "docs/failure-taxonomy.md",
    "docs/quality-rubric.md",
    "templates/agent-run-log-template.yaml",
    "templates/dev-tasks-template.yaml",
    "templates/evaluation-case-template.md",
    "templates/optimization-cycle-template.yaml",
    "templates/launch-decision-template.yaml",
    "templates/direct-request-template.md",
    "templates/document-prototype-template.html",
    "templates/prd-template.md",
    "templates/implemented-feature-prd-template.md",
    "templates/structured-catalog-template.md",
    "templates/tracking-plan-template.csv",
    "scripts/install_adapter.py",
    "scripts/extract_ui_region.py",
    "scripts/inspect_host_frontend.py",
    "scripts/preflight_tools.py",
    "scripts/agent_improvement_scorecard.py",
    "scripts/analyze_agent_run_evidence.py",
    "scripts/run_delivery_checks.py",
    "scripts/setup_visual_validation.py",
    "scripts/render_prd_html.py",
    "scripts/validate_outputs.py",
    "scripts/validate_agent_trace.py",
    "scripts/validate_runtime_routing.py",
    "scripts/evaluate_agent_loop.py",
    "scripts/test_agent_loop.py",
    "scripts/test_prd_contract.py",
    "scripts/test_prd_media_rendering.py",
    "scripts/test_reflection_learning_trace.py",
    "scripts/validate_prototype_visual.py",
    "scripts/validate_ui_preview.py",
    "docs/implemented-feature-prd-workflow.md",
    "vendor/mermaid/LICENSE",
    "vendor/mermaid/README.md",
    "vendor/mermaid/mermaid.min.js",
    "skills/skill-cleaner/SKILL.md",
    "skills/skill-cleaner/scripts/skill_cleaner.py",
    "adapters/codex/AGENTS.snippet.md",
    "adapters/claude-code/CLAUDE.snippet.md",
    "adapters/cursor/.cursor/rules/pm-copilot.mdc",
    "adapters/cursor/CURSOR_RULE.snippet.md",
    "agents/agent-operating-model.md",
    "agents/ui-delivery-agent.md",
]

TRACKING_COLUMNS = [
    "event_name",
    "description",
    "trigger",
    "platform",
    "actor",
    "required_properties",
    "optional_properties",
    "success_criteria",
    "validation_notes",
    "privacy_notes",
]

BINARY_SUFFIXES = {
    ".avif",
    ".docx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".pptx",
    ".webp",
    ".xls",
    ".xlsx",
    ".zip",
}

IGNORED_FILE_NAMES = {
    ".DS_Store",
    "Thumbs.db",
}

IGNORED_DIR_NAMES = {
    ".pytest_cache",
    "__pycache__",
}

IGNORED_TEXT_SCAN_DIR_NAMES = {
    "assets",
    "tool-results",
    "visual-review",
    "vendor",
}

REFERENCE_FIXTURE_ALLOWED_PREFIXES = (
    "evals/",
    "outputs/",
)

LOCAL_MACHINE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"("
    r"/Users/(?!<you>)[A-Za-z0-9._-]+/[^\s`'\"<>)]*"
    r"|/home/(?!<you>)[A-Za-z0-9._-]+/[^\s`'\"<>)]*"
    r"|[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\[^\s`'\"<>)]*"
    r")"
)

MACHINE_PATH_RE = re.compile(r"^[A-Za-z0-9._@+/-]+$")
PROPERTY_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

SELF_ITERATION_CORE_PREFIXES = (
    "PM_COPILOT.md",
    ".github/workflows/",
    "adapters/",
    "agents/",
    "artifacts/",
    "indexes/",
    "docs/practice-self-iteration.md",
    "docs/optimization-playbook.md",
    "docs/release-checklist.md",
    "docs/self-improvement-system.md",
    "docs/versioning.md",
    "guardrails/",
    "prompts/",
    "policies/",
    "scripts/",
    "skills/",
    "templates/",
    "tools/",
    "workflow/",
)
SELF_ITERATION_RELEASE_METADATA = ("VERSION", "CHANGELOG.md")
SELF_ITERATION_RECORD_PREFIXES = ("docs/optimization-cycles/",)

FORBIDDEN_OBSOLETE_PATHS = (
    "workflow/package-workflow.md",
    "agents/" + "prototype-agent.md",
    "tools/" + "prototype-tooling.md",
    "docs/migration-3.0.md",
    "docs/migration-3.1.md",
    "artifacts/" + "prototype-contract.md",
    "skills/" + "multi-platform-prototype",
)

FORBIDDEN_CURRENT_SOURCE_TOKENS = (
    "--allow-" + "legacy-run-id",
    "--strict-" + "agent-trace",
    "compatibility_" + "command:",
    "strict_agent_" + "trace_command:",
    "agents/" + "prototype-agent.md",
    "tools/" + "prototype-tooling.md",
    "artifacts/" + "prototype-contract.md",
    "skills/" + "multi-platform-prototype",
    "self_contained_html_" + "from_host_code",
    "compatibility_html_" + "review_artifact",
    "S0" + "-S12",
)

REQUIRED_AGENT_SECTIONS = [
    "Purpose",
    "Responsibilities",
    "Inputs",
    "Outputs",
    "Completion Criteria",
    "Handoffs",
]

REQUIRED_TOOL_STATUS_VALUES = [
    "available",
    "setup_required",
    "unavailable",
    "skipped",
    "external_runtime",
    "not_applicable",
]

EXPECTED_TOOL_IDS = [
    "repo_context.file_read",
    "repo_context.git_inspection",
    "research.web_search",
    "validation.repo",
    "validation.outputs",
    "validation.visual",
    "ui_delivery.source_extract",
    "validation.html",
    "validation.delivery_orchestrator",
    "validation.agent_trace",
    "analysis.agent_runs",
    "optimization.scorecard",
    "handoff.dev_tasks",
    "launch.decision_support",
]

REQUIRED_TEXT_TOKENS = {
    "PM_COPILOT.md": [
        "AI Product Manager Agent System",
        "policies/role-boundary.md",
        "indexes/runtime-routing.yaml",
        "task_mode",
        "autonomy_level",
        "Generalization Boundary",
        "reference projects are fixtures",
        "engineering handoff",
        "launch status",
        "content source",
        "navigation visibility",
        "indexes/runtime-routing.yaml",
        "auxiliary PM agent work",
        "validate_outputs.py",
        "preflight_tools.py",
        "run_delivery_checks.py",
        "agent_improvement_scorecard.py",
        "validate_agent_trace.py",
        "analyze_agent_run_evidence.py",
        "tool-registry.yaml",
        "tool-result-contract.md",
        "setup_visual_validation.py",
        "validate_prototype_visual.py",
        "validate_ui_preview.py",
        "runtime-routing.yaml",
        "dev-tasks.yaml",
        "launch-decision.yaml",
        "structured-catalog-contract.md",
        "structured-catalog-template.md",
        "implemented-feature-prd-template.md",
        "render_prd_html.py",
        "占位图",
        "Mermaid",
        "pure text",
    ],
    "README.md": [
        "README.en.md",
        "AI 产品经理 Agent 系统",
        "agents/agent-operating-model.md",
        "docs/use-cases.md",
        "docs/output-gallery.md",
        "docs/agent-modes.md",
        "语言支持",
        "validate_outputs.py",
        "preflight_tools.py",
        "run_delivery_checks.py",
        "agent_improvement_scorecard.py",
        "validate_agent_trace.py",
        "analyze_agent_run_evidence.py",
        "tool-registry.yaml",
        "tool-result-contract.md",
        "setup_visual_validation.py",
        "validate_prototype_visual.py",
        "validate_ui_preview.py",
        "runtime-routing.yaml",
        "render_prd_html.py",
        "占位图",
        "dev-tasks.yaml",
        "launch-decision.yaml",
        "微状态",
    ],
    "README.en.md": [
        "README.md",
        "AI Product Manager Agent System",
        "agents/agent-operating-model.md",
        "docs/use-cases.md",
        "docs/output-gallery.md",
        "docs/agent-modes.md",
        "Language Support",
        "validate_outputs.py",
        "preflight_tools.py",
        "run_delivery_checks.py",
        "agent_improvement_scorecard.py",
        "validate_agent_trace.py",
        "analyze_agent_run_evidence.py",
        "tool-registry.yaml",
        "tool-result-contract.md",
        "setup_visual_validation.py",
        "validate_prototype_visual.py",
        "validate_ui_preview.py",
        "runtime-routing.yaml",
        "render_prd_html.py",
        "占位图",
        "dev-tasks.yaml",
        "launch-decision.yaml",
        "micro-states",
    ],
    "docs/direct-use.md": [
        "validate_outputs.py",
        "preflight_tools.py",
        "run_delivery_checks.py",
        "agent_improvement_scorecard.py",
        "setup_visual_validation.py",
        "visual diff",
        "validate_ui_preview.py",
        "extract_ui_region.py",
        "render_prd_html.py",
        "占位图",
        "dev-tasks.yaml",
        "launch-decision.yaml",
    ],
    "prompts/prompt-system.md": [
        "Prompt Stack",
        "Request Classification",
        "task_mode",
        "autonomy_level",
        "effort_budget",
        "delegation_plan",
        "termination_condition",
        "Agent operating model",
        "Agent interface contract",
        "Memory Use",
        "Clarification Prompt Rules",
        "Memory Update Prompt Rules",
        "资料卡片-加载中.png",
    ],
    "agents/agent-interface.md": [
        "Runtime Protocol",
        "Mutation Boundaries",
        "Exit Checklist",
        "alternatives",
        "next_actions",
        "status: complete",
        "artifact_delta",
        "validation_delta",
    ],
    "context/memory-model.md": [
        "Product Memory",
        "User Preference Memory",
        "Decision Log",
        "Priority Rules",
        "Write Rules",
    ],
    "workflow/main-workflow.md": [
        "Agent Execution Graph",
        "Graph Nodes",
        "Routing Rules",
        "Common Subgraphs",
        "Loop Integration",
        "task_mode",
        "autonomy_level",
        "effort_budget",
        "delegation_plan",
        "termination_condition",
        "evaluate_agent_loop.py",
        "run_delivery_checks.py",
    ],
    "workflow/delivery-check-workflow.md": [
        "PM Usefulness Review",
        "task_mode",
        "autonomy_level",
        "run_delivery_checks.py",
        "dev-tasks.yaml",
        "launch-decision.yaml",
    ],
    "artifacts/artifact-contracts.md": [
        "Default Delivery",
        "Requirement details",
        "Tracking Plan",
        "UI Deliverable",
        "Engineering and Launch Handoff",
        "Structured References",
        "Document Prototype",
        "structured-catalog-contract.md",
        "tool-result-contract.md",
        "tool-results",
        "Optional Exports",
        "资料卡片-加载中.png",
    ],
    "artifacts/tool-result-contract.md": [
        "tool_id:",
        "status:",
        "artifacts_created:",
        "Prohibited Claims",
    ],
    "artifacts/structured-catalog-contract.md": [
        "artifact_type: structured_catalog",
        "structured_reference",
        "catalog.md",
        "catalog.html",
        "reference.md",
        "document_prototype",
        "item_id",
        "model_id",
        "source_status",
        "review_status",
        "implementation_notes",
    ],
    "artifacts/dev-task-contract.md": [
        "dev-tasks.yaml",
        "ready_for_issue",
        "source_requirements",
    ],
    "artifacts/launch-decision-contract.md": [
        "launch-decision.yaml",
        "decision_owner_required",
        "ready_to_launch",
    ],
    "artifacts/trace-contract.md": [
        "agent_strategy:",
        "task_mode:",
        "autonomy_level:",
        "effort_budget:",
        "delegation_plan:",
        "resume_checkpoint:",
        "termination_condition:",
        "tool_plan:",
        "decision_record:",
        "replan_triggers:",
        "review_loop:",
        "loop_policy:",
        "loop_state:",
        "iteration_trace:",
        "loop_summary:",
        "memory_candidates:",
        "action_closure:",
        "request_source:",
        "readiness:",
        "external_research:",
        "style_evidence:",
        "existing_ui_visual_baseline:",
        "design_calibration:",
        "content_sources:",
        "structured_catalog:",
        "structured_reference:",
        "tool_preflight:",
        "agent_transitions:",
        "last_reliable_state:",
        "resume_source:",
        "visual_validation:",
        "handoff_artifacts:",
        "security_and_audit:",
        "review_findings:",
        "validation_results:",
    ],
    "templates/agent-run-log-template.yaml": [
        "agent_strategy:",
        "task_mode:",
        "autonomy_level:",
        "effort_budget:",
        "delegation_plan:",
        "resume_checkpoint:",
        "termination_condition:",
        "success_criteria:",
        "tool_plan:",
        "decision_record:",
        "replan_triggers:",
        "review_loop:",
        "loop_policy:",
        "loop_state:",
        "iteration_trace:",
        "loop_summary:",
        "memory_candidates:",
        "next_actions:",
        "action_closure:",
        "request_source:",
        "readiness:",
        "external_research:",
        "engineering_handoff_status:",
        "launch_status:",
        "surface_decisions:",
        "style_evidence:",
        "existing_ui_visual_baseline:",
        "design_calibration:",
        "content_sources:",
        "structured_catalog:",
        "structured_reference:",
        "tool_preflight:",
        "agent_transitions:",
        "last_reliable_state:",
        "resume_source:",
        "visual_validation:",
        "handoff_artifacts:",
        "security_and_audit:",
        "review_findings:",
    ],
    "templates/structured-catalog-template.md": [
        "artifact_type: structured_catalog",
        "structured_reference",
        "attention_points",
        "source_status",
        "review_status",
        "item_id",
        "model_id",
        "required_parameters",
        "implementation_notes",
    ],
    "templates/dev-tasks-template.yaml": [
        "ready_for_issue:",
        "source_requirements:",
        "validation_commands:",
    ],
    "templates/launch-decision-template.yaml": [
        "decision_owner_required:",
        "visual_validation:",
        "rollback_plan:",
    ],
    "templates/prd-template.md": [
        "# <一句话需求> - <YYYY-MM-DD>",
        "## 1. <产品决策摘要>",
        "<置信度>",
        "## 4. <范围与非目标>",
        "## 5. <需求详情>",
        "<界面与交互>",
        "## 7. <风险、决策与待确认>",
        "## 8. <验收与就绪度>",
    ],
    "templates/evaluation-case-template.md": [
        "Agentic Expectation Matrix",
        "Fixture Scope",
        "PM User Type",
        "Risk Profile",
        "Fixture Isolation Terms",
        "Artifact Expectation Matrix",
        "generalization boundary",
        "PRD status, engineering handoff status, and launch status",
        "Reference or regulated content records source status",
        "Review findings include artifact, evidence, owner",
        "Validation results are concrete and consistent",
    ],
    "agents/agent-operating-model.md": [
        "Observe -> Frame -> Decide -> Act -> Verify -> Learn",
        "Task Modes",
        "Autonomy Levels",
        "Replanning Triggers",
        "Final Delivery Contract",
        "Effort Budgets",
        "Delegation Model",
        "Resume Checkpoints",
        "Termination Conditions",
        "prd_delivery",
        "implemented_feature_prd",
        "self_improvement",
    ],
    "docs/use-cases.md": [
        "Implemented Feature To PRD",
        "Launch Readiness",
        "Structured Reference",
        "python3 scripts/run_delivery_checks.py",
    ],
    "docs/output-gallery.md": [
        "PRD Markdown",
        "UI Delivery",
        "Development Tasks",
        "Launch Decision",
        "Structured Reference",
        "Run Log",
    ],
    "docs/agent-modes.md": [
        "Task Modes",
        "Autonomy Levels",
        "clarify-first",
        "draft-with-risk",
        "full-loop",
        "self-iteration",
    ],
    "docs/agent-system-references.md": [
        "OpenAI Agents SDK",
        "Anthropic",
        "LangGraph",
        "AutoGen",
        "validation.agent_trace",
        "analysis.agent_runs",
        "bounded Loop",
        "termination",
    ],
    "scripts/validate_agent_trace.py": [
        "TASK_MODES",
        "AUTONOMY_LEVELS",
        "EFFORT_BUDGETS",
        "termination_condition",
        "ACTION_DUE_PHASES",
        "ACTION_STATUSES",
        "LOOP_TYPES",
        "ITERATION_OUTCOMES",
        "LOOP_NEXT_DECISIONS",
    ],
    "scripts/evaluate_agent_loop.py": [
        "nested_section",
        "stop_needs_input",
        "stop_blocked",
        "stop_no_progress",
        "stop_human_checkpoint",
        "iteration budget exhausted",
        "tool-call budget exhausted",
    ],
    "scripts/test_agent_loop.py": [
        "human_checkpoint_precedes_success",
        "iteration_budget",
        "tool_budget",
        "time_budget",
        "invalid_budget",
    ],
    "scripts/test_reflection_learning_trace.py": [
        "missing_final_recommendation",
        "unresolved_severe_finding",
        "unrelated_severe_closure",
        "unsafe_sensitive_memory",
        "self_improvement_without_regression",
    ],
    "scripts/test_prd_media_rendering.py": [
        "mov_becomes_video",
        "mov_has_controls",
        "mov_has_mime",
        "mov_keeps_fallback_link",
        "non_video_link_unchanged",
        "failed_conversion_keeps_source",
    ],
    "agents/ui-delivery-agent.md": [
        "UI Delivery Agent",
        "reviewable UI evidence",
        "read-only",
        "portable",
    ],
    "evals/bounded-agent-loop-eval.md": [
        "bounded Agent Loop",
        "false-progress",
        "human checkpoint",
        "stop_needs_input",
        "stop_blocked",
    ],
    "evals/fixtures/agent-runtime-delivery-pass/run-log.yaml": [
        "agent_strategy:",
        "loop_policy:",
        "stop_needs_input",
        "stopped_before_generation: true",
        "must_answer_before_generation:",
    ],
    "scripts/analyze_agent_run_evidence.py": [
        "AGENTIC_FIELDS",
        "PRD_AGENTIC_MARKERS",
        "agentic_trace_completion_rate",
    ],
    "tools/tool-registry.yaml": [
        "validation.delivery_orchestrator",
        "validation.visual",
        "setup_visual_validation.py",
        "run_delivery_checks.py",
        "preflight_tools.py",
        "validate_ui_preview.py",
        "extract_ui_region.py",
        "artifacts/tool-result-contract.md",
    ],
    "tools/tool-use-protocol.md": [
        "tool-registry.yaml",
        "tool-result-contract.md",
        "preflight_tools.py",
        "run_delivery_checks.py",
    ],
    "tools/validation-tooling.md": [
        "run_delivery_checks.py",
        "validate_outputs.py",
        "validate_prototype_visual.py",
        "validate_ui_preview.py",
        "render_prd_html.py",
    ],
    "skills/prd-writing/SKILL.md": [
        "资料卡片-加载中.png",
    ],
    "artifacts/prd-contract.md": [
        "资料卡片-加载中.png",
    ],
    "docs/implemented-feature-prd-workflow.md": [
        "Output Folder",
        "render_prd_html.py",
        "占位图",
        "assets/mermaid.min.js",
        "pure-text",
    ],
    "templates/implemented-feature-prd-template.md": [
        "# <一句话需求> - <YYYY-MM-DD>",
        "## 1. <产品决策摘要>",
        "<实现与产品意图一致度>",
        "## 5. <需求详情>",
        "<界面与交互>",
        "## 9. <实现证据与覆盖映射>",
        "## 10. <验证结果>",
        "占位图",
    ],
    "scripts/render_prd_html.py": [
        "pagetitle",
        "image-lightbox",
        "IntersectionObserver",
        "mermaid.min.js",
    ],
    "scripts/validate_outputs.py": [
        "check_prd_output_contract",
        "GENERIC_STATE_SUFFIX_RE",
        "DETACHED_IMAGE_SECTION_RE",
        "check_prd_flow_sections",
        "check_prd_copy_i18n_sections",
    ],
    "requirements-dev.txt": [
        "playwright",
    ],
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def check_required_paths() -> None:
    for directory in REQUIRED_DIRS:
        path = ROOT / directory
        if not path.is_dir():
            fail(f"Missing required directory: {directory}")

    for file_name in REQUIRED_FILES:
        path = ROOT / file_name
        if not path.is_file():
            fail(f"Missing required file: {file_name}")


def check_obsolete_runtime_removed() -> None:
    for relative_path in FORBIDDEN_OBSOLETE_PATHS:
        if (ROOT / relative_path).exists():
            fail(f"Obsolete runtime path must be removed: {relative_path}")

    current_paths = [
        ROOT / "PM_COPILOT.md",
        ROOT / "README.md",
        ROOT / "README.en.md",
        ROOT / "agents",
        ROOT / "artifacts",
        ROOT / "prompts",
        ROOT / "scripts",
        ROOT / "templates",
        ROOT / "tools",
        ROOT / "workflow",
    ]
    for root in current_paths:
        paths = [root] if root.is_file() else sorted(root.rglob("*"))
        for path in paths:
            if not path.is_file() or path.suffix not in {".md", ".py", ".yaml", ".yml"}:
                continue
            text = path.read_text(encoding="utf-8")
            for token in FORBIDDEN_CURRENT_SOURCE_TOKENS:
                if token in text:
                    fail(
                        f"Obsolete runtime token '{token}' found in "
                        f"{path.relative_to(ROOT)}"
                    )


def check_contract_template_alignment() -> None:
    for relative_path, tokens in REQUIRED_TEXT_TOKENS.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        lowered_text = text.lower()
        for token in tokens:
            if token.lower() not in lowered_text:
                fail(f"Missing required token '{token}' in {relative_path}")


def check_agent_definitions() -> None:
    for agent_path in sorted((ROOT / "agents").glob("*-agent.md")):
        text = agent_path.read_text(encoding="utf-8")
        for section in REQUIRED_AGENT_SECTIONS:
            marker = f"## {section}"
            if marker not in text:
                fail(f"Agent definition missing '{marker}': {agent_path.relative_to(ROOT)}")
        if "status" not in text.lower():
            fail(f"Agent definition does not reference handoff status: {agent_path.relative_to(ROOT)}")


def markdown_table_value(text: str, field: str) -> str:
    match = re.search(rf"^\|\s*{re.escape(field)}\s*\|\s*(.*?)\s*\|", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def markdown_section(text: str, heading: str) -> str:
    match = re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end].strip()


def fixture_isolation_terms(text: str) -> list[str]:
    terms: list[str] = []
    for raw_line in markdown_section(text, "Fixture Isolation Terms").splitlines():
        match = re.match(r"^\s*-\s+(.+?)\s*$", raw_line)
        if not match:
            continue
        term = match.group(1).split("#", 1)[0].strip().strip("`\"'")
        if term and not term.startswith("<"):
            terms.append(term)
    return terms


def collect_reference_fixture_terms() -> list[str]:
    terms: list[str] = []
    for eval_path in sorted((ROOT / "evals").glob("*.md")):
        text = eval_path.read_text(encoding="utf-8")
        if "fixture-scoped" in markdown_table_value(text, "Fixture Scope").lower():
            terms.extend(fixture_isolation_terms(text))
    deduped: dict[str, str] = {}
    for term in terms:
        deduped.setdefault(term.lower(), term)
    return list(deduped.values())


def check_tool_registry() -> None:
    registry_path = ROOT / "tools/tool-registry.yaml"
    text = registry_path.read_text(encoding="utf-8")
    for status in REQUIRED_TOOL_STATUS_VALUES:
        if not re.search(rf"^\s+- {re.escape(status)}\s*$", text, re.MULTILINE):
            fail(f"Tool registry missing status value: {status}")

    tool_ids = re.findall(r"^\s+- id:\s*([A-Za-z0-9_.-]+)\s*$", text, re.MULTILINE)
    if len(tool_ids) != len(set(tool_ids)):
        fail("Tool registry contains duplicate capability IDs")
    for tool_id in EXPECTED_TOOL_IDS:
        if tool_id not in tool_ids:
            fail(f"Tool registry missing capability ID: {tool_id}")

    for marker in ("strict_command:", "network_required_command:", "result_contract:"):
        if marker not in text:
            fail(f"Tool registry missing marker: {marker}")


def check_preflight_tool_alignment() -> None:
    registry_text = (ROOT / "tools/tool-registry.yaml").read_text(encoding="utf-8")
    registry_ids = set(re.findall(r"^\s+- id:\s*([A-Za-z0-9_.-]+)\s*$", registry_text, re.MULTILINE))

    preflight_text = (ROOT / "scripts/preflight_tools.py").read_text(encoding="utf-8")
    preflight_ids = set(re.findall(r"capability\(\s*\n\s*\"([A-Za-z0-9_.-]+)\"", preflight_text))

    missing = sorted(registry_ids - preflight_ids)
    extra = sorted(preflight_ids - registry_ids)
    if missing:
        fail(f"preflight_tools.py missing registry capability IDs: {', '.join(missing)}")
    if extra:
        fail(f"preflight_tools.py has unregistered capability IDs: {', '.join(extra)}")


def check_gitignore_does_not_hide_regression_assets() -> None:
    gitignore_path = ROOT / ".gitignore"
    if not gitignore_path.is_file():
        return
    ignored_public_assets = {
        "docs/",
        "scripts/",
        "templates/",
        "skills/",
        "workflow/",
        "artifacts/",
        "tools/",
        "guardrails/",
    }
    for line_number, raw_line in enumerate(gitignore_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if line in ignored_public_assets:
            fail(f".gitignore must not hide public PM Copilot assets ({line}) at line {line_number}")


def strip_yaml_comment(line: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(line):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return line[:index]
    return line


def check_yaml_template_duplicate_keys() -> None:
    key_re = re.compile(r"^(\s*)(-\s+)?([A-Za-z_][A-Za-z0-9_-]*):")

    for yaml_path in sorted((ROOT / "templates").glob("*.yaml")):
        stack: list[tuple[int, set[str], str]] = [(-1, set(), "<root>")]
        for line_number, raw_line in enumerate(yaml_path.read_text(encoding="utf-8").splitlines(), 1):
            without_comment = strip_yaml_comment(raw_line).rstrip()
            if not without_comment.strip():
                continue

            match = key_re.match(without_comment)
            if not match:
                continue

            indent = len(match.group(1))
            is_list_item = bool(match.group(2))
            key = match.group(3)

            if is_list_item:
                while stack and stack[-1][0] >= indent:
                    stack.pop()
                stack.append((indent + 1, set(), "<list-item>"))
                effective_indent = indent + 2
            else:
                effective_indent = indent
                while stack and stack[-1][0] >= effective_indent:
                    stack.pop()

            current_keys = stack[-1][1]
            if key in current_keys:
                fail(
                    f"Duplicate YAML key '{key}' in {yaml_path.relative_to(ROOT)} "
                    f"at line {line_number}"
                )
            current_keys.add(key)

            value = without_comment.split(":", 1)[1].strip()
            if not value:
                stack.append((effective_indent, set(), key))


def check_quality_threshold_alignment() -> None:
    template = (ROOT / "templates/agent-run-log-template.yaml").read_text(encoding="utf-8")
    rubric = (ROOT / "docs/quality-rubric.md").read_text(encoding="utf-8")

    expected = {
        "delivery": (32, 23),
        "prd": (40, 31),
        "metrics_and_tracking": (28, 21),
        "ui_delivery": (32, 24),
        "review_checklist": (20, 15),
    }

    for key, (max_score, threshold) in expected.items():
        if not re.search(
            rf"{re.escape(key)}:\n\s+score:\s+null\n\s+max_score:\s+{max_score}\b",
            template,
        ):
            fail(f"Run-log template max score mismatch for {key}")
        if not re.search(rf"^\s+{re.escape(key)}:\s+{threshold}\b", template, re.MULTILINE):
            fail(f"Run-log template threshold mismatch for {key}")

    rubric_checks = [
        ("delivery", "23 / 32"),
        ("PRD", "31 / 40"),
        ("analytics", "21 / 28"),
        ("UI delivery", "24 / 32"),
        ("review", "15 / 20"),
    ]
    for label, score_text in rubric_checks:
        if score_text not in rubric:
            fail(f"Quality rubric missing {label} threshold {score_text}")


def check_reference_fixture_boundary() -> None:
    """Keep borrowed host-project evidence out of the universal PM Copilot surface."""
    normalized_terms = [(term, term.lower()) for term in collect_reference_fixture_terms()]
    for path in ROOT.rglob("*"):
        if should_skip_text_file(path):
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path.startswith(REFERENCE_FIXTURE_ALLOWED_PREFIXES):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        local_path_match = LOCAL_MACHINE_PATH_RE.search(text)
        if local_path_match:
            fail(
                "Local machine path found outside evals/outputs: "
                f"{local_path_match.group(1)!r} in {relative_path}"
            )
        lowered_text = text.lower()
        for term, lowered_term in normalized_terms:
            if lowered_term in lowered_text:
                fail(
                    "Reference fixture leakage found outside evals/outputs: "
                    f"{term!r} in {relative_path}"
                )


def check_agent_operating_model() -> None:
    model_path = ROOT / "agents/agent-operating-model.md"
    if not model_path.is_file():
        fail("Missing agents/agent-operating-model.md")

    required_references = {
        "PM_COPILOT.md": ("agents/agent-operating-model.md", "Observe -> Frame -> Decide -> Act -> Verify -> Learn"),
        "README.md": ("agents/agent-operating-model.md",),
        "README.en.md": ("agents/agent-operating-model.md",),
        "workflow/main-workflow.md": ("agents/agent-operating-model.md", "execution graph"),
        "prompts/prompt-system.md": ("agents/agent-operating-model.md",),
    }
    for relative_path, tokens in required_references.items():
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        lowered_text = text.lower()
        for token in tokens:
            if token.lower() not in lowered_text:
                fail(f"{relative_path} does not reference Agent operating model token: {token}")


def check_readme_agent_positioning() -> None:
    forbidden = ("agent workflow kit", "workflow kit")
    required = {
        "README.md": "AI 产品经理 Agent 系统",
        "README.en.md": "AI Product Manager Agent System",
    }
    for relative_path, required_token in required.items():
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        first_screen = "\n".join(text.splitlines()[:32]).lower()
        if required_token.lower() not in first_screen:
            fail(f"{relative_path} first screen does not position PM Copilot as an Agent system")
        for token in forbidden:
            if token in first_screen:
                fail(f"{relative_path} still leads with old workflow-kit positioning: {token}")
        if "what it does" not in first_screen and "它能做什么" not in first_screen:
            fail(f"{relative_path} first screen does not foreground practical PM outcomes")


def check_changelog_no_pending_markers() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if "Commit: pending" in changelog:
        fail("CHANGELOG.md contains stale 'Commit: pending' marker")


def check_scorecard_not_stale() -> None:
    scorecard_path = ROOT / "outputs/improvement-scorecard.json"
    if not scorecard_path.exists():
        return
    try:
        scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"outputs/improvement-scorecard.json is not valid JSON: {exc}")

    recorded_total = scorecard.get("eval_quality", {}).get("total")
    actual_total = len(list((ROOT / "evals").glob("*.md")))
    if recorded_total != actual_total:
        fail(
            "outputs/improvement-scorecard.json is stale: "
            f"eval_quality.total={recorded_total}, actual eval files={actual_total}"
        )

    latest_eval_mtime = max((path.stat().st_mtime for path in (ROOT / "evals").glob("*.md")), default=0)
    if scorecard_path.stat().st_mtime < latest_eval_mtime:
        fail("outputs/improvement-scorecard.json is older than the latest eval case")


def check_adapter_snippets_alignment() -> None:
    essential_tokens = (
        "product-manager work such as PRD",
        "@pm-copilot",
        "do not modify host source",
        "do not modify host source",
        "structured reference or document prototype",
    )
    snippet_paths = [
        "adapters/codex/AGENTS.snippet.md",
        "adapters/claude-code/CLAUDE.snippet.md",
        "adapters/cursor/CURSOR_RULE.snippet.md",
        "adapters/cursor/.cursor/rules/pm-copilot.mdc",
    ]
    for relative_path in snippet_paths:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        for token in essential_tokens:
            if token not in text:
                fail(f"Adapter snippet drift in {relative_path}: missing {token!r}")

    install_text = (ROOT / "scripts/install_adapter.py").read_text(encoding="utf-8")
    for token in essential_tokens:
        if token not in install_text:
            fail(f"scripts/install_adapter.py missing adapter alignment token: {token!r}")


def check_no_orphan_one_off_plan_docs() -> None:
    one_off_docs = [
        ROOT / "docs/archive/real-run-ui-delivery-improvement-plan.md",
    ]
    for path in one_off_docs:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "Status: Archived" not in text:
            fail(
                f"{path.relative_to(ROOT)} is a one-off plan doc and must be archived "
                "or generalized into current docs"
            )


def check_version() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        fail(f"VERSION must use MAJOR.MINOR.PATCH format: {version}")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if version not in changelog:
        fail(f"CHANGELOG.md does not mention VERSION {version}")
    latest_match = re.search(r"^##\s+\[(\d+\.\d+\.\d+)\]", changelog, re.MULTILINE)
    if not latest_match:
        fail("CHANGELOG.md missing top-level version entry")
    if latest_match.group(1) != version:
        fail(
            "CHANGELOG.md latest version entry must match VERSION: "
            f"{latest_match.group(1)} != {version}"
        )


def check_self_iteration_release_guard() -> None:
    changed_paths = git_changed_paths()
    if not changed_paths:
        return

    core_changes = sorted(path for path in changed_paths if is_self_iteration_core_path(path))
    if not core_changes:
        return

    missing_metadata = [
        path for path in SELF_ITERATION_RELEASE_METADATA if path not in changed_paths
    ]
    if missing_metadata:
        fail(
            "PM Copilot core source changed without release metadata updates: "
            f"{', '.join(missing_metadata)}. Core changes: {', '.join(core_changes[:8])}"
        )

    if not any(path.startswith(SELF_ITERATION_RECORD_PREFIXES) for path in changed_paths):
        fail(
            "PM Copilot core source changed without an optimization-cycle note under "
            "docs/optimization-cycles/. Record source run, generalized failure, fix surface, "
            "validation, version change, remote-push status, and embedded-copy sync targets."
        )


def git_changed_paths() -> set[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all", "--", "."],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if result.returncode != 0:
        return set()

    paths: set[str] = set()
    for raw_line in result.stdout.splitlines():
        if len(raw_line) < 4:
            continue
        path = raw_line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        path = path.strip('"')
        if path:
            paths.add(path)
    return paths


def is_self_iteration_core_path(path: str) -> bool:
    parts = path.split("/")
    if "__pycache__" in parts or path.endswith((".pyc", ".pyo")):
        return False
    if path in SELF_ITERATION_RELEASE_METADATA:
        return False
    if path.startswith(SELF_ITERATION_RECORD_PREFIXES):
        return False
    if path.startswith("outputs/"):
        return False
    return any(
        path == prefix.rstrip("/") or path.startswith(prefix)
        for prefix in SELF_ITERATION_CORE_PREFIXES
    )


def check_skills() -> None:
    skill_dirs = sorted(path for path in (ROOT / "skills").iterdir() if path.is_dir())
    if not skill_dirs:
        fail("No skills found")

    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            fail(f"Missing SKILL.md in {skill_dir.relative_to(ROOT)}")
        text = skill_file.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            fail(f"Skill missing YAML frontmatter: {skill_file.relative_to(ROOT)}")
        name_match = re.search(r"^name:\s*(\S+)", text, re.MULTILINE)
        if not name_match:
            fail(f"Skill missing name: {skill_file.relative_to(ROOT)}")
        if name_match and name_match.group(1) != skill_dir.name:
            fail(
                f"Skill name '{name_match.group(1)}' must match directory "
                f"'{skill_dir.name}' in {skill_file.relative_to(ROOT)}"
            )
        if not re.search(r"^description:\s*.+", text, re.MULTILINE):
            fail(f"Skill missing description: {skill_file.relative_to(ROOT)}")
        for heading in ("## Goal", "## Workflow", "## Output", "## Quality Bar"):
            if heading not in text:
                fail(f"Skill missing required heading '{heading}': {skill_file.relative_to(ROOT)}")
        check_markdown_ordered_lists(skill_file, text)


def check_markdown_ordered_lists(path: Path, text: str) -> None:
    """Catch accidental duplicate or skipped explicit list numbers in public docs."""
    in_fence = False
    numbers: list[int] = []

    def flush() -> None:
        if len(numbers) < 2:
            numbers.clear()
            return
        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            fail(
                f"Ordered list numbering invalid in {path.relative_to(ROOT)}: "
                f"found {numbers}, expected {expected}"
            )
        numbers.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"^\d+\.\s+\S", line)
        if match:
            numbers.append(int(line.split(".", 1)[0]))
            continue
        flush()
    flush()


def check_tracking_plans() -> None:
    for csv_path in sorted((ROOT / "outputs").glob("*/tracking-plan.csv")):
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != TRACKING_COLUMNS:
                fail(f"Tracking columns invalid in {csv_path.relative_to(ROOT)}")
            rows = list(reader)
            if not rows:
                fail(f"Tracking plan has no rows: {csv_path.relative_to(ROOT)}")
            for row in rows:
                event_name = row["event_name"]
                if not PROPERTY_NAME_RE.match(event_name):
                    fail(f"Invalid event name '{event_name}' in {csv_path.relative_to(ROOT)}")
                for column in ("required_properties", "optional_properties"):
                    for property_name in parse_property_list(row[column]):
                        if not PROPERTY_NAME_RE.match(property_name):
                            fail(
                                f"Invalid property name '{property_name}' in "
                                f"{csv_path.relative_to(ROOT)}"
                            )

    for md_path in sorted((ROOT / "outputs").glob("*/tracking-plan.md")):
        text = md_path.read_text(encoding="utf-8")
        required_headers = [
            "event_name",
            "description",
            "trigger",
            "required_properties",
            "privacy_notes",
            "property_name",
            "privacy_level",
        ]
        for header in required_headers:
            if header not in text:
                fail(f"Tracking markdown missing '{header}' in {md_path.relative_to(ROOT)}")


def parse_property_list(value: str) -> list[str]:
    if not value:
        return []
    normalized = value.replace(";", ",").replace("|", ",")
    return [part.strip() for part in normalized.split(",") if part.strip()]


def check_user_flows() -> None:
    for md_path in sorted((ROOT / "outputs").glob("*/user-flow.md")):
        text = md_path.read_text(encoding="utf-8")
        if "```mermaid" not in text or "flowchart" not in text:
            fail(f"User flow markdown must include renderable Mermaid flowchart: {md_path.relative_to(ROOT)}")


def check_eval_cases() -> None:
    forbidden_required_artifacts = {
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
    required_metadata_fields = (
        "Case ID",
        "Scenario",
        "Platform",
        "Product Area",
        "Fixture Scope",
        "PM User Type",
        "Risk Profile",
    )
    for eval_path in sorted((ROOT / "evals").glob("*.md")):
        text = eval_path.read_text(encoding="utf-8")
        for field in required_metadata_fields:
            if not markdown_table_value(text, field):
                fail(f"Eval case missing metadata field '{field}': {eval_path.relative_to(ROOT)}")
        if "fixture-scoped" in markdown_table_value(text, "Fixture Scope").lower():
            if not fixture_isolation_terms(text):
                fail(
                    "Fixture-scoped eval must list ## Fixture Isolation Terms: "
                    f"{eval_path.relative_to(ROOT)}"
                )
        if "## Pass Criteria" not in text:
            fail(f"Eval case missing ## Pass Criteria: {eval_path.relative_to(ROOT)}")
        if not any(section in text for section in ("## Raw Request", "## Scenario Set", "## Context")):
            fail(f"Eval case missing raw request, scenario set, or context: {eval_path.relative_to(ROOT)}")
        if "## Raw Request" in text and "## Latest Result" not in text:
            fail(f"Single-scenario eval missing ## Latest Result: {eval_path.relative_to(ROOT)}")
        required_match = re.search(
            r"## Required Artifacts\n(?P<body>.*?)(?:\n## |\Z)",
            text,
            re.DOTALL,
        )
        if required_match:
            body = required_match.group("body")
            for artifact in forbidden_required_artifacts:
                if artifact in body:
                    fail(
                        f"Eval case requires forbidden default split artifact {artifact}: "
                        f"{eval_path.relative_to(ROOT)}"
                    )
        if (
            "validate_outputs.py" not in text
            and "run_delivery_checks.py" not in text
            and "pre-clarification" not in text.lower()
        ):
            fail(f"Eval case missing output validation expectation: {eval_path.relative_to(ROOT)}")


def check_text_files_are_utf8() -> None:
    for path in ROOT.rglob("*"):
        if should_skip_text_file(path):
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            fail(f"Non-UTF-8 file: {path.relative_to(ROOT)}")
        except IsADirectoryError:
            continue
        for index, char in enumerate(text):
            if char == "\n" or char == "\r" or char == "\t":
                continue
            if ord(char) < 32:
                fail(f"Control character in {path.relative_to(ROOT)} at offset {index}")


def check_machine_readable_paths() -> None:
    for path in ROOT.rglob("*"):
        if should_skip_machine_path(path):
            continue
        relative_path = path.relative_to(ROOT).as_posix()
        if not MACHINE_PATH_RE.match(relative_path):
            fail(f"Non-ASCII or unsupported character in path: {relative_path}")


def should_skip_text_file(path: Path) -> bool:
    if path.is_dir() or ".git" in path.parts:
        return True
    if path.name in IGNORED_FILE_NAMES:
        return True
    relative_parts = path.relative_to(ROOT).parts
    if relative_parts and relative_parts[0] == "vendor":
        return True
    if relative_parts and relative_parts[0] == "outputs":
        return any(part in IGNORED_TEXT_SCAN_DIR_NAMES for part in relative_parts)
    return any(part in IGNORED_DIR_NAMES for part in path.parts)


def should_skip_machine_path(path: Path) -> bool:
    if ".git" in path.parts:
        return True
    if path.name in IGNORED_FILE_NAMES:
        return True
    relative_parts = path.relative_to(ROOT).parts
    if relative_parts and relative_parts[0] == "outputs":
        return True
    return any(part in IGNORED_DIR_NAMES for part in path.parts)


def main() -> None:
    check_required_paths()
    check_obsolete_runtime_removed()
    check_contract_template_alignment()
    check_tool_registry()
    check_preflight_tool_alignment()
    check_gitignore_does_not_hide_regression_assets()
    check_agent_definitions()
    check_yaml_template_duplicate_keys()
    check_quality_threshold_alignment()
    check_reference_fixture_boundary()
    check_agent_operating_model()
    check_readme_agent_positioning()
    check_changelog_no_pending_markers()
    check_scorecard_not_stale()
    check_adapter_snippets_alignment()
    check_no_orphan_one_off_plan_docs()
    runtime_routing = subprocess.run(
        [sys.executable, "scripts/validate_runtime_routing.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if runtime_routing.returncode:
        fail(runtime_routing.stderr.strip() or runtime_routing.stdout.strip())
    check_version()
    check_self_iteration_release_guard()
    check_skills()
    check_tracking_plans()
    check_user_flows()
    check_eval_cases()
    check_text_files_are_utf8()
    check_machine_readable_paths()
    print("PM Copilot repository validation passed.")


if __name__ == "__main__":
    main()
