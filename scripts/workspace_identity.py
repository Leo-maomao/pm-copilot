#!/usr/bin/env python3
"""Describe the PM Copilot workspace that owns one bounded run."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def identify(cwd: Path) -> dict[str, Any]:
    """Return a stable, local-only identity without assuming a canonical copy."""
    root = cwd.resolve()
    parent = root.parent
    embedded = root.name == "pm-copilot" and parent.name != "Desktop"
    return {
        "execution_root": str(root),
        "display_label": f"{parent.name}/{root.name}",
        "kind": "embedded_copy" if embedded else "standalone_repository",
        "host_project_root": str(parent) if embedded else "",
        "sync_direction": "promote_to_source_then_sync_copies" if embedded else "source_to_embedded_copies",
    }


def scope_notice(identity: dict[str, Any]) -> str:
    """Keep specialist evidence scoped to the selected copy, not a same-named sibling."""
    return (
        "Execution workspace: "
        f"{identity['display_label']} ({identity['kind']}); root={identity['execution_root']}. "
        "Use evidence from this workspace only. Do not assume that same-named PM Copilot "
        "repositories elsewhere on the machine share its project records, outputs, or uncommitted changes."
    )
