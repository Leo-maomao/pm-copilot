#!/usr/bin/env python3
"""Normalize an A2A-style task envelope into PM Copilot's local task boundary."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from project_workspace import resolve


AGENT_CARD = {
    "name": "PM Copilot",
    "description": "Evidence-backed product-manager artifacts and review workflows.",
    "version": "4.9.0",
    "interoperability": "local-task-envelope-only",
    "capabilities": ["prd_delivery", "implemented_feature_prd", "product_review", "tracking_plan", "self_improvement"],
    "input": {"required": ["message"], "optional": ["task_id", "artifacts"]},
}


def normalize(task: dict[str, object], workspace: Path) -> dict[str, object]:
    message = str(task.get("message") or task.get("input") or "").strip()
    if not message:
        raise ValueError("A2A task must include a non-empty message or input.")
    context = resolve(workspace, ensure=True)
    return {
        "schema_version": "1.0",
        "task_id": str(task.get("task_id") or task.get("id") or uuid.uuid4()),
        "status": "accepted",
        "message": message,
        "artifacts": task.get("artifacts", []),
        "workspace": context,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="PM Copilot local task-envelope adapter; it is not a network A2A server.")
    parser.add_argument("--agent-card", action="store_true")
    parser.add_argument("--task", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.agent_card:
        print(json.dumps(AGENT_CARD, ensure_ascii=False, indent=2))
        return
    if not args.task:
        parser.error("--task is required unless --agent-card is used")
    normalized = normalize(json.loads(args.task.read_text(encoding="utf-8")), args.workspace)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(normalized, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
