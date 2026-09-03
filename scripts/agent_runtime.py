#!/usr/bin/env python3
"""Discover and execute the user's active local agent runtime without API keys."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from runtime_policy import DEFAULT_SEAWORK_MODEL
from model_catalog import discover_model_catalog, select_model
from runtime_limits import (
    DEFAULT_EXECUTION_TIMEOUT_MINUTES,
    DEFAULT_LOOP_MAX_ITERATIONS,
    DEFAULT_LOOP_TIMEOUT_MINUTES,
)

EXECUTABLE_PROVIDERS = (
    "seawork", "seawork-claude", "codex", "claude", "qwen", "kimi", "qoder", "codebuddy",
)
CANDIDATE_TOOLS = ("gemini", "aider", "opencode", "cursor-agent", "trae", "comate")
SECRET_PATTERN = re.compile(
    r"(?i)(?P<label>api[_ -]?key|token|password)\s*[:=]\s*[^\s,;]+"
    r"|(?P<authorization>authorization)\s*[:=]\s*(?:(?:bearer|basic)[^\s,;]*|[A-Za-z0-9._~-]{16,})"
)
AGENT_ID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\b", re.IGNORECASE,
)
STAGE_TARGET_PATTERN = re.compile(
    r"(?:Write exactly one complete artifact at|Write ONLY one JSON object to) "
    r"(.+\.[A-Za-z0-9_-]+)(?=\.|\s|$)"
)
# A write-first stage without an artifact is not productive work. Keep this
# deliberately short for every runtime so an upstream queue or protocol stall
# is attributed promptly instead of consuming the case's full stage budget.
FIRST_ARTIFACT_SECONDS = 30
POST_ARTIFACT_GRACE_SECONDS = 5
SEAWORK_CONTROL_PLANE_FAILURE_LIMIT = 2


@dataclass(frozen=True)
class RuntimeStatus:
    provider: str
    executable: str | None
    status: str
    supports_detached: bool
    supports_structured_output: bool
    supports_verifier: bool
    detail: str


@dataclass(frozen=True)
class ActiveRuntime:
    runtime: str | None
    model: str | None
    source: str


def _run(
    command: Sequence[str], cwd: Path | None = None, timeout: int = 15,
    env: dict[str, str] | None = None, progress_path: Path | None = None,
    no_progress_timeout: int | None = None, progress_baseline: str | None = None,
) -> subprocess.CompletedProcess[str]:
    stdout_file = tempfile.NamedTemporaryFile(prefix="pm-copilot-stdout-", delete=False)
    stderr_file = tempfile.NamedTemporaryFile(prefix="pm-copilot-stderr-", delete=False)
    stdout_path, stderr_path = Path(stdout_file.name), Path(stderr_file.name)
    stdout_file.close()
    stderr_file.close()
    stdout_handle = stdout_path.open("w", encoding="utf-8")
    stderr_handle = stderr_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        list(command), cwd=str(cwd) if cwd else None, text=True,
        stdin=subprocess.DEVNULL,
        stdout=stdout_handle, stderr=stderr_handle, start_new_session=True, env=env,
    )
    stdout_handle.close()
    stderr_handle.close()
    timed_out = False
    deadline = time.monotonic() + timeout
    progress_deadline = time.monotonic() + no_progress_timeout if progress_path and no_progress_timeout else None
    post_progress_deadline: float | None = None
    observed_progress = False
    try:
        while process.poll() is None and time.monotonic() < deadline:
            if (
                progress_path
                and progress_path.is_file()
                and progress_path.stat().st_size > 0
                and _artifact_digest(progress_path) != progress_baseline
            ):
                if not observed_progress:
                    observed_progress = True
                    post_progress_deadline = time.monotonic() + POST_ARTIFACT_GRACE_SECONDS
            if progress_deadline is not None and not observed_progress and time.monotonic() >= progress_deadline:
                timed_out = True
                break
            if post_progress_deadline is not None and time.monotonic() >= post_progress_deadline:
                timed_out = True
                break
            time.sleep(0.05)
    except KeyboardInterrupt:
        # An operator stop must also stop the child Agent process group. A
        # Python traceback alone otherwise leaves Codex running in the
        # background and consuming the user's budget.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        raise
    if process.poll() is None:
        timed_out = True
        # ``seawork wait`` can ignore SIGTERM. The caller owns this process
        # group, so terminate it directly and bound collection after each
        # signal instead of waiting forever for a watchdog side effect.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        kill_deadline = time.monotonic() + 2
        while process.poll() is None and time.monotonic() < kill_deadline:
            time.sleep(0.05)
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            kill_deadline = time.monotonic() + 2
            while process.poll() is None and time.monotonic() < kill_deadline:
                time.sleep(0.05)
    stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
    stdout_path.unlink(missing_ok=True)
    stderr_path.unlink(missing_ok=True)
    if timed_out:
        raise subprocess.TimeoutExpired(list(command), timeout, output=stdout, stderr=stderr)
    return subprocess.CompletedProcess(list(command), process.returncode, stdout, stderr)


def _artifact_digest(path: Path) -> str | None:
    """Return the durable content identity used by a write-first checkpoint."""
    if not path.is_file() or path.stat().st_size == 0:
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def _isolated_codex_environment() -> Any:
    """Keep Codex state isolated without loading unrelated interactive plugins."""
    source_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
    with tempfile.TemporaryDirectory(prefix="pm-copilot-codex-home-") as temporary_home:
        isolated = Path(temporary_home)
        auth = source_home / "auth.json"
        if auth.exists():
            (isolated / "auth.json").symlink_to(auth)
        _write_minimal_codex_config(source_home / "config.toml", isolated / "config.toml")
        environment = os.environ.copy()
        environment["CODEX_HOME"] = str(isolated)
        yield environment


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _write_minimal_codex_config(source: Path, destination: Path) -> None:
    """Copy only the selected model-provider configuration into a fresh home."""
    try:
        source_lines = source.read_text(encoding="utf-8").splitlines() if source.exists() else []
    except OSError:
        source_lines = []
    provider_match = next((re.match(r'\s*model_provider\s*=\s*["\']([^"\']+)["\']\s*$', line) for line in source_lines), None)
    provider = provider_match.group(1) if provider_match else None
    selected: list[str] = []
    if provider:
        header = f"[model_providers.{provider}]"
        try:
            start = next(index for index, line in enumerate(source_lines) if line.strip() == header)
        except StopIteration:
            start = -1
        if start >= 0:
            for line in source_lines[start + 1:]:
                if line.strip().startswith("["):
                    break
                if re.match(r"\s*[A-Za-z0-9_]+\s*=", line):
                    selected.append(line.strip())
    # Stage Agents are evaluated on the artifact and review evidence, not on
    # exploratory planning depth. Keep local execution responsive even when a
    # user's global profile requests xhigh reasoning.
    # Stage execution uses the authenticated model provider but never needs
    # the interactive remote plugin catalog. Disabling it prevents a ChatGPT
    # plugin-auth startup path from consuming the write-first budget.
    # Every stage receives a complete, tightly scoped prompt and has an
    # independent quality gate. Minimal reasoning prioritizes producing the
    # required write-first checkpoint inside the bounded stage budget.
    lines = ["disable_response_storage = true", 'model_reasoning_effort = "minimal"']
    if provider and selected:
        lines.append(f"model_provider = {_toml_value(provider)}")
        lines.append("")
        lines.append(f"[model_providers.{provider}]")
        lines.extend(selected)
    lines.extend([
        "", "[features]",
        # Evaluation stages do not use Codex plugins. Disable the framework
        # as well as its remote catalog so startup cannot spend the first-write
        # budget resolving an interactive plugin installation.
        "plugins = false",
        "remote_plugin = false",
    ])
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _clean(value: str, limit: int = 600) -> str:
    value = SECRET_PATTERN.sub(_redact_secret, value.strip())
    return value[:limit]


def _diagnostic(value: str, limit: int = 2000) -> str:
    """Preserve the terminal failure while bounding and redacting noisy CLI logs."""
    cleaned = SECRET_PATTERN.sub(_redact_secret, value.strip())
    if len(cleaned) <= limit:
        return cleaned
    head = max(200, limit // 3)
    tail = limit - head - 48
    return f"{cleaned[:head]}\n... [diagnostic truncated] ...\n{cleaned[-tail:]}"


def _redact_secret(match: re.Match[str]) -> str:
    return f"{match.group('label') or match.group('authorization')}=[REDACTED]"


def _portable_command(command: Sequence[str], cwd: Path) -> list[str]:
    home = str(Path.home())
    workspace = str(cwd.resolve())
    return [
        str(part).replace(workspace, ".").replace(home, "$HOME")
        for part in command
    ]


def _reject_credential_prompt(prompt: str) -> None:
    if SECRET_PATTERN.search(prompt):
        raise RuntimeError("agent prompts must not contain credentials; use the already authenticated local runtime")


def _which(name: str) -> str | None:
    return shutil.which(name)


def _probe(command: Sequence[str], executable: str) -> tuple[bool, str]:
    try:
        result = _run(command)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    detail = _clean(result.stdout or result.stderr)
    return result.returncode == 0, detail


def discover_runtimes() -> list[RuntimeStatus]:
    """Return only verified executable providers plus safely detected candidates."""
    statuses: list[RuntimeStatus] = []

    seawork = _which("seawork")
    if not seawork:
        statuses.append(RuntimeStatus("seawork", None, "unavailable", True, True, True, "CLI not found"))
    else:
        ready, detail = _probe([seawork, "status"], seawork)
        connected = bool(re.search(r"Connected Daemon\s+reachable", detail))
        seawork_status = RuntimeStatus(
            "seawork", seawork, "ready" if ready and connected else "degraded",
            True, True, True,
            "local daemon reachable" if ready and connected else (detail or "daemon probe failed"),
        )
        statuses.append(seawork_status)
        statuses.append(RuntimeStatus(
            "seawork-claude", seawork, seawork_status.status,
            True, True, True,
            "Seawork-managed Claude runtime" if seawork_status.status == "ready" else seawork_status.detail,
        ))

    codex = _which("codex")
    if not codex:
        statuses.append(RuntimeStatus("codex", None, "unavailable", False, True, False, "CLI not found"))
    else:
        ready, detail = _probe([codex, "exec", "--help"], codex)
        statuses.append(RuntimeStatus(
            "codex", codex, "ready" if ready else "degraded", False, True, False,
            "non-interactive exec available" if ready else (detail or "exec probe failed"),
        ))

    claude = _which("claude")
    if not claude:
        statuses.append(RuntimeStatus("claude", None, "unavailable", False, True, False, "CLI not found"))
    else:
        ready, detail = _probe([claude, "-p", "--help"], claude)
        statuses.append(RuntimeStatus(
            "claude", claude, "ready" if ready else "degraded", False, True, False,
            "non-interactive print mode available" if ready else (detail or "print probe failed"),
        ))

    for provider, executable_name, help_command, detail in (
        ("qwen", "qwen", ["--help"], "Qwen Code headless prompt mode available"),
        ("kimi", "kimi", ["--help"], "Kimi Code headless prompt mode available"),
        ("qoder", "qodercli", ["--help"], "Qoder CLI headless prompt mode available"),
        ("codebuddy", "codebuddy", ["--help"], "CodeBuddy Code print mode available"),
    ):
        executable = _which(executable_name)
        if not executable:
            statuses.append(RuntimeStatus(provider, None, "unavailable", False, True, False, "CLI not found"))
            continue
        ready, probe_detail = _probe([executable, *help_command], executable)
        statuses.append(RuntimeStatus(
            provider, executable, "ready" if ready else "degraded", False, True, False,
            detail if ready else (probe_detail or "headless CLI probe failed"),
        ))

    for name in CANDIDATE_TOOLS:
        executable = _which(name)
        statuses.append(RuntimeStatus(
            name, executable, "detected_unverified" if executable else "unavailable", False, False, False,
            "detected; no stable PM Copilot headless adapter registered" if executable else "CLI not found",
        ))
    return statuses


def _parent_commands(limit: int = 8) -> list[str]:
    process_id = os.getppid()
    commands: list[str] = []
    for _ in range(limit):
        if process_id < 2:
            break
        try:
            result = _run(["ps", "-p", str(process_id), "-o", "ppid=,command="], timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            break
        if result.returncode != 0 or not result.stdout.strip():
            break
        parent, _, command = result.stdout.strip().partition(" ")
        commands.append(command)
        try:
            process_id = int(parent)
        except ValueError:
            break
    return commands


def active_runtime(cwd: Path | None = None) -> ActiveRuntime:
    """Infer the active host/model from the process tree and matching Seawork agent."""
    commands = "\n".join(_parent_commands())
    seawork_provider = re.search(r'X-Seawork-Agent-Provider"="([^" ]+)', commands)
    if seawork_provider or 'model_provider="seawork"' in commands:
        model = None
        seawork = _which("seawork")
        if seawork:
            try:
                result = _run([seawork, "ls", "--json"], timeout=8)
                agents = json.loads(result.stdout) if result.returncode == 0 else []
                target = str((cwd or Path.cwd()).resolve())
                matches = [
                    agent for agent in agents
                    if str(agent.get("cwd", "")).replace("~", str(Path.home()), 1) == target
                    and agent.get("status") == "running"
                ]
                if len(matches) == 1:
                    model = str(matches[0].get("provider") or "") or None
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
                pass
        return ActiveRuntime("seawork", model, "current Seawork-backed host session")
    for provider, executable_name, label in (
        ("claude", "claude", "Claude"),
        ("codex", "codex", "Codex"),
        ("qwen", "qwen", "Qwen Code"),
        ("kimi", "kimi", "Kimi Code"),
        ("qoder", "qodercli", "Qoder CLI"),
        ("codebuddy", "codebuddy", "CodeBuddy Code"),
    ):
        if re.search(rf"(?:^|[ /]){re.escape(executable_name)}(?:\s|$)", commands, re.IGNORECASE):
            return ActiveRuntime(provider, None, f"current {label} host session")
    return ActiveRuntime(None, None, "no active runtime signal")


def runtime_capabilities(cwd: Path | None = None) -> dict[str, object]:
    """Report what can run automatically now, without treating a CLI probe as a guarantee."""
    cwd = (cwd or Path.cwd()).resolve()
    statuses = {status.provider: status for status in discover_runtimes()}
    context = active_runtime(cwd)
    try:
        selected = select_runtime("auto", cwd)
        single_status, selected_provider, selection_reason = "available", selected.provider, context.source
        if selected.provider != context.runtime:
            selection_reason = f"fallback from {context.runtime or 'unknown'} active runtime"
    except RuntimeError as error:
        single_status, selected_provider, selection_reason = "unavailable", None, str(error)
    seawork = statuses.get("seawork")
    model_options, model_warnings = discover_model_catalog(
        selected_provider or (context.runtime or "codex"), cwd,
    )
    return {
        "active_runtime": asdict(context),
        "single_agent_auto": {
            "status": single_status,
            "selected_provider": selected_provider,
            "reason": selection_reason,
        },
        "multi_agent_loop": {
            "status": "available" if seawork and seawork.status == "ready" else "unavailable",
            "reason": "Seawork daemon reachable" if seawork and seawork.status == "ready" else "Seawork worker/verifier loop requires a reachable daemon",
        },
        "model_catalog": {
            "provider": selected_provider or context.runtime or "codex",
            "models": [item.model for item in model_options if item.model],
            "capabilities": [
                {"model": item.model, "provider": item.provider, "capabilities": sorted(item.capabilities), "source": item.source}
                for item in model_options
            ],
            "warnings": model_warnings,
        },
    }


def select_runtime(requested: str = "auto", cwd: Path | None = None) -> RuntimeStatus:
    statuses = {status.provider: status for status in discover_runtimes()}
    if requested != "auto":
        status = statuses.get(requested)
        if not status or status.status != "ready":
            detail = status.detail if status else "unknown provider"
            raise RuntimeError(f"runtime '{requested}' is not ready: {detail}")
        if requested not in EXECUTABLE_PROVIDERS:
            raise RuntimeError(f"runtime '{requested}' is detected but has no stable headless adapter")
        return status
    active = active_runtime(cwd)
    if active.runtime and statuses.get(active.runtime) and statuses[active.runtime].status == "ready":
        return statuses[active.runtime]
    if active.runtime == "seawork" and active.model and "/" in active.model:
        provider_family, _ = active.model.split("/", 1)
        fallback = statuses.get(provider_family)
        if fallback and fallback.status == "ready":
            return fallback
    raise RuntimeError(
        "no active local agent runtime detected; specify --provider explicitly or start an authenticated agent session"
    )


def _load_schema(path: str | None) -> str | None:
    if not path:
        return None
    schema_path = Path(path).expanduser().resolve()
    try:
        json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"invalid output schema '{schema_path}': {error}") from error
    return str(schema_path)


def build_command(
    provider: str,
    executable: str,
    prompt: str,
    cwd: Path,
    timeout_minutes: int,
    model: str | None,
    schema_path: str | None,
    output_path: Path | None,
) -> list[str]:
    """Build a documented non-interactive invocation without embedding secrets."""
    if provider in {"seawork", "seawork-claude"}:
        if not model:
            raise RuntimeError(
                "no model selected for Seawork; configure a provider model or pass --model explicitly"
            )
        command = [
            executable, "run",
            "--mode", "bypassPermissions" if provider == "seawork-claude" else "full-access",
            "--provider", "claude" if provider == "seawork-claude" else model,
            "--wait-timeout", f"{timeout_minutes}m",
        ]
        if provider == "seawork-claude" and model:
            command.extend(["--model", model.split("/", 1)[-1]])
        if schema_path:
            command.extend(["--output-schema", Path(schema_path).read_text(encoding="utf-8")])
        return command + [prompt]
    if provider == "codex":
        # Evaluation stages run from an intentionally minimal temporary
        # workspace rather than a Git checkout. This prevents Codex from
        # spending the stage budget discovering unrelated repository history.
        command = [
            # CODEX_HOME is replaced with a minimal, isolated configuration
            # by _isolated_codex_environment. Do not pass
            # --ignore-user-config here: it would discard that very provider
            # configuration and silently fall back to OpenAI's default.
            executable,
            # Command-line settings take precedence over any inherited config
            # layer. The stage prompt carries all required instruction, so no
            # plugin or remote catalog is part of this execution path.
            "--disable", "plugins",
            "--disable", "remote_plugin",
            "exec", "--ephemeral", "--skip-git-repo-check",
            "--cd", str(cwd), "--sandbox", "workspace-write",
            "--config", 'model_reasoning_effort="minimal"',
        ]
        if model:
            command.extend(["--model", model])
        if schema_path:
            command.extend(["--output-schema", schema_path])
        if output_path:
            command.extend(["--output-last-message", str(output_path)])
        return command + [prompt]
    if provider == "claude":
        command = [executable, "-p", "--output-format", "json"]
        if model:
            command.extend(["--model", model])
        if schema_path:
            command.extend(["--json-schema", Path(schema_path).read_text(encoding="utf-8")])
        return command + [prompt]
    if provider == "qwen":
        command = [executable, "--prompt", prompt, "--output-format", "json"]
        if model:
            command.extend(["--model", model])
        return command
    if provider == "kimi":
        command = [executable, "--prompt", prompt, "--output-format", "stream-json"]
        if model:
            command.extend(["--model", model])
        return command
    if provider == "qoder":
        return [executable, "-p", prompt, "--output-format", "json"]
    if provider == "codebuddy":
        command = [executable, "-p", prompt]
        if model:
            command.extend(["--model", model])
        return command
    raise RuntimeError(f"unsupported provider: {provider}")


def _seawork_detached_command(command: Sequence[str]) -> list[str]:
    """Convert a worker launch into an attributable detached Seawork task."""
    values = list(command)
    prompt = values.pop()
    if "--wait-timeout" in values:
        position = values.index("--wait-timeout")
        del values[position:position + 2]
    return values + ["--detach", "--quiet", prompt]


def _agent_id(value: str) -> str | None:
    match = AGENT_ID_PATTERN.search(value or "")
    return match.group(0) if match else None


def _seawork_agent_record(executable: str, agent_id: str) -> tuple[dict[str, Any] | None, str]:
    """Read the daemon's record for an attributable Agent ID."""
    try:
        listed = _run([executable, "ls", "--json"], timeout=15)
        agents = json.loads(listed.stdout or "[]") if listed.returncode == 0 else []
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        return None, f"could not query Agent state: {error}"
    agent = next((item for item in agents if item.get("id") == agent_id), None)
    return agent if isinstance(agent, dict) else None, str(agent.get("status", "missing")) if isinstance(agent, dict) else "missing"


def _seawork_agent_is_terminal(executable: str, agent_id: str) -> tuple[bool, str]:
    """Accept only an explicit terminal state; stale or missing state is unsafe."""
    _, status = _seawork_agent_record(executable, agent_id)
    # Seawork keeps completed tasks as reusable records with status ``idle``.
    # An idle task has no active execution and is safe to clean up around.
    return status in {"completed", "complete", "closed", "failed", "error", "interrupted", "stopped", "archived", "idle"}, status


def _stage_target_from_command(command: Sequence[str]) -> Path | None:
    """Find the promised write-first artifact without inspecting unrelated files."""
    match = STAGE_TARGET_PATTERN.search(str(command[-1])) if command else None
    return Path(match.group(1)) if match else None


def _stage_artifact_written(path: Path | None) -> bool:
    """Check the one promised stage artifact without inferring broader progress."""
    return bool(path and path.is_file() and path.stat().st_size > 0)


def _stage_artifact_updated(path: Path | None, baseline: str | None) -> bool:
    """Require this Agent call to have changed its promised artifact."""
    return _stage_artifact_written(path) and _artifact_digest(path) != baseline


def _poll_seawork_terminal(
    executable: str, agent_id: str, timeout_seconds: int, progress_path: Path | None = None,
    progress_baseline: str | None = None, first_artifact_seconds: int | None = FIRST_ARTIFACT_SECONDS,
) -> tuple[bool, str]:
    """Stop quickly on control-plane failure or no write-first stage progress."""
    deadline = time.monotonic() + max(0, timeout_seconds)
    progress_deadline = (
        time.monotonic() + min(timeout_seconds, first_artifact_seconds)
        if progress_path and first_artifact_seconds is not None else None
    )
    control_plane_failures = 0
    observed_progress = False
    last_state = "unknown"
    while True:
        _, last_state = _seawork_agent_record(executable, agent_id)
        if last_state.startswith("could not query Agent state"):
            control_plane_failures += 1
            if control_plane_failures >= SEAWORK_CONTROL_PLANE_FAILURE_LIMIT:
                return False, "control_plane_unavailable"
        else:
            control_plane_failures = 0
        if last_state in {"completed", "complete", "closed", "failed", "error", "interrupted", "stopped", "archived", "idle"}:
            return True, last_state
        if _stage_artifact_updated(progress_path, progress_baseline):
            observed_progress = True
        if progress_path and not observed_progress and progress_deadline is not None and time.monotonic() >= progress_deadline:
            return False, "no_progress_before_first_artifact"
        if time.monotonic() >= deadline:
            return False, last_state
        time.sleep(min(2, max(0.1, deadline - time.monotonic())))


def _execute_seawork(
    command: Sequence[str], executable: str, cwd: Path, timeout_minutes: int,
    result: dict[str, Any], output_limit: int, first_artifact_seconds: int | None,
) -> dict[str, Any]:
    """Run a Seawork Agent with a durable ID and a verified timeout cleanup path."""
    target = _stage_target_from_command(command)
    target_baseline = _artifact_digest(target) if target is not None else None
    detached = _seawork_detached_command(command)
    try:
        launch = _run(detached, cwd=cwd, timeout=30)
    except subprocess.TimeoutExpired:
        result.update({"status": "failed", "error": "Seawork did not acknowledge detached launch within 30 seconds"})
        return result
    launch_output = (launch.stdout or "") + "\n" + (launch.stderr or "")
    agent_id = _agent_id(launch_output)
    result["launch_command"] = _portable_command(detached[:-1], cwd) + ["[PROMPT REDACTED]"]
    if launch.returncode != 0 or not agent_id:
        detail = _clean(launch.stderr or launch.stdout, 2000) or "Seawork detached launch did not return an Agent ID"
        result.update({"status": "failed", "error": detail, "exit_code": launch.returncode})
        return result
    result["agent_id"] = agent_id
    requested_provider = command[command.index("--provider") + 1] if "--provider" in command else ""
    explicit_model = command[command.index("--model") + 1] if "--model" in command else ""
    expected_model = (
        f"claude/{explicit_model}" if explicit_model
        else requested_provider if "/" in requested_provider
        else "claude"
    )
    record, state = _seawork_agent_record(executable, agent_id)
    actual_model = str(record.get("provider", "")) if record else ""
    result["requested_model"] = expected_model
    result["actual_model"] = actual_model or None
    if actual_model:
        result["model"] = actual_model
    model_mismatch = (
        not record
        or (bool(explicit_model) and actual_model != expected_model)
        or (not explicit_model and "/" in requested_provider and actual_model != expected_model)
        or (not explicit_model and "/" not in requested_provider and actual_model and not actual_model.startswith("claude/"))
    )
    if model_mismatch:
        stop_output = ""
        try:
            stopped = _run([executable, "stop", agent_id], cwd=cwd, timeout=30)
            stop_output = _clean((stopped.stdout or "") + "\n" + (stopped.stderr or ""), 1000)
        except (OSError, subprocess.TimeoutExpired) as stop_error:
            stop_output = f"stop command failed: {stop_error}"
        terminal, terminal_state = _seawork_agent_is_terminal(executable, agent_id)
        if not terminal:
            result.update({
                "status": "orphaned",
                "error": f"Seawork model verification failed (requested {expected_model}, actual {actual_model or state}); stop remains unconfirmed",
                "failure_category": "seawork_model_mismatch",
                "cleanup_blocked": True,
                "stop_evidence": stop_output,
                "agent_state_after_stop": terminal_state,
            })
        else:
            result.update({
                "status": "failed",
                "error": f"Seawork model mismatch: requested {expected_model}, actual {actual_model or state}",
                "failure_category": "seawork_model_mismatch",
                "stop_evidence": stop_output,
                "agent_state_after_stop": terminal_state,
            })
        return result
    terminal, polled_state = _poll_seawork_terminal(
        executable, agent_id, timeout_minutes * 60, target, target_baseline, first_artifact_seconds,
    )
    if not terminal:
        # A detached Agent can write the promised artifact just before its
        # control-plane record catches up. Refresh once before sending stop:
        # only an actual successful terminal state plus the written artifact
        # is enough to accept completion.
        final_record, final_state = _seawork_agent_record(executable, agent_id)
        if final_state in {"completed", "complete", "closed", "idle"} and _stage_artifact_updated(target, target_baseline):
            final_model = str(final_record.get("provider", "")) if final_record else ""
            if final_model:
                result["actual_model"] = final_model
                result["model"] = final_model
            output = f"Agent {agent_id} wrote its target and reached terminal control-plane state {final_state}."
            result.update({
                "status": "complete",
                "exit_code": 0,
                "completion_basis": "artifact_checkpoint_after_control_plane_refresh",
                "control_plane_refresh_state": final_state,
                "output": _clean(output, output_limit),
                "output_sha256": hashlib.sha256(_clean(output, output_limit).encode("utf-8")).hexdigest(),
                "output_truncated": False,
                "error": "",
            })
            return result
        stop_output = ""
        try:
            stopped = _run([executable, "stop", agent_id], cwd=cwd, timeout=30)
            stop_output = _clean((stopped.stdout or "") + "\n" + (stopped.stderr or ""), 1000)
        except (OSError, subprocess.TimeoutExpired) as stop_error:
            stop_output = f"stop command failed: {stop_error}"
        stopped_terminal, state = _seawork_agent_is_terminal(executable, agent_id)
        if (
            stopped_terminal
            and state in {"completed", "complete", "closed", "idle"}
            and _stage_artifact_updated(target, target_baseline)
        ):
            output = f"Agent {agent_id} wrote its target and reached terminal control-plane state {state} after stop."
            result.update({
                "status": "complete",
                "exit_code": 0,
                "completion_basis": "artifact_checkpoint_after_stop",
                "control_plane_refresh_state": state,
                "stop_evidence": stop_output,
                "agent_state_after_stop": state,
                "output": _clean(output, output_limit),
                "output_sha256": hashlib.sha256(_clean(output, output_limit).encode("utf-8")).hexdigest(),
                "output_truncated": False,
                "error": "",
            })
            return result
        result.update({
            "status": "timed_out" if stopped_terminal else "orphaned",
            "error": f"Agent exceeded {timeout_minutes} minute(s); control-plane state was {polled_state}",
            "failure_category": (
                "seawork_control_plane_timeout" if polled_state == "control_plane_unavailable"
                else "agent_no_progress" if polled_state == "no_progress_before_first_artifact"
                else "agent_timeout"
            ),
            "stop_evidence": stop_output,
            "agent_state_after_stop": state,
            **({"cleanup_blocked": True} if not stopped_terminal else {}),
        })
        return result
    # Artifacts and daemon state are the evidence needed by the stage gate.
    # ``seawork wait`` only supplies conversational text and has repeatedly
    # leaked a detached CLI on macOS, so it must not govern execution.
    output = f"Agent {agent_id} reached terminal control-plane state {polled_state}."
    result.update({
        "status": "complete" if polled_state in {"completed", "complete", "closed", "idle"} else "failed",
        "exit_code": 0 if polled_state in {"completed", "complete", "closed", "idle"} else 1,
        "output": _clean(output, output_limit),
        "output_sha256": hashlib.sha256(_clean(output, output_limit).encode("utf-8")).hexdigest(),
        "output_truncated": False,
        "error": "" if polled_state in {"completed", "complete", "closed", "idle"} else f"Agent terminal state: {polled_state}",
        "failure_category": "seawork_agent_error" if polled_state == "error" else None,
    })
    return result


def _requires_direct_codex_fallback(result: dict[str, Any]) -> bool:
    """Only transport and no-progress failures justify one alternate runtime."""
    return result.get("failure_category") in {
        "seawork_control_plane_timeout",
        "agent_no_progress",
        # A detached Seawork Agent that remains ``running`` until its bounded
        # stop has the same recovery semantics as a broken response stream.
        # The controller still requires a changed staged artifact before it
        # can promote any fallback output.
        "agent_timeout",
        "seawork_agent_error",
    }


def _is_stream_disconnected(result: dict[str, Any]) -> bool:
    detail = " ".join(str(result.get(key, "")) for key in ("error", "output", "failure_category")).lower()
    return "stream disconnected" in detail or "stream_disconnected" in detail


def _transport_fallback_candidates(
    failed_provider: str, failed_model: str | None, cwd: Path,
    advertised_models: Sequence[str] | None = None,
) -> list[tuple[str, str | None, str]]:
    """Discover auditable local alternatives in preference order at failure time."""
    ranked: list[tuple[int, int, tuple[str, str | None, str]]] = []
    failed_name = (failed_model or "").rsplit("/", 1)[-1]
    for status in discover_runtimes():
        if status.status != "ready" or status.provider not in EXECUTABLE_PROVIDERS:
            continue
        catalog, _ = discover_model_catalog(status.provider, cwd)
        for index, option in enumerate(catalog):
            if option.model and option.model.rsplit("/", 1)[-1] == failed_name:
                continue
            if option.model and "standard" not in option.capabilities and "judgment" not in option.capabilities:
                continue
            if option.model is None and "configured_default" not in option.capabilities:
                continue
            # Capability signals come from the runtime query. When a provider
            # cannot rank equal-capability models, retain its reported order.
            capability_rank = 0 if "judgment" in option.capabilities else 1
            default_rank = 1 if option.model is None else 0
            ranked.append((capability_rank + default_rank, index, (status.provider, option.model, option.source)))
    candidates = [candidate for _, _, candidate in sorted(ranked, key=lambda item: (item[0], item[1]))]
    # Preserve the model catalog captured by the failed dispatch. A transient
    # daemon/catalog probe must not erase all fallback options; the failed call
    # already recorded the device-advertised choices for auditability.
    seen = {(provider, model) for provider, model, _ in candidates}
    failed_name = (failed_model or "").rsplit("/", 1)[-1]
    for index, option in enumerate(advertised_models or ()):
        if not isinstance(option, str) or not option.strip():
            continue
        model = option.strip()
        if model.rsplit("/", 1)[-1] == failed_name:
            continue
        key = (failed_provider, model)
        if key in seen:
            continue
        candidates.append((failed_provider, model, "failed-call-model-catalog"))
        seen.add(key)
    # Prefer explicit device-discovered models, then the last known-good
    # catalog in its reported order. Provider/default fallbacks are safe only
    # when their completion payload reveals the actual model.
    return candidates


def _fallback_from_transport(
    result: dict[str, Any], prompt: str, cwd: Path, timeout_minutes: int,
    output_limit: int, first_artifact_seconds: int | None,
) -> dict[str, Any]:
    """Try bounded distinct current-device models after a transport failure."""
    candidates = _transport_fallback_candidates(
        str(result.get("provider", "")), str(result.get("model", "")), cwd,
        result.get("available_models") if isinstance(result.get("available_models"), list) else None,
    )
    if not candidates:
        return result
    attempts: list[dict[str, Any]] = []
    # A device may advertise a model that the upstream rejects at dispatch
    # time. Try a small, ordered set instead of treating that single 403 as a
    # product-artifact failure. Each candidate retains normal SHA attribution.
    for provider, fallback_model, source in candidates[:3]:
        try:
            fallback = execute(
                provider, prompt, cwd, timeout_minutes, fallback_model, None, False, output_limit,
                first_artifact_seconds=first_artifact_seconds, allow_transport_fallback=False,
            )
        except (OSError, RuntimeError) as error:
            attempts.append({
                "provider": provider, "model": fallback_model, "source": source,
                "status": "unavailable", "reason": str(error),
            })
            continue
        attempts.append({
            "provider": provider, "model": fallback_model, "source": source,
            "status": fallback.get("status"), "reason": _clean(str(fallback.get("error", "")), 240),
        })
        if fallback.get("status") != "complete":
            continue
        fallback["fallback_used"] = True
        fallback["fallback_from"] = {
            "provider": result.get("provider"),
            "model": result.get("model"),
            "failure_category": "stream_disconnected",
            "error": result.get("error"),
        }
        fallback["fallback_selection_source"] = source
        fallback["fallback_attempts"] = attempts
        return fallback
    result["fallback_attempts"] = attempts
    return result


def _actual_provider_model(provider: str, output: str) -> str | None:
    """Extract a model ID from a provider's structured completion envelope."""
    if provider != "claude":
        return None
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    direct = payload.get("model")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    usage = payload.get("modelUsage")
    if isinstance(usage, dict):
        return next((str(key) for key in usage if str(key).strip()), None)
    return None


def execute(
    requested_provider: str,
    prompt: str,
    cwd: Path,
    timeout_minutes: int,
    model: str | None,
    schema_path: str | None,
    dry_run: bool,
    output_limit: int = 4000,
    first_artifact_seconds: int | None = FIRST_ARTIFACT_SECONDS,
    allow_transport_fallback: bool = True,
) -> dict[str, Any]:
    _reject_credential_prompt(prompt)
    cwd = cwd.resolve()
    status = select_runtime(requested_provider, cwd)
    context = active_runtime(cwd)
    schema_path = _load_schema(schema_path)
    selected_model = model or (context.model if status.provider == "seawork" else None)
    if not selected_model and context.model and "/" in context.model:
        provider_family, provider_model = context.model.split("/", 1)
        if provider_family == status.provider:
            selected_model = provider_model
    catalog, catalog_warnings = discover_model_catalog(status.provider, cwd, selected_model)
    configured_model = next((item.model for item in catalog if item.source == "provider-config" and item.model), None)
    selected_model = selected_model or configured_model
    model_requirement = "judgment" if status.provider in {"seawork", "seawork-claude"} else "standard"
    model_selection = select_model(model_requirement, status.provider, catalog, selected_model)
    # Seawork has no implicit model contract. A discovered capability-selected
    # model must become the actual launch argument before command construction.
    if not selected_model and model_selection.option and model_selection.option.model:
        selected_model = model_selection.option.model
    if status.provider in {"seawork", "seawork-claude"} and not selected_model:
        return {
            "provider": status.provider, "model": None, "status": "blocked",
            "failure_category": "no_available_model",
            "selection_status": "blocked",
            "selection_reason": model_selection.reason,
            "available_models": [item.model for item in catalog if item.model],
            "model_catalog_warnings": catalog_warnings,
            "cwd": ".", "dry_run": dry_run, "output": "", "error": "No available model for provider",
        }
    output_path: Path | None = None
    temporary_output: tempfile.NamedTemporaryFile[str] | None = None
    if status.provider == "codex" and not dry_run:
        temporary_output = tempfile.NamedTemporaryFile(prefix="pm-copilot-agent-", suffix=".txt", delete=False)
        temporary_output.close()
        output_path = Path(temporary_output.name)
    command = build_command(
        status.provider, status.executable or status.provider, prompt, cwd,
        timeout_minutes, selected_model, schema_path, output_path,
    )
    if model_selection.status == "blocked":
        return {
            "provider": status.provider, "model": None, "status": "blocked",
            "failure_category": "no_available_model",
            "selection_status": "blocked",
            "selection_reason": model_selection.reason,
            "available_models": [item.model for item in catalog if item.model],
            "model_catalog_warnings": catalog_warnings,
            "cwd": ".", "dry_run": dry_run, "output": "", "error": model_selection.reason,
        }
    result: dict[str, Any] = {
        "provider": status.provider,
        "model": selected_model or "configured default",
        "available_models": [item.model for item in catalog if item.model],
        "model_catalog_warnings": catalog_warnings,
        "selection_status": model_selection.status,
        "selection_reason": model_selection.reason,
        "runtime_selection_reason": (
            context.source if requested_provider == "auto" and status.provider == context.runtime
            else f"fallback from {context.runtime or 'unknown'} active runtime" if requested_provider == "auto"
            else "explicit provider request"
        ),
        "cwd": ".",
        "dry_run": dry_run,
        "command": _portable_command(command[:-1], cwd) + ["[PROMPT REDACTED]"],
        "status": "planned" if dry_run else "failed",
        "output": "",
        "error": "",
    }
    if dry_run:
        return result
    try:
        if status.provider in {"seawork", "seawork-claude"} and not schema_path:
            seawork_result = _execute_seawork(
                command, status.executable or status.provider, cwd, timeout_minutes, result, output_limit,
                first_artifact_seconds,
            )
            if status.provider != "seawork" or not _requires_direct_codex_fallback(seawork_result):
                return seawork_result
            if seawork_result.get("failure_category") in {"agent_timeout", "seawork_agent_error"}:
                return _fallback_from_transport(
                    seawork_result, prompt, cwd, timeout_minutes, output_limit, first_artifact_seconds,
                )
            # One alternate path is useful after a transport/no-progress stop;
            # another detached Seawork launch would repeat the same condition.
            direct_model = selected_model.split("/", 1)[-1] if selected_model and "/" in selected_model else selected_model
            try:
                fallback = execute("codex", prompt, cwd, timeout_minutes, direct_model, None, False, output_limit)
            except (OSError, RuntimeError) as error:
                seawork_result["fallback_attempt"] = {
                    "provider": "codex",
                    "status": "unavailable",
                    "reason": str(error),
                }
                return seawork_result
            fallback["fallback_used"] = True
            fallback["fallback_from"] = {
                "provider": "seawork",
                "model": selected_model,
                "failure_category": seawork_result.get("failure_category"),
                "error": seawork_result.get("error"),
                "agent_id": seawork_result.get("agent_id"),
            }
            return fallback
        execution_environment = None
        environment_context = _isolated_codex_environment() if status.provider == "codex" else None
        if environment_context is not None:
            execution_environment = environment_context.__enter__()
        try:
            progress_path = _stage_target_from_command(command) if status.provider == "codex" else None
            progress_baseline = _artifact_digest(progress_path) if progress_path else None
            completed = _run(
                command, cwd=cwd, timeout=timeout_minutes * 60, env=execution_environment,
                progress_path=progress_path,
                no_progress_timeout=first_artifact_seconds if progress_path else None,
                progress_baseline=progress_baseline,
            )
            output = output_path.read_text(encoding="utf-8") if output_path and output_path.exists() else completed.stdout
            fallback_used = False
            if (
                status.provider == "seawork"
                and completed.returncode != 0
                and selected_model
                and "OUTPUT_SCHEMA_FAILED" in (completed.stderr or "")
            ):
                fallback_model = next(
                    (item.model for item in catalog if item.model and item.model != selected_model),
                    None,
                )
                if not fallback_model:
                    raise RuntimeError(
                        "structured output failed and no alternate user-declared model is available"
                    )
                fallback_command = build_command(
                    status.provider, status.executable or status.provider, prompt, cwd,
                    timeout_minutes, fallback_model, schema_path, output_path,
                )
                fallback = _run(fallback_command, cwd=cwd, timeout=timeout_minutes * 60)
                if fallback.returncode == 0:
                    completed = fallback
                    output = output_path.read_text(encoding="utf-8") if output_path and output_path.exists() else fallback.stdout
                    fallback_used = True
                    result["fallback_from_model"] = selected_model
                    result["fallback_model"] = fallback_model
                    result["selection_reason"] += "; active model failed structured execution, fell back to another declared model"
                    result["model"] = fallback_model
        finally:
            if environment_context is not None:
                environment_context.__exit__(None, None, None)
        result.update({
            "status": "complete" if completed.returncode == 0 else "failed",
            "exit_code": completed.returncode,
            "output": _clean(output, output_limit),
            "output_sha256": hashlib.sha256(_clean(output, output_limit).encode("utf-8")).hexdigest(),
            "output_truncated": len(_clean(output, output_limit)) < len(SECRET_PATTERN.sub(_redact_secret, output.strip())),
            "error": _diagnostic(completed.stderr, 2000),
        })
        actual_model = _actual_provider_model(status.provider, output)
        if actual_model:
            result["model"] = actual_model
        if allow_transport_fallback and result["status"] == "failed" and _is_stream_disconnected(result):
            return _fallback_from_transport(
                result, prompt, cwd, timeout_minutes, output_limit, first_artifact_seconds,
            )
        if fallback_used:
            result["fallback_used"] = True
    except subprocess.TimeoutExpired as error:
        artifact_changed = bool(
            progress_path
            and _artifact_digest(progress_path) is not None
            and _artifact_digest(progress_path) != progress_baseline
        )
        progress_missing = bool(progress_path and not artifact_changed)
        output = _clean(str(error.output or ""), output_limit)
        stderr = _diagnostic(str(error.stderr or ""), 2000)
        artifact_checkpoint = bool(
            artifact_changed
        )
        result.update({
            # A stage's durable handoff is its assigned artifact. Preserve a
            # completed write that is visible at timeout, but label it so the
            # independent quality gate, rather than process exit alone,
            # decides whether the stage can advance.
            "status": "complete" if artifact_checkpoint else "timed_out",
            "failure_category": (
                "agent_no_progress" if progress_missing
                else "agent_post_write_timeout" if artifact_checkpoint
                else "agent_timeout"
            ),
            "completion_basis": "artifact_checkpoint_before_process_timeout" if artifact_checkpoint else None,
            "post_write_timeout": artifact_checkpoint,
            "error": (
                f"no first artifact within {FIRST_ARTIFACT_SECONDS} second(s)"
                if progress_missing else f"execution exceeded {timeout_minutes} minute(s)"
            ) + (f"; runtime stderr: {stderr}" if stderr else ""),
            "output": output,
            "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        })
    finally:
        if output_path:
            output_path.unlink(missing_ok=True)
    return result


def execute_loop(
    worker_prompt: str,
    verifier_prompt: str,
    cwd: Path,
    timeout_minutes: int,
    max_iterations: int,
    worker_model: str | None,
    verifier_model: str | None,
    dry_run: bool,
) -> dict[str, Any]:
    """Run Seawork's bounded worker/verifier loop with the local login."""
    _reject_credential_prompt(worker_prompt)
    _reject_credential_prompt(verifier_prompt)
    cwd = cwd.resolve()
    status = select_runtime("seawork", cwd)
    context = active_runtime(cwd)
    catalog, warnings = discover_model_catalog("seawork", cwd, worker_model or context.model)
    worker_selection = select_model("judgment", "seawork", catalog, worker_model or context.model)
    if worker_selection.status == "blocked" or not worker_selection.option or not worker_selection.option.model:
        return {
            "provider": "seawork", "status": "blocked", "failure_category": "no_available_model",
            "selection_status": "blocked", "selection_reason": worker_selection.reason,
            "available_models": [item.model for item in catalog if item.model],
            "model_catalog_warnings": warnings,
        }
    selected_worker_model = worker_selection.option.model
    command = [
        status.executable or "seawork", "loop", "run", worker_prompt,
        "--verify", verifier_prompt,
        "--max-iterations", str(max_iterations),
        "--max-time", f"{timeout_minutes}m",
        "--provider", selected_worker_model,
    ]
    if verifier_model:
        command.extend(["--verify-provider", verifier_model])
    result: dict[str, Any] = {
        "provider": "seawork",
        "worker_model": selected_worker_model,
        "verifier_model": verifier_model or "configured default",
        "selection_status": worker_selection.status,
        "selection_reason": worker_selection.reason,
        "cwd": str(cwd.resolve()),
        "dry_run": dry_run,
        "command": [
            *command[:3], "[WORKER PROMPT REDACTED]", *command[4:5],
            "[VERIFIER PROMPT REDACTED]", *command[6:],
        ],
        "status": "planned" if dry_run else "failed",
        "output": "",
        "error": "",
    }
    if dry_run:
        return result
    try:
        completed = _run(command, cwd=cwd, timeout=timeout_minutes * 60)
        result.update({
            "status": "complete" if completed.returncode == 0 else "failed",
            "exit_code": completed.returncode,
            "output": _clean(completed.stdout, 4000),
            "error": _clean(completed.stderr, 2000),
        })
    except subprocess.TimeoutExpired:
        result.update({"status": "timed_out", "error": f"loop exceeded {timeout_minutes} minute(s)"})
    return result


def _read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).expanduser().read_text(encoding="utf-8").strip()
    return (args.prompt or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    discover_parser = subparsers.add_parser("discover", help="inspect local runtime readiness")
    discover_parser.add_argument("--json", action="store_true", help="emit JSON")
    execute_parser = subparsers.add_parser("execute", help="run one agent with an existing local login")
    execute_parser.add_argument("--provider", choices=("auto",) + EXECUTABLE_PROVIDERS, default="auto")
    execute_parser.add_argument("--model")
    execute_parser.add_argument("--cwd", default=".")
    execute_parser.add_argument("--timeout-minutes", type=int, default=DEFAULT_EXECUTION_TIMEOUT_MINUTES)
    execute_parser.add_argument("--output-schema")
    execute_parser.add_argument("--prompt")
    execute_parser.add_argument("--prompt-file")
    execute_parser.add_argument("--dry-run", action="store_true")
    loop_parser = subparsers.add_parser("loop", help="run a bounded Seawork worker/verifier loop")
    loop_parser.add_argument("--worker-prompt")
    loop_parser.add_argument("--worker-prompt-file")
    loop_parser.add_argument("--verify-prompt", required=True)
    loop_parser.add_argument("--cwd", default=".")
    loop_parser.add_argument("--timeout-minutes", type=int, default=DEFAULT_LOOP_TIMEOUT_MINUTES)
    loop_parser.add_argument("--max-iterations", type=int, default=DEFAULT_LOOP_MAX_ITERATIONS)
    loop_parser.add_argument("--model")
    loop_parser.add_argument("--verify-model")
    loop_parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.command == "discover":
        results = [asdict(status) for status in discover_runtimes()]
        if args.json:
            capabilities = runtime_capabilities()
            print(json.dumps({
                "runtimes": results,
                **capabilities,
            }, ensure_ascii=False, indent=2))
        else:
            for status in results:
                print(f"{status['provider']}: {status['status']} — {status['detail']}")
        return 0

    if args.command == "loop":
        if args.timeout_minutes < 1 or args.max_iterations < 1:
            parser.error("--timeout-minutes and --max-iterations must be at least 1")
        if args.worker_prompt_file:
            worker_prompt = Path(args.worker_prompt_file).expanduser().read_text(encoding="utf-8").strip()
        else:
            worker_prompt = (args.worker_prompt or "").strip()
        if not worker_prompt:
            parser.error("provide --worker-prompt or --worker-prompt-file")
        try:
            result = execute_loop(
                worker_prompt, args.verify_prompt, Path(args.cwd), args.timeout_minutes,
                args.max_iterations, args.model, args.verify_model, args.dry_run,
            )
        except RuntimeError as error:
            print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] in {"planned", "complete"} else 1

    if args.timeout_minutes < 1:
        parser.error("--timeout-minutes must be at least 1")
    prompt = _read_prompt(args)
    if not prompt:
        parser.error("provide --prompt or --prompt-file")
    try:
        result = execute(
            args.provider, prompt, Path(args.cwd), args.timeout_minutes,
            args.model, args.output_schema, args.dry_run,
        )
    except RuntimeError as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"planned", "complete"} else 1




if __name__ == "__main__":
    raise SystemExit(main())
