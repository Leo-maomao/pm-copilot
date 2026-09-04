#!/usr/bin/env python3
"""Expose canonical interactive PRD controls over the MCP stdio protocol."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


# A plugin cache is not a writable or authoritative PM Copilot runtime. The
# host must select a source checkout explicitly; neither a legacy installation
# variable nor the MCP process working directory is a valid substitute.
_REPOSITORY_ENV = "PM_COPILOT_REPOSITORY"


def _selected_runtime_home() -> Path | None:
    selected = os.environ.get(_REPOSITORY_ENV, "").strip()
    return Path(selected).expanduser() if selected else None


RUNTIME_HOME = _selected_runtime_home()
CONTROLLER = RUNTIME_HOME / "scripts" / "run_interactive_request.py" if RUNTIME_HOME else None
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


def _is_plugin_cache_path(path: Path) -> bool:
    parts = path.parts
    marker_length = len(_CACHE_PATH_MARKER)
    return any(
        parts[index:index + marker_length] == _CACHE_PATH_MARKER
        for index in range(len(parts) - marker_length + 1)
    )


def _runtime_checkout_error(runtime_home: Path | None) -> str | None:
    """Return a diagnostic when the selected runtime is not a source checkout."""
    if runtime_home is None:
        return (
            "PM Copilot checkout is not configured. Set PM_COPILOT_REPOSITORY "
            "to an explicit PM Copilot repository checkout."
        )

    runtime_path = _resolved_path(runtime_home)
    if _is_plugin_cache_path(runtime_path):
        return (
            "PM_COPILOT_REPOSITORY must point to a source checkout, not a "
            f"Codex plugin cache: {runtime_path}"
        )

    required_paths = (
        ".git",
        "PM_COPILOT.md",
        "scripts/run_interactive_request.py",
        "plugins/pm-copilot/scripts/pm_copilot_mcp.py",
    )
    missing = [relative for relative in required_paths if not (runtime_path / relative).exists()]
    if missing:
        return (
            "PM_COPILOT_REPOSITORY must point to a PM Copilot repository checkout "
            f"with {', '.join(missing)}: {runtime_path}"
        )
    return None


def _read_optional_version(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def _file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


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
    manifest = _plugin_manifest_path(path)
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = payload.get("version") if isinstance(payload, dict) else None
    if value is None:
        return None
    version = str(value).strip()
    return version or None


def _plugin_manifest_path(path: Path) -> Path:
    return path.parent.parent / ".codex-plugin" / "plugin.json"


def _version_base(version: str | None) -> str | None:
    if not version:
        return None
    value = version.partition("+")[0].strip()
    return value or None


def _wrapper_identity(path: Path) -> dict[str, Any]:
    """Describe the exact bridge code that is safe to dispatch through."""
    script_path = _resolved_path(path)
    cache_version = _cache_wrapper_version(script_path)
    manifest_path = _plugin_manifest_path(script_path)
    manifest_version = _plugin_manifest_version(script_path)
    plugin_version = manifest_version or cache_version
    return {
        "script_path": str(script_path),
        "script_sha256": _file_sha256(script_path),
        "plugin_manifest_path": str(_resolved_path(manifest_path)),
        "plugin_manifest_sha256": _file_sha256(manifest_path),
        "plugin_version": plugin_version,
        "plugin_version_source": (
            "plugin_manifest" if manifest_version else "cache_path" if cache_version else None
        ),
        "is_persistent_cache": cache_version is not None,
    }


# This is intentionally captured once. Codex may replace or delete the cache
# directory while the stdio process remains alive, but that cannot replace the
# Python code already loaded by this process.
_INITIAL_WRAPPER_SCRIPT = WRAPPER_SCRIPT
_LOADED_WRAPPER_IDENTITY = _wrapper_identity(WRAPPER_SCRIPT)


def _loaded_wrapper_identity() -> dict[str, Any]:
    """Return the process-start identity, with a small test seam for path mocks."""
    if WRAPPER_SCRIPT != _INITIAL_WRAPPER_SCRIPT:
        return _wrapper_identity(WRAPPER_SCRIPT)
    return dict(_LOADED_WRAPPER_IDENTITY)


def _canonical_wrapper_identity(runtime_home: Path) -> dict[str, Any]:
    runtime_path = _resolved_path(runtime_home)
    identity = _wrapper_identity(
        runtime_path / "plugins" / "pm-copilot" / "scripts" / "pm_copilot_mcp.py"
    )
    identity["runtime_path"] = str(runtime_path)
    identity["runtime_version"] = _read_optional_version(runtime_path / "VERSION")
    return identity


def _dispatch_mismatch_reasons(
    wrapper: dict[str, Any], canonical: dict[str, Any],
) -> list[str]:
    """Return proof that a persistent bridge cannot safely launch delivery."""
    if not wrapper.get("is_persistent_cache"):
        return []

    reasons: list[str] = []
    if not wrapper.get("script_sha256"):
        reasons.append("loaded_wrapper_content_unavailable")
    if not wrapper.get("plugin_version"):
        reasons.append("loaded_wrapper_build_unavailable")
    if not wrapper.get("plugin_manifest_sha256"):
        reasons.append("loaded_wrapper_manifest_unavailable")
    if not canonical.get("script_sha256"):
        reasons.append("canonical_wrapper_content_unavailable")
    if not canonical.get("plugin_version"):
        reasons.append("canonical_wrapper_build_unavailable")
    if not canonical.get("plugin_manifest_sha256"):
        reasons.append("canonical_wrapper_manifest_unavailable")
    if not canonical.get("runtime_version"):
        reasons.append("canonical_runtime_version_unavailable")

    if reasons:
        return reasons

    if wrapper["script_sha256"] != canonical["script_sha256"]:
        reasons.append("wrapper_content_mismatch")
    if wrapper["plugin_manifest_sha256"] != canonical["plugin_manifest_sha256"]:
        reasons.append("wrapper_manifest_mismatch")
    if wrapper["plugin_version"] != canonical["plugin_version"]:
        reasons.append("wrapper_build_mismatch")
    if _version_base(str(wrapper["plugin_version"])) != canonical["runtime_version"]:
        reasons.append("wrapper_runtime_version_mismatch")
    return reasons


def _runtime_provenance() -> tuple[dict[str, Any], bool]:
    """Report the loaded wrapper and the runtime that it will dispatch to.

    Codex keeps MCP processes alive across plugin-cache refreshes. The loaded
    cache bridge must exactly match the installed canonical bridge before it
    can initiate a mutating controller invocation. A status query remains
    diagnostic and never dispatches a controller when a restart is needed.
    """
    wrapper = _loaded_wrapper_identity()
    configuration_error = _runtime_checkout_error(RUNTIME_HOME)
    if configuration_error:
        runtime_path = _resolved_path(RUNTIME_HOME) if RUNTIME_HOME is not None else None
        return {
            "wrapper": wrapper,
            "canonical_runtime": {
                "path": str(runtime_path) if runtime_path is not None else None,
                "version": _read_optional_version(runtime_path / "VERSION") if runtime_path else None,
                "plugin": {
                    "script_path": None,
                    "script_sha256": None,
                    "plugin_manifest_path": None,
                    "plugin_manifest_sha256": None,
                    "plugin_version": None,
                    "plugin_version_source": None,
                },
            },
            "selection": {
                "environment_variable": _REPOSITORY_ENV,
                "configured": RUNTIME_HOME is not None,
                "checkout_valid": False,
                "error": configuration_error,
            },
            "dispatch": {
                "current": False,
                "restart_required": False,
                "mismatch_reasons": [],
                "configuration_error": configuration_error,
            },
        }, False

    assert RUNTIME_HOME is not None
    canonical = _canonical_wrapper_identity(RUNTIME_HOME)
    mismatch_reasons = _dispatch_mismatch_reasons(wrapper, canonical)
    restart_required = bool(mismatch_reasons)
    return {
        "wrapper": wrapper,
        "canonical_runtime": {
            "path": canonical["runtime_path"],
            "version": canonical["runtime_version"],
            "plugin": {
                key: canonical[key]
                for key in (
                    "script_path", "script_sha256", "plugin_manifest_path",
                    "plugin_manifest_sha256", "plugin_version", "plugin_version_source",
                )
            },
        },
        "selection": {
            "environment_variable": _REPOSITORY_ENV,
            "configured": True,
            "checkout_valid": True,
            "error": None,
        },
        "dispatch": {
            "current": not restart_required,
            "restart_required": restart_required,
            "mismatch_reasons": mismatch_reasons,
            "configuration_error": None,
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


def _write_json(path: Path, value: dict[str, Any]) -> None:
    """Replace a run checkpoint without exposing partially-written JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False,
    ) as temporary:
        temporary.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def _controller_pid_alive(state: dict[str, Any]) -> bool:
    """Return whether the controller recorded for an active delivery exists."""
    try:
        os.kill(int(state.get("controller_pid")), 0)
        return True
    except (TypeError, ValueError, ProcessLookupError, PermissionError):
        return False


def _recover_interrupted_delivery(state: dict[str, Any], folder: Path) -> bool:
    """Mirror the controller's dead-lease recovery before reporting status.

    A controller normally performs this repair at startup. The MCP bridge must
    do it too because status polling can be the only remaining entry point
    after a controller process exits unexpectedly.
    """
    if (
        state.get("status") not in {"delivery", "confirmed"}
        or state.get("termination") != "running"
        or _controller_pid_alive(state)
    ):
        return False

    raw_pid = state.get("controller_pid")
    promoted = [
        name
        for name in ("confirmed-requirements.md", "prd.md", "prd.html", "run-log.yaml")
        if (folder / name).is_file()
    ]
    state["status"] = "recovery_required"
    state["termination"] = "interrupted"
    state["last_error"] = "controller process exited during delivery; prior running state was recovered"
    state["recovery"] = {
        "status": "retry_required",
        "detected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "controller_pid": raw_pid,
        "promoted_artifacts": promoted,
        "retry_entry": "--confirm",
    }
    return True


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
    if _recover_interrupted_delivery(state, folder):
        _write_json(folder / "interactive-run.json", state)
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
    runtime_provenance, restart_required = _runtime_provenance()
    configuration_error = runtime_provenance["dispatch"]["configuration_error"]
    if configuration_error:
        return {
            "ok": False,
            "error": configuration_error,
            "error_code": "checkout_not_configured" if RUNTIME_HOME is None else "checkout_invalid",
            "runtime_restart_required": False,
            "runtime_provenance": runtime_provenance,
        }
    if restart_required:
        reasons = runtime_provenance["dispatch"]["mismatch_reasons"]
        return {
            "ok": False,
            "error": (
                "PM Copilot plugin restart required before a mutating request: "
                + ", ".join(reasons)
                + ". This persistent MCP process was loaded from an older or "
                "unverifiable plugin build; reload/restart the PM Copilot plugin once, then retry."
            ),
            "error_code": "restart_required",
            "runtime_restart_required": True,
            "runtime_provenance": runtime_provenance,
        }
    if CONTROLLER is None or not CONTROLLER.is_file():
        return _error(
            "PM Copilot checkout controller is unavailable. Verify that "
            "PM_COPILOT_REPOSITORY points to the selected checkout."
        )
    assert RUNTIME_HOME is not None
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
    confirmed_recovery_pause = (
        effective_status == "needs_input"
        and isinstance(state.get("user_confirmation"), dict)
        and state["user_confirmation"].get("confirmed") is True
    )
    # The controller owns the meaning of a persisted needs_input state.  A
    # prior explicit confirmation can coexist with a controller-repairable
    # legacy pause, while a genuine unanswered question remains a no-op there.
    if (
        effective_status not in {"awaiting_confirmation", "recovery_required", "confirmed", "delivery", "failed"}
        and not confirmed_recovery_pause
    ):
        return _error(f"cannot confirm or resume delivery while run status is {effective_status}")
    return _invoke(run_folder, ["--confirm"])


TOOLS = [
    {
        "name": "prd_run_status",
        "description": "Read the canonical controller state for an interactive PRD run, recovering a dead controller lease before reporting progress.",
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
