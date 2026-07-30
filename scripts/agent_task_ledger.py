#!/usr/bin/env python3
"""Persist bounded PM Copilot multi-agent work without hiding execution evidence."""

from __future__ import annotations

import json
import hashlib
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workspace_identity import identify


LEDGER_VERSION = "1.0"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def task_id(phase: str, role: str, index: int) -> str:
    return f"{phase}-{index + 1}-{role.lower().replace(' ', '-') }"


def create_ledger(request: str, task_mode: str, plan: dict[str, Any], cwd: Path) -> dict[str, Any]:
    tasks: list[dict[str, Any]] = []
    for group in plan.get("dispatch_groups", []):
        phase = str(group.get("phase", "evidence"))
        for index, worker in enumerate(group.get("workers", [])):
            role = str(worker.get("role", "Unknown Agent"))
            tasks.append({
                "id": task_id(phase, role, index),
                "phase": phase,
                "role": role,
                "owned_question": str(worker.get("owned_question", "")),
                "validation_expectation": str(worker.get("validation_expectation", "")),
                "status": "planned",
                "attempts": 0,
                "runtime": "",
                "model": "",
                "output_ref": "",
                "evidence_refs": [],
                "error": "",
                "started_at": "",
                "finished_at": "",
            })
    tasks.append({
        "id": "arbitration-1-pm-orchestrator",
        "phase": "arbitration",
        "role": "PM Orchestrator",
        "owned_question": "Resolve only material evidence conflicts raised by Review Agent.",
        "validation_expectation": "Return evidence-backed claims, cross-reviews, and an arbitration outcome.",
        "status": "planned",
        "attempts": 0,
        "runtime": "",
        "model": "",
        "output_ref": "",
        "evidence_refs": [],
        "error": "",
        "started_at": "",
        "finished_at": "",
    })
    return {
        "schema_version": LEDGER_VERSION,
        "run_id": str(uuid.uuid4()),
        "created_at": now(),
        "updated_at": now(),
        "request": request,
        "task_mode": task_mode,
        "workspace": identify(cwd),
        "status": "planned",
        "plan": plan,
        "tasks": tasks,
        "artifacts": {},
        "claims": [],
        "cross_reviews": [],
        "arbitrations": [],
        "resume": {"count": 0, "last_safe_phase": "planned", "reason": ""},
        "limitations": [],
    }


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ledger["updated_at"] = now()
    payload = json.dumps(ledger, ensure_ascii=False, indent=2) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        Path(temporary_name).replace(path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def task(ledger: dict[str, Any], identifier: str) -> dict[str, Any]:
    for item in ledger.get("tasks", []):
        if item.get("id") == identifier:
            return item
    raise KeyError(identifier)


def complete_tasks(ledger: dict[str, Any], phase: str) -> bool:
    selected = [item for item in ledger.get("tasks", []) if item.get("phase") == phase]
    return bool(selected) and all(item.get("status") == "complete" for item in selected)


def validate(ledger: dict[str, Any], base_path: Path | None = None) -> list[str]:
    failures: list[str] = []
    if ledger.get("schema_version") != LEDGER_VERSION:
        failures.append("unsupported ledger schema_version")
    if not str(ledger.get("run_id", "")).strip():
        failures.append("ledger requires run_id")
    workspace = ledger.get("workspace")
    if not isinstance(workspace, dict):
        failures.append("ledger requires workspace identity")
    else:
        for field in ("execution_root", "display_label", "kind", "sync_direction"):
            if not str(workspace.get(field, "")):
                failures.append(f"workspace requires {field}")
    statuses = {"planned", "running", "complete", "needs_input", "blocked", "degraded", "failed", "skipped"}
    identifiers: set[str] = set()
    for item in ledger.get("tasks", []):
        identifier = str(item.get("id", ""))
        if not identifier or identifier in identifiers:
            failures.append("tasks require unique non-empty ids")
        identifiers.add(identifier)
        if item.get("status") not in statuses:
            failures.append(f"task {identifier or '<empty>'} has invalid status")
        if item.get("status") == "complete":
            if int(item.get("attempts", 0)) < 1:
                failures.append(f"completed task {identifier} requires an attempt")
            output_ref = str(item.get("output_ref", ""))
            if not output_ref:
                failures.append(f"completed task {identifier} requires output_ref")
            elif base_path and not (base_path / output_ref).is_file():
                failures.append(f"completed task {identifier} output_ref does not exist")
    for artifact_id, artifact in ledger.get("artifacts", {}).items():
        if not artifact.get("path") or not artifact.get("sha256"):
            failures.append(f"artifact {artifact_id} requires path and sha256")
            continue
        if base_path:
            artifact_path = base_path / str(artifact["path"])
            if not artifact_path.is_file():
                failures.append(f"artifact {artifact_id} path does not exist")
            elif hashlib.sha256(artifact_path.read_bytes()).hexdigest() != artifact["sha256"]:
                failures.append(f"artifact {artifact_id} hash mismatch")
    if ledger.get("status") == "complete" and not (ledger.get("claims") or ledger.get("arbitrations")):
        failures.append("complete ledger requires claims or arbitrations")
    if ledger.get("status") in {"complete", "blocked", "degraded", "failed"}:
        unfinished = [str(item.get("id", "<empty>")) for item in ledger.get("tasks", []) if item.get("status") == "running"]
        if unfinished:
            failures.append("terminal ledger cannot retain running tasks: " + ", ".join(unfinished))
    return failures
