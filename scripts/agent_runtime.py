#!/usr/bin/env python3
"""Execute an attributable PRD stage through the local Codex CLI."""

from __future__ import annotations

import hashlib
import os
import signal
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_CODEX_MODEL = "gpt-5.6-terra"


def _terminate_process_group(process: subprocess.Popen[str]) -> None:
    """Stop a timed-out Codex stage and every process it started."""
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        process.communicate()


def _codex_model(value: str | None) -> str | None:
    candidate = str(value or "").strip()
    if candidate.startswith("codex/"):
        candidate = candidate.split("/", 1)[1]
    if "/" in candidate:
        raise ValueError("PM Copilot only supports Codex model identifiers")
    return candidate or None


def execute(
    requested_provider: str,
    prompt: str,
    cwd: Path,
    timeout_minutes: int,
    model: str | None,
    schema_path: str | None,
    dry_run: bool,
    output_limit: int = 4000,
    first_artifact_seconds: int | None = None,
    allow_transport_fallback: bool = False,
) -> dict[str, Any]:
    """Run one bounded stage without vendor discovery, fallback, or daemon state.

    The controller owns staging and verifies the promised artifact itself. This
    adapter only owns the Codex process and returns attributable completion
    evidence for that stage.
    """
    del first_artifact_seconds, allow_transport_fallback
    if requested_provider not in {"auto", "codex"}:
        return {
            "provider": "codex", "model": None, "status": "blocked",
            "failure_category": "unsupported_runtime", "output": "",
            "error": "PM Copilot supports only the local Codex runtime",
        }
    executable = shutil.which("codex")
    if not executable:
        return {
            "provider": "codex", "model": None, "status": "blocked",
            "failure_category": "codex_unavailable", "output": "",
            "error": "Codex CLI is not available on PATH",
        }
    try:
        selected_model = _codex_model(model) or DEFAULT_CODEX_MODEL
    except ValueError as error:
        return {
            "provider": "codex", "model": None, "status": "blocked",
            "failure_category": "unsupported_model", "output": "", "error": str(error),
        }
    if schema_path and not Path(schema_path).is_file():
        return {
            "provider": "codex", "model": selected_model, "status": "blocked",
            "failure_category": "invalid_output_schema", "output": "",
            "error": f"output schema not found: {schema_path}",
        }

    output_file = tempfile.NamedTemporaryFile(prefix="pm-copilot-stage-", suffix=".txt", delete=False)
    output_file.close()
    output_path = Path(output_file.name)
    command = [
        executable, "--disable", "plugins", "--disable", "remote_plugin",
        "exec", "--ephemeral", "--skip-git-repo-check", "--cd", str(cwd.resolve()),
        "--sandbox", "workspace-write", "--config", 'model_reasoning_effort="minimal"',
    ]
    command.extend(["--model", selected_model])
    if schema_path:
        command.extend(["--output-schema", str(Path(schema_path).resolve())])
    command.extend(["--output-last-message", str(output_path), prompt])
    result: dict[str, Any] = {
        "provider": "codex", "model": selected_model,
        "cwd": ".", "dry_run": dry_run,
        "command": [*command[:-1], "[PROMPT REDACTED]"],
        "status": "planned" if dry_run else "failed", "output": "", "error": "",
    }
    if dry_run:
        output_path.unlink(missing_ok=True)
        return result
    try:
        process = subprocess.Popen(
            command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True,
        )
        stdout, stderr = process.communicate(timeout=max(1, timeout_minutes) * 60)
        output = output_path.read_text(encoding="utf-8", errors="replace") if output_path.is_file() else stdout
        output = output.strip()
        result.update({
            "status": "complete" if process.returncode == 0 else "failed",
            "exit_code": process.returncode,
            "failure_category": None if process.returncode == 0 else "codex_execution_failed",
            "output": output[-output_limit:],
            "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
            "output_truncated": len(output) > output_limit,
            "error": stderr[-2000:].strip(),
        })
    except subprocess.TimeoutExpired as error:
        _terminate_process_group(process)
        output = str(error.stdout or "").strip()
        result.update({
            "status": "timed_out", "failure_category": "agent_timeout",
            "output": output[-output_limit:],
            "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
            "output_truncated": len(output) > output_limit,
            "error": f"Codex execution exceeded {timeout_minutes} minute(s)",
        })
    except BaseException:
        _terminate_process_group(process)
        raise
    finally:
        output_path.unlink(missing_ok=True)
    return result
