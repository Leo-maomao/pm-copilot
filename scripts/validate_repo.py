#!/usr/bin/env python3
"""Validate the intentionally small PM Copilot PRD-generator runtime."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "PM_COPILOT.md", "README.md", "README.en.md", "indexes/runtime-routing.yaml",
    "policies/role-boundary.md", "workflow/context-loading.md", "workflow/main-workflow.md",
    "artifacts/prd-contract.md", "artifacts/trace-contract.md", "templates/prd-template.md",
    "templates/agent-run-log-template.yaml", "scripts/prd_request_controller.py",
    "scripts/run_interactive_request.py", "scripts/agent_runtime.py", "scripts/project_workspace.py",
    "scripts/revision_scope.py", "scripts/render_prd_html.py", "scripts/setup_prd_renderer.py",
    "scripts/validate_outputs.py", "scripts/prd_visual_contract.py",
    "scripts/validate_agent_trace.py", "scripts/collect_implemented_feature_evidence.py", "scripts/generate_reconstructed_figure.py",
    "scripts/capture_frontend_figure.py", "scripts/specialist_dispatch.py", "scripts/prd_manager.py",
    "scripts/refresh_codex_plugin.py", ".githooks/pre-commit", ".githooks/post-commit",
    "tools/prd-manager/index.html", "tools/prd-manager/app.js", "tools/prd-manager/app.css",
    "tools/prd-manager/logo.svg",
    "plugins/pm-copilot/.codex-plugin/plugin.json",
    "plugins/pm-copilot/.mcp.json",
    "plugins/pm-copilot/scripts/pm_copilot_mcp.py",
    "plugins/pm-copilot/skills/pm-copilot/SKILL.md",
)
REQUIRED_AGENTS = (
    "agents/pm-orchestrator-agent.md", "agents/requirements-agent.md",
    "agents/ui-delivery-agent.md", "agents/review-agent.md",
)
ALLOWED_SKILLS = {
    "prd-writing", "requirement-intake", "review-checklist", "multi-platform-ui-delivery",
}
REMOVED_PATHS = (
    "distribution/seawork-skill", "adapters/claude-code", "adapters/cursor", "seawork",
    "scripts/install_adapter.py", "scripts/install_pm_copilot.py",
    "scripts/ensure_runtime_current.py", "scripts/sync_embedded_copies.py",
)
LOCAL_MACHINE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:/Users/(?!<you>)[A-Za-z0-9._-]+/[^\s`'\"<>)]*|/home/(?!<you>)[A-Za-z0-9._-]+/[^\s`'\"<>)]*)"
)


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def check_required_paths() -> None:
    for relative in (*REQUIRED_FILES, *REQUIRED_AGENTS):
        if not (ROOT / relative).is_file():
            fail(f"Missing required runtime file: {relative}")
    for relative in REMOVED_PATHS:
        if (ROOT / relative).exists():
            fail(f"Removed legacy surface is still present: {relative}")


def check_prd_positioning() -> None:
    text = (ROOT / "PM_COPILOT.md").read_text(encoding="utf-8")
    for mode in ("new_prd", "implemented_feature_prd", "prd_revision", "prd_composition"):
        if mode not in text:
            fail(f"PM_COPILOT.md does not define {mode}")
    for token in ("standalone UI", "engineering handoff", "launch decision"):
        if token not in text:
            fail(f"PM_COPILOT.md must state the excluded boundary: {token}")
    if "at most three specialists" in text or "最多三个" in text:
        fail("PM_COPILOT.md must not impose a fixed specialist-count cap")


def check_agents() -> None:
    sections = ("Purpose", "Responsibilities", "Inputs", "Outputs", "Completion Criteria", "Handoffs")
    for relative in REQUIRED_AGENTS:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for section in sections:
            if f"## {section}" not in text:
                fail(f"Agent definition lacks {section}: {relative}")


def check_skills() -> None:
    skills = ROOT / "skills"
    actual = {path.name for path in skills.iterdir() if path.is_dir() and (path / "SKILL.md").is_file()}
    if actual != ALLOWED_SKILLS:
        fail(f"Active skills mismatch; expected {sorted(ALLOWED_SKILLS)}, found {sorted(actual)}")


def check_plugin() -> None:
    wrapper = (ROOT / "plugins/pm-copilot/scripts/pm_copilot_mcp.py").read_text(encoding="utf-8")
    skill = (ROOT / "plugins/pm-copilot/skills/pm-copilot/SKILL.md").read_text(encoding="utf-8")
    if "_personal_plugin_runtime_home" not in wrapper or "prd_start_request" not in wrapper:
        fail("Codex plugin must resolve its installed source and expose PRD start")
    if "PM_COPILOT_REPOSITORY" in wrapper or "PM_COPILOT_REPOSITORY" in skill:
        fail("Codex plugin must not allow a user or environment runtime-path override")
    if "append_implemented_feature" not in skill:
        fail("Codex plugin skill must document explicit implemented-feature append delivery")
    for legacy_fallback in ("PM_COPILOT_HOME", "os.getcwd", "~/.agents"):
        if legacy_fallback in wrapper or legacy_fallback in skill:
            fail(f"Codex plugin must not use the legacy runtime fallback: {legacy_fallback}")
    try:
        mcp_config = json.loads((ROOT / "plugins/pm-copilot/.mcp.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"Plugin MCP configuration is invalid JSON: {error}")
    if "env_vars" in mcp_config.get("mcpServers", {}).get("pm-copilot", {}):
        fail("Plugin MCP configuration must not require user environment variables")
    server = mcp_config.get("mcpServers", {}).get("pm-copilot", {})
    if server.get("command") != "python3":
        fail("Plugin MCP server must start with python3")
    if server.get("args") != ["./scripts/pm_copilot_mcp.py"]:
        fail("Plugin MCP server must launch only the canonical bridge")
    try:
        manifest = json.loads((ROOT / "plugins/pm-copilot/.codex-plugin/plugin.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"Plugin manifest is invalid JSON: {error}")
    if "PRD" not in str(manifest.get("description", "")):
        fail("Plugin manifest must describe PRD generation")


def check_reference_fixture_boundary() -> None:
    """Reject accidental workstation paths outside installer metadata fixtures."""
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".py", ".yaml", ".yml", ".json"}:
            continue
        if path.name in {"install-state.json", "install-manifest.json"}:
            continue
        if LOCAL_MACHINE_PATH_RE.search(path.read_text(encoding="utf-8", errors="ignore")):
            fail(f"Local machine path found in source: {path.relative_to(ROOT)}")


def main() -> None:
    check_required_paths()
    check_prd_positioning()
    check_agents()
    check_skills()
    check_plugin()
    check_reference_fixture_boundary()
    print("PM Copilot repository validation passed.")


if __name__ == "__main__":
    main()
