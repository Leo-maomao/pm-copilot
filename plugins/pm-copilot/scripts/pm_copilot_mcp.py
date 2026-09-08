#!/usr/bin/env python3
"""Expose the one PM Copilot v2 delivery controller over MCP stdio."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any


_PERSONAL_PLUGIN_SOURCE = Path.home() / "plugins" / "pm-copilot"


def _personal_plugin_runtime_home() -> Path | None:
    try:
        source = _PERSONAL_PLUGIN_SOURCE.resolve()
    except OSError:
        return None
    root = source.parent.parent
    return root if (root / ".git").exists() and (source / ".codex-plugin/plugin.json").is_file() else None


def _selected_runtime_home() -> Path | None:
    """Resolve the one installed personal-marketplace source checkout."""
    return _personal_plugin_runtime_home()


RUNTIME_HOME = _selected_runtime_home()
CONTROLLER = RUNTIME_HOME / "scripts/prd_request_controller.py" if RUNTIME_HOME else None


def _error(message: str) -> dict[str, Any]:
    return {"ok": False, "error": message}


def _load_run(run_folder: str) -> tuple[Path, dict[str, Any]]:
    folder = Path(run_folder).expanduser().resolve()
    path = folder / "delivery-run.json"
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"v2 PRD run not found or invalid: {error}") from error
    if state.get("protocol_version") != 2:
        raise ValueError("run does not use the supported v2 delivery protocol")
    return folder, state


def run_summary(run_folder: str) -> dict[str, Any]:
    folder, state = _load_run(run_folder)
    questions = state.get("turns", [])[-1].get("questions", []) if state.get("turns") else []
    return {
        "ok": True, "run_folder": str(folder), "status": state.get("status"),
        "termination": state.get("termination"), "user_confirmation": state.get("user_confirmation"),
        "artifacts": state.get("artifacts", []), "last_error": state.get("last_error"),
        "next_questions": questions if state.get("status") == "needs_input" else [],
        "protocol_version": 2,
    }


def _invoke(folder: Path, args: list[str], *, background: bool = False) -> dict[str, Any]:
    if CONTROLLER is None or not CONTROLLER.is_file():
        return _error("PM Copilot v2 source checkout is unavailable. Reinstall the plugin and start a new task.")
    result = subprocess.run(
        [sys.executable, str(CONTROLLER), "--run-folder", str(folder), *args, *( ["--background"] if background else [])],
        cwd=folder.parent, text=True, capture_output=True, check=False,
    )
    try:
        payload = run_summary(str(folder))
    except ValueError:
        payload = _error(result.stdout.strip() or result.stderr.strip() or "controller did not create a v2 run")
    payload.update({"controller_exit_code": result.returncode, "controller_stdout": result.stdout[-2000:], "controller_stderr": result.stderr[-2000:]})
    return payload


def start_request(request: str, project_root: str, run_folder: str = "", append_implemented_feature: bool = False, revise: bool = False, revision_requirement_ids: list[str] | None = None) -> dict[str, Any]:
    if not request.strip():
        return _error("request must not be empty")
    project = Path(project_root).expanduser().resolve()
    if not project.is_dir():
        return _error(f"project_root is not a directory: {project}")
    if append_implemented_feature and not run_folder:
        return _error("append_implemented_feature requires run_folder")
    if revise and not run_folder:
        return _error("revise requires run_folder")
    command = [sys.executable, str(CONTROLLER)] if CONTROLLER else []
    command.extend(["--request", request])
    if run_folder:
        command.extend(["--run-folder", str(Path(run_folder).expanduser().resolve())])
    else:
        command.append("--new-requirement")
    if revise:
        command.append("--revise")
        for identifier in revision_requirement_ids or []:
            command.extend(["--revision-requirement-id", identifier])
    if append_implemented_feature:
        command.append("--append-implemented-feature")
    if CONTROLLER is None or not CONTROLLER.is_file():
        return _error("PM Copilot v2 source checkout is unavailable. Reinstall the plugin and start a new task.")
    result = subprocess.run(command, cwd=project, text=True, capture_output=True, check=False)
    try:
        response = json.loads(result.stdout)
        folder = response.get("run_folder") or response.get("folder")
        payload = run_summary(str(folder)) if folder else _error(result.stdout.strip())
    except (json.JSONDecodeError, ValueError):
        payload = _error(result.stdout.strip() or result.stderr.strip())
    payload.update({"controller_exit_code": result.returncode, "controller_stdout": result.stdout[-2000:], "controller_stderr": result.stderr[-2000:]})
    return payload


def submit_answer(run_folder: str, answer: str) -> dict[str, Any]:
    folder, state = _load_run(run_folder)
    return _error("run is not awaiting input") if state.get("status") != "needs_input" else _invoke(folder, ["--answers", answer])


def confirm_delivery(run_folder: str) -> dict[str, Any]:
    folder, state = _load_run(run_folder)
    return _error("run is not ready") if state.get("status") != "ready" else _invoke(folder, ["--confirm"], background=True)


TOOLS = [{"name": "prd_start_request", "description": "Start a v2 PRD request.", "inputSchema": {"type": "object", "properties": {"request": {"type": "string"}, "project_root": {"type": "string"}, "run_folder": {"type": "string"}, "append_implemented_feature": {"type": "boolean"}, "revise": {"type": "boolean"}, "revision_requirement_ids": {"type": "array", "items": {"type": "string"}}}, "required": ["request", "project_root"]}}, {"name": "prd_run_status", "description": "Read v2 PRD run status.", "inputSchema": {"type": "object", "properties": {"run_folder": {"type": "string"}}, "required": ["run_folder"]}}, {"name": "prd_submit_answer", "description": "Answer the sole consolidated product question.", "inputSchema": {"type": "object", "properties": {"run_folder": {"type": "string"}, "answer": {"type": "string"}}, "required": ["run_folder", "answer"]}}, {"name": "prd_confirm_delivery", "description": "Confirm and deliver the v2 PRD.", "inputSchema": {"type": "object", "properties": {"run_folder": {"type": "string"}}, "required": ["run_folder"]}}]


def _handle(message: dict[str, Any]) -> dict[str, Any] | None:
    if message.get("method") == "initialize": return {"jsonrpc": "2.0", "id": message.get("id"), "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "pm-copilot", "version": "2"}}}
    if message.get("method") == "tools/list": return {"jsonrpc": "2.0", "id": message.get("id"), "result": {"tools": TOOLS}}
    if message.get("method") != "tools/call": return None
    args = message.get("params", {}).get("arguments", {})
    try:
        name = message["params"]["name"]
        payload = start_request(str(args["request"]), str(args["project_root"]), str(args.get("run_folder", "")), bool(args.get("append_implemented_feature", False)), bool(args.get("revise", False)), args.get("revision_requirement_ids")) if name == "prd_start_request" else run_summary(str(args["run_folder"])) if name == "prd_run_status" else submit_answer(str(args["run_folder"]), str(args["answer"])) if name == "prd_submit_answer" else confirm_delivery(str(args["run_folder"])) if name == "prd_confirm_delivery" else _error("unknown tool")
    except (KeyError, TypeError, ValueError) as error: payload = _error(str(error))
    return {"jsonrpc": "2.0", "id": message.get("id"), "result": {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}], "isError": not payload.get("ok", False)}}


def main() -> int:
    for line in sys.stdin:
        try:
            response = _handle(json.loads(line))
            if response: print(json.dumps(response, ensure_ascii=False), flush=True)
        except json.JSONDecodeError: print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}), flush=True)
    return 0


if __name__ == "__main__": raise SystemExit(main())
