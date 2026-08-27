#!/usr/bin/env python3
"""Regression tests for the plugin's canonical interactive PRD MCP bridge."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "plugins" / "pm-copilot" / "scripts" / "pm_copilot_mcp.py"
SPEC = importlib.util.spec_from_file_location("pm_copilot_mcp", MODULE_PATH)
assert SPEC and SPEC.loader
MCP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MCP)


class PmCopilotMcpTest(unittest.TestCase):
    def write_state(self, folder: Path, **overrides: object) -> None:
        state = {
            "mode": "interactive",
            "status": "awaiting_confirmation",
            "termination": "human_checkpoint",
            "user_confirmation": None,
            "artifacts": ["discussion.md"],
            "agent_calls": [],
            "turns": [{"questions": []}],
        }
        state.update(overrides)
        (folder / "interactive-run.json").write_text(json.dumps(state), encoding="utf-8")

    def test_status_reports_controller_state_not_agent_narrative(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.write_state(folder)
            summary = MCP.run_summary(str(folder))
            self.assertTrue(summary["ok"])
            self.assertEqual(summary["status"], "awaiting_confirmation")
            self.assertEqual(summary["delivery_calls"], [])
            self.assertNotIn("confirmed-requirements.md", summary["artifacts"])

    def test_confirm_requires_awaiting_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.write_state(folder, status="needs_input")
            result = MCP.confirm_delivery(str(folder))
            self.assertFalse(result["ok"])
            self.assertIn("needs_input", result["error"])

    def test_confirm_allows_explicit_recovery_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.write_state(folder, status="recovery_required", termination="interrupted")
            controller = folder / "controller.py"
            controller.write_text("# mocked controller\n", encoding="utf-8")
            with patch.object(MCP, "CONTROLLER", controller), patch.object(MCP.subprocess, "run", return_value=type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()):
                result = MCP.confirm_delivery(str(folder))
            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "recovery_required")

    def test_status_detects_legacy_interruption_without_mutating_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "run"
            folder.mkdir()
            self.write_state(folder)
            (folder / "confirmed-requirements.md").write_text("# partial\n", encoding="utf-8")
            (folder.parent / ".run.stage-abandoned").mkdir()
            summary = MCP.run_summary(str(folder))
            self.assertEqual(summary["status"], "recovery_required")
            self.assertEqual(summary["termination"], "interrupted")
            persisted = json.loads((folder / "interactive-run.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "awaiting_confirmation")

    def test_submit_answer_requires_needs_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.write_state(folder)
            result = MCP.submit_answer(str(folder), "确认执行")
            self.assertFalse(result["ok"])
            self.assertIn("awaiting_confirmation", result["error"])

    def test_confirm_returns_the_post_controller_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.write_state(folder)
            controller = folder / "controller.py"
            controller.write_text("# mocked controller\n", encoding="utf-8")

            def complete(command, **kwargs):
                self.write_state(folder, status="complete", termination="complete", user_confirmation={"confirmed": True}, artifacts=["discussion.md", "confirmed-requirements.md", "prd.md"])
                return type("Result", (), {"returncode": 0, "stdout": "delivery complete", "stderr": ""})()

            with patch.object(MCP, "CONTROLLER", controller), patch.object(MCP.subprocess, "run", side_effect=complete):
                result = MCP.confirm_delivery(str(folder))
            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "complete")
            self.assertIn("prd.md", result["artifacts"])

    def test_cli_status_uses_the_same_canonical_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.write_state(folder)
            stdout = io.StringIO()
            with patch.object(sys, "argv", ["pm_copilot_mcp.py", "--run-folder", str(folder), "--status"]), patch("sys.stdout", stdout):
                self.assertEqual(MCP.main(), 0)
            self.assertEqual(json.loads(stdout.getvalue())["status"], "awaiting_confirmation")


if __name__ == "__main__":
    unittest.main()
