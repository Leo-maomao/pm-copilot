#!/usr/bin/env python3
"""Regression-test reflection, memory, and self-improvement trace gates."""

from __future__ import annotations

import tempfile
from pathlib import Path

from validate_agent_trace import validate_run_log


ROOT = Path(__file__).resolve().parents[1]
BASE_LOG = ROOT / "evals/fixtures/bounded-loop-pass/run-log.yaml"


def validate_text(text: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="pm-copilot-reflection-") as directory:
        run_log = Path(directory) / "run-log.yaml"
        run_log.write_text(text, encoding="utf-8")
        return validate_run_log(run_log)


def expect(name: str, text: str, passed: bool, failure_fragment: str = "") -> None:
    result = validate_text(text)
    actual_passed = result["status"] == "passed"
    failures = result.get("failures", [])
    if actual_passed != passed:
        raise AssertionError(f"{name}: unexpected result: {result}")
    if failure_fragment and not any(failure_fragment in item for item in failures):
        raise AssertionError(
            f"{name}: expected failure containing {failure_fragment!r}, got {failures}"
        )
    print(f"PASS {name}: {'accepted' if passed else 'rejected'}")


def main() -> None:
    base = BASE_LOG.read_text(encoding="utf-8")
    expect("valid_reflection", base, True)

    expect(
        "missing_final_recommendation",
        base.replace("  final_recommendation: proceed_with_controls\n", ""),
        False,
        "review_loop.final_recommendation",
    )

    unresolved = base.replace(
        "  unresolved_findings: []\n  final_recommendation: proceed_with_controls\n",
        "  unresolved_findings:\n    - H2 launch evidence missing\n"
        "  final_recommendation: proceed_with_controls\n",
    )
    expect(
        "unresolved_severe_finding",
        unresolved,
        False,
        "complete termination cannot retain unresolved review findings",
    )

    unrelated_closure = base.replace(
        "    - finding: H1 rollback owner missing\n",
        "    - finding: H9 unrelated copy issue\n",
    )
    expect(
        "unrelated_severe_closure",
        unrelated_closure,
        False,
        "missing exact closure",
    )

    unsafe_memory = base.replace(
        "memory_candidates:\n  none: true\n",
        "memory_candidates:\n"
        "  product_memory:\n"
        "    - fact: Customer health condition\n"
        "      source: User interview transcript\n"
        "      confidence: high\n"
        "      sensitivity: sensitive\n"
        "      write_recommendation: suggest\n",
    )
    expect(
        "unsafe_sensitive_memory",
        unsafe_memory,
        False,
        "cannot be suggested for silent write",
    )

    self_improvement = (
        base.replace("task_mode: product_review", "task_mode: self_improvement")
        .replace("autonomy_level: full-loop", "autonomy_level: self-iteration")
        .replace("loop_type: evaluator_optimizer", "loop_type: self_improvement")
        + """

self_iteration:
  triggered: true
  source_run_id: runtime-failure-001
  source_run_ids: []
  failure_evidence:
    - A sensitive memory candidate passed without confirmation.
  user_corrections: []
  generalized_failures:
    - Memory safety depended on prompt compliance instead of validation.
  selected_fix_surfaces:
    - scripts/validate_agent_trace.py
  regression_updates:
    - scripts/test_reflection_learning_trace.py::unsafe_sensitive_memory
  generalization_boundary: Applies to trace validation, not external memory stores.
  validation_commands:
    - python3 scripts/test_reflection_learning_trace.py
  version_change: 4.0 runtime contract strengthened
  embedded_copy_sync: []
"""
    )
    expect("valid_self_improvement", self_improvement, True)
    expect(
        "self_improvement_without_regression",
        self_improvement.replace(
            "  regression_updates:\n"
            "    - scripts/test_reflection_learning_trace.py::unsafe_sensitive_memory\n",
            "  regression_updates: []\n",
        ),
        False,
        "self_iteration.regression_updates",
    )


if __name__ == "__main__":
    main()
