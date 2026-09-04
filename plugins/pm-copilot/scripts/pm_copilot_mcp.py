#!/usr/bin/env python3
"""Expose canonical interactive PRD controls over the MCP stdio protocol."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


RUNTIME_HOME = Path(os.environ.get("PM_COPILOT_HOME", str(Path.home() / ".agents" / "pm-copilot"))).expanduser()
CONTROLLER = RUNTIME_HOME / "scripts" / "run_interactive_request.py"
WRAPPER_SCRIPT = Path(__file__).resolve()
_CACHE_PATH_MARKER = (".codex", "plugins", "cache")


def _error(message: str) -> dict[str, Any]:
    return {"ok": False, "error": message}


def _resolved_path(path: Path) -> Path:
    """Resolve a path for reporting without making a missing cache bundle fatal."""
    try:
        return path.expanduser().resolve()
    except (OSError, RuntimeError):
        return path.expanduser().absolute()


def _read_optional_version(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def _cache_wrapper_version(path: Path) -> str | None:
    """Read the version encoded in a versioned Codex plugin-cache path."""
    parts = path.parts
    marker_length = len(_CACHE_PATH_MARKER)
    for index in range(len(parts) - marker_length + 1):
        if parts[index:index + marker_length] != _CACHE_PATH_MARKER:
            continue
        try:
            scripts_index = parts.index("scripts", index + marker_length)
        except ValueError:
            return None
        if scripts_index <= index + marker_length:
            return None
        version = parts[scripts_index - 1].strip()
        return version or None
    return None


def _plugin_manifest_version(path: Path) -> str | None:
    manifest = path.parent.parent / ".codex-plugin" / "plugin.json"
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = payload.get("version") if isinstance(payload, dict) else None
    if value is None:
        return None
    version = str(value).strip()
    return version or None


def _version_base(version: str | None) -> str | None:
    if not version:
        return None
    value = version.partition("+")[0].strip()
    return value or None


def _runtime_provenance() -> tuple[dict[str, Any], bool]:
    """Report the loaded wrapper and the runtime that it will dispatch to.

    Codex keeps MCP processes alive across plugin-cache refreshes. A cached
    wrapper can therefore outlive the bundle on disk while continuing to
    delegate to the global runtime. The signal is informational: delivery
    dispatch remains unchanged.
    """
    wrapper_path = _resolved_path(WRAPPER_SCRIPT)
    cache_version = _cache_wrapper_version(wrapper_path)
    manifest_version = _plugin_manifest_version(wrapper_path)
    wrapper_version = manifest_version or cache_version
    wrapper_version_source = (
        "plugin_manifest" if manifest_version else "cache_path" if cache_version else None
    )
    runtime_path = _resolved_path(RUNTIME_HOME)
    runtime_version = _read_optional_version(runtime_path / "VERSION")
    is_cached_wrapper = cache_version is not None
    restart_required = bool(
        is_cached_wrapper
        and _version_base(wrapper_version)
        and runtime_version
        and _version_base(wrapper_version) != _version_base(runtime_version)
    )
    return {
        "wrapper": {
            "script_path": str(wrapper_path),
            "plugin_version": wrapper_version,
            "plugin_version_source": wrapper_version_source,
            "is_persistent_cache": is_cached_wrapper,
        },
        "canonical_runtime": {
            "path": str(runtime_path),
            "version": runtime_version,
        },
    }, restart_required


def _run_attempt_provenance(
    state: dict[str, Any], canonical_runtime_version: str | None,
) -> dict[str, Any] | None:
    """Expose the newest recorded stage attempt without confusing it with runtime state.

    A resumed PRD run can retain delivery-stage metadata from an older global
    runtime. That is useful failure evidence, but it must not be presented as
    the version that a fresh controller invocation would dispatch today.
    """
    stages = state.get("delivery_stages")
    if not isinstance(stages, dict):
        return None
    candidates: list[tuple[str, int, str, dict[str, Any], str]] = []
    for index, (artifact, stage) in enumerate(stages.items()):
        if not isinstance(stage, dict):
            continue
        version = str(stage.get("pm_copilot_version") or "").strip()
        if not version:
            continue
        recorded_at = str(stage.get("updated_at") or "")
        candidates.append((recorded_at, index, str(artifact), stage, version))
    if not candidates:
        return None
    _, _, artifact, stage, attempt_version = max(candidates, key=lambda candidate: candidate[:2])
    attempt_base = _version_base(attempt_version)
    runtime_base = _version_base(canonical_runtime_version)
    version_relation = (
        "current_runtime"
        if attempt_base and runtime_base and attempt_base == runtime_base
        else "historical_attempt"
        if attempt_base and runtime_base
        else "runtime_version_unknown"
    )
    return {
        "artifact": artifact,
        "artifact_status": stage.get("artifact_status"),
        "review_status": stage.get("review_status"),
        "recorded_at": stage.get("updated_at"),
        "pm_copilot_version": attempt_version,
        "canonical_runtime_version": canonical_runtime_version,
        "version_relation": version_relation,
    }


def _load_run(run_folder: str) -> tuple[Path, dict[str, Any]]:
    folder = Path(run_folder).expanduser().resolve()
    state_path = folder / "interactive-run.json"
    if not state_path.is_file():
        raise ValueError(f"interactive PRD run not found: {folder}")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"interactive run state is invalid JSON: {error}") from error
    if state.get("mode") != "interactive":
        raise ValueError(f"run is not an interactive production PRD run: {folder}")
    return folder, state


def _legacy_interruption(folder: Path, state: dict[str, Any]) -> dict[str, Any] | None:
    """Detect the pre-checkpoint controller inconsistency without mutating a run."""
    if state.get("status") != "awaiting_confirmation" or state.get("user_confirmation"):
        return None
    promoted = [name for name in ("confirmed-requirements.md", "prd.md", "run-log.yaml") if (folder / name).is_file()]
    traces = list(folder.parent.glob(f".{folder.name}.stage-*")) + list(folder.parent.glob(f".{folder.name}.review-*"))
    if not promoted or not traces:
        return None
    return {
        "status": "confirmation_required",
        "promoted_artifacts": promoted,
        "staging_traces": [str(path) for path in traces],
        "message": "检测到旧版控制器在交付阶段中断；请明确确认恢复交付。",
    }


def run_summary(run_folder: str) -> dict[str, Any]:
    folder, state = _load_run(run_folder)
    recovery = state.get("recovery") or _legacy_interruption(folder, state)
    status = "recovery_required" if recovery and state.get("status") == "awaiting_confirmation" else state.get("status")
    runtime_provenance, runtime_restart_required = _runtime_provenance()
    run_attempt_provenance = _run_attempt_provenance(
        state, runtime_provenance["canonical_runtime"]["version"],
    )
    delivery_calls = [
        {
            "artifact": call.get("artifact"),
            "status": call.get("status"),
            "error": call.get("error", ""),
        }
        for call in state.get("agent_calls", [])
        if call.get("phase") in {"delivery", "stage_quality_review"}
    ]
    latest_turn = state.get("turns", [])[-1] if state.get("turns") else {}
    return {
        "ok": True,
        "run_folder": str(folder),
        "status": status,
        "termination": "interrupted" if status == "recovery_required" else state.get("termination"),
        "user_confirmation": state.get("user_confirmation"),
        "artifacts": state.get("artifacts", []),
        "last_error": state.get("last_error"),
        "recovery": recovery,
        "delivery_calls": delivery_calls,
        "next_questions": latest_turn.get("questions", []) if state.get("status") == "needs_input" else [],
        "runtime_provenance": runtime_provenance,
        "runtime_restart_required": runtime_restart_required,
        "run_attempt_provenance": run_attempt_provenance,
    }


def _invoke(run_folder: str, extra_args: list[str]) -> dict[str, Any]:
    folder, _ = _load_run(run_folder)
    if not CONTROLLER.is_file():
        return _error(f"PM Copilot runtime controller not found: {CONTROLLER}")
    result = subprocess.run(
        [sys.executable, str(CONTROLLER), "--run-folder", str(folder), *extra_args],
        cwd=RUNTIME_HOME,
        text=True,
        capture_output=True,
        check=False,
    )
    summary = run_summary(str(folder))
    summary.update({
        "controller_exit_code": result.returncode,
        "controller_stdout": result.stdout[-4000:],
        "controller_stderr": result.stderr[-2000:],
    })
    return summary


def submit_answer(run_folder: str, answer: str) -> dict[str, Any]:
    _, state = _load_run(run_folder)
    if state.get("status") != "needs_input":
        return _error(f"cannot submit an answer while run status is {state.get('status')}")
    if not answer.strip():
        return _error("answer must not be empty")
    return _invoke(run_folder, ["--answers", answer])


def confirm_delivery(run_folder: str) -> dict[str, Any]:
    folder, state = _load_run(run_folder)
    effective_status = "recovery_required" if _legacy_interruption(folder, state) else state.get("status")
    if effective_status not in {"awaiting_confirmation", "recovery_required", "confirmed", "delivery", "failed"}:
        return _error(f"cannot confirm or resume delivery while run status is {effective_status}")
    return _invoke(run_folder, ["--confirm"])


TOOLS = [
    {
        "name": "prd_run_status",
        "description": "Read the canonical controller state for an interactive PRD run before reporting progress to the user.",
        "inputSchema": {"type": "object", "properties": {"run_folder": {"type": "string"}}, "required": ["run_folder"], "additionalProperties": False},
    },
    {
        "name": "prd_submit_answer",
        "description": "Submit the user's answer to a PRD run that is currently needs_input.",
        "inputSchema": {"type": "object", "properties": {"run_folder": {"type": "string"}, "answer": {"type": "string"}}, "required": ["run_folder", "answer"], "additionalProperties": False},
    },
    {
        "name": "prd_confirm_delivery",
        "description": "Start canonical PRD delivery only after the user explicitly confirms the displayed clarified scope in this conversation.",
        "inputSchema": {"type": "object", "properties": {"run_folder": {"type": "string"}}, "required": ["run_folder"], "additionalProperties": False},
    },
]


def _tool_result(payload: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}], "isError": not payload.get("ok", False)}


def _handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "pm-copilot", "version": "1.0.0"}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = message.get("params", {})
        arguments = params.get("arguments", {})
        try:
            name = params.get("name")
            if name == "prd_run_status":
                payload = run_summary(str(arguments["run_folder"]))
            elif name == "prd_submit_answer":
                payload = submit_answer(str(arguments["run_folder"]), str(arguments["answer"]))
            elif name == "prd_confirm_delivery":
                payload = confirm_delivery(str(arguments["run_folder"]))
            else:
                payload = _error(f"unknown tool: {name}")
        except (KeyError, TypeError, ValueError) as error:
            payload = _error(str(error))
        return {"jsonrpc": "2.0", "id": request_id, "result": _tool_result(payload)}
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"method not found: {method}"}}


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-folder", required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--status", action="store_true")
    action.add_argument("--answer")
    action.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    try:
        if args.status:
            payload = run_summary(args.run_folder)
        elif args.answer is not None:
            payload = submit_answer(args.run_folder, args.answer)
        else:
            payload = confirm_delivery(args.run_folder)
    except (KeyError, TypeError, ValueError) as error:
        payload = _error(str(error))
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("ok", False) else 2


def main() -> int:
    if len(sys.argv) > 1:
        return _cli()
    for line in sys.stdin:
        try:
            response = _handle(json.loads(line))
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
        except json.JSONDecodeError:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
