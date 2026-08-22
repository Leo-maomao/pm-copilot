#!/usr/bin/env python3
"""Run the complete evaluation portfolio in bounded, resumable case batches.

This is an evaluation control plane only. It never turns a dry-run or a
controlled fixture into human approval, and it records each case's actual
runner report, Agent calls, artifacts, and validation outcome.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from plan_evaluation_portfolio import ROOT, portfolio
from portfolio_contract import plan_digest
from runtime_limits import (
    DEFAULT_EXECUTION_TIMEOUT_MINUTES,
    DEFAULT_PORTFOLIO_MAX_REVISIONS,
    DEFAULT_PORTFOLIO_WORKERS,
    MAX_CODEX_CASE_WORKERS,
    SEAWORK_RESTART_TIMEOUT_SECONDS,
)
from run_evaluation_scenario import execute_case


SEAWORK_STATE_RUNTIME_FAILURE = re.compile(
    r"failed to initialize (?:sqlite )?state runtime|failed to create agent: codex app-server",
    re.IGNORECASE,
)
SEAWORK_DAEMON_UNAVAILABLE = re.compile(
    r"runtime 'seawork(?:-claude)?' is not ready|local daemon\s+unresponsive|connected daemon\s+unreachable",
    re.IGNORECASE,
)
SEAWORK_MODEL_MISMATCH = re.compile(r"seawork model mismatch|seawork model verification failed", re.IGNORECASE)


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _canonical_completed_cases(index_path: Path | None, selected_cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Load only hash-pinned completed cases from an explicit canonical index."""
    if index_path is None:
        return {}
    data = json.loads(index_path.read_text(encoding="utf-8"))
    if data.get("mode") != "evaluation_canonical_index":
        raise ValueError(f"not an evaluation canonical index: {index_path}")
    if data.get("plan_sha256") != plan_digest(data.get("plan_snapshot", [])):
        raise ValueError(f"canonical index plan digest is invalid: {index_path}")
    selected = {case["case_id"] for case in selected_cases}
    restored: dict[str, dict[str, Any]] = {}
    for case_id, entry in data.get("cases", {}).items():
        if case_id not in selected or entry.get("status") != "complete":
            continue
        folder = Path(str(entry.get("folder", "")))
        manifest = folder / "scenario-run.json"
        if not manifest.is_file() or hashlib.sha256(manifest.read_bytes()).hexdigest() != entry.get("scenario_manifest_sha256"):
            raise ValueError(f"canonical case evidence changed or is missing: {case_id}")
        restored[case_id] = {
            "case_id": case_id, "status": "complete", "folder": str(folder),
            "canonical_index": str(index_path.resolve()),
            "scenario_manifest_sha256": entry["scenario_manifest_sha256"],
            "controlled_confirmation": "evaluation-only; not human approval",
        }
    return restored


def acquire_portfolio_lock(output_root: Path):
    """Return an exclusive non-blocking lock for one portfolio control plane."""
    output_root.mkdir(parents=True, exist_ok=True)
    handle = (output_root / ".portfolio.lock").open("w", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise RuntimeError(f"portfolio is already running: {output_root}")
    return handle


def portfolio_folder(root: Path) -> Path:
    name = f"evaluation-portfolio-{dt.datetime.now(dt.timezone.utc):%Y-%m-%d}"
    folder = root / name
    suffix = 2
    while folder.exists():
        folder = root / f"{name}-{suffix}"
        suffix += 1
    return folder


def _case_folder(root: Path, case_id: str) -> Path:
    """Return the canonical PRD folder for one evaluation case."""
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    return root / f"{case_id}-{today}"


def _case_summary(report: dict[str, Any], case: dict[str, Any], folder: Path) -> dict[str, Any]:
    calls = report.get("agent_calls", [])
    completed = report.get("status") == "complete"
    fingerprint = {"category": "none", "digest": "", "evidence": ""} if completed else _failure_fingerprint(report)
    return {
        "case_id": case["case_id"],
        "task_mode": case["task_mode"],
        "status": report.get("status", "unknown"),
        "error": "" if completed else _failure_error(report),
        "failure_fingerprint": fingerprint,
        "folder": str(folder),
        "phase_status": {phase["name"]: phase["status"] for phase in report.get("phases", [])},
        "agent_calls": [
            {
                "phase": call.get("phase"),
                "artifact": call.get("artifact"),
                "provider": call.get("provider"),
                "model": call.get("model"),
                "status": call.get("status"),
                "agent_id": call.get("agent_id") or call.get("id"),
                "command": call.get("command"),
                "error": call.get("error", ""),
                "exit_code": call.get("exit_code"),
                "cleanup_blocked": call.get("cleanup_blocked", False),
                "stop_evidence": call.get("stop_evidence", ""),
            }
            for call in calls
        ],
        "artifacts": report.get("artifacts", {}),
        "validation": report.get("validation", []),
        "runtime_fallbacks": report.get("runtime_fallbacks", []),
        "runtime_recoveries": report.get("runtime_recoveries", []),
        "controlled_confirmation": "evaluation-only; not human approval",
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def _interrupted_case_report(folder: Path) -> dict[str, Any]:
    """Retain the case checkpoint when an outer portfolio is interrupted."""
    checkpoint = folder / "scenario-run.json"
    if checkpoint.is_file():
        try:
            report = json.loads(checkpoint.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            report = {}
    else:
        report = {}
    report["status"] = "interrupted"
    report["last_error"] = "portfolio interrupted by operator"
    return report


def _failure_values(report: dict[str, Any]) -> list[str]:
    values = [str(report.get("last_error", "")), str(report.get("error", ""))]
    for call in report.get("agent_calls", []):
        values.extend((str(call.get("error", "")), str(call.get("output", ""))))
    return [value for value in values if value]


def _failure_error(report: dict[str, Any]) -> str:
    values = _failure_values(report)
    if values:
        return values[0]
    failed_call = next((call for call in reversed(report.get("agent_calls", [])) if call.get("status") != "complete"), None)
    return f"Agent call ended with status {failed_call.get('status')} without error output" if failed_call else ""


def _failure_fingerprint(report: dict[str, Any]) -> dict[str, str]:
    values = "\n".join(_failure_values(report))
    calls = report.get("agent_calls", [])
    if SEAWORK_DAEMON_UNAVAILABLE.search(values):
        category = "seawork_daemon_unavailable"
    elif SEAWORK_MODEL_MISMATCH.search(values):
        category = "seawork_model_mismatch"
    elif any(call.get("status") == "orphaned" for call in calls):
        category = "seawork_agent_stop_unconfirmed"
    elif any(call.get("status") == "timed_out" for call in calls):
        category = "agent_timeout"
    elif any("validation" in value.lower() or "contract" in value.lower() for value in _failure_values(report)):
        category = "artifact_or_contract_failure"
    elif values:
        category = "agent_or_stage_failure"
    else:
        category = "unknown_missing_evidence"
    digest = hashlib.sha256((category + "\n" + values).encode("utf-8")).hexdigest()[:16]
    return {"category": category, "digest": digest, "evidence": values[:2000]}


def _is_seawork_state_failure(report: dict[str, Any]) -> bool:
    """Identify only the documented Seawork state-runtime outage class."""
    return any(SEAWORK_STATE_RUNTIME_FAILURE.search(value) for value in _failure_values(report))


def _is_seawork_daemon_unavailable(error: BaseException) -> bool:
    return bool(SEAWORK_DAEMON_UNAVAILABLE.search(str(error)))


def _report_has_seawork_daemon_failure(report: dict[str, Any]) -> bool:
    return any(SEAWORK_DAEMON_UNAVAILABLE.search(value) for value in _failure_values(report))


def _is_empty_agent_timeout(report: dict[str, Any]) -> bool:
    """Identify a runtime-wide no-progress timeout without masking artifact defects.

    A timed-out stage can be a legitimate case-specific capacity signal when it
    produced an artifact that a review or validator can attribute. It is a
    runtime circuit-breaker signal only when every dispatched Agent timed out
    and none promoted an artifact into the case checkpoint.
    """
    calls = report.get("agent_calls", [])
    if not calls or not all(call.get("status") == "timed_out" for call in calls):
        return False
    artifacts = report.get("artifacts", {})
    return not any(
        isinstance(evidence, dict) and evidence.get("exists")
        for evidence in artifacts.values()
    )


def _restart_seawork_daemon() -> dict[str, Any]:
    """Restart only the local Seawork daemon after an attributable outage."""
    executable = shutil.which("seawork")
    if not executable:
        return {"status": "failed", "error": "seawork CLI not found"}
    try:
        result = subprocess.run(
            [executable, "restart"], text=True, capture_output=True,
            timeout=SEAWORK_RESTART_TIMEOUT_SECONDS, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"status": "failed", "error": str(error)}
    return {
        "status": "complete" if result.returncode == 0 else "failed",
        "exit_code": result.returncode,
        "output": (result.stdout or "").strip()[:1000],
        "error": (result.stderr or "").strip()[:1000],
    }


def run_portfolio(
    output_root: Path,
    timeout_minutes: int = DEFAULT_EXECUTION_TIMEOUT_MINUTES,
    provider: str = "codex",
    resume: bool = True,
    dry_run: bool = False,
    case_ids: set[str] | None = None,
    max_revisions: int = DEFAULT_PORTFOLIO_MAX_REVISIONS,
    model: str | None = None,
    workers: int = DEFAULT_PORTFOLIO_WORKERS,
    force_retry: bool = False,
    canonical_index: Path | None = None,
) -> dict[str, Any]:
    plan = portfolio()
    output_root.mkdir(parents=True, exist_ok=True)
    # The portfolio manifest is a container, not an output run. Individual
    # cases must remain direct children of the project's resolved output root
    # so the shared output and delivery validators can enforce their contracts.
    # The manifest is always a control-plane directory. Case run folders must
    # be its sibling under the resolved output root so validators see the
    # required ``outputs/<run-id>`` shape even when callers use a temporary
    # manifest directory for an isolated portfolio.
    case_output_root = output_root if output_root.name in {"outputs", "pm-copilot-outputs"} else output_root.parent
    case_output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "portfolio-run.json"
    selected_cases = [case for case in plan["cases"] if not case_ids or case["case_id"] in case_ids]
    canonical_cases = _canonical_completed_cases(canonical_index, selected_cases)
    if resume and manifest_path.is_file():
        state = json.loads(manifest_path.read_text(encoding="utf-8"))
        previous_provider = state.get("provider_requested")
        previous_model = state.get("model_requested")
        if previous_provider != provider or previous_model != model:
            state.setdefault("runtime_overrides", []).append({
                "from_provider": previous_provider,
                "from_model": previous_model,
                "to_provider": provider,
                "to_model": model,
                "reason": "The current invocation is authoritative; prior runtime selection is retained only as audit history.",
                "at": dt.datetime.now(dt.timezone.utc).isoformat(),
            })
        state["provider_requested"] = provider
        state["model_requested"] = model
        state["timeout_minutes"] = timeout_minutes
        state["dry_run"] = dry_run
    else:
        state = {
            "schema_version": 1,
            "mode": "evaluation",
            "purpose": "full portfolio evidence; controlled confirmations are not user approvals",
            "provider_requested": provider,
            "model_requested": model,
            "timeout_minutes": timeout_minutes,
            "dry_run": dry_run,
            "total_cases": len(selected_cases),
            "plan_snapshot": selected_cases,
            "plan_sha256": plan_digest(selected_cases),
            "cases": {},
            "status": "running",
            "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
    for case_id, summary in canonical_cases.items():
        state["cases"].setdefault(case_id, summary)
    # Persist the control-plane state before any model call. A process can be
    # interrupted while the first Agent is working; without this checkpoint a
    # full portfolio has no recoverable record of the run it just started.
    _write(manifest_path, state)
    if workers < 1:
        raise ValueError("workers must be at least 1")
    # Case controllers own separate run folders and scenario locks. Direct
    # Codex calls additionally receive isolated CODEX_HOME directories, so a
    # small batch can advance independently without producing two canonical
    # results for one case. SeaWork's daemon control plane is shared and has
    # previously produced unobservable queue stalls, so retain serial case
    # execution on that transport.
    requested_workers = workers
    if workers > 1 and not dry_run:
        if provider == "codex":
            workers = min(workers, MAX_CODEX_CASE_WORKERS)
            state["runtime_policy"] = {
                "requested_workers": requested_workers,
                "effective_workers": workers,
                "mode": "case_parallelism",
                "reason": "Bounded Codex case parallelism: each case has one fixed folder, one scenario lock, and one canonical manifest entry.",
            }
        else:
            workers = 1
            state["runtime_policy"] = {
                "requested_workers": requested_workers,
                "effective_workers": workers,
                "mode": "serial",
                "reason": "The SeaWork daemon control plane is shared; serial execution prevents unobservable queue stalls.",
            }
        _write(manifest_path, state)
    if workers > 1 and not dry_run:
        # Cases have isolated run folders; only the case-level controller is
        # parallelized. Stages and reviews within one case remain serial.
        jobs = []
        for case in selected_cases:
            previous = state["cases"].get(case["case_id"], {})
            if resume and previous.get("status") == "complete":
                continue
            folder = Path(previous.get("folder", "")) if previous.get("folder") else _case_folder(case_output_root, case["case_id"])
            if not (resume and previous):
                state["cases"][case["case_id"]] = {
                    "case_id": case["case_id"], "task_mode": case["task_mode"], "status": "running", "error": "",
                    "folder": str(folder), "phase_status": {phase: "planned" for phase in case["required_phases"]},
                    "agent_calls": [], "artifacts": {}, "validation": [],
                    "controlled_confirmation": "evaluation-only; not human approval",
                    "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                }
            jobs.append((case, folder))
        _write(manifest_path, state)

        def run_parallel(item: tuple[dict[str, Any], Path]) -> tuple[dict[str, Any], Path, dict[str, Any]]:
            case, folder = item
            try:
                report = execute_case(case["case_id"], case_output_root, timeout_minutes, False,
                                      provider=provider, run_folder_path=folder, repair_trace=False,
                                      max_revisions=max_revisions, model=model, force_retry=force_retry)
            except KeyboardInterrupt:
                report = {"status": "interrupted", "last_error": "portfolio interrupted by operator", "agent_calls": [], "phases": [], "artifacts": {}, "validation": []}
            except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
                report = {"status": "failed", "last_error": f"portfolio case execution failed: {error}", "agent_calls": [], "phases": [], "artifacts": {}, "validation": []}
            return case, folder, report

        interrupted = False
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="pm-case") as pool:
            futures = [pool.submit(run_parallel, job) for job in jobs]
            try:
                for future in as_completed(futures):
                    case, folder, report = future.result()
                    state["cases"][case["case_id"]] = _case_summary(report, case, folder)
                    state["last_case_id"] = case["case_id"]
                    _write(manifest_path, state)
                    interrupted |= report.get("status") == "interrupted"
            except KeyboardInterrupt:
                interrupted = True
                for future in futures:
                    future.cancel()
                # Futures that were pre-registered but never started must not
                # remain `running` forever. Preserve the distinction between
                # a completed case, a case that returned an actual failure,
                # and work that was never allowed to begin.
                for future, (case, folder) in zip(futures, jobs):
                    case_id = case["case_id"]
                    current = state["cases"].get(case_id, {})
                    if future.cancelled() or current.get("status") == "running":
                        state["cases"][case_id] = {
                            **current,
                            "status": "interrupted",
                            "error": "portfolio interrupted before case completion",
                            "failure_fingerprint": {
                                "category": "operator_interruption",
                                "digest": hashlib.sha256(case_id.encode("utf-8")).hexdigest()[:16],
                                "evidence": "portfolio interrupted before case completion",
                            },
                            "folder": str(folder),
                            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                        }
        if interrupted:
            state["interrupted_by_operator"] = True
            state["status"] = "interrupted"
        else:
            state["status"] = "complete" if selected_cases and all(state["cases"].get(c["case_id"], {}).get("status") == "complete" for c in selected_cases) else "failed"
        expected = {case["case_id"] for case in selected_cases}
        selected_statuses = [state["cases"].get(case_id, {}).get("status") for case_id in expected]
        state["summary"] = {"selected_cases": len(expected), "recorded_cases": sum(status is not None for status in selected_statuses), "complete": sum(s == "complete" for s in selected_statuses), "failed": sum(s in {"failed", "timed_out", "orphaned"} for s in selected_statuses), "pending": sum(s in {None, "planned", "running", "interrupted"} for s in selected_statuses)}
        state["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        _write(manifest_path, state)
        return state
    portfolio_interrupted = False
    for case in selected_cases:
        case_id = case["case_id"]
        if case_ids and case_id not in case_ids:
            continue
        previous = state["cases"].get(case_id, {})
        if resume and previous.get("status") == "complete" and not dry_run:
            continue
        folder = Path(previous.get("folder", "")) if previous.get("folder") else _case_folder(case_output_root, case_id)
        state["current_case_id"] = case_id
        state["cases"][case_id] = {
            "case_id": case_id,
            "task_mode": case["task_mode"],
            "status": "running",
            "error": "",
            "folder": str(folder),
            "phase_status": {phase: "planned" for phase in case["required_phases"]},
            "agent_calls": [],
            "artifacts": {},
            "validation": [],
            "controlled_confirmation": "evaluation-only; not human approval",
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        _write(manifest_path, state)
        try:
            report = execute_case(
                case_id,
                case_output_root,
                timeout_minutes,
                dry_run,
                provider=provider,
                run_folder_path=folder,
                repair_trace=False,
                max_revisions=max_revisions,
                model=model,
                force_retry=force_retry,
            )
            # The case runner normally records agent failures instead of
            # raising them. Treat a daemon outage in that report exactly like
            # a startup outage: one attributable recovery attempt, then stop
            # the portfolio rather than spending tokens on later cases.
            if provider in {"seawork", "seawork-claude"} and report.get("status") == "failed" and _report_has_seawork_daemon_failure(report):
                recovery = _restart_seawork_daemon()
                report.setdefault("runtime_recoveries", []).append({
                    "reason": "Seawork daemon was unavailable during case execution.",
                    "recovery": recovery,
                    "retry_policy": "one_recovery_retry",
                    "at": dt.datetime.now(dt.timezone.utc).isoformat(),
                })
                if recovery.get("status") == "complete":
                    report = execute_case(
                        case_id, case_output_root, timeout_minutes, dry_run,
                        provider=provider, run_folder_path=folder,
                        repair_trace=False, max_revisions=max_revisions,
                        model=model,
                    )
                    report.setdefault("runtime_recoveries", []).append({
                        "reason": "Seawork daemon was unavailable during case execution.",
                        "recovery": recovery,
                        "retry_policy": "one_recovery_retry",
                        "at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    })
            if provider == "seawork" and report.get("status") == "failed" and _is_seawork_state_failure(report):
                fallback = {
                    "from_provider": "seawork",
                    "to_provider": "codex",
                    "reason": "Seawork could not initialize its SQLite-backed Codex state runtime.",
                    "at": dt.datetime.now(dt.timezone.utc).isoformat(),
                }
                report = execute_case(
                    case_id,
                    case_output_root,
                    timeout_minutes,
                    dry_run,
                    provider="codex",
                    run_folder_path=folder,
                    repair_trace=False,
                    max_revisions=max_revisions,
                    model=model,
                )
                report.setdefault("runtime_fallbacks", []).append(fallback)
                folder.mkdir(parents=True, exist_ok=True)
                _write(folder / "scenario-run.json", report)
        except KeyboardInterrupt:
            # An operator stop is a terminal control-plane outcome for this
            # case, not an implicit retry and not a successful checkpoint.
            report = _interrupted_case_report(folder)
            portfolio_interrupted = True
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
            recovery: dict[str, Any] | None = None
            if provider in {"seawork", "seawork-claude"} and _is_seawork_daemon_unavailable(error):
                recovery = _restart_seawork_daemon()
                if recovery.get("status") == "complete":
                    try:
                        report = execute_case(
                            case_id, case_output_root, timeout_minutes, dry_run,
                            provider=provider, run_folder_path=folder,
                            repair_trace=False, max_revisions=max_revisions,
                            model=model,
                        )
                    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as retry_error:
                        error = retry_error
                    else:
                        report.setdefault("runtime_recoveries", []).append({
                            "reason": "Seawork daemon was unreachable before case execution.",
                            "recovery": recovery,
                            "at": dt.datetime.now(dt.timezone.utc).isoformat(),
                        })
                        state["cases"][case_id] = _case_summary(report, case, folder)
                        state["last_case_id"] = case_id
                        _write(manifest_path, state)
                        continue
            # A provider/runtime outage must be attributable to this case and
            # resumable, never crash the portfolio before later cases can run.
            state_path = folder / "scenario-run.json"
            if state_path.is_file():
                try:
                    report = json.loads(state_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    report = {}
            else:
                report = {}
            report.update({"status": "failed", "last_error": f"portfolio case execution failed: {error}"})
            if recovery:
                report.setdefault("runtime_recoveries", []).append({
                    "reason": "Seawork daemon was unreachable before case execution.",
                    "recovery": recovery,
                    "at": dt.datetime.now(dt.timezone.utc).isoformat(),
                })
        state["cases"][case_id] = _case_summary(report, case, folder)
        state["last_case_id"] = case_id
        _write(manifest_path, state)
        if portfolio_interrupted:
            state["interrupted_by_operator"] = True
            break
        category = state["cases"][case_id]["failure_fingerprint"]["category"]
        runtime_no_progress = _is_empty_agent_timeout(report)
        if category in {"seawork_daemon_unavailable", "seawork_model_mismatch"} or runtime_no_progress:
            breaker_category = "agent_runtime_no_progress" if runtime_no_progress else category
            state["circuit_breaker"] = {
                "category": breaker_category,
                "case_id": case_id,
                "reason": (
                    "one recovery retry did not establish a usable Seawork daemon"
                    if category == "seawork_daemon_unavailable"
                    else "Seawork did not honor the requested model selection"
                    if category == "seawork_model_mismatch"
                    else "every Agent call timed out before any case artifact was promoted"
                ),
                "retry_policy": (
                    "no_automatic_retry_after_recovery_failure"
                    if category == "seawork_daemon_unavailable" else "no_automatic_retry"
                ),
                "at": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
            _write(manifest_path, state)
            break
    statuses = [item.get("status") for item in state["cases"].values()]
    expected = {case["case_id"] for case in selected_cases}
    completed = sum(status == "complete" for status in statuses)
    failed = sum(status in {"failed", "timed_out", "orphaned"} for status in statuses)
    state["summary"] = {"selected_cases": len(expected), "recorded_cases": len(statuses), "complete": completed, "failed": failed, "pending": max(len(expected) - len(statuses), 0)}
    state["status"] = "planned" if dry_run else (
        "interrupted" if portfolio_interrupted
        else
        "halted_infrastructure" if state.get("circuit_breaker")
        else "complete" if expected and all(state["cases"].get(case_id, {}).get("status") == "complete" for case_id in expected)
        else "failed"
    )
    state["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    _write(manifest_path, state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / f"evaluation-portfolio-{dt.datetime.now(dt.timezone.utc):%Y-%m-%d}")
    parser.add_argument("--provider", default="codex", help="Agent runtime; use seawork only when its remote model or scheduler is required")
    parser.add_argument("--model", help="explicit local runtime model override for every Agent stage")
    parser.add_argument("--timeout-minutes", type=int, default=DEFAULT_EXECUTION_TIMEOUT_MINUTES)
    parser.add_argument("--resume", action="store_true", default=False)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-revisions", type=int, default=DEFAULT_PORTFOLIO_MAX_REVISIONS)
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--workers", type=int, default=DEFAULT_PORTFOLIO_WORKERS)
    parser.add_argument("--force-retry", action="store_true", help="permit one explicitly requested retry after a recorded revision budget stop")
    parser.add_argument("--canonical-index", type=Path, help="resume only hash-pinned cases from a canonical index")
    args = parser.parse_args()
    if args.timeout_minutes < 1 or args.max_revisions < 0:
        parser.error("--timeout-minutes must be at least 1 and --max-revisions cannot be negative")
    try:
        lock = acquire_portfolio_lock(args.output_root)
    except RuntimeError as error:
        parser.error(str(error))
    with lock:
        state = run_portfolio(args.output_root, args.timeout_minutes, args.provider, args.resume, args.dry_run, set(args.case_ids or []), args.max_revisions, args.model, args.workers, args.force_retry, args.canonical_index)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0 if state["status"] in {"complete", "planned"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
