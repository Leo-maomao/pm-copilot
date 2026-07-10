#!/usr/bin/env python3
"""Run deterministic regression tests for the bounded Agent Loop controller."""

from __future__ import annotations

import tempfile
from pathlib import Path

from evaluate_agent_loop import evaluate


BASE_POLICY = """loop_policy:
  enabled: true
  loop_type: execution
  max_iterations: {max_iterations}
  max_tool_calls: {max_tool_calls}
  max_elapsed_minutes: {max_elapsed_minutes}
  max_consecutive_no_progress: {max_no_progress}
  min_progress_score_delta: 5
  human_checkpoint:
    required_after_iteration: {checkpoint_after}
    status: {checkpoint_status}
loop_state:
  current_iteration: {current_iteration}
  tool_calls_used: {tool_calls_used}
  elapsed_minutes: {elapsed_minutes}
  consecutive_no_progress: {no_progress}
  last_progress_score: 60
  success_criteria_met: {success}
termination_condition:
  status: {termination}
loop_summary:
  iterations_completed: {current_iteration}
  stop_reason: {stop_reason}
  final_progress_score: 60
"""


def run_case(name: str, expected: str, **overrides: object) -> None:
    values: dict[str, object] = {
        "max_iterations": 4,
        "max_tool_calls": 12,
        "max_elapsed_minutes": 45,
        "max_no_progress": 2,
        "checkpoint_after": 0,
        "checkpoint_status": "not_required",
        "current_iteration": 1,
        "tool_calls_used": 3,
        "elapsed_minutes": 10,
        "no_progress": 0,
        "success": "false",
        "termination": "degraded",
        "stop_reason": "",
    }
    values.update(overrides)
    with tempfile.TemporaryDirectory(prefix="pm-copilot-loop-") as directory:
        run_folder = Path(directory)
        (run_folder / "run-log.yaml").write_text(
            BASE_POLICY.format(**values),
            encoding="utf-8",
        )
        result = evaluate(run_folder / "run-log.yaml")
    actual = result.get("decision")
    if actual != expected:
        raise AssertionError(f"{name}: expected {expected}, got {actual}: {result}")
    print(f"PASS {name}: {actual}")


def main() -> None:
    run_case("continue", "continue")
    run_case("success", "stop_success", success="true", stop_reason="success")
    run_case("needs_input", "stop_needs_input", termination="needs_input", stop_reason="needs_input")
    run_case("blocked", "stop_blocked", termination="blocked", stop_reason="blocked")
    run_case("failed", "stop_failed", termination="failed", stop_reason="failed")
    run_case(
        "human_checkpoint_precedes_success",
        "stop_human_checkpoint",
        checkpoint_after=1,
        checkpoint_status="pending",
        success="true",
        stop_reason="human_checkpoint",
    )
    run_case("iteration_budget", "stop_budget", current_iteration=4, stop_reason="budget")
    run_case("tool_budget", "stop_budget", tool_calls_used=12, stop_reason="budget")
    run_case("time_budget", "stop_budget", elapsed_minutes=45, stop_reason="budget")
    run_case("no_progress", "stop_no_progress", no_progress=2, stop_reason="no_progress")

    with tempfile.TemporaryDirectory(prefix="pm-copilot-loop-invalid-") as directory:
        run_folder = Path(directory)
        (run_folder / "run-log.yaml").write_text(
            BASE_POLICY.format(
                max_iterations=0,
                max_tool_calls=12,
                max_elapsed_minutes=45,
                max_no_progress=2,
                checkpoint_after=0,
                checkpoint_status="not_required",
                current_iteration=0,
                tool_calls_used=0,
                elapsed_minutes=0,
                no_progress=0,
                success="false",
                termination="degraded",
                stop_reason="",
            ),
            encoding="utf-8",
        )
        result = evaluate(run_folder / "run-log.yaml")
    if result.get("status") != "failed" or result.get("decision") != "stop_failed":
        raise AssertionError(f"invalid budget was not rejected: {result}")
    print("PASS invalid_budget: stop_failed")


if __name__ == "__main__":
    main()
