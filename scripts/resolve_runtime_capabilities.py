#!/usr/bin/env python3
"""Resolve optional PM Copilot skills from the runtime routing index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTING_PATH = ROOT / "indexes" / "runtime-routing.yaml"


def load_registry() -> dict[str, object]:
    registry = json.loads(ROUTING_PATH.read_text(encoding="utf-8"))
    if not isinstance(registry, dict):
        raise ValueError("Routing registry root must be an object")
    return registry


def resolve_capabilities(task_mode: str, request: str) -> dict[str, object]:
    registry = load_registry()
    selectors = registry.get("capability_selectors")
    documents = registry.get("documents")
    if not isinstance(selectors, dict) or not isinstance(documents, dict):
        raise ValueError("Routing registry must define documents and capability_selectors")

    normalized_request = request.casefold()
    selected: list[dict[str, object]] = []
    document_ids: list[str] = []

    for selector_id, raw_selector in selectors.items():
        if not isinstance(raw_selector, dict):
            continue
        task_modes = raw_selector.get("task_modes")
        triggers = raw_selector.get("triggers")
        selected_documents = raw_selector.get("documents")
        if (
            not isinstance(task_modes, list)
            or task_mode not in task_modes
            or not isinstance(triggers, list)
            or not isinstance(selected_documents, list)
        ):
            continue
        matched_triggers = [
            trigger
            for trigger in triggers
            if isinstance(trigger, str) and trigger.casefold() in normalized_request
        ]
        if not matched_triggers:
            continue
        selected.append(
            {
                "id": selector_id,
                "matched_triggers": matched_triggers,
                "documents": selected_documents,
            }
        )
        for document_id in selected_documents:
            if isinstance(document_id, str) and document_id not in document_ids:
                document_ids.append(document_id)

    resolved_documents = []
    for document_id in document_ids:
        raw_document = documents.get(document_id)
        if not isinstance(raw_document, dict):
            continue
        path = raw_document.get("path")
        if isinstance(path, str):
            resolved_documents.append({"id": document_id, "path": path})

    return {
        "task_mode": task_mode,
        "selectors": selected,
        "documents": resolved_documents,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-mode", required=True)
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            resolve_capabilities(args.task_mode, args.request),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
