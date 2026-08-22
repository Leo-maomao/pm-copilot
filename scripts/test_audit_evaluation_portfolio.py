#!/usr/bin/env python3
"""Regression tests for portfolio evidence auditing."""

from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audit_evaluation_portfolio import _accepted_current_review, audit


class PortfolioAuditTest(unittest.TestCase):
    def test_missing_manifest_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            self.assertTrue(audit(Path(temporary)))

    def test_complete_case_requires_actual_agent_and_review_evidence(self) -> None:
        case = {
            "case_id": "case-a",
            "fixture_scope": "Public generic",
            "required_phases": ["intake", "discussion", "confirmation", "delivery", "validation"],
            "required_artifacts": ["prd.md", "prd.html", "discussion.md", "confirmed-requirements.md", "run-log.yaml"],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "case-a"
            folder.mkdir()
            for name in case["required_artifacts"]:
                (folder / name).write_text("ok", encoding="utf-8")
            calls = []
            execution = {"provider": "test", "command": ["test"], "exit_code": 0, "output_sha256": "agent-output"}
            digest = hashlib.sha256(b"ok").hexdigest()
            for phase, artifact in (("discussion", "discussion.md"), ("confirmation", "confirmed-requirements.md"), ("delivery", "prd.md"), ("trace", "run-log.yaml")):
                calls.append({"phase": phase, "artifact": artifact, "status": "complete", **execution})
            for phase, artifact in (("discussion", "discussion.md"), ("confirmation", "confirmed-requirements.md"), ("delivery", "prd.md"), ("trace", "run-log.yaml")):
                calls.append({"phase": "stage_quality_review", "reviewed_phase": phase, "artifact": artifact, "review_passed": True, "reviewed_sha256": digest, **execution})
            (folder / "scenario-run.json").write_text(json.dumps({
                "status": "complete", "confirmation_mode": "fixture_confirmation", "human_confirmation": False,
                "language": "en", "phases": [{"name": phase, "status": "complete"} for phase in case["required_phases"]], "agent_calls": calls,
            }), encoding="utf-8")
            plan_digest = hashlib.sha256(json.dumps([case], ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
            (root / "portfolio-run.json").write_text(json.dumps({"status": "complete", "plan_snapshot": [case], "plan_sha256": plan_digest, "cases": {"case-a": {"status": "complete", "folder": str(folder)}}}), encoding="utf-8")
            with patch("audit_evaluation_portfolio.portfolio", return_value={"cases": [case]}):
                self.assertEqual(audit(root), [])

    def test_claimed_completion_without_review_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "portfolio-run.json").write_text(json.dumps({"status": "complete", "cases": {}}), encoding="utf-8")
            with patch("audit_evaluation_portfolio.portfolio", return_value={"cases": [{"case_id": "case-a", "required_phases": [], "required_artifacts": []}]}):
                failures = audit(root)
            self.assertTrue(any("plan snapshot" in failure or "case set" in failure for failure in failures))

    def test_invalid_plan_digest_fails(self) -> None:
        case = {"case_id": "case-a", "required_phases": [], "required_artifacts": []}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "portfolio-run.json").write_text(json.dumps({
                "status": "complete", "plan_snapshot": [case], "plan_sha256": "invalid", "cases": {},
            }), encoding="utf-8")
            with patch("audit_evaluation_portfolio.portfolio", return_value={"cases": [case]}):
                self.assertTrue(any("digest" in failure for failure in audit(root)))

    def test_trace_review_allows_only_deterministic_quality_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            trace = folder / "run-log.yaml"
            reviewed = "quality_decision:\n  passed: false\n  rationale: validators pending\n"
            trace.write_text(reviewed.replace("false", "true"), encoding="utf-8")
            state = {"agent_calls": [{
                "phase": "stage_quality_review", "reviewed_phase": "trace", "artifact": "run-log.yaml",
                "review_passed": True, "reviewed_sha256": hashlib.sha256(reviewed.encode("utf-8")).hexdigest(),
                "provider": "test", "command": ["test"], "exit_code": 0, "output_sha256": "review",
            }]}
            self.assertTrue(_accepted_current_review(state, folder, "trace", "run-log.yaml"))
            trace.write_text(trace.read_text(encoding="utf-8") + "failures: []\n", encoding="utf-8")
            self.assertFalse(_accepted_current_review(state, folder, "trace", "run-log.yaml"))


if __name__ == "__main__":
    unittest.main()
