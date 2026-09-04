#!/usr/bin/env python3
"""Shared schema for immutable PM Copilot runtime provenance."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Mapping


RUNTIME_IDENTITY_VERSION = 1
RUNTIME_IDENTITY_MANIFEST_SCHEMA_VERSION = 1
RUNTIME_IDENTITY_MANIFEST_FILES = (
    "VERSION",
    "scripts/runtime_identity_contract.py",
    "scripts/run_interactive_request.py",
    "scripts/collect_implemented_feature_evidence.py",
    "scripts/agent_runtime.py",
    "scripts/delivery_failure_guard.py",
    "scripts/project_workspace.py",
    "scripts/revision_scope.py",
    "scripts/render_prd_html.py",
    "scripts/validate_agent_trace.py",
    "scripts/validate_outputs.py",
    "scripts/run_delivery_checks.py",
    "plugins/pm-copilot/scripts/pm_copilot_mcp.py",
    "templates/agent-run-log-template.yaml",
    "artifacts/prd-contract.md",
    "artifacts/trace-contract.md",
)
SHA256_RE = re.compile(r"[0-9a-f]{64}")


def runtime_manifest_digest(files: Mapping[str, str]) -> str:
    """Return the stable digest for a bounded runtime manifest."""
    payload = {
        "schema_version": RUNTIME_IDENTITY_MANIFEST_SCHEMA_VERSION,
        "files": dict(files),
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def complete_runtime_identity_failures(identity: object) -> list[str]:
    """Reject a declared identity unless every provenance field is bound."""
    if not isinstance(identity, Mapping):
        return ["runtime_identity must be a mapping when present"]
    if identity.get("identity_version") != RUNTIME_IDENTITY_VERSION:
        return [f"runtime_identity.identity_version must be {RUNTIME_IDENTITY_VERSION}"]
    if not isinstance(identity.get("runtime_root"), str) or not identity["runtime_root"].strip():
        return ["runtime_identity.runtime_root must be a non-empty path"]
    if not isinstance(identity.get("version"), str) or not identity["version"].strip():
        return ["runtime_identity.version must be a non-empty string"]

    manifest = identity.get("runtime_manifest")
    if not isinstance(manifest, Mapping):
        return ["runtime_identity.runtime_manifest must be a mapping"]
    if manifest.get("schema_version") != RUNTIME_IDENTITY_MANIFEST_SCHEMA_VERSION:
        return [
            "runtime_identity.runtime_manifest.schema_version must be "
            f"{RUNTIME_IDENTITY_MANIFEST_SCHEMA_VERSION}"
        ]
    files = manifest.get("files")
    if not isinstance(files, Mapping) or set(files) != set(RUNTIME_IDENTITY_MANIFEST_FILES):
        return [
            "runtime_identity.runtime_manifest.files must contain the exact runtime identity file set"
        ]
    normalized_files: dict[str, str] = {}
    for relative_path in RUNTIME_IDENTITY_MANIFEST_FILES:
        value = files.get(relative_path)
        if not isinstance(value, str) or not SHA256_RE.fullmatch(value.lower()):
            return [
                "runtime_identity.runtime_manifest.files."
                f"{relative_path} must be a SHA-256 digest"
            ]
        normalized_files[relative_path] = value

    if identity.get("controller_sha256") != normalized_files["scripts/run_interactive_request.py"]:
        return [
            "runtime_identity.controller_sha256 must match the runtime manifest controller digest"
        ]
    if identity.get("plugin_entry_sha256") != normalized_files[
        "plugins/pm-copilot/scripts/pm_copilot_mcp.py"
    ]:
        return [
            "runtime_identity.plugin_entry_sha256 must match the runtime manifest plugin digest"
        ]
    if identity.get("runtime_manifest_sha256") != runtime_manifest_digest(normalized_files):
        return [
            "runtime_identity.runtime_manifest_sha256 must match the runtime manifest"
        ]
    return []
