#!/usr/bin/env python3
"""Lightweight repository validator for PM Copilot."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRS = [
    "adapters",
    "agents",
    "skills",
    "context",
    "prompts",
    "workflow",
    "artifacts",
    "tools",
    "guardrails",
    "templates",
    "evals",
    "docs",
    "scripts",
]

REQUIRED_FILES = [
    "README.md",
    "README.en.md",
    "PM_COPILOT.md",
    "LICENSE",
    "VERSION",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "workflow/main-workflow.md",
    "workflow/context-loading.md",
    "workflow/execution-handoff-workflow.md",
    "artifacts/artifact-contracts.md",
    "artifacts/dev-task-contract.md",
    "artifacts/launch-decision-contract.md",
    "artifacts/prd-contract.md",
    "artifacts/prototype-contract.md",
    "artifacts/tool-result-contract.md",
    "artifacts/trace-contract.md",
    "artifacts/tracking-plan-contract.md",
    "tools/tool-registry.yaml",
    "tools/handoff-tooling.md",
    "tools/launch-tooling.md",
    "tools/repo-context-tooling.md",
    "tools/research-tooling.md",
    "tools/tool-use-protocol.md",
    "tools/validation-tooling.md",
    "guardrails/guardrails.md",
    "guardrails/failover.md",
    "context/product-context.example.yaml",
    "context/product-memory.example.yaml",
    "context/user-preferences.example.yaml",
    "context/decision-log.example.yaml",
    "context/memory-model.md",
    "prompts/prompt-system.md",
    "docs/direct-use.md",
    "docs/embedded-use.md",
    "docs/optimization-playbook.md",
    "docs/failure-taxonomy.md",
    "docs/quality-rubric.md",
    "templates/agent-run-log-template.yaml",
    "templates/dev-tasks-template.yaml",
    "templates/evaluation-case-template.md",
    "templates/launch-decision-template.yaml",
    "templates/direct-request-template.md",
    "templates/prd-template.md",
    "templates/tracking-plan-template.csv",
    "scripts/install_adapter.py",
    "scripts/preflight_tools.py",
    "scripts/run_delivery_checks.py",
    "scripts/setup_visual_validation.py",
    "scripts/validate_outputs.py",
    "scripts/validate_prototype_visual.py",
    "adapters/codex/AGENTS.snippet.md",
    "adapters/claude-code/CLAUDE.snippet.md",
    "adapters/cursor/.cursor/rules/pm-copilot.mdc",
    "adapters/cursor/CURSOR_RULE.snippet.md",
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

MACHINE_PATH_RE = re.compile(r"^[A-Za-z0-9._@+/-]+$")
PROPERTY_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

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
    "validation.html",
    "validation.delivery_orchestrator",
    "handoff.dev_tasks",
    "launch.decision_support",
]

REQUIRED_TEXT_TOKENS = {
    "PM_COPILOT.md": [
        "engineering handoff",
        "launch status",
        "content source",
        "navigation visibility",
        "product-memory.local.yaml",
        "agent-interface.md",
        "validate_outputs.py",
        "preflight_tools.py",
        "run_delivery_checks.py",
        "tool-registry.yaml",
        "tool-result-contract.md",
        "setup_visual_validation.py",
        "validate_prototype_visual.py",
        "dev-tasks.yaml",
        "launch-decision.yaml",
    ],
    "README.md": [
        "README.en.md",
        "语言支持",
        "validate_outputs.py",
        "preflight_tools.py",
        "run_delivery_checks.py",
        "tool-registry.yaml",
        "tool-result-contract.md",
        "setup_visual_validation.py",
        "validate_prototype_visual.py",
        "dev-tasks.yaml",
        "launch-decision.yaml",
    ],
    "README.en.md": [
        "README.md",
        "Language Support",
        "validate_outputs.py",
        "preflight_tools.py",
        "run_delivery_checks.py",
        "tool-registry.yaml",
        "tool-result-contract.md",
        "setup_visual_validation.py",
        "validate_prototype_visual.py",
        "dev-tasks.yaml",
        "launch-decision.yaml",
    ],
    "docs/direct-use.md": [
        "validate_outputs.py",
        "preflight_tools.py",
        "run_delivery_checks.py",
        "setup_visual_validation.py",
        "visual diff",
        "dev-tasks.yaml",
        "launch-decision.yaml",
    ],
    "prompts/prompt-system.md": [
        "Prompt Stack",
        "Request Classification",
        "Agent interface contract",
        "Memory Use",
        "Clarification Prompt Rules",
        "Memory Update Prompt Rules",
    ],
    "agents/agent-interface.md": [
        "Runtime Protocol",
        "Mutation Boundaries",
        "Exit Checklist",
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
        "Readiness Model",
        "engineering handoff status",
        "launch status",
        "content source",
        "structured review findings",
        "Agent State And Handoff Discipline",
        "Resume And Idempotency",
        "Conflict Resolution",
        "Visual Prototype Validation",
        "Tool Preflight",
        "Delivery Orchestrator",
        "Execution Handoff",
    ],
    "artifacts/artifact-contracts.md": [
        "Default Delivery",
        "Requirement details",
        "Tracking Plan",
        "HTML Prototype",
        "Engineering and Launch Handoff",
        "tool-result-contract.md",
        "tool-results",
        "Optional Exports",
    ],
    "artifacts/tool-result-contract.md": [
        "tool_id:",
        "status:",
        "artifacts_created:",
        "Prohibited Claims",
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
        "request_source:",
        "readiness:",
        "external_research:",
        "style_evidence:",
        "existing_ui_visual_baseline:",
        "design_calibration:",
        "content_sources:",
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
        "tool_preflight:",
        "agent_transitions:",
        "last_reliable_state:",
        "resume_source:",
        "visual_validation:",
        "handoff_artifacts:",
        "security_and_audit:",
        "review_findings:",
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
        "<localized version history>",
        "<localized requirement input and confirmation record>",
        "<localized research and reference findings>",
        "<localized requirement details>",
        "<localized prototype reference>",
        "<localized validation results>",
    ],
    "templates/evaluation-case-template.md": [
        "PRD status, engineering handoff status, and launch status",
        "Reference or regulated content records source status",
        "Review findings include artifact, evidence, owner",
        "Validation results are concrete and consistent",
    ],
    "tools/tool-registry.yaml": [
        "validation.delivery_orchestrator",
        "validation.visual",
        "setup_visual_validation.py",
        "run_delivery_checks.py",
        "preflight_tools.py",
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
        "prototype": (32, 24),
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
        ("prototype", "24 / 32"),
        ("review", "15 / 20"),
    ]
    for label, score_text in rubric_checks:
        if score_text not in rubric:
            fail(f"Quality rubric missing {label} threshold {score_text}")


def check_version() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        fail(f"VERSION must use MAJOR.MINOR.PATCH format: {version}")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if version not in changelog:
        fail(f"CHANGELOG.md does not mention VERSION {version}")


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
    return any(part in IGNORED_DIR_NAMES for part in path.parts)


def should_skip_machine_path(path: Path) -> bool:
    if ".git" in path.parts:
        return True
    if path.name in IGNORED_FILE_NAMES:
        return True
    return any(part in IGNORED_DIR_NAMES for part in path.parts)


def main() -> None:
    check_required_paths()
    check_contract_template_alignment()
    check_tool_registry()
    check_preflight_tool_alignment()
    check_agent_definitions()
    check_yaml_template_duplicate_keys()
    check_quality_threshold_alignment()
    check_version()
    check_skills()
    check_tracking_plans()
    check_user_flows()
    check_text_files_are_utf8()
    check_machine_readable_paths()
    print("PM Copilot repository validation passed.")


if __name__ == "__main__":
    main()
