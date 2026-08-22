#!/usr/bin/env python3
"""Independently audit a full PM Copilot evaluation portfolio."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from plan_evaluation_portfolio import ROOT, portfolio
from portfolio_contract import plan_digest
from run_evaluation_scenario import confirmation_mode_for


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _phase_statuses(state: dict[str, Any]) -> dict[str, str]:
    return {str(item.get("name")): str(item.get("status")) for item in state.get("phases", [])}


def _agent_artifacts(case: dict[str, Any]) -> list[str]:
    return [item for item in case["required_artifacts"] if item not in {"prd.html", "discussion.md", "confirmed-requirements.md", "run-log.yaml"}]


def _completed_agent_call(call: dict[str, Any], phase: str, artifact: str) -> bool:
    """Require attributable execution evidence, not a hand-written status label."""
    return (
        call.get("phase") == phase
        and call.get("artifact") == artifact
        and call.get("status") == "complete"
        and bool(call.get("provider"))
        and isinstance(call.get("command"), list)
        and isinstance(call.get("exit_code"), int)
        and bool(call.get("output_sha256"))
    )


def _has_deterministic_trace_recovery(state: dict[str, Any], folder: Path) -> bool:
    """Accept the controller's narrow recovery for an attributable no-output trace.

    A trace is normally model-authored.  The only exception is a prior trace
    call that ended without writing its assigned file: the controller can then
    reconstruct observable facts, which still require the normal independent
    current-hash review below.  This does not permit an arbitrary hand-written
    trace or relax execution evidence for any other stage.
    """
    trace = folder / "run-log.yaml"
    if not trace.is_file():
        return False
    text = trace.read_text(encoding="utf-8")
    controller_owned = (
        "pm_copilot_revision: evaluation-controller" in text
        and re.search(
            r"trace is\s+controller-generated\s+after the trace Agent produced no output",
            text,
        ) is not None
    )
    no_output_failure = any(
        call.get("phase") == "trace"
        and call.get("artifact") == "run-log.yaml"
        and call.get("status") == "failed"
        and call.get("failure_category") == "agent_no_output"
        for call in state.get("agent_calls", [])
    )
    return controller_owned and no_output_failure


def _accepted_current_review(state: dict[str, Any], folder: Path, phase: str, artifact: str) -> bool:
    path = folder / ("proposed-skill/SKILL.md" if artifact == "SKILL.md" else artifact)
    if not path.is_file():
        return False
    accepted_digests = {hashlib.sha256(path.read_bytes()).hexdigest()}
    if phase == "trace" and artifact == "run-log.yaml":
        # Trace review occurs before deterministic final validation. The only
        # permitted post-review mutation is closing this status bit after all
        # validators pass; any other content change still invalidates review.
        text = path.read_text(encoding="utf-8")
        prevalidation = re.sub(
            r"(?ms)(^quality_decision:\n.*?^\s*passed:)\s*true\s*$", r"\1 false", text, count=1,
        )
        accepted_digests.add(hashlib.sha256(prevalidation.encode("utf-8")).hexdigest())
    return any(
        call.get("phase") == "stage_quality_review"
        and call.get("reviewed_phase") == phase
        and call.get("artifact") == artifact
        and call.get("review_passed") is True
        and call.get("reviewed_sha256") in accepted_digests
        and call.get("provider")
        and isinstance(call.get("command"), list)
        and isinstance(call.get("exit_code"), int)
        and call.get("output_sha256")
        for call in state.get("agent_calls", [])
    )


def case_evidence_failures(case: dict[str, Any], folder: Path, verify: bool = False) -> list[str]:
    """Validate one case folder independently of any portfolio manifest."""
    failures: list[str] = []
    state_path = folder / "scenario-run.json"
    if not state_path.is_file():
        return ["missing scenario manifest"]
    try:
        state = _load(state_path)
    except json.JSONDecodeError:
        return ["scenario manifest is invalid JSON"]
    if state.get("status") != "complete":
        failures.append(f"scenario status is not complete: {state.get('status')}")
    phases = _phase_statuses(state)
    for phase in case["required_phases"]:
        if phases.get(phase) != "complete":
            failures.append(f"phase {phase} is not complete")
    if state.get("confirmation_mode") != confirmation_mode_for(case) or state.get("human_confirmation") is not False:
        failures.append("evaluation confirmation provenance is invalid")
    calls = state.get("agent_calls", [])
    for phase, artifact in (("discussion", "discussion.md"), ("confirmation", "confirmed-requirements.md")):
        if not any(_completed_agent_call(call, phase, artifact) for call in calls):
            failures.append(f"missing completed Agent call for {phase}/{artifact}")
    if not any(_completed_agent_call(call, "trace", "run-log.yaml") for call in calls) and not _has_deterministic_trace_recovery(state, folder):
        failures.append("missing completed Agent call for trace/run-log.yaml")
    for artifact in _agent_artifacts(case):
        if not any(_completed_agent_call(call, "delivery", artifact) for call in calls):
            failures.append(f"missing completed delivery Agent call for {artifact}")
    reviewed = [("discussion", "discussion.md"), ("confirmation", "confirmed-requirements.md"), *[("delivery", item) for item in _agent_artifacts(case)], ("trace", "run-log.yaml")]
    for phase, artifact in reviewed:
        if not _accepted_current_review(state, folder, phase, artifact):
            failures.append(f"missing accepted independent review for {artifact}")
    for artifact in case["required_artifacts"]:
        path = folder / ("proposed-skill/SKILL.md" if artifact == "SKILL.md" else artifact)
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(f"missing required artifact {artifact}")
    if verify:
        language = state.get("language", "en")
        for command in (
            [sys.executable, "scripts/validate_outputs.py", str(folder), "--language", language],
            [sys.executable, "scripts/validate_agent_trace.py", str(folder)],
            [sys.executable, "scripts/run_delivery_checks.py", str(folder), "--language", language],
        ):
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
            if result.returncode != 0:
                failures.append(f"final audit command failed: {' '.join(command)}")
    return failures


def audit(portfolio_root: Path, verify: bool = False) -> list[str]:
    manifest_path = portfolio_root / "portfolio-run.json"
    if not manifest_path.is_file():
        return [f"missing portfolio manifest: {manifest_path}"]
    manifest = _load(manifest_path)
    active_cases = portfolio()["cases"]
    active = {case["case_id"]: case for case in active_cases}
    snapshot = manifest.get("plan_snapshot")
    plan = {case["case_id"]: case for case in snapshot} if isinstance(snapshot, list) else {}
    recorded = manifest.get("cases", {})
    failures: list[str] = []
    if not isinstance(snapshot, list):
        failures.append("portfolio manifest has no immutable plan snapshot")
    elif manifest.get("plan_sha256") != plan_digest(snapshot):
        failures.append("portfolio manifest plan snapshot digest is invalid")
    elif set(plan) and any(active.get(case_id) != case for case_id, case in plan.items()):
        failures.append("portfolio plan snapshot no longer matches active fixture provenance")
    if set(recorded) != set(plan):
        failures.append("portfolio manifest case set does not exactly match the active plan")
    if manifest.get("status") != "complete":
        failures.append(f"portfolio status is not complete: {manifest.get('status')}")

    for case_id, case in plan.items():
        summary = recorded.get(case_id)
        if not isinstance(summary, dict):
            failures.append(f"{case_id}: missing case summary")
            continue
        if summary.get("status") != "complete":
            failures.append(f"{case_id}: summary status is not complete")
        folder = Path(str(summary.get("folder", "")))
        failures.extend(f"{case_id}: {failure}" for failure in case_evidence_failures(case, folder, verify))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portfolio_root", type=Path)
    parser.add_argument("--verify", action="store_true", help="rerun all final case validators")
    args = parser.parse_args()
    failures = audit(args.portfolio_root, args.verify)
    if failures:
        print("portfolio audit failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"portfolio audit passed: {args.portfolio_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
