#!/usr/bin/env python3
"""Run a bounded PM Copilot specialist plan, then a targeted Review challenge."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Callable

from agent_runtime import execute, runtime_capabilities
from agent_event_ledger import append_event
from agent_task_ledger import complete_tasks, create_ledger, load as load_ledger, task as ledger_task, write as write_ledger
from plan_agent_delegation import build_plan
from workspace_identity import identify, scope_notice


def worker_prompt(role: str, question: str, request: str, workspace: dict[str, Any]) -> str:
    return (
        f"You are the PM Copilot {role}. Answer only this owned question: {question}\n"
        f"User request: {request}\n"
        f"{scope_notice(workspace)}\n"
        "Do not modify repository files. Return JSON only with keys claims, rejected_evidence, open_questions, "
        "risks, validation_delta. Every claim must include statement, kind (observed|user_confirmed|inferred|proposed|unknown), "
        "confidence, evidence_refs, and decision_impact."
    )


def review_prompt(request: str, results: list[dict[str, Any]], workspace: dict[str, Any]) -> str:
    evidence = json.dumps(results, ensure_ascii=False)[:12000]
    return (
        "You are the PM Copilot Review Agent. Challenge only material evidence gaps, user conflicts, "
        "scope conflicts, or metric conflicts in these specialist handoffs. Do not invent a debate. "
        "Return JSON only with keys cross_reviews, unresolved_findings, recommendation. "
        "Every cross review must identify target_claim_id, challenge_type, severity, evidence_refs, and disposition.\n"
        f"User request: {request}\n{scope_notice(workspace)}\nSpecialist handoffs: {evidence}"
    )


def orchestration_prompt(request: str, results: list[dict[str, Any]], workspace: dict[str, Any]) -> str:
    evidence = json.dumps(results, ensure_ascii=False)[:14000]
    return (
        "You are the PM Copilot PM Orchestrator. Resolve only material conflicts identified by Review Agent. "
        "Do not vote or invent evidence. Return JSON with keys claims, cross_reviews, arbitrations, limitations. "
        "Each claim needs id, statement, evidence_refs, confidence. Each arbitration needs issue_ref, "
        "evidence_compared, outcome (accepted|rejected|escalated_to_human), and rationale. "
        f"User request: {request}\n{scope_notice(workspace)}\nEvidence and review: {evidence}"
    )


def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_json_output(value: str) -> dict[str, Any] | None:
    value = value.strip()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start, end = value.find("{"), value.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(value[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def output_schema(phase: str) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "claims": {"type": "array"},
        "rejected_evidence": {"type": "array"},
        "open_questions": {"type": "array"},
        "risks": {"type": "array"},
        "validation_delta": {"type": "array"},
        "cross_reviews": {"type": "array"},
        "unresolved_findings": {"type": "array"},
        "recommendation": {"type": "string"},
        "arbitrations": {"type": "array"},
        "limitations": {"type": "array"},
    }
    required_by_phase = {
        "evidence": ["claims", "rejected_evidence", "open_questions", "risks", "validation_delta"],
        "challenge": ["cross_reviews", "unresolved_findings", "recommendation"],
        "arbitration": ["claims", "cross_reviews", "arbitrations", "limitations"],
    }
    return {"type": "object", "properties": properties, "required": required_by_phase[phase], "additionalProperties": False}


def valid_structured_output(phase: str, parsed: dict[str, Any] | None) -> bool:
    if not parsed:
        return False
    for key in output_schema(phase)["required"]:
        if key not in parsed:
            return False
        if key == "recommendation":
            if not isinstance(parsed[key], str):
                return False
        elif not isinstance(parsed[key], list):
            return False
    return True


def deterministic_runtime_startup_failure(result: dict[str, Any]) -> bool:
    """Return true when a local runtime failure makes further dispatch predictably futile."""
    detail = " ".join(
        str(result.get(key, ""))
        for key in ("status", "error", "output")
    ).lower()
    markers = (
        "output_schema_failed",
        "failed to load configuration",
        "configuration error",
        "duplicate key",
        "runtime initialization failed",
    )
    return result.get("status") != "complete" and any(marker in detail for marker in markers)


def skip_unstarted_tasks(ledger: dict[str, Any], reason: str) -> None:
    for item in ledger.get("tasks", []):
        if item.get("status") != "planned":
            continue
        item["status"] = "skipped"
        item["error"] = reason
        item["finished_at"] = timestamp()


def persist_worker_output(ledger_path: Path, identifier: str, result: dict[str, Any]) -> str:
    output_path = ledger_path.parent / f"{identifier}.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path.name


def record_event(ledger_path: Path | None, ledger: dict[str, Any], event_type: str, data: dict[str, object]) -> None:
    if not ledger_path:
        return
    append_event(
        ledger_path.parent / "agent-events.jsonl",
        str(ledger.get("run_id") or ledger_path.parent.name),
        str(ledger.get("workspace", {}).get("execution_root") or ledger_path.parent),
        event_type,
        data,
    )


def execute_task(
    ledger: dict[str, Any],
    identifier: str,
    prompt: str,
    cwd: Path,
    execute_worker: Callable[..., dict[str, Any]],
    ledger_path: Path | None,
    max_attempts: int,
    ledger_lock: Lock,
) -> dict[str, Any]:
    with ledger_lock:
        item = ledger_task(ledger, identifier)
        if item.get("status") == "complete":
            return {"status": "complete", "resumed": True, "output_ref": item.get("output_ref", "")}
        item["status"] = "running"
        item["started_at"] = timestamp()
        record_event(ledger_path, ledger, "agent_started", {"task_id": identifier, "role": str(item["role"]), "phase": str(item["phase"])})
        if ledger_path:
            write_ledger(ledger_path, ledger)
    last_result: dict[str, Any] = {}
    for _ in range(max_attempts):
        with ledger_lock:
            item["attempts"] = int(item.get("attempts", 0)) + 1
            if ledger_path:
                write_ledger(ledger_path, ledger)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", encoding="utf-8", delete=False) as schema_file:
            json.dump(output_schema(str(item["phase"])), schema_file)
            schema_path = schema_file.name
        try:
            result = execute_worker("auto", prompt, cwd, 15, None, schema_path, False)
        finally:
            Path(schema_path).unlink(missing_ok=True)
        last_result = result
        with ledger_lock:
            record_event(ledger_path, ledger, "tool_called", {"task_id": identifier, "tool": "agent_runtime", "provider": str(result.get("provider", "")), "status": str(result.get("status", ""))})
            item["runtime"] = str(result.get("provider", ""))
            item["model"] = str(result.get("model", ""))
            parsed = parse_json_output(str(result.get("output", "")))
            if result.get("status") == "complete" and valid_structured_output(str(item["phase"]), parsed):
                item["status"] = "complete"
                item["error"] = ""
                break
            item["status"] = "failed"
            item["error"] = str(result.get("error") or "worker did not return the required structured output")
            if deterministic_runtime_startup_failure(result):
                break
    with ledger_lock:
        item["finished_at"] = timestamp()
        if ledger_path:
            item["output_ref"] = persist_worker_output(ledger_path, identifier, last_result)
            artifact_id = f"artifact-{identifier}"
            artifact_path = ledger_path.parent / item["output_ref"]
            ledger["artifacts"][artifact_id] = {
                "path": item["output_ref"],
                "sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
                "producer_task_id": identifier,
                "redaction_status": "runtime_redacted",
            }
            item["evidence_refs"] = [artifact_id]
            record_event(ledger_path, ledger, "evidence_recorded", {"task_id": identifier, "artifact_id": artifact_id, "status": str(item["status"])})
            if item["phase"] == "challenge":
                record_event(ledger_path, ledger, "review_completed", {"task_id": identifier, "status": str(item["status"])})
            parsed_worker = parse_json_output(str(last_result.get("output", "")))
            if parsed_worker and isinstance(parsed_worker.get("claims"), list):
                for index, claim in enumerate(parsed_worker["claims"]):
                    if not isinstance(claim, dict) or not claim.get("statement"):
                        continue
                    ledger["claims"].append({
                        "id": str(claim.get("id") or f"{identifier}-claim-{index + 1}"),
                        "task_id": identifier,
                        "owner_role": item["role"],
                        "statement": str(claim["statement"]),
                        "kind": str(claim.get("kind", "unknown")),
                        "confidence": str(claim.get("confidence", "low")),
                        "evidence_refs": [artifact_id],
                        "decision_impact": str(claim.get("decision_impact", "prd")),
                    })
            write_ledger(ledger_path, ledger)
    return last_result


def run_plan(
    request: str,
    task_mode: str,
    cwd: Path,
    execute_worker: Callable[..., dict[str, Any]],
    dispatch: bool,
    ledger_path: Path | None = None,
    resume: bool = False,
    max_attempts: int = 2,
) -> dict[str, Any]:
    plan = build_plan(request, task_mode)
    workspace = identify(cwd)
    capabilities = runtime_capabilities(cwd)
    evidence_workers = plan["dispatch_groups"][0]["workers"]
    results: list[dict[str, Any]] = []
    ledger_lock = Lock()
    if ledger_path and resume and ledger_path.is_file():
        ledger = load_ledger(ledger_path)
        recorded_workspace = ledger.get("workspace", {})
        if recorded_workspace.get("execution_root") != workspace["execution_root"]:
            message = (
                "refusing to resume a ledger from another PM Copilot workspace: "
                f"{recorded_workspace.get('execution_root', '<missing>')} != {workspace['execution_root']}"
            )
            return {"status": "blocked", "reason": message, "plan": plan, "workers": [], "ledger": ledger}
        ledger["resume"]["count"] = int(ledger["resume"].get("count", 0)) + 1
        ledger["resume"]["last_safe_phase"] = "resume"
    else:
        ledger = create_ledger(request, task_mode, plan, cwd)
    if ledger_path:
        write_ledger(ledger_path, ledger)
        record_event(ledger_path, ledger, "task_started", {"task_mode": task_mode, "dispatch": dispatch})
    if dispatch and capabilities["single_agent_auto"]["status"] != "available":
        ledger["status"] = "blocked"
        ledger["limitations"].append(str(capabilities["single_agent_auto"]["reason"]))
        if ledger_path:
            write_ledger(ledger_path, ledger)
            record_event(ledger_path, ledger, "task_failed", {"status": "blocked", "limitations": ledger["limitations"]})
        return {"status": "blocked", "reason": capabilities["single_agent_auto"]["reason"], "plan": plan, "workers": [], "ledger": ledger}
    if dispatch:
        first_worker = evidence_workers[0]
        first_identifier = f"evidence-1-{first_worker['role'].lower().replace(' ', '-')}"
        first_result = execute_task(
            ledger, first_identifier,
            worker_prompt(first_worker["role"], first_worker["owned_question"], request, workspace), cwd,
            execute_worker, ledger_path, max_attempts, ledger_lock,
        )
        results.append({"role": first_worker["role"], **first_result})
        if deterministic_runtime_startup_failure(first_result):
            reason = "Specialist dispatch stopped after deterministic runtime startup failure."
            skip_unstarted_tasks(ledger, reason)
            ledger["status"] = "degraded"
            ledger["limitations"].append(reason)
            if ledger_path:
                write_ledger(ledger_path, ledger)
                record_event(ledger_path, ledger, "task_failed", {"status": "degraded", "limitations": ledger["limitations"]})
            return {
                "status": "degraded",
                "plan": plan,
                "runtime": capabilities,
                "workers": results,
                "ledger": ledger,
                "next_step": "Repair the local runtime before resuming the persisted ledger; no specialist review or arbitration was completed.",
            }
        remaining_workers = evidence_workers[1:]
        with ThreadPoolExecutor(max_workers=min(3, len(remaining_workers))) as pool:
            futures = []
            for index, worker in enumerate(remaining_workers, start=2):
                identifier = f"evidence-{index}-{worker['role'].lower().replace(' ', '-')}"
                futures.append(pool.submit(
                    execute_task, ledger, identifier,
                    worker_prompt(worker["role"], worker["owned_question"], request, workspace), cwd,
                    execute_worker, ledger_path, max_attempts, ledger_lock,
                ))
            results.extend({"role": worker["role"], **future.result()} for worker, future in zip(remaining_workers, futures))
        review_workers = plan["dispatch_groups"][1]["workers"]
        if review_workers and complete_tasks(ledger, "evidence"):
            review = execute_task(
                ledger, "challenge-1-review-agent", review_prompt(request, results, workspace), cwd,
                execute_worker, ledger_path, max_attempts, ledger_lock,
            )
            results.append({"role": "Review Agent", **review})
            if complete_tasks(ledger, "challenge"):
                arbitration = execute_task(
                    ledger, "arbitration-1-pm-orchestrator", orchestration_prompt(request, results, workspace), cwd,
                    execute_worker, ledger_path, max_attempts, ledger_lock,
                )
                parsed = parse_json_output(str(arbitration.get("output", "")))
                if parsed:
                    ledger["claims"] = parsed.get("claims", [])
                    ledger["cross_reviews"] = parsed.get("cross_reviews", [])
                    ledger["arbitrations"] = parsed.get("arbitrations", [])
                    ledger["limitations"].extend(parsed.get("limitations", []))
                else:
                    ledger["limitations"].append("PM Orchestrator output was not structured JSON; no claim was accepted automatically.")
                results.append({"role": "PM Orchestrator", **arbitration})
        elif review_workers:
            ledger["limitations"].append("Review and arbitration were skipped because evidence workers did not complete.")
    structured_arbitration = bool(ledger.get("claims") or ledger.get("arbitrations"))
    ledger["status"] = (
        "complete" if dispatch and complete_tasks(ledger, "arbitration") and structured_arbitration
        else ("planned" if not dispatch else "degraded")
    )
    if ledger_path:
        write_ledger(ledger_path, ledger)
        if ledger["status"] in {"complete", "degraded", "blocked", "failed"}:
            terminal_event = "task_completed" if ledger["status"] == "complete" else "task_failed"
            record_event(ledger_path, ledger, terminal_event, {"status": ledger["status"], "limitations": ledger["limitations"]})
    return {
        "status": ledger["status"],
        "plan": plan,
        "runtime": capabilities,
        "workers": results,
        "ledger": ledger,
        "next_step": "Use the persisted ledger as the only source for claims, targeted review, arbitration, and resume state.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--task-mode", default="auto")
    parser.add_argument("--cwd", type=Path, default=Path("."))
    parser.add_argument("--execute", action="store_true", help="run selected workers; default only plans")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ledger", type=Path, help="durable task ledger; defaults under cwd when executing")
    parser.add_argument("--resume", action="store_true", help="resume completed tasks from an existing ledger")
    parser.add_argument("--max-attempts", type=int, default=2)
    args = parser.parse_args()
    if args.max_attempts < 1:
        parser.error("--max-attempts must be at least 1")
    ledger_path = args.ledger or (args.cwd / "tool-results" / "agent-task-ledger.json" if args.execute else None)
    def delegated_execute(*call_args: Any) -> dict[str, Any]:
        return execute(*call_args, output_limit=24000)

    report = run_plan(args.request, args.task_mode, args.cwd, delegated_execute, args.execute, ledger_path, args.resume, args.max_attempts)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["status"] in {"planned", "complete", "degraded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
