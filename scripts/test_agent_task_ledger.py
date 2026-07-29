#!/usr/bin/env python3
"""Regression checks for durable PM Copilot agent task ledgers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_task_ledger import create_ledger, load, validate, write
from plan_agent_delegation import build_plan
from run_agent_delegation import run_plan


def structured_execute(*args: object) -> dict[str, object]:
    prompt = str(args[1])
    if "PM Orchestrator" in prompt:
        return {"status": "complete", "provider": "test", "model": "fixture", "output": '{"claims":[{"id":"C1","statement":"verified"}],"cross_reviews":[],"arbitrations":[{"id":"A1"}],"limitations":[]}' }
    if "Review Agent" in prompt:
        return {"status": "complete", "provider": "test", "model": "fixture", "output": '{"cross_reviews":[],"unresolved_findings":[],"recommendation":"continue"}' }
    return {"status": "complete", "provider": "test", "model": "fixture", "output": '{"claims":[],"rejected_evidence":[],"open_questions":[],"risks":[],"validation_delta":[]}' }


class AgentTaskLedgerTest(unittest.TestCase):
    def test_atomic_write_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ledger.json"
            ledger = create_ledger("需求 PRD", "auto", build_plan("需求 PRD"), Path(temporary))
            write(path, ledger)
            self.assertEqual(load(path)["schema_version"], "1.0")
            self.assertIn("completed task", " ".join(validate({**ledger, "tasks": [{"id": "T1", "status": "complete", "attempts": 0, "output_ref": ""}]})))

    def test_resume_skips_completed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ledger.json"
            capabilities = {"single_agent_auto": {"status": "available", "reason": "test"}, "multi_agent_loop": {"status": "available", "reason": "test"}}
            from unittest.mock import patch

            with patch("run_agent_delegation.runtime_capabilities", return_value=capabilities):
                first = run_plan("需求和埋点", "auto", Path(temporary), structured_execute, True, path)
                second = run_plan("需求和埋点", "auto", Path(temporary), structured_execute, True, path, True)
            self.assertEqual(first["status"], "complete")
            self.assertEqual(second["status"], "complete")
            self.assertGreater(load(path)["resume"]["count"], 0)
            self.assertEqual(validate(load(path), path.parent), [])


if __name__ == "__main__":
    unittest.main()
