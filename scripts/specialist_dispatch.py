#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""On-demand, isolated specialist dispatch for confirmed PRD deliveries."""

from __future__ import annotations

import concurrent.futures
import copy
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

from agent_runtime import execute


_UI_SIGNAL = re.compile(
    r"(?:ui|ux|page|screen|route|frontend|front-end|interface|页面|界面|前端|交互|截图|图示)",
    re.IGNORECASE,
)


def _values(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _safe_id(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return normalized or "specialist"


def _task(mode: str, role: str, subject: str, context: Mapping[str, Any]) -> dict[str, Any]:
    task_id = _safe_id(f"{role}-{subject}")
    return {
        "id": task_id,
        "role": role,
        "subject": subject,
        "context": dict(context),
        "mode": mode,
    }


def select_tasks(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Choose independent questions. There is deliberately no count cap."""
    mode = str(state.get("task_mode") or "new_prd")
    packet = state.get("confirmed_fact_packet")
    packet = packet if isinstance(packet, Mapping) else {}
    scope = packet.get("scope")
    scope = scope if isinstance(scope, Mapping) else {}
    in_scope = _values(scope.get("in_scope"))
    risks = _values(packet.get("risks"))
    request = str(state.get("raw_request") or "")
    tasks: list[dict[str, Any]] = []

    # Each confirmed scope item is an independent logic question. This scales
    # with the request instead of silently discarding work after a fixed limit.
    if len(in_scope) > 1 or risks or mode in {"prd_revision", "prd_composition"}:
        for index, item in enumerate(in_scope or [str(scope.get("goal") or request)], start=1):
            tasks.append(_task(mode, "functional_logic", f"scope-{index}", {
                "scope_item": item,
                "risks": risks,
            }))

    sources = state.get("extraction_sources")
    sources = sources if isinstance(sources, list) else []
    if mode == "prd_composition":
        for index, source in enumerate(sources, start=1):
            source = source if isinstance(source, Mapping) else {}
            source_id = str(source.get("source_id") or f"source-{index}")
            tasks.append(_task(mode, "source_resolution", source_id, {
                "source_id": source_id,
                "snapshot_path": str(source.get("snapshot_path") or ""),
                "selected_scope": _values(source.get("selected_scope")),
            }))

    frontend_needed = (
        mode == "implemented_feature_prd"
        or bool(state.get("input_assets"))
        or any(_UI_SIGNAL.search(item) for item in [request, *in_scope])
    )
    if frontend_needed:
        tasks.append(_task(mode, "frontend_evidence", "confirmed-surface", {
            "scope": in_scope,
            "input_assets": _values(state.get("input_assets")),
        }))
    return tasks


def _prompt(task: Mapping[str, Any]) -> str:
    role = str(task["role"])
    instructions = {
        "functional_logic": (
            "Analyze the confirmed scope item for user scenarios, rules, boundaries, and edge states. "
            "Return only evidence-backed PRD candidates and open questions."
        ),
        "frontend_evidence": (
            "Inspect available frontend evidence read-only. Identify verifiable user-visible states and the "
            "appropriate real, reconstructed, or controlled-placeholder figure decision. Do not modify host code."
        ),
        "source_resolution": (
            "Read only the supplied immutable source snapshot. Resolve the selected requirement scope, report "
            "conflicts or missing references, and never inherit source numbering or structure."
        ),
    }[role]
    return f"""You are the PM Copilot {role.replace('_', ' ').title()} specialist.
This is advisory evidence for a confirmed {task['mode']} PRD delivery, not a vote and not a final PRD.
{instructions}
Do not write files or change product code. Return a concise report with evidence references, confidence, and limitations.
Task context: {json.dumps(task['context'], ensure_ascii=False)}
"""


def _run_one(
    task: Mapping[str, Any], workspace: Path, provider: str, timeout: int, model: str | None,
    runner: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    # A specialist gets a private workspace copy. Its model process cannot alter
    # the staged PRD or another specialist's evidence while running in parallel.
    with tempfile.TemporaryDirectory(prefix=".prd-specialist-", dir=str(workspace.parent)) as temporary:
        isolated = Path(temporary) / workspace.name
        shutil.copytree(workspace, isolated)
        result = runner(provider, _prompt(task), isolated, timeout, model, None, False, 6000)
    output = str(result.get("output") or "")
    return {
        "id": str(task["id"]),
        "role": str(task["role"]),
        "subject": str(task["subject"]),
        "status": "passed" if result.get("status") == "complete" else "failed",
        "provider": str(result.get("provider") or "codex"),
        "model": str(result.get("model") or ""),
        "output": output,
        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "error": str(result.get("error") or ""),
        "failure_category": result.get("failure_category"),
        "context": dict(task["context"]),
    }


def dispatch(
    state: Mapping[str, Any], workspace: Path, provider: str, timeout: int, model: str | None,
    runner: Callable[..., dict[str, Any]] = execute,
) -> list[dict[str, Any]]:
    """Run all independently selected specialists concurrently and persist evidence.

    A failure is durable evidence, not an inferred product fact. The caller is
    responsible for deciding whether a failed specialist blocks the workflow.
    """
    tasks = select_tasks(state)
    if not tasks:
        return []
    evidence_root = workspace / "specialist-evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    # No max_workers constant: workload, rather than an arbitrary policy cap,
    # determines parallelism.
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        futures = {
            pool.submit(_run_one, task, workspace, provider, timeout, model, runner): task
            for task in tasks
        }
        for future, task in futures.items():
            try:
                record = future.result()
            except Exception as error:  # Preserve a failed specialist as evidence.
                record = {
                    "id": str(task["id"]), "role": str(task["role"]),
                    "subject": str(task["subject"]), "status": "failed",
                    "provider": "codex", "model": str(model or ""), "output": "",
                    "output_sha256": hashlib.sha256(b"").hexdigest(), "error": str(error),
                    "failure_category": "specialist_dispatch_failed", "context": dict(task["context"]),
                }
            path = evidence_root / f"{record['id']}.json"
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            record["path"] = path.relative_to(workspace).as_posix()
            # Full model output belongs in the per-specialist evidence file.
            # The controller trace keeps only an attributable digest and path.
            record.pop("output", None)
            records.append(record)
    return records
