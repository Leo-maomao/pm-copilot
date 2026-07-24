#!/usr/bin/env python3
"""Validate the runtime document-routing registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTING_PATH = ROOT / "indexes" / "runtime-routing.yaml"
EXPECTED_TASK_MODES = {
    "prd_delivery",
    "implemented_feature_prd",
    "ui_delivery",
    "tracking_plan",
    "launch_readiness",
    "dev_handoff",
    "structured_reference",
    "product_review",
    "self_improvement",
    "mixed_delivery",
}
DISALLOWED_RUNTIME_PREFIXES = ("docs/archive/", "outputs/", "context/")


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_registry() -> dict[str, object]:
    try:
        registry = json.loads(ROUTING_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"Missing routing registry: {ROUTING_PATH.relative_to(ROOT)}")
    except json.JSONDecodeError as error:
        fail(f"Routing registry must use JSON-compatible YAML: {error}")
    if not isinstance(registry, dict):
        fail("Routing registry root must be an object")
    return registry


def require_active_document(
    document_id: str,
    documents: dict[str, object],
    context: str,
) -> dict[str, object]:
    document = documents.get(document_id)
    if not isinstance(document, dict):
        fail(f"{context} references unknown document ID: {document_id}")
    if document.get("status") != "active":
        fail(f"{context} references non-active document: {document_id}")
    path_value = document.get("path")
    if not isinstance(path_value, str) or not path_value:
        fail(f"Document {document_id} must define a path")
    if path_value.startswith(DISALLOWED_RUNTIME_PREFIXES):
        fail(f"{context} routes to disallowed runtime path: {path_value}")
    if not (ROOT / path_value).is_file():
        fail(f"Document {document_id} path does not exist: {path_value}")
    return document


def validate_registry(registry: dict[str, object]) -> None:
    documents = registry.get("documents")
    routes = registry.get("routes")
    bootstrap = registry.get("bootstrap")
    capability_selectors = registry.get("capability_selectors")
    memory_selection = registry.get("memory_selection")
    if not isinstance(documents, dict):
        fail("Routing registry must define documents")
    if not isinstance(routes, dict):
        fail("Routing registry must define routes")
    if not isinstance(bootstrap, list) or not bootstrap:
        fail("Routing registry must define non-empty bootstrap")

    canonical_owners: dict[str, str] = {}
    for document_id, raw_document in documents.items():
        if not isinstance(raw_document, dict):
            fail(f"Document {document_id} must be an object")
        status = raw_document.get("status")
        path_value = raw_document.get("path")
        canonical_for = raw_document.get("canonical_for")
        if status not in {"active", "archived"}:
            fail(f"Document {document_id} has invalid status: {status}")
        if not isinstance(path_value, str) or not (ROOT / path_value).is_file():
            fail(f"Document {document_id} path does not exist: {path_value}")
        if status == "active":
            if not isinstance(canonical_for, str) or not canonical_for:
                fail(f"Active document {document_id} must declare canonical_for")
            prior_owner = canonical_owners.get(canonical_for)
            if prior_owner:
                fail(
                    f"Active canonical_for {canonical_for} has multiple owners: "
                    f"{prior_owner}, {document_id}"
                )
            canonical_owners[canonical_for] = document_id

    for document_id in bootstrap:
        if not isinstance(document_id, str):
            fail("Bootstrap document IDs must be strings")
        require_active_document(document_id, documents, "bootstrap")

    if set(routes) != EXPECTED_TASK_MODES:
        missing = sorted(EXPECTED_TASK_MODES - set(routes))
        extra = sorted(set(routes) - EXPECTED_TASK_MODES)
        fail(f"Route task modes mismatch; missing={missing}, extra={extra}")
    for task_mode, document_ids in routes.items():
        if not isinstance(document_ids, list) or not document_ids:
            fail(f"Route {task_mode} must contain at least one document ID")
        for document_id in document_ids:
            if not isinstance(document_id, str):
                fail(f"Route {task_mode} contains non-string document ID")
            require_active_document(document_id, documents, f"route {task_mode}")

    if not isinstance(capability_selectors, dict):
        fail("Routing registry must define capability_selectors")
    for selector_id, raw_selector in capability_selectors.items():
        if not isinstance(selector_id, str) or not selector_id:
            fail("Capability selector IDs must be non-empty strings")
        if not isinstance(raw_selector, dict):
            fail(f"Capability selector {selector_id} must be an object")
        triggers = raw_selector.get("triggers")
        task_modes = raw_selector.get("task_modes")
        document_ids = raw_selector.get("documents")
        if not isinstance(triggers, list) or not triggers or not all(
            isinstance(trigger, str) and trigger.strip() for trigger in triggers
        ):
            fail(f"Capability selector {selector_id} must define non-empty string triggers")
        if not isinstance(task_modes, list) or not task_modes:
            fail(f"Capability selector {selector_id} must define task_modes")
        unknown_task_modes = sorted(
            task_mode for task_mode in task_modes if task_mode not in EXPECTED_TASK_MODES
        )
        if unknown_task_modes:
            fail(
                f"Capability selector {selector_id} references unknown task modes: "
                f"{unknown_task_modes}"
            )
        if not isinstance(document_ids, list) or not document_ids:
            fail(f"Capability selector {selector_id} must define documents")
        for document_id in document_ids:
            if not isinstance(document_id, str):
                fail(f"Capability selector {selector_id} contains non-string document ID")
            require_active_document(document_id, documents, f"capability selector {selector_id}")

    if not isinstance(memory_selection, dict):
        fail("Routing registry must define memory_selection")
    for field in ("allowed_files", "required_fields", "selection_fields"):
        values = memory_selection.get(field)
        if not isinstance(values, list) or not values:
            fail(f"memory_selection.{field} must be a non-empty list")


def main() -> None:
    validate_registry(load_registry())
    print("Runtime routing validation passed.")


if __name__ == "__main__":
    main()
