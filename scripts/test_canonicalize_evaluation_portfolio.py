#!/usr/bin/env python3
"""Regression tests for deterministic canonical evaluation selection."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonicalize_evaluation_portfolio import canonicalize
from run_evaluation_portfolio import run_portfolio


CASE = {
    "case_id": "case-a", "fixture_scope": "Public generic",
    "required_phases": ["intake", "discussion", "confirmation", "delivery", "validation"],
    "required_artifacts": ["prd.md", "prd.html", "discussion.md", "confirmed-requirements.md", "run-log.yaml"],
}


def completed_case(folder: Path, marker: str) -> None:
    folder.mkdir()
    for name in CASE["required_artifacts"]:
        (folder / name).write_text(marker, encoding="utf-8")
    digest = hashlib.sha256(marker.encode()).hexdigest()
    execution = {"provider": "codex", "command": ["codex"], "exit_code": 0, "output_sha256": "output"}
    calls = []
    for phase, artifact in (("discussion", "discussion.md"), ("confirmation", "confirmed-requirements.md"), ("delivery", "prd.md"), ("trace", "run-log.yaml")):
        calls.append({"phase": phase, "artifact": artifact, "status": "complete", "completed_at": f"2026-08-21T00:00:0{marker}+00:00", **execution})
        calls.append({"phase": "stage_quality_review", "reviewed_phase": phase, "artifact": artifact, "review_passed": True, "reviewed_sha256": digest, **execution})
    (folder / "scenario-run.json").write_text(json.dumps({
        "status": "complete", "confirmation_mode": "fixture_confirmation", "human_confirmation": False,
        "language": "en", "case": {"case_id": "case-a"},
        "phases": [{"name": phase, "status": "complete"} for phase in CASE["required_phases"]], "agent_calls": calls,
    }), encoding="utf-8")


class CanonicalSelectionTest(unittest.TestCase):
    def test_selects_one_duplicate_deterministically_and_records_other(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            completed_case(root / "older", "1")
            completed_case(root / "newer", "2")
            with patch("canonicalize_evaluation_portfolio.portfolio", return_value={"cases": [CASE]}):
                result = canonicalize(root)
            self.assertEqual(result["cases"]["case-a"]["folder"], str((root / "newer").resolve()))
            self.assertIn("case-a", result["rejections"])

    def test_invalid_completed_claim_is_not_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "invalid"
            folder.mkdir()
            (folder / "scenario-run.json").write_text(json.dumps({"status": "complete", "case": {"case_id": "case-a"}}), encoding="utf-8")
            with patch("canonicalize_evaluation_portfolio.portfolio", return_value={"cases": [CASE]}):
                result = canonicalize(root)
            self.assertEqual(result["cases"]["case-a"]["status"], "missing")

    def test_selects_reviewed_controller_trace_after_attributed_no_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "recovered"
            completed_case(folder, "1")
            trace = folder / "run-log.yaml"
            trace.write_text(
                "pm_copilot_revision: evaluation-controller\n"
                "current_state_summary: trace is controller-generated after the trace Agent produced no output.\n",
                encoding="utf-8",
            )
            manifest = folder / "scenario-run.json"
            state = json.loads(manifest.read_text(encoding="utf-8"))
            state["agent_calls"] = [
                call for call in state["agent_calls"]
                if not (call.get("phase") == "trace" and call.get("artifact") == "run-log.yaml")
            ]
            digest = hashlib.sha256(trace.read_bytes()).hexdigest()
            state["agent_calls"].extend([
                {"phase": "trace", "artifact": "run-log.yaml", "status": "failed", "failure_category": "agent_no_output"},
                {"phase": "stage_quality_review", "reviewed_phase": "trace", "artifact": "run-log.yaml", "review_passed": True, "reviewed_sha256": digest,
                 "provider": "codex", "command": ["codex"], "exit_code": 0, "output_sha256": "review"},
            ])
            manifest.write_text(json.dumps(state), encoding="utf-8")
            with patch("canonicalize_evaluation_portfolio.portfolio", return_value={"cases": [CASE]}):
                result = canonicalize(root)
            self.assertEqual(result["cases"]["case-a"]["status"], "complete")

    def test_resume_accepts_only_hash_pinned_canonical_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            completed_case(root / "chosen", "1")
            manifest = root / "chosen" / "scenario-run.json"
            index = root / "index.json"
            index.write_text(json.dumps({
                "mode": "evaluation_canonical_index", "plan_snapshot": [CASE],
                "plan_sha256": hashlib.sha256(json.dumps([CASE], ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                "cases": {"case-a": {"status": "complete", "folder": str(root / "chosen"), "scenario_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest()}},
            }), encoding="utf-8")
            with patch("run_evaluation_portfolio.portfolio", return_value={"cases": [CASE]}), patch("run_evaluation_portfolio.execute_case") as execute:
                result = run_portfolio(root / "control", timeout_minutes=1, case_ids={"case-a"}, canonical_index=index)
            execute.assert_not_called()
            self.assertEqual(result["cases"]["case-a"]["folder"], str(root / "chosen"))


if __name__ == "__main__":
    unittest.main()
