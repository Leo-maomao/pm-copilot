#!/usr/bin/env python3
"""Discover and execute the user's active local agent runtime without API keys."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import select
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
SEAWORK_TRANSPORT_PROVIDERS = frozenset({"seawork", "seawork-claude"})
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
# A transport failure normally means the local Seawork control plane is not a
# useful path for the next stage either. Keep the breaker process-local and
# short-lived so a recovered daemon is probed again without carrying a stale
# failure into a later controller invocation.
SEAWORK_CIRCUIT_BREAKER_SECONDS = 90
_SEAWORK_CIRCUIT_OPEN_UNTIL = 0.0
# Per-agent inspection must fail promptly. A stalled control-plane query is
# neither evidence of a model mismatch nor a reason to consume a full stage.
SEAWORK_AGENT_INSPECT_TIMEOUT_SECONDS = 5
# Reusing a known-healthy daemon probe avoids repeated process startup during
# a burst of stage dispatches. Agent records and model catalogs are never
# cached, so an Agent state or model change is always observed directly.
SEAWORK_HEALTH_CACHE_SECONDS = 2.0
SEAWORK_CONTROL_PLANE_FAILURE_PREFIX = "could not query Agent state:"
_SEAWORK_HEALTH_CACHE: tuple[str, float, str] | None = None
ACTIVE_MODEL_CACHE_SECONDS = 30.0
_DIRECT_CODEX_MODEL_CACHE: dict[str, tuple[str, float, str]] = {}
_SEAWORK_ACTIVE_MODEL_CACHE: dict[str, tuple[str, float]] = {}


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
    def wait_for_exit(wait_seconds: float) -> bool:
        """Poll without ``time.sleep`` so an interrupt cannot abort cleanup."""
        wait_deadline = time.monotonic() + wait_seconds
        while process.poll() is None and time.monotonic() < wait_deadline:
            select.select([], [], [], min(0.05, max(0.0, wait_deadline - time.monotonic())))
        return process.poll() is not None

    try:
        process = subprocess.Popen(
            list(command), cwd=str(cwd) if cwd else None, text=True,
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle, stderr=stderr_handle, start_new_session=True, env=env,
        )
    except BaseException:
        # Failed short-lived probes are common when a local runtime is being
        # restarted. They must not leak two descriptors and their temporary
        # output files on every failed attempt.
        stdout_handle.close()
        stderr_handle.close()
        stdout_path.unlink(missing_ok=True)
        stderr_path.unlink(missing_ok=True)
        raise
    stdout_handle.close()
    stderr_handle.close()
    timed_out = False
    deadline = time.monotonic() + timeout
    progress_deadline = (
        time.monotonic() + max(0, no_progress_timeout)
        if progress_path and no_progress_timeout is not None else None
    )
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
                    # Content stages deliberately disable the first-write
                    # watchdog. In that mode a durable first write is useful
                    # progress, not permission to cut the Agent off five
                    # seconds later; the caller's full stage deadline remains
                    # the only execution bound.
                    if no_progress_timeout is not None:
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
        if not wait_for_exit(2):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            if not wait_for_exit(2):
                # The caller still receives its interrupt promptly, but make a
                # final parent-only kill attempt so Popen cannot be discarded
                # while its process remains alive.
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                wait_for_exit(1)
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
        if process.poll() is None:
            # A detached child can survive an unavailable group leader on
            # some platforms. Bound one final wait on the direct process so
            # timeout handling never leaks a live Popen object.
            try:
                process.kill()
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
    stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
    stdout_path.unlink(missing_ok=True)
    stderr_path.unlink(missing_ok=True)
    if timed_out:
        timeout_error = subprocess.TimeoutExpired(list(command), timeout, output=stdout, stderr=stderr)
        # Callers must not start a second writer in the same workspace unless
        # this local process has actually exited. ``TimeoutExpired`` supports
        # dynamic attributes and keeps the public exception contract intact.
        timeout_error.cleanup_blocked = process.poll() is None  # type: ignore[attr-defined]
        raise timeout_error
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


def _probe(command: Sequence[str], executable: str, timeout: int = 15) -> tuple[bool, str]:
    try:
        result = _run(command, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    detail = _clean(result.stdout or result.stderr)
    return result.returncode == 0, detail


def _seawork_daemon_health(executable: str) -> tuple[bool, str]:
    """Return a very short-lived healthy daemon observation.

    Only a positive health result is cached. A degraded daemon is always
    re-probed so recovery is visible on the next dispatch, while per-Agent
    status and model data remain uncached for exact attribution.
    """
    global _SEAWORK_HEALTH_CACHE
    now = time.monotonic()
    cached = _SEAWORK_HEALTH_CACHE
    if cached is not None:
        cached_executable, observed_at, detail = cached
        age = now - observed_at
        if cached_executable == executable and 0 <= age < SEAWORK_HEALTH_CACHE_SECONDS:
            return True, detail
    ready, detail = _probe([executable, "status"], executable, timeout=5)
    connected = ready and bool(re.search(r"Connected Daemon\s+reachable", detail))
    if connected:
        # The probe itself can take longer than the cache TTL. Timestamp the
        # observation after it completes so the next stage can actually reuse
        # the successful health result instead of immediately probing again.
        _SEAWORK_HEALTH_CACHE = (executable, time.monotonic(), detail)
    else:
        _SEAWORK_HEALTH_CACHE = None
    return connected, detail


def discover_runtimes(providers: Sequence[str] | None = None) -> list[RuntimeStatus]:
    """Return verified runtimes, optionally probing only explicit providers.

    An explicit direct CLI request must not start an unrelated Seawork daemon
    probe. Besides reducing latency, that keeps a degraded external scheduler
    from becoming a dependency of a normal local Codex stage.
    """
    statuses: list[RuntimeStatus] = []
    requested = set(providers) if providers is not None else None

    def includes(provider: str) -> bool:
        return requested is None or provider in requested

    if includes("seawork") or includes("seawork-claude"):
        seawork = _which("seawork")
        if not seawork:
            seawork_status = RuntimeStatus("seawork", None, "unavailable", True, True, True, "CLI not found")
        elif _seawork_circuit_remaining() > 0:
            seawork_status = RuntimeStatus(
                "seawork", seawork, "degraded", True, True, True,
                "Seawork transport circuit is temporarily open; control-plane probing is suppressed",
            )
        else:
            connected, detail = _seawork_daemon_health(seawork)
            seawork_status = RuntimeStatus(
                "seawork", seawork, "ready" if connected else "degraded",
                True, True, True,
                "local daemon reachable" if connected else (detail or "daemon probe failed"),
            )
        if includes("seawork"):
            statuses.append(seawork_status)
        if includes("seawork-claude"):
            statuses.append(RuntimeStatus(
                "seawork-claude", seawork_status.executable, seawork_status.status,
                True, True, True,
                "Seawork-managed Claude runtime" if seawork_status.status == "ready" else seawork_status.detail,
            ))

    if includes("codex"):
        codex = _which("codex")
        if not codex:
            statuses.append(RuntimeStatus("codex", None, "unavailable", False, True, False, "CLI not found"))
        else:
            ready, detail = _probe([codex, "exec", "--help"], codex)
            statuses.append(RuntimeStatus(
                "codex", codex, "ready" if ready else "degraded", False, True, False,
                "non-interactive exec available" if ready else (detail or "exec probe failed"),
            ))

    if includes("claude"):
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
        if not includes(provider):
            continue
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
        if not includes(name):
            continue
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


def _direct_codex_model(value: str | None) -> str | None:
    """Normalize a model only when it can be passed to the direct Codex CLI."""
    candidate = str(value or "").strip()
    if candidate.startswith("codex/"):
        candidate = candidate.split("/", 1)[1]
    return candidate if candidate and "/" not in candidate else None


def _model_provider_family(value: str | None) -> str | None:
    """Return an explicit model's provider family without inventing one."""
    candidate = str(value or "").strip()
    if "/" not in candidate:
        return None
    provider, _, model_name = candidate.partition("/")
    return provider.lower() if provider and model_name else None


def _model_for_runtime(provider: str, model: str | None) -> str | None:
    """Keep provider-qualified IDs at the boundary that understands them."""
    if not model:
        return None
    if provider == "codex":
        direct_model = _direct_codex_model(model)
        if not direct_model:
            raise RuntimeError(
                f"model '{model}' is not compatible with the direct Codex CLI; "
                "select Seawork explicitly for a non-Codex model"
            )
        return direct_model
    family = _model_provider_family(model)
    if family == provider:
        return str(model).split("/", 1)[1]
    return model


def _cached_direct_codex_model(cwd: Path) -> tuple[str | None, str]:
    cached = _DIRECT_CODEX_MODEL_CACHE.get(str(cwd.resolve()))
    if cached is None:
        return None, ""
    model, observed_at, source = cached
    if 0 <= time.monotonic() - observed_at < ACTIVE_MODEL_CACHE_SECONDS:
        return model, source
    _DIRECT_CODEX_MODEL_CACHE.pop(str(cwd.resolve()), None)
    return None, ""


def _remember_direct_codex_model(cwd: Path, model: str | None, source: str) -> None:
    direct_model = _direct_codex_model(model)
    if direct_model:
        _DIRECT_CODEX_MODEL_CACHE[str(cwd.resolve())] = (direct_model, time.monotonic(), source)


def _declared_direct_codex_model(cwd: Path) -> str | None:
    """Use a local declared Codex model without consulting Seawork."""
    catalog, _warnings = discover_model_catalog("codex", cwd)
    selection = select_model("standard", "codex", catalog)
    return _direct_codex_model(selection.option.model if selection.option else None)


def _cached_seawork_model(cwd: Path) -> str | None:
    cached = _SEAWORK_ACTIVE_MODEL_CACHE.get(str(cwd.resolve()))
    if cached is None:
        return None
    model, observed_at = cached
    if 0 <= time.monotonic() - observed_at < ACTIVE_MODEL_CACHE_SECONDS:
        return model
    _SEAWORK_ACTIVE_MODEL_CACHE.pop(str(cwd.resolve()), None)
    return None


def _remember_seawork_model(cwd: Path, model: str | None) -> None:
    value = str(model or "").strip()
    if value and "/" in value:
        _SEAWORK_ACTIVE_MODEL_CACHE[str(cwd.resolve())] = (value, time.monotonic())


def _ready_direct_codex_runtime() -> RuntimeStatus | None:
    """Check direct Codex without touching the Seawork control plane."""
    for status in discover_runtimes(("codex",)):
        if status.provider == "codex" and status.status == "ready" and status.executable:
            return status
    return None


def active_runtime(cwd: Path | None = None) -> ActiveRuntime:
    """Infer the active host/model from the process tree and matching Seawork agent."""
    commands = "\n".join(_parent_commands())
    seawork_provider = re.search(r'X-Seawork-Agent-Provider"="([^" ]+)', commands)
    if seawork_provider or 'model_provider="seawork"' in commands:
        target = (cwd or Path.cwd()).resolve()
        declared_model = seawork_provider.group(1).strip() if seawork_provider else ""
        if "/" in declared_model:
            _remember_seawork_model(target, declared_model)
            return ActiveRuntime("seawork", declared_model, "current Seawork-backed host session declared its model")
        cached_direct, direct_source = _cached_direct_codex_model(target)
        if cached_direct and _ready_direct_codex_runtime() is not None:
            return ActiveRuntime("codex", cached_direct, f"{direct_source} direct Codex model cache")
        direct_model = _declared_direct_codex_model(target)
        if direct_model and _ready_direct_codex_runtime() is not None:
            return ActiveRuntime("codex", direct_model, "locally declared direct Codex model")
        cached_seawork = _cached_seawork_model(target)
        if cached_seawork:
            return ActiveRuntime("seawork", cached_seawork, "short-lived Seawork model cache")
        if _seawork_circuit_remaining() > 0:
            return ActiveRuntime(
                "seawork", None,
                "Seawork transport circuit is open; control-plane model lookup is suppressed",
            )
        # A full daemon listing is neither a stable model-attribution source
        # nor a cheap health check. It can block ordinary local dispatch for
        # seconds while the daemon is reconnecting, so only an explicit parent
        # signal, a fresh cache, or the configured direct runtime may select a
        # model here. A later dispatch will either use its catalog or ask for
        # an explicit model instead of guessing from unrelated Agents.
        return ActiveRuntime(
            "seawork", None,
            "current Seawork-backed host session; no attributable model declaration",
        )
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
    catalog_provider = selected_provider or (context.runtime or "codex")
    # Model discovery is itself a Seawork control-plane call. The breaker must
    # cover that path too; otherwise a harmless capability query recreates the
    # same stalled provider/models traffic the dispatcher just suppressed.
    if catalog_provider in {"seawork", "seawork-claude"} and _seawork_circuit_remaining() > 0:
        model_options, model_warnings = [], [
            "Seawork model discovery is temporarily suppressed while its transport circuit is open"
        ]
    else:
        model_options, model_warnings = discover_model_catalog(catalog_provider, cwd)
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
            "provider": catalog_provider,
            "models": [item.model for item in model_options if item.model],
            "capabilities": [
                {"model": item.model, "provider": item.provider, "capabilities": sorted(item.capabilities), "source": item.source}
                for item in model_options
            ],
            "warnings": model_warnings,
        },
    }


def select_runtime(requested: str = "auto", cwd: Path | None = None) -> RuntimeStatus:
    cwd = (cwd or Path.cwd()).resolve()
    if requested != "auto":
        if requested in SEAWORK_TRANSPORT_PROVIDERS and _seawork_circuit_remaining() > 0:
            raise RuntimeError("Seawork transport circuit is temporarily open; control-plane probing is suppressed")
        # An explicit provider is an operator-selected local route. Probe only
        # that executable rather than turning a normal Codex stage into a
        # Seawork daemon health check.
        statuses = {status.provider: status for status in discover_runtimes((requested,))}
        status = statuses.get(requested)
        if not status or status.status != "ready":
            detail = status.detail if status else "unknown provider"
            raise RuntimeError(f"runtime '{requested}' is not ready: {detail}")
        if requested not in EXECUTABLE_PROVIDERS:
            raise RuntimeError(f"runtime '{requested}' is detected but has no stable headless adapter")
        return status
    active = active_runtime(cwd)
    if active.runtime == "codex":
        direct_codex = _ready_direct_codex_runtime()
        if direct_codex is not None:
            return direct_codex
        if _seawork_circuit_remaining() > 0:
            raise RuntimeError("direct Codex is not ready while Seawork transport circuit is open")
    if active.runtime == "seawork" and (active.model or "").startswith("codex/"):
        direct_codex = _ready_direct_codex_runtime()
        if direct_codex is not None:
            return direct_codex
    if active.runtime == "seawork" and _seawork_circuit_remaining() > 0:
        direct_codex = _ready_direct_codex_runtime()
        if direct_codex is not None:
            return direct_codex
        raise RuntimeError("Seawork transport circuit is temporarily open; control-plane probing is suppressed")
    statuses = {status.provider: status for status in discover_runtimes()}
    # Ordinary PM stages do not need Seawork's scheduler when its active Agent
    # is already backed by the same Codex family. Prefer the direct CLI, whose
    # isolated execution avoids Seawork control-plane, metadata, and plugin
    # startup overhead. Explicit ``--provider seawork`` and execute_loop keep
    # their operator-requested orchestration behavior above.
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


def _seawork_inspected_record(payload: Any, agent_id: str) -> dict[str, Any] | None:
    """Extract exactly the requested Agent record from inspect JSON."""
    candidates: list[Any] = []
    if isinstance(payload, dict):
        candidates.extend([payload, payload.get("agent"), payload.get("data")])
    elif isinstance(payload, list):
        # Older Seawork releases returned a one-element list for inspect.
        # Accept it only when it contains the exact requested ID.
        candidates.extend(payload)
    for candidate in candidates:
        if isinstance(candidate, dict) and str(candidate.get("id", "")) == agent_id:
            return candidate
    return None


def _seawork_missing_agent(detail: str) -> bool:
    """Distinguish an explicit deleted Agent from a broken control plane."""
    normalized = detail.lower()
    return "agent_not_found" in normalized or "agent not found" in normalized


def _seawork_control_plane_failure(detail: str) -> bool:
    return detail.startswith(SEAWORK_CONTROL_PLANE_FAILURE_PREFIX)


def _is_seawork_transport(provider: str | None) -> bool:
    """Return whether a runtime shares Seawork's daemon and stream bridge."""
    return str(provider or "") in SEAWORK_TRANSPORT_PROVIDERS


def _seawork_agent_record(executable: str, agent_id: str) -> tuple[dict[str, Any] | None, str]:
    """Read the daemon's record for an attributable Agent ID."""
    try:
        inspected = _run(
            [executable, "inspect", agent_id, "--json"],
            timeout=SEAWORK_AGENT_INSPECT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, f"could not query Agent state: {error}"
    detail = _clean((inspected.stdout or "") + "\n" + (inspected.stderr or ""), 1000)
    if inspected.returncode != 0:
        if _seawork_missing_agent(detail):
            return None, "missing"
        return None, f"could not query Agent state: {detail or f'inspect exited {inspected.returncode}'}"
    try:
        payload = json.loads(inspected.stdout or "")
    except json.JSONDecodeError as error:
        return None, f"could not query Agent state: malformed inspect JSON ({error.msg})"
    agent = _seawork_inspected_record(payload, agent_id)
    if agent is None:
        return None, "could not query Agent state: inspect response did not contain the requested Agent"
    status = str(agent.get("status", "")).strip()
    if not status:
        return None, "could not query Agent state: inspect response omitted Agent status"
    return agent, status.lower()


def _seawork_agent_is_terminal(executable: str, agent_id: str) -> tuple[bool, str]:
    """Accept explicit terminal states, including a confirmed deleted Agent."""
    _, status = _seawork_agent_record(executable, agent_id)
    # Seawork keeps completed tasks as reusable records with status ``idle``.
    # An idle task has no active execution and is safe to clean up around.
    # ``missing`` is safe only because _seawork_agent_record maps an explicit
    # agent_not_found response to it. Malformed or unavailable inspect replies
    # retain their control-plane failure text and therefore remain nonterminal.
    return status in {
        "completed", "complete", "closed", "failed", "error", "interrupted", "stopped", "archived", "idle", "missing",
    }, status


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
    poll_interval = 1.0
    while True:
        _, last_state = _seawork_agent_record(executable, agent_id)
        # A successful exact-ID lookup that says the Agent no longer exists is
        # evidence that it cannot still write into this stage. Do not spend the
        # remainder of the delivery budget treating absence as a transient
        # running state.
        if last_state == "missing":
            return False, "missing"
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
        # Starting the Seawork CLI for every status query is comparatively
        # expensive. Poll quickly once for terminal acknowledgement, then
        # back off while preserving the hard deadline and artifact checks.
        remaining = max(0.1, deadline - time.monotonic())
        time.sleep(min(poll_interval, remaining))
        poll_interval = min(8.0, poll_interval * 1.5)


def _execute_seawork(
    command: Sequence[str], executable: str, cwd: Path, timeout_minutes: int,
    result: dict[str, Any], output_limit: int, first_artifact_seconds: int | None,
) -> dict[str, Any]:
    """Run a Seawork Agent with a durable ID and a verified timeout cleanup path."""
    target = _stage_target_from_command(command)
    target_baseline = _artifact_digest(target) if target is not None else None
    detached = _seawork_detached_command(command)
    result["launch_command"] = _portable_command(detached[:-1], cwd) + ["[PROMPT REDACTED]"]
    try:
        launch = _run(detached, cwd=cwd, timeout=30)
    except subprocess.TimeoutExpired:
        # ``--detach`` may have reached the daemon even though the CLI's
        # acknowledgement stream did not. With no attributable Agent ID there
        # is no safe way to stop or exclude that writer, so never reuse this
        # stage workspace for a direct fallback.
        result.update({
            "status": "orphaned",
            "error": "Seawork did not acknowledge detached launch within 30 seconds",
            "failure_category": "seawork_launch_unconfirmed",
            "cleanup_blocked": True,
            "agent_state_after_stop": "unknown",
            "launch_acknowledged": False,
        })
        return result
    launch_output = (launch.stdout or "") + "\n" + (launch.stderr or "")
    agent_id = _agent_id(launch_output)
    if launch.returncode != 0 or not agent_id:
        detail = _clean(launch.stderr or launch.stdout, 2000) or "Seawork detached launch did not return an Agent ID"
        # A process exit or malformed acknowledgement does not prove that a
        # detached daemon task was not created. Treat it as ambiguous until a
        # future isolated retry rather than racing an unknown writer in place.
        result.update({
            "status": "orphaned", "error": detail, "exit_code": launch.returncode,
            "failure_category": "seawork_launch_unconfirmed",
            "cleanup_blocked": True,
            "agent_state_after_stop": "unknown",
            "launch_acknowledged": False,
        })
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
    if _seawork_control_plane_failure(state):
        # The launch returned an attributable ID, but a malformed or
        # unavailable inspect response cannot prove either the model or the
        # Agent's lifecycle. Do not mislabel it as a model mismatch or issue
        # an unverified stop; the caller retains the ID for safe recovery.
        result.update({
            "status": "orphaned",
            "error": f"Seawork control plane unavailable while verifying Agent {agent_id}: {state}",
            "failure_category": "seawork_control_plane_unavailable",
            "cleanup_blocked": True,
            "agent_state_after_stop": state,
        })
        return result
    if state == "missing":
        # The daemon definitively no longer has this exact Agent record. This
        # is a failed stage, never a successful one, but it is safe to leave
        # the workspace and try a bounded local fallback because no detached
        # writer remains to race it.
        result.update({
            "status": "failed",
            "error": f"Seawork Agent {agent_id} disappeared before model verification",
            "failure_category": "seawork_agent_missing",
            "agent_state_after_stop": "missing",
            "control_plane_terminal_state": "missing",
        })
        return result
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
        if final_state == "missing":
            result.update({
                "status": "failed",
                "error": f"Seawork Agent {agent_id} disappeared before terminal completion",
                "failure_category": "seawork_agent_missing",
                "agent_state_after_stop": "missing",
                "control_plane_terminal_state": "missing",
            })
            return result
        stop_output = ""
        try:
            stopped = _run([executable, "stop", agent_id], cwd=cwd, timeout=30)
            stop_output = _clean((stopped.stdout or "") + "\n" + (stopped.stderr or ""), 1000)
        except (OSError, subprocess.TimeoutExpired) as stop_error:
            stop_output = f"stop command failed: {stop_error}"
        stopped_terminal, state = _seawork_agent_is_terminal(executable, agent_id)
        artifact_sha256_after_stop = _artifact_digest(target) if target is not None else None
        artifact_changed_after_stop = bool(
            target is not None
            and _stage_artifact_written(target)
            and artifact_sha256_after_stop != target_baseline
        )
        timeout_error = f"Agent exceeded {timeout_minutes} minute(s); control-plane state was {polled_state}"
        if stopped_terminal:
            timeout_error += f"; stop reached terminal control-plane state {state}"
        if artifact_changed_after_stop:
            # A write observed only after the controller had already timed
            # out is not proof of a complete handoff. It can be a partial
            # write interrupted by ``stop``. Keep the checkpoint as recovery
            # evidence, but require a fresh attributable Agent call before
            # any controller can promote bytes from this stage workspace.
            timeout_error += "; staged artifact changed after stop and was not accepted as completion"
        result.update({
            "status": "timed_out" if stopped_terminal else "orphaned",
            "error": timeout_error,
            "failure_category": (
                "seawork_control_plane_timeout" if polled_state == "control_plane_unavailable"
                else "agent_no_progress" if polled_state == "no_progress_before_first_artifact"
                else "agent_timeout"
            ),
            "stop_evidence": stop_output,
            "agent_state_after_stop": state,
            "artifact_checkpoint": artifact_changed_after_stop,
            "artifact_checkpoint_after_stop": artifact_changed_after_stop,
            "artifact_sha256_after_stop": artifact_sha256_after_stop,
            "artifact_baseline_sha256": target_baseline,
            **({"control_plane_terminal_state": state} if stopped_terminal else {}),
            **({"cleanup_blocked": True} if not stopped_terminal else {}),
        })
        return result
    # Artifacts and daemon state are the evidence needed by the stage gate.
    # ``seawork wait`` only supplies conversational text and has repeatedly
    # leaked a detached CLI on macOS, so it must not govern execution.
    successful_terminal = polled_state in {"completed", "complete", "closed", "idle"}
    artifact_updated = _stage_artifact_updated(target, target_baseline) if target is not None else True
    output = f"Agent {agent_id} reached terminal control-plane state {polled_state}."
    result.update({
        "status": "complete" if successful_terminal and artifact_updated else "failed",
        "exit_code": 0 if successful_terminal and artifact_updated else 1,
        "control_plane_terminal_state": polled_state,
        "artifact_checkpoint": artifact_updated,
        "output": _clean(output, output_limit),
        "output_sha256": hashlib.sha256(_clean(output, output_limit).encode("utf-8")).hexdigest(),
        "output_truncated": False,
        "error": (
            "" if successful_terminal and artifact_updated
            else f"Agent reached terminal state {polled_state} without changing its promised artifact"
            if successful_terminal
            else f"Agent terminal state: {polled_state}"
        ),
        "failure_category": (
            None if successful_terminal and artifact_updated
            else "agent_no_progress" if successful_terminal
            else "seawork_agent_error"
        ),
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
        "seawork_agent_missing",
        # Detached launch can stall before an Agent ID is returned. Treat it
        # as a transport failure so the next device-available model is tried.
        "seawork_launch_error",
    }


def _is_stream_disconnected(result: dict[str, Any]) -> bool:
    detail = " ".join(str(result.get(key, "")) for key in ("error", "output", "failure_category")).lower()
    return "stream disconnected" in detail or "stream_disconnected" in detail


def _seawork_circuit_remaining() -> float:
    """Return the remaining local cooldown without persisting a stale failure."""
    return max(0.0, _SEAWORK_CIRCUIT_OPEN_UNTIL - time.monotonic())


def _open_seawork_circuit() -> float:
    """Avoid repeating a known-bad local Seawork path for a bounded interval."""
    global _SEAWORK_CIRCUIT_OPEN_UNTIL
    _SEAWORK_CIRCUIT_OPEN_UNTIL = max(
        _SEAWORK_CIRCUIT_OPEN_UNTIL,
        time.monotonic() + SEAWORK_CIRCUIT_BREAKER_SECONDS,
    )
    return _seawork_circuit_remaining()


def _close_seawork_circuit() -> None:
    """Let a proven healthy Seawork stage immediately restore the normal path."""
    global _SEAWORK_CIRCUIT_OPEN_UNTIL
    _SEAWORK_CIRCUIT_OPEN_UNTIL = 0.0


def _reset_seawork_circuit() -> None:
    """Test-only reset for the process-local Seawork circuit breaker."""
    global _SEAWORK_HEALTH_CACHE
    _close_seawork_circuit()
    _SEAWORK_HEALTH_CACHE = None
    _DIRECT_CODEX_MODEL_CACHE.clear()
    _SEAWORK_ACTIVE_MODEL_CACHE.clear()


def _direct_codex_model_name(model: str | None) -> str | None:
    """Translate a Seawork ``codex/<model>`` identifier for the Codex CLI."""
    return _direct_codex_model(model)


def _matching_ready_direct_codex(
    cwd: Path, seawork_model: str | None,
) -> tuple[str | None, str, list[str]]:
    """Find an auditable direct-Codex route for the same or ready catalog model.

    The Seawork-selected ``codex/<model>`` is itself evidence that the current
    device exposed that model. When the direct Codex CLI is ready, pass that
    same ID explicitly even if its local configuration catalog omits it; a
    direct rejection remains a recorded fallback failure rather than a silent
    model substitution. If dispatch failed before Seawork reported a model,
    choose an actually declared direct-Codex catalog entry instead of turning
    a transient control-plane failure into ``no_available_model``.
    """
    raw_model = str(seawork_model or "").strip()
    # Only a provider-qualified Codex ID proves that an upstream Seawork model
    # can be passed unchanged to the direct Codex CLI. An unqualified or
    # non-Codex model must use the local catalog selection below.
    direct_model = _direct_codex_model_name(raw_model) if raw_model.startswith("codex/") else None
    if _ready_direct_codex_runtime() is None:
        return None, "direct Codex CLI is not ready on this device", []
    catalog, warnings = discover_model_catalog("codex", cwd)
    eligible: list[tuple[int, str]] = []
    for index, option in enumerate(catalog):
        if option.provider != "codex" or not option.model:
            continue
        candidate = _direct_codex_model_name(option.model)
        if not candidate or not {"standard", "judgment"}.intersection(option.capabilities):
            continue
        if direct_model and candidate == direct_model:
            return direct_model, "direct-codex-catalog", warnings
        # Prefer an explicit judgment capability, then the runtime-declared
        # quality rank; retain catalog order as the final deterministic tie.
        score = (
            (1 if "judgment" in option.capabilities else 0) * 1_000_000
            + option.quality_rank * 1_000
            - index
        )
        eligible.append((score, candidate))
    if direct_model:
        return direct_model, "seawork-discovered-or-operator-selected", warnings
    if eligible:
        return max(eligible, key=lambda item: item[0])[1], "direct-codex-catalog", warnings
    return None, "no ready direct Codex model is declared", warnings


def _distinct_ready_direct_codex(
    cwd: Path, excluded_model: str,
) -> tuple[str | None, str, list[str]]:
    """Choose one declared direct-Codex alternative without returning to Seawork."""
    if _ready_direct_codex_runtime() is None:
        return None, "direct Codex CLI is not ready on this device", []
    catalog, warnings = discover_model_catalog("codex", cwd)
    for option in catalog:
        if option.provider != "codex" or not option.model:
            continue
        candidate = _direct_codex_model_name(option.model)
        if not candidate or candidate == excluded_model:
            continue
        if not {"standard", "judgment"}.intersection(option.capabilities):
            continue
        return candidate, "direct-codex-catalog-distinct", warnings
    return None, "no distinct ready direct Codex model is declared", warnings


def _direct_model_rejected(result: dict[str, Any]) -> bool:
    """Limit a second model attempt to explicit model-selection failures."""
    if result.get("failure_category") == "no_available_model" or result.get("status") == "blocked":
        return True
    detail = " ".join(str(result.get(key, "")) for key in ("error", "output")).lower()
    return "model" in detail and any(
        marker in detail for marker in ("unavailable", "not found", "unsupported", "rejected", "not allowed")
    )


def _direct_model_retryable(result: dict[str, Any]) -> bool:
    """Allow one distinct direct model after an infrastructure-level failure."""
    if _direct_model_rejected(result) or _is_stream_disconnected(result):
        return True
    return result.get("failure_category") in {
        "agent_no_output",
        "agent_no_progress",
        "agent_timeout",
        "seawork_control_plane_timeout",
        "seawork_launch_error",
    }


def _retry_distinct_direct_codex(
    result: dict[str, Any], prompt: str, cwd: Path, timeout_minutes: int,
    schema_path: str | None, output_limit: int, first_artifact_seconds: int | None,
) -> dict[str, Any]:
    """Retry one different local Codex model after a safe local failure."""
    failed_model = _direct_codex_model(str(result.get("model") or ""))
    if not failed_model or not _direct_model_retryable(result):
        return result
    alternate_model, source, warnings = _distinct_ready_direct_codex(cwd, failed_model)
    if not alternate_model:
        result["fallback_attempts"] = [{
            "provider": "codex", "model": failed_model, "status": result.get("status"),
            "reason": _clean(str(result.get("error", "")), 240),
            "source": "initial-direct-dispatch",
        }]
        result["fallback_unavailable_reason"] = source
        result["model_catalog_warnings"] = [
            *list(result.get("model_catalog_warnings") or []), *warnings,
        ]
        return result
    try:
        alternate = execute(
            "codex", prompt, cwd, timeout_minutes, alternate_model, schema_path, False,
            output_limit, first_artifact_seconds, allow_transport_fallback=False,
        )
    except (OSError, RuntimeError) as error:
        alternate = {
            "provider": "codex", "model": alternate_model, "status": "unavailable", "error": str(error),
        }
    attempts = [
        {
            "provider": "codex", "model": failed_model, "status": result.get("status"),
            "reason": _clean(str(result.get("error", "")), 240),
            "source": "initial-direct-dispatch",
        },
        {
            "provider": "codex", "model": alternate_model, "status": alternate.get("status"),
            "reason": _clean(str(alternate.get("error", "")), 240), "source": source,
        },
    ]
    if alternate.get("status") != "complete":
        result["fallback_attempts"] = attempts
        return result
    alternate["fallback_used"] = True
    alternate["fallback_selection_source"] = source
    alternate["fallback_attempts"] = attempts
    alternate["fallback_from"] = {
        "provider": "codex", "model": result.get("model"),
        "failure_category": result.get("failure_category"), "error": result.get("error"),
    }
    alternate["runtime_selection_reason"] = "distinct local Codex retry after a retryable direct failure"
    return alternate


def _seawork_failure_result(
    model: str | None, failure_category: str, error: str,
    *, provider: str = "seawork", transport_duration_seconds: float | None = None,
) -> dict[str, Any]:
    """Represent a pre-dispatch Seawork failure with the same audit shape as a stage failure."""
    result: dict[str, Any] = {
        "provider": provider,
        "model": model,
        "status": "blocked",
        "failure_category": failure_category,
        "error": error,
        "output": "",
        "runtime_selection_reason": "Seawork was unavailable before stage dispatch",
        # This result is created before an Agent launch command is attempted,
        # so a same-workspace local fallback cannot race an unknown writer.
        "dispatch_proven_not_started": True,
    }
    if transport_duration_seconds is not None:
        result["transport_duration_seconds"] = round(max(0.0, transport_duration_seconds), 3)
    return result


def _attempt_direct_codex_fallback(
    seawork_result: dict[str, Any], prompt: str, cwd: Path, timeout_minutes: int,
    schema_path: str | None, output_limit: int, first_artifact_seconds: int | None,
) -> dict[str, Any]:
    """Try the matching direct model, then one distinct retryable alternative."""
    fallback_started = time.monotonic()
    direct_model, selection_reason, catalog_warnings = _matching_ready_direct_codex(
        cwd, str(seawork_result.get("model") or "") or None,
    )
    if not direct_model:
        seawork_result["fallback_attempt"] = {
            "provider": "codex",
            "status": "unavailable",
            "reason": selection_reason,
            "model_catalog_warnings": catalog_warnings,
            "fallback_duration_seconds": round(max(0.0, time.monotonic() - fallback_started), 3),
        }
        return seawork_result
    attempts: list[dict[str, Any]] = []
    try:
        fallback = execute(
            "codex", prompt, cwd, timeout_minutes, direct_model, schema_path, False,
            output_limit, first_artifact_seconds, allow_transport_fallback=False,
        )
    except (OSError, RuntimeError) as error:
        seawork_result["fallback_attempt"] = {
            "provider": "codex", "model": direct_model, "status": "unavailable",
            "reason": str(error), "model_catalog_warnings": catalog_warnings,
            "fallback_duration_seconds": round(max(0.0, time.monotonic() - fallback_started), 3),
        }
        return seawork_result
    first_attempt = {
        "provider": "codex", "model": direct_model, "source": selection_reason,
        "status": fallback.get("status"),
        "reason": _clean(str(fallback.get("error", "")), 240),
        "fallback_duration_seconds": round(max(0.0, time.monotonic() - fallback_started), 3),
    }
    attempts.append(first_attempt)
    if fallback.get("status") != "complete":
        if not _direct_model_retryable(fallback):
            seawork_result["fallback_attempt"] = {**first_attempt, "model_catalog_warnings": catalog_warnings}
            seawork_result["fallback_attempts"] = attempts
            return seawork_result
        alternate_model, alternate_source, alternate_warnings = _distinct_ready_direct_codex(cwd, direct_model)
        if not alternate_model:
            seawork_result["fallback_attempt"] = {**first_attempt, "model_catalog_warnings": catalog_warnings}
            seawork_result["fallback_attempts"] = attempts
            return seawork_result
        alternate_started = time.monotonic()
        try:
            alternate = execute(
                "codex", prompt, cwd, timeout_minutes, alternate_model, schema_path, False,
                output_limit, first_artifact_seconds, allow_transport_fallback=False,
            )
        except (OSError, RuntimeError) as error:
            alternate = {"provider": "codex", "model": alternate_model, "status": "unavailable", "error": str(error)}
        alternate_attempt = {
            "provider": "codex", "model": alternate_model, "source": alternate_source,
            "status": alternate.get("status"),
            "reason": _clean(str(alternate.get("error", "")), 240),
            "fallback_duration_seconds": round(max(0.0, time.monotonic() - alternate_started), 3),
        }
        attempts.append(alternate_attempt)
        if alternate.get("status") != "complete":
            seawork_result["fallback_attempt"] = {
                **alternate_attempt, "model_catalog_warnings": alternate_warnings,
            }
            seawork_result["fallback_attempts"] = attempts
            return seawork_result
        fallback = alternate
        selection_reason = alternate_source
    fallback["fallback_used"] = True
    fallback["fallback_reason"] = seawork_result.get("failure_category")
    fallback["fallback_selection_source"] = selection_reason
    fallback["fallback_duration_seconds"] = round(max(0.0, time.monotonic() - fallback_started), 3)
    fallback["fallback_attempts"] = attempts
    fallback["fallback_from"] = {
        "provider": seawork_result.get("provider", "seawork"),
        "model": seawork_result.get("model"),
        "failure_category": seawork_result.get("failure_category"),
        "error": seawork_result.get("error"),
        "agent_id": seawork_result.get("agent_id"),
        "transport_duration_seconds": seawork_result.get("transport_duration_seconds"),
    }
    fallback["runtime_selection_reason"] = (
        f"direct Codex fallback after Seawork {seawork_result.get('failure_category', 'failure')}"
    )
    return fallback


def _opens_seawork_circuit(result: dict[str, Any]) -> bool:
    """Limit the breaker to transport/control-plane/no-progress conditions."""
    return result.get("failure_category") in {
        "seawork_runtime_unhealthy",
        "seawork_circuit_open",
        "seawork_control_plane_timeout",
        "agent_no_progress",
        "agent_timeout",
        "seawork_agent_error",
        "seawork_agent_missing",
        "seawork_launch_error",
        "seawork_launch_unconfirmed",
    } or _is_stream_disconnected(result)


def _safe_to_direct_codex_fallback(result: dict[str, Any]) -> bool:
    """Do not share a target workspace with a Seawork Agent that may still write.

    A control-plane loss after a detached Agent ID exists is intentionally
    recoverable, not eligible for an in-place direct retry. A pre-dispatch
    failure, or a confirmed terminal/stop state, is safe to route elsewhere.
    """
    if not _opens_seawork_circuit(result) or result.get("cleanup_blocked"):
        return False
    if not result.get("agent_id"):
        # A missing ID is safe only for a failure observed *before* dispatch.
        # A disconnected synchronous structured-output call has no ID by CLI
        # design, but may still leave a remote Agent running.
        return result.get("dispatch_proven_not_started") is True
    terminal_state = str(
        result.get("agent_state_after_stop")
        or result.get("control_plane_terminal_state")
        or ""
    ).lower()
    return terminal_state in {
        "completed", "complete", "closed", "failed", "error", "interrupted",
        "stopped", "archived", "idle", "missing",
    }


def _transport_fallback_candidates(
    failed_provider: str, failed_model: str | None, cwd: Path,
    advertised_models: Sequence[str] | None = None, *,
    excluded_providers: Sequence[str] = (),
) -> list[tuple[str, str | None, str]]:
    """Discover auditable local alternatives in preference order at failure time."""
    ranked: list[tuple[int, int, tuple[str, str | None, str]]] = []
    excluded = {str(provider) for provider in excluded_providers}
    failed_name = (failed_model or "").rsplit("/", 1)[-1]
    for status in discover_runtimes():
        if (
            status.status != "ready"
            or status.provider not in EXECUTABLE_PROVIDERS
            or status.provider in excluded
        ):
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
        if failed_provider in excluded:
            break
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
    output_limit: int, first_artifact_seconds: int | None, schema_path: str | None = None, *,
    excluded_providers: Sequence[str] = (), prior_attempts: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Try bounded distinct current-device models after a transport failure."""
    candidates = _transport_fallback_candidates(
        str(result.get("provider", "")), str(result.get("model", "")), cwd,
        result.get("available_models") if isinstance(result.get("available_models"), list) else None,
        excluded_providers=excluded_providers,
    )
    attempts = [dict(item) for item in prior_attempts if isinstance(item, dict)]
    if not candidates:
        if attempts:
            result["fallback_attempts"] = attempts
        return result
    attempted = {
        (str(item.get("provider", "")), str(item.get("model") or ""))
        for item in attempts
    }
    dispatched = 0
    # A device may advertise a model that the upstream rejects at dispatch
    # time. Try a small, ordered set instead of treating that single 403 as a
    # product-artifact failure. Each candidate retains normal SHA attribution.
    for provider, fallback_model, source in candidates:
        if (provider, str(fallback_model or "")) in attempted:
            continue
        if dispatched >= 3:
            break
        dispatched += 1
        try:
            fallback = execute(
                provider, prompt, cwd, timeout_minutes, fallback_model, schema_path, False, output_limit,
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
            "failure_category": result.get("failure_category") or "stream_disconnected",
            "error": result.get("error"),
        }
        fallback["fallback_selection_source"] = source
        fallback["fallback_attempts"] = attempts
        return fallback
    result["fallback_attempts"] = attempts
    return result


def _attempt_safe_seawork_fallback(
    seawork_result: dict[str, Any], prompt: str, cwd: Path, timeout_minutes: int,
    schema_path: str | None, output_limit: int, first_artifact_seconds: int | None,
) -> dict[str, Any]:
    """Replace a confirmed-terminal Seawork stage without reusing its transport.

    Prefer a directly compatible Codex model for a Codex-backed Seawork Agent.
    If no direct Codex route is ready, continue with distinct current-device
    providers, but never reintroduce either Seawork transport alias while its
    circuit is open. Callers must already have proved that no remote writer can
    still modify this stage workspace.
    """
    if not _safe_to_direct_codex_fallback(seawork_result):
        return seawork_result
    direct = _attempt_direct_codex_fallback(
        seawork_result, prompt, cwd, timeout_minutes, schema_path, output_limit,
        first_artifact_seconds,
    )
    if direct is not seawork_result:
        return direct
    existing_attempts = list(seawork_result.get("fallback_attempts") or [])
    fallback_attempt = seawork_result.get("fallback_attempt")
    if isinstance(fallback_attempt, dict) and fallback_attempt not in existing_attempts:
        existing_attempts.append(fallback_attempt)
    return _fallback_from_transport(
        seawork_result, prompt, cwd, timeout_minutes, output_limit, first_artifact_seconds,
        schema_path, excluded_providers=tuple(SEAWORK_TRANSPORT_PROVIDERS),
        prior_attempts=existing_attempts,
    )


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
    dispatch_started = time.monotonic()
    context = active_runtime(cwd)
    explicit_model_family = _model_provider_family(model)
    # A provider-qualified non-Codex model must never be sent to the direct
    # Codex CLI just because the current host happens to use Codex. Seawork is
    # the generic provider boundary for these IDs; its normal readiness and
    # fallback checks still apply.
    auto_requires_seawork_model_route = (
        requested_provider == "auto"
        and explicit_model_family is not None
        and explicit_model_family != "codex"
    )
    auto_equivalent_direct_codex_context = (
        requested_provider == "auto"
        and context.runtime == "seawork"
        and (context.model or "").startswith("codex/")
        and not auto_requires_seawork_model_route
    )
    requested_seawork = (
        _is_seawork_transport(requested_provider)
        or (requested_provider == "auto" and context.runtime == "seawork")
        or auto_requires_seawork_model_route
    )
    requested_seawork_model = model or (
        context.model if context.runtime == "seawork" else None
    )
    requested_seawork_provider = (
        requested_provider if _is_seawork_transport(requested_provider) else "seawork"
    )
    remaining_cooldown = _seawork_circuit_remaining()
    # An auto-selected Codex-backed Seawork session may use the equivalent
    # direct Codex CLI. Resolve that route before applying a Seawork cooldown;
    # otherwise a prior Seawork fault turns a normal direct dispatch into a
    # misleading fallback and adds unnecessary transport work.
    if (
        requested_seawork
        and not auto_equivalent_direct_codex_context
        and not dry_run
        and remaining_cooldown > 0
    ):
        unavailable = _seawork_failure_result(
            requested_seawork_model,
            "seawork_circuit_open",
            "Seawork transport circuit is temporarily open after a recent failure",
            provider=requested_seawork_provider,
            transport_duration_seconds=time.monotonic() - dispatch_started,
        )
        unavailable["circuit_cooldown_seconds"] = round(remaining_cooldown, 3)
        return _attempt_safe_seawork_fallback(
            unavailable, prompt, cwd, timeout_minutes, schema_path, output_limit,
            first_artifact_seconds,
        )
    try:
        status = select_runtime("seawork" if auto_requires_seawork_model_route else requested_provider, cwd)
    except RuntimeError as error:
        if not requested_seawork or dry_run:
            raise
        unavailable = _seawork_failure_result(
            requested_seawork_model,
            "seawork_runtime_unhealthy",
            str(error),
            provider=requested_seawork_provider,
            transport_duration_seconds=time.monotonic() - dispatch_started,
        )
        unavailable["circuit_cooldown_seconds"] = round(_open_seawork_circuit(), 3)
        return _attempt_safe_seawork_fallback(
            unavailable, prompt, cwd, timeout_minutes, schema_path, output_limit,
            first_artifact_seconds,
        )
    auto_equivalent_direct_codex = (
        auto_equivalent_direct_codex_context
        and status.provider == "codex"
    )
    # The direct CLI may be unavailable even though the active Seawork Agent
    # uses Codex. In that case selection remains Seawork-backed and must still
    # honor the existing cooldown rather than relaunching a known-bad path.
    if (
        requested_seawork
        and _is_seawork_transport(status.provider)
        and not dry_run
        and remaining_cooldown > 0
    ):
        unavailable = _seawork_failure_result(
            requested_seawork_model,
            "seawork_circuit_open",
            "Seawork transport circuit is temporarily open after a recent failure",
            provider=requested_seawork_provider,
            transport_duration_seconds=time.monotonic() - dispatch_started,
        )
        unavailable["circuit_cooldown_seconds"] = round(remaining_cooldown, 3)
        return _attempt_safe_seawork_fallback(
            unavailable, prompt, cwd, timeout_minutes, schema_path, output_limit,
            first_artifact_seconds,
        )
    # ``select_runtime(auto)`` can correctly identify a Seawork-backed host
    # and choose direct Codex after its daemon health probe fails. Route that
    # failure through strict matching and provenance. A healthy Codex-backed
    # Seawork session instead takes the normal Codex-first route above.
    if (
        not dry_run
        and requested_provider == "auto"
        and context.runtime == "seawork"
        and status.provider == "codex"
        and not auto_equivalent_direct_codex
    ):
        unavailable = _seawork_failure_result(
            requested_seawork_model,
            "seawork_runtime_unhealthy",
            "Seawork was not ready; auto selection chose direct Codex",
            provider=requested_seawork_provider,
            transport_duration_seconds=time.monotonic() - dispatch_started,
        )
        unavailable["circuit_cooldown_seconds"] = round(_open_seawork_circuit(), 3)
        return _attempt_safe_seawork_fallback(
            unavailable, prompt, cwd, timeout_minutes, schema_path, output_limit,
            first_artifact_seconds,
        )
    schema_path = _load_schema(schema_path)
    selected_model = _model_for_runtime(status.provider, model) or (
        context.model
        if _is_seawork_transport(status.provider) or (status.provider == "codex" and context.runtime == "codex")
        else None
    )
    if not selected_model and context.model and "/" in context.model:
        provider_family, provider_model = context.model.split("/", 1)
        if provider_family == status.provider:
            selected_model = provider_model
    catalog, catalog_warnings = discover_model_catalog(status.provider, cwd, selected_model)
    configured_model = next((item.model for item in catalog if item.source == "provider-config" and item.model), None)
    selected_model = selected_model or configured_model
    model_requirement = "judgment" if _is_seawork_transport(status.provider) else "standard"
    model_selection = select_model(model_requirement, status.provider, catalog, selected_model)
    # Seawork has no implicit model contract. A discovered capability-selected
    # model must become the actual launch argument before command construction.
    if not selected_model and model_selection.option and model_selection.option.model:
        selected_model = model_selection.option.model
    if _is_seawork_transport(status.provider) and not selected_model:
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
            "Codex-first direct route for an equivalent Seawork-backed Codex session"
            if auto_equivalent_direct_codex
            else "explicit provider-qualified model requires the Seawork model boundary"
            if auto_requires_seawork_model_route
            else context.source if requested_provider == "auto" and status.provider == context.runtime
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
        if _is_seawork_transport(status.provider) and not schema_path:
            seawork_started = time.monotonic()
            seawork_result = _execute_seawork(
                command, status.executable or status.provider, cwd, timeout_minutes, result, output_limit,
                first_artifact_seconds,
            )
            seawork_result["transport_duration_seconds"] = round(
                max(0.0, time.monotonic() - seawork_started), 3,
            )
            if seawork_result.get("status") == "complete":
                _close_seawork_circuit()
                return seawork_result
            if _opens_seawork_circuit(seawork_result):
                seawork_result["circuit_cooldown_seconds"] = round(_open_seawork_circuit(), 3)
            if _safe_to_direct_codex_fallback(seawork_result):
                return _attempt_safe_seawork_fallback(
                    seawork_result, prompt, cwd, timeout_minutes, schema_path, output_limit,
                    first_artifact_seconds,
                )
            return seawork_result
        execution_environment = None
        progress_path: Path | None = None
        progress_baseline: str | None = None
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
                _is_seawork_transport(status.provider)
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
        artifact_updated = _stage_artifact_updated(progress_path, progress_baseline) if progress_path else True
        completed_successfully = completed.returncode == 0 and artifact_updated
        completed_error = _diagnostic(completed.stderr, 2000)
        if completed.returncode == 0 and not artifact_updated:
            completed_error = "runtime exited without changing its promised artifact in the staging workspace"
        result.update({
            "status": "complete" if completed_successfully else "failed",
            "exit_code": 0 if completed_successfully else (completed.returncode or 1),
            "artifact_checkpoint": artifact_updated,
            "failure_category": "agent_no_output" if completed.returncode == 0 and not artifact_updated else None,
            "output": _clean(output, output_limit),
            "output_sha256": hashlib.sha256(_clean(output, output_limit).encode("utf-8")).hexdigest(),
            "output_truncated": len(_clean(output, output_limit)) < len(SECRET_PATTERN.sub(_redact_secret, output.strip())),
            "error": completed_error,
        })
        actual_model = _actual_provider_model(status.provider, output)
        if actual_model:
            result["model"] = actual_model
        if status.provider == "codex" and result["status"] == "complete":
            _remember_direct_codex_model(cwd, str(result.get("model") or ""), "verified")
        if allow_transport_fallback and status.provider == "codex" and result["status"] == "failed":
            retried = _retry_distinct_direct_codex(
                result, prompt, cwd, timeout_minutes, schema_path, output_limit, first_artifact_seconds,
            )
            if retried is not result:
                return retried
        if allow_transport_fallback and result["status"] == "failed" and _is_stream_disconnected(result):
            if _is_seawork_transport(status.provider) and schema_path:
                # Seawork documents structured output as a synchronous
                # operation that cannot be detached. A broken response stream
                # therefore gives us neither an Agent ID nor proof that the
                # daemon discarded the request. Treat this as an unknown
                # writer and let the controller quarantine before any retry
                # instead of sharing its workspace with Codex.
                result.update({
                    "status": "orphaned",
                    "failure_category": "seawork_stream_unconfirmed",
                    "cleanup_blocked": True,
                    "dispatch_proven_not_started": False,
                })
                result["circuit_cooldown_seconds"] = round(_open_seawork_circuit(), 3)
                return result
            if _is_seawork_transport(status.provider):
                result["transport_duration_seconds"] = round(
                    max(0.0, time.monotonic() - dispatch_started), 3,
                )
                if _safe_to_direct_codex_fallback(result):
                    result["circuit_cooldown_seconds"] = round(_open_seawork_circuit(), 3)
                    return _attempt_safe_seawork_fallback(
                        result, prompt, cwd, timeout_minutes, schema_path, output_limit,
                        first_artifact_seconds,
                    )
                return result
            return _fallback_from_transport(
                result, prompt, cwd, timeout_minutes, output_limit, first_artifact_seconds, schema_path,
            )
        if fallback_used:
            result["fallback_used"] = True
    except subprocess.TimeoutExpired as error:
        cleanup_blocked = bool(getattr(error, "cleanup_blocked", False))
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
            "status": "orphaned" if cleanup_blocked else "complete" if artifact_checkpoint else "timed_out",
            "failure_category": (
                "agent_cleanup_unconfirmed" if cleanup_blocked
                else "agent_no_progress" if progress_missing
                else "agent_post_write_timeout" if artifact_checkpoint
                else "agent_timeout"
            ),
            "completion_basis": "artifact_checkpoint_before_process_timeout" if artifact_checkpoint and not cleanup_blocked else None,
            "post_write_timeout": artifact_checkpoint,
            "cleanup_blocked": cleanup_blocked,
            "error": (
                f"local runtime cleanup was not confirmed after {timeout_minutes} minute(s)"
                if cleanup_blocked
                else f"no first artifact within {first_artifact_seconds} second(s)"
                if progress_missing else f"execution exceeded {timeout_minutes} minute(s)"
            ) + (f"; runtime stderr: {stderr}" if stderr else ""),
            "output": output,
            "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        })
        if _is_seawork_transport(status.provider) and schema_path:
            # Structured Seawork output cannot use --detach, so a local
            # timeout has no attributable Agent ID. It is unsafe to infer that
            # nothing was launched from the vanished stream.
            result.update({
                "status": "orphaned",
                "failure_category": "seawork_stream_unconfirmed",
                "cleanup_blocked": True,
                "dispatch_proven_not_started": False,
            })
            result["circuit_cooldown_seconds"] = round(_open_seawork_circuit(), 3)
        if _is_seawork_transport(status.provider):
            result["transport_duration_seconds"] = round(
                max(0.0, time.monotonic() - dispatch_started), 3,
            )
            if _safe_to_direct_codex_fallback(result):
                result["circuit_cooldown_seconds"] = round(_open_seawork_circuit(), 3)
                return _attempt_safe_seawork_fallback(
                    result, prompt, cwd, timeout_minutes, schema_path, output_limit,
                    first_artifact_seconds,
                )
        elif status.provider == "codex" and allow_transport_fallback and not cleanup_blocked:
            retried = _retry_distinct_direct_codex(
                result, prompt, cwd, timeout_minutes, schema_path, output_limit, first_artifact_seconds,
            )
            if retried is not result:
                return retried
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
