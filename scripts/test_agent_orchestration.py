#!/usr/bin/env python3
"""Mocked end-to-end checks for the bounded multi-agent control plane."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from run_agent_delegation import run_plan


def fake_execute(*args: object) -> dict[str, object]:
    return {"status": "complete", "provider": "test", "output": "evidence"}


class AgentOrchestrationTest(unittest.TestCase):
    def test_planning_does_not_call_models(self) -> None:
        report = run_plan("需求 PRD、UI、埋点和竞品调研", "auto", Path.cwd(), fake_execute, False)
        self.assertEqual(report["status"], "planned")
        self.assertEqual(report["workers"], [])

    def test_execution_runs_review_after_specialists(self) -> None:
        capabilities = {"single_agent_auto": {"status": "available", "reason": "test"}, "multi_agent_loop": {"status": "unavailable", "reason": "test"}}
        calls: list[str] = []
        def recording_execute(*args: object) -> dict[str, object]:
            calls.append(str(args[1]))
            return fake_execute()
        with patch("run_agent_delegation.runtime_capabilities", return_value=capabilities):
            report = run_plan("需求 PRD、UI、埋点和竞品调研", "auto", Path.cwd(), recording_execute, True)
        self.assertEqual(report["status"], "complete")
        self.assertTrue(calls[-1].startswith("You are the PM Copilot Review Agent"))
        self.assertGreaterEqual(len(calls), 5)

    def test_execution_blocks_without_auto_runtime(self) -> None:
        capabilities = {"single_agent_auto": {"status": "unavailable", "reason": "no session"}, "multi_agent_loop": {"status": "unavailable", "reason": "test"}}
        with patch("run_agent_delegation.runtime_capabilities", return_value=capabilities):
            report = run_plan("需求 PRD", "auto", Path.cwd(), fake_execute, True)
        self.assertEqual(report["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
