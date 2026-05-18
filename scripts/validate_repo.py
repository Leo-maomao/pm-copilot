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
    "PM_COPILOT.md",
    "LICENSE",
    "VERSION",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "workflow/main-workflow.md",
    "workflow/context-loading.md",
    "artifacts/artifact-contracts.md",
    "artifacts/prd-contract.md",
    "artifacts/prototype-contract.md",
    "artifacts/trace-contract.md",
    "artifacts/tracking-plan-contract.md",
    "tools/tool-use-protocol.md",
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
    "templates/evaluation-case-template.md",
    "templates/direct-request-template.md",
    "templates/prd-template.md",
    "templates/tracking-plan-template.csv",
    "scripts/install_adapter.py",
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

MACHINE_PATH_RE = re.compile(r"^[A-Za-z0-9._@+/-]+$")
PROPERTY_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

REQUIRED_TEXT_TOKENS = {
    "PM_COPILOT.md": [
        "engineering handoff",
        "launch status",
        "content source",
        "navigation visibility",
        "product-memory.local.yaml",
    ],
    "prompts/prompt-system.md": [
        "Prompt Stack",
        "Request Classification",
        "Memory Use",
        "Clarification Prompt Rules",
        "Memory Update Prompt Rules",
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
    ],
    "artifacts/artifact-contracts.md": [
        "Default Delivery",
        "Requirement details",
        "Tracking Plan",
        "HTML Prototype",
        "Optional Exports",
    ],
    "artifacts/trace-contract.md": [
        "request_source:",
        "readiness:",
        "content_sources:",
        "review_findings:",
        "validation_results:",
    ],
    "templates/agent-run-log-template.yaml": [
        "request_source:",
        "readiness:",
        "engineering_handoff_status:",
        "launch_status:",
        "surface_decisions:",
        "content_sources:",
        "review_findings:",
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
        if not re.search(r"^name:\s*\S+", text, re.MULTILINE):
            fail(f"Skill missing name: {skill_file.relative_to(ROOT)}")
        if not re.search(r"^description:\s*.+", text, re.MULTILINE):
            fail(f"Skill missing description: {skill_file.relative_to(ROOT)}")


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
        if path.is_dir() or ".git" in path.parts:
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
        if ".git" in path.parts:
            continue
        relative_path = path.relative_to(ROOT).as_posix()
        if not MACHINE_PATH_RE.match(relative_path):
            fail(f"Non-ASCII or unsupported character in path: {relative_path}")


def main() -> None:
    check_required_paths()
    check_contract_template_alignment()
    check_version()
    check_skills()
    check_tracking_plans()
    check_user_flows()
    check_text_files_are_utf8()
    check_machine_readable_paths()
    print("PM Copilot repository validation passed.")


if __name__ == "__main__":
    main()
