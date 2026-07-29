#!/usr/bin/env python3
"""Discover and execute the user's active local agent runtime without API keys."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

DEFAULT_SEAWORK_MODEL = "codex/gpt-5.4"
EXECUTABLE_PROVIDERS = (
    "seawork", "codex", "claude", "qwen", "kimi", "qoder", "codebuddy",
)
CANDIDATE_TOOLS = ("gemini", "aider", "opencode", "cursor-agent", "trae", "comate")
SECRET_PATTERN = re.compile(
    r"(?i)(api[_ -]?key|token|password|authorization)\s*[:=]\s*[^\s,;]+"
)


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


def _run(command: Sequence[str], cwd: Path | None = None, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=str(cwd) if cwd else None,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def _clean(value: str, limit: int = 600) -> str:
    value = SECRET_PATTERN.sub(r"\1=[REDACTED]", value.strip())
    return value[:limit]


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
        statuses.append(RuntimeStatus(
            "seawork", seawork, "ready" if ready and connected else "degraded",
            True, True, True,
            "local daemon reachable" if ready and connected else (detail or "daemon probe failed"),
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
    if provider == "seawork":
        command = [
            executable, "run", "--mode", "full-access", "--provider", model or DEFAULT_SEAWORK_MODEL,
            "--wait-timeout", f"{timeout_minutes}m",
        ]
        if schema_path:
            command.extend(["--output-schema", Path(schema_path).read_text(encoding="utf-8")])
        return command + [prompt]
    if provider == "codex":
        command = [executable, "exec", "--cd", str(cwd), "--sandbox", "workspace-write"]
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


def execute(
    requested_provider: str,
    prompt: str,
    cwd: Path,
    timeout_minutes: int,
    model: str | None,
    schema_path: str | None,
    dry_run: bool,
    output_limit: int = 4000,
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
    result: dict[str, Any] = {
        "provider": status.provider,
        "model": selected_model or (DEFAULT_SEAWORK_MODEL if status.provider == "seawork" else "configured default"),
        "selection_reason": (
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
        completed = _run(command, cwd=cwd, timeout=timeout_minutes * 60)
        output = output_path.read_text(encoding="utf-8") if output_path and output_path.exists() else completed.stdout
        fallback_used = False
        if (
            status.provider == "seawork"
            and completed.returncode != 0
            and selected_model
            and selected_model != DEFAULT_SEAWORK_MODEL
            and "OUTPUT_SCHEMA_FAILED" in (completed.stderr or "")
        ):
            fallback_command = build_command(
                status.provider, status.executable or status.provider, prompt, cwd,
                timeout_minutes, DEFAULT_SEAWORK_MODEL, schema_path, output_path,
            )
            fallback = _run(fallback_command, cwd=cwd, timeout=timeout_minutes * 60)
            if fallback.returncode == 0:
                completed = fallback
                output = output_path.read_text(encoding="utf-8") if output_path and output_path.exists() else fallback.stdout
                fallback_used = True
                result["fallback_from_model"] = selected_model
                result["fallback_model"] = DEFAULT_SEAWORK_MODEL
                result["selection_reason"] += "; active Seawork model failed structured execution, fell back to verified default"
                result["model"] = DEFAULT_SEAWORK_MODEL
        result.update({
            "status": "complete" if completed.returncode == 0 else "failed",
            "exit_code": completed.returncode,
            "output": _clean(output, output_limit),
            "output_sha256": hashlib.sha256(_clean(output, output_limit).encode("utf-8")).hexdigest(),
            "output_truncated": len(_clean(output, output_limit)) < len(SECRET_PATTERN.sub(r"\1=[REDACTED]", output.strip())),
            "error": _clean(completed.stderr, 2000),
        })
        if fallback_used:
            result["fallback_used"] = True
    except subprocess.TimeoutExpired:
        result.update({"status": "timed_out", "error": f"execution exceeded {timeout_minutes} minute(s)"})
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
    selected_worker_model = worker_model or context.model or DEFAULT_SEAWORK_MODEL
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
    execute_parser.add_argument("--timeout-minutes", type=int, default=15)
    execute_parser.add_argument("--output-schema")
    execute_parser.add_argument("--prompt")
    execute_parser.add_argument("--prompt-file")
    execute_parser.add_argument("--dry-run", action="store_true")
    loop_parser = subparsers.add_parser("loop", help="run a bounded Seawork worker/verifier loop")
    loop_parser.add_argument("--worker-prompt")
    loop_parser.add_argument("--worker-prompt-file")
    loop_parser.add_argument("--verify-prompt", required=True)
    loop_parser.add_argument("--cwd", default=".")
    loop_parser.add_argument("--timeout-minutes", type=int, default=30)
    loop_parser.add_argument("--max-iterations", type=int, default=2)
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
                print(f"{status.provider}: {status.status} — {status.detail}")
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
