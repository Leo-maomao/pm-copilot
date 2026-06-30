#!/usr/bin/env python3
"""Install PM Copilot adapter snippets into a host repository."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START = "<!-- PM_COPILOT_ADAPTER_START -->"
END = "<!-- PM_COPILOT_ADAPTER_END -->"
TRIGGER_TEXT = (
    "When the user asks for product-manager work such as PRD, requirements, "
    "user stories, acceptance criteria, metrics, tracking plans, analytics events, "
    "user flows, UI deliverables, prototypes, structured references, document handoffs, "
    "parameter tables, rule references, data dictionaries, SOPs/runbooks, competitor "
    "research, review checklists, or equivalent Chinese-language PM tasks"
)
CONTEXT_RULE = (
    "Before generating PM artifacts, inspect relevant current product context. "
    "Use host project files when available, and use PRDs, specs, docs, screenshots, "
    "analytics exports, support tickets, or meeting notes when no code context exists. "
    "Ask must-answer questions and identify development or launch confirmation blockers "
    "if current product fit, scope, platform, metrics, or risk is unclear. Do not generate PRD/UI deliverables until "
    "those questions are answered, unless the user explicitly asks for a draft with risk. For repo-backed UI work, "
    "user wording like \"prototype\" or \"only generate a prototype\" means review scope only; use source-backed "
    "preview/delta files when frontend source exists, and use standalone HTML only for explicit portable HTML, "
    "explicit redesign/greenfield, no-source, or concretely blocked source rendering. For document-class requests "
    "where the user says no PRD is needed, use the structured reference or document prototype as the primary "
    "delivery and do not force a PRD."
)


def build_block(pm_path: str, tool: str) -> str:
    target = f"{pm_path.rstrip('/')}/PM_COPILOT.md"
    local_reference_rule = (
        f"When the user writes `@pm-copilot`, \"按 pm-copilot 规范\", "
        f"\"按仓库内 {target} 工作流产出 PRD\", or equivalent local-project wording, "
        f"treat it as a reference to the local `{target}` file. Do not search for or invoke "
        "an external agent, MCP server, plugin, hosted Copilot product, or tool-discovery "
        "target because of `@pm-copilot`.\n\n"
    )
    if tool == "codex":
        title = "PM Copilot"
        body = (
            f"{TRIGGER_TEXT}, read `{target}` and follow that workflow.\n\n"
            + local_reference_rule +
            "Do not require the user to say \"Use PM Copilot\". Natural product-manager "
            "requests should trigger it.\n\n"
            f"{CONTEXT_RULE}\n\n"
            f"Write generated PM Copilot artifacts under `{pm_path.rstrip('/')}/outputs/<run-id>/` "
            "unless the user asks for another location.\n\n"
            "Keep normal software-engineering tasks governed by this host repository's "
            "regular instructions."
        )
    elif tool == "claude-code":
        title = "PM Copilot"
        body = (
            f"{TRIGGER_TEXT}, read `{target}` and follow that workflow.\n\n"
            + local_reference_rule +
            "Do not require the user to say \"Use PM Copilot\". Natural product-manager "
            "requests should trigger it.\n\n"
            f"{CONTEXT_RULE}\n\n"
            f"Write generated PM Copilot artifacts under `{pm_path.rstrip('/')}/outputs/<run-id>/` "
            "unless the user asks for another location."
        )
    elif tool == "cursor":
        title = "PM Copilot"
        body = (
            f"{TRIGGER_TEXT}, read `{target}` and follow that workflow.\n\n"
            + local_reference_rule +
            "Do not require the user to say \"Use PM Copilot\". Natural product-manager "
            "requests should trigger it.\n\n"
            f"{CONTEXT_RULE}\n\n"
            "Keep normal software-engineering tasks governed by the host repository's regular rules.\n\n"
            f"Write generated PM Copilot artifacts under `{pm_path.rstrip('/')}/outputs/<run-id>/` "
            "unless the user asks for another location."
        )
    else:
        raise ValueError(f"Unsupported tool: {tool}")

    return f"{START}\n## {title}\n\n{body}\n{END}\n"


def update_file(path: Path, block: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        original = path.read_text(encoding="utf-8")
    else:
        original = ""

    if START in original and END in original:
        before = original.split(START, 1)[0].rstrip()
        after = original.split(END, 1)[1].lstrip()
        text = f"{before}\n\n{block}\n{after}".rstrip() + "\n"
        action = "updated"
    else:
        text = original.rstrip()
        if text:
            text += "\n\n"
        text += block
        action = "installed"

    path.write_text(text, encoding="utf-8")
    return action


def install_cursor_rule(path: Path, pm_path: str) -> str:
    target = f"{pm_path.rstrip('/')}/PM_COPILOT.md"
    content = f"""---
description: Trigger PM Copilot for product-manager workflows
globs:
  - "**/*"
alwaysApply: true
---

{TRIGGER_TEXT}, read `{target}` and follow that workflow.

When the user writes `@pm-copilot`, "按 pm-copilot 规范", "按仓库内 {target} 工作流产出 PRD", or equivalent local-project wording, treat it as a reference to the local `{target}` file. Do not search for or invoke an external agent, MCP server, plugin, hosted Copilot product, or tool-discovery target because of `@pm-copilot`.

Do not require the user to say "Use PM Copilot". Natural product-manager requests should trigger it.

{CONTEXT_RULE}

Keep normal software-engineering tasks governed by the host repository's regular rules.

Write generated PM Copilot artifacts under `{pm_path.rstrip('/')}/outputs/<run-id>/` unless the user asks for another location.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    action = "updated" if path.exists() else "installed"
    path.write_text(content, encoding="utf-8")
    return action


def infer_pm_path(host: Path) -> str:
    try:
        relative = os.path.relpath(ROOT, host)
    except ValueError:
        relative = str(ROOT)
    if relative.startswith(".."):
        raise SystemExit(
            "PM Copilot is not inside the host repository. Pass --pm-path with the path "
            "the host agent should use, for example: --pm-path tools/pm-copilot"
        )
    return relative.replace(os.sep, "/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Install PM Copilot host-repository adapters.")
    parser.add_argument("--host", required=True, help="Path to the host repository root.")
    parser.add_argument(
        "--tool",
        required=True,
        choices=["codex", "claude-code", "cursor", "all"],
        help="Agent tool adapter to install.",
    )
    parser.add_argument(
        "--pm-path",
        default=None,
        help="Path from the host repository root to PM Copilot. Defaults to the relative path of this repository.",
    )
    args = parser.parse_args()

    host = Path(args.host).expanduser().resolve()
    if not host.is_dir():
        raise SystemExit(f"Host repository does not exist or is not a directory: {host}")

    pm_path = args.pm_path or infer_pm_path(host)
    tools = ["codex", "claude-code", "cursor"] if args.tool == "all" else [args.tool]

    results: list[str] = []
    for tool in tools:
        if tool == "codex":
            target = host / "AGENTS.md"
            action = update_file(target, build_block(pm_path, "codex"))
            results.append(f"{action}: {target}")
        elif tool == "claude-code":
            target = host / "CLAUDE.md"
            action = update_file(target, build_block(pm_path, "claude-code"))
            results.append(f"{action}: {target}")
        elif tool == "cursor":
            target = host / ".cursor" / "rules" / "pm-copilot.mdc"
            action = install_cursor_rule(target, pm_path)
            results.append(f"{action}: {target}")

    for result in results:
        print(result)
    print(f"PM Copilot path used by adapter: {pm_path}")


if __name__ == "__main__":
    main()
