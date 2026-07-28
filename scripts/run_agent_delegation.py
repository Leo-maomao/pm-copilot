#!/usr/bin/env python3
"""Run a bounded PM Copilot specialist plan, then a targeted Review challenge."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from agent_runtime import execute, runtime_capabilities
from plan_agent_delegation import build_plan


def worker_prompt(role: str, question: str, request: str) -> str:
    return (
        f"You are the PM Copilot {role}. Answer only this owned question: {question}\n"
        f"User request: {request}\n"
        "Do not modify repository files. Return a compact handoff with facts, assumptions, "
        "open questions, decisions, evidence references, risks, and validation delta."
    )


def review_prompt(request: str, results: list[dict[str, Any]]) -> str:
    evidence = json.dumps(results, ensure_ascii=False)[:12000]
    return (
        "You are the PM Copilot Review Agent. Challenge only material evidence gaps, user conflicts, "
        "scope conflicts, or metric conflicts in these specialist handoffs. Do not invent a debate. "
        "For every issue, name the target role, evidence gap, severity, and correction.\n"
        f"User request: {request}\nSpecialist handoffs: {evidence}"
    )


def run_plan(
    request: str,
    task_mode: str,
    cwd: Path,
    execute_worker: Callable[..., dict[str, Any]],
    dispatch: bool,
) -> dict[str, Any]:
    plan = build_plan(request, task_mode)
    capabilities = runtime_capabilities(cwd)
    evidence_workers = plan["dispatch_groups"][0]["workers"]
    results: list[dict[str, Any]] = []
    if dispatch and capabilities["single_agent_auto"]["status"] != "available":
        return {"status": "blocked", "reason": capabilities["single_agent_auto"]["reason"], "plan": plan, "workers": []}
    if dispatch:
        with ThreadPoolExecutor(max_workers=min(3, len(evidence_workers))) as pool:
            futures = [
                pool.submit(execute_worker, "auto", worker_prompt(worker["role"], worker["owned_question"], request), cwd, 15, None, None, False)
                for worker in evidence_workers
            ]
            results = [future.result() for future in futures]
        review_workers = plan["dispatch_groups"][1]["workers"]
        if review_workers:
            review = execute_worker("auto", review_prompt(request, results), cwd, 15, None, None, False)
            results.append({"role": "Review Agent", **review})
    return {
        "status": "complete" if dispatch else "planned",
        "plan": plan,
        "runtime": capabilities,
        "workers": results,
        "next_step": "PM Orchestrator must record claims, any material conflict, and arbitration in run-log.yaml before final delivery.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--task-mode", default="auto")
    parser.add_argument("--cwd", type=Path, default=Path("."))
    parser.add_argument("--execute", action="store_true", help="run selected workers; default only plans")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_plan(args.request, args.task_mode, args.cwd, execute, args.execute)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["status"] in {"planned", "complete"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
