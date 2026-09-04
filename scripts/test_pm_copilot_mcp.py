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

    def write_runtime(self, root: Path, runtime_version: str, wrapper_version: str, *, manifest: bool = True) -> tuple[Path, Path]:
        runtime = root / "global-runtime"
        runtime.mkdir()
        (runtime / "VERSION").write_text(f"{runtime_version}\n", encoding="utf-8")
        plugin_root = (
            root / ".codex" / "plugins" / "cache" / "personal" / "pm-copilot" / wrapper_version
        )
        wrapper = plugin_root / "scripts" / "pm_copilot_mcp.py"
        wrapper.parent.mkdir(parents=True)
        if manifest:
            manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
            manifest_path.parent.mkdir()
            manifest_path.write_text(json.dumps({"version": wrapper_version}), encoding="utf-8")
        return runtime, wrapper

    def test_status_reports_controller_state_not_agent_narrative(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.write_state(folder)
            summary = MCP.run_summary(str(folder))
            self.assertTrue(summary["ok"])
            self.assertEqual(summary["status"], "awaiting_confirmation")
            self.assertEqual(summary["delivery_calls"], [])
            self.assertNotIn("confirmed-requirements.md", summary["artifacts"])

    def test_status_reports_matching_cached_wrapper_and_runtime_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "run"
            folder.mkdir()
            self.write_state(folder)
            runtime, wrapper = self.write_runtime(root, "6.2.104", "6.2.104+codex.cachebuster")
            with patch.object(MCP, "RUNTIME_HOME", runtime), patch.object(MCP, "WRAPPER_SCRIPT", wrapper):
                summary = MCP.run_summary(str(folder))
            self.assertFalse(summary["runtime_restart_required"])
            self.assertEqual(summary["runtime_provenance"], {
                "wrapper": {
                    "script_path": str(wrapper.resolve()),
                    "plugin_version": "6.2.104+codex.cachebuster",
                    "plugin_version_source": "plugin_manifest",
                    "is_persistent_cache": True,
                },
                "canonical_runtime": {
                    "path": str(runtime.resolve()),
                    "version": "6.2.104",
                },
            })

    def test_status_flags_stale_deleted_cache_wrapper_from_its_path_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "run"
            folder.mkdir()
            self.write_state(folder)
            runtime, wrapper = self.write_runtime(root, "6.2.104", "6.2.103+codex.cachebuster", manifest=False)
            with patch.object(MCP, "RUNTIME_HOME", runtime), patch.object(MCP, "WRAPPER_SCRIPT", wrapper):
                summary = MCP.run_summary(str(folder))
            self.assertTrue(summary["runtime_restart_required"])
            self.assertEqual(summary["runtime_provenance"]["wrapper"]["plugin_version"], "6.2.103+codex.cachebuster")
            self.assertEqual(summary["runtime_provenance"]["wrapper"]["plugin_version_source"], "cache_path")

    def test_status_distinguishes_historical_delivery_attempt_from_current_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "run"
            folder.mkdir()
            self.write_state(
                folder,
                status="recovery_required",
                delivery_stages={
                    "confirmed-requirements.md": {
                        "artifact_status": "failed",
                        "review_status": "not_started",
                        "pm_copilot_version": "6.2.103",
                        "updated_at": "2026-09-04T04:57:48.643488+00:00",
                    },
                },
            )
            runtime, wrapper = self.write_runtime(root, "6.2.105", "6.2.105+codex.cachebuster")
            with patch.object(MCP, "RUNTIME_HOME", runtime), patch.object(MCP, "WRAPPER_SCRIPT", wrapper):
                summary = MCP.run_summary(str(folder))
            self.assertFalse(summary["runtime_restart_required"])
            self.assertEqual(summary["runtime_provenance"]["canonical_runtime"]["version"], "6.2.105")
            self.assertEqual(summary["run_attempt_provenance"], {
                "artifact": "confirmed-requirements.md",
                "artifact_status": "failed",
                "review_status": "not_started",
                "recorded_at": "2026-09-04T04:57:48.643488+00:00",
                "pm_copilot_version": "6.2.103",
                "canonical_runtime_version": "6.2.105",
                "version_relation": "historical_attempt",
            })

    def test_status_does_not_flag_a_non_cache_wrapper_with_a_different_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "run"
            folder.mkdir()
            self.write_state(folder)
            runtime = root / "global-runtime"
            runtime.mkdir()
            (runtime / "VERSION").write_text("6.2.104\n", encoding="utf-8")
            wrapper = root / "plugin-source" / "scripts" / "pm_copilot_mcp.py"
            wrapper.parent.mkdir(parents=True)
            manifest_path = wrapper.parent.parent / ".codex-plugin" / "plugin.json"
            manifest_path.parent.mkdir()
            manifest_path.write_text(json.dumps({"version": "6.2.103+codex.source"}), encoding="utf-8")
            with patch.object(MCP, "RUNTIME_HOME", runtime), patch.object(MCP, "WRAPPER_SCRIPT", wrapper):
                summary = MCP.run_summary(str(folder))
            self.assertFalse(summary["runtime_restart_required"])
            self.assertFalse(summary["runtime_provenance"]["wrapper"]["is_persistent_cache"])

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

    def test_confirm_allows_explicit_failed_run_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.write_state(folder, status="failed", termination="failed", user_confirmation={"confirmed": True})
            controller = folder / "controller.py"
            controller.write_text("# mocked controller\n", encoding="utf-8")
            with patch.object(MCP, "CONTROLLER", controller), patch.object(MCP.subprocess, "run", return_value=type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()):
                result = MCP.confirm_delivery(str(folder))
            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "failed")

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

    def test_submit_answer_forwards_a_confirmed_delivery_selector_to_the_controller(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.write_state(
                folder,
                status="needs_input",
                termination="needs_input",
                user_confirmation={"confirmed": True},
                required_input={"field": "revision_selector", "question": "请选择需求 ID"},
            )
            controller = folder / "controller.py"
            controller.write_text("# mocked controller\n", encoding="utf-8")

            def resume(command, **kwargs):
                self.assertEqual(command[-2:], ["--answers", "5.1"])
                self.write_state(
                    folder,
                    status="awaiting_confirmation",
                    termination="human_checkpoint",
                    user_confirmation={"confirmed": True},
                    revision_requirement_ids=["5.1"],
                )
                return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

            with patch.object(MCP, "CONTROLLER", controller), patch.object(MCP.subprocess, "run", side_effect=resume):
                result = MCP.submit_answer(str(folder), "5.1")
            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "awaiting_confirmation")

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
            root = Path(temporary)
            folder = root / "run"
            folder.mkdir()
            self.write_state(folder)
            runtime, wrapper = self.write_runtime(root, "6.2.104", "6.2.103+codex.cachebuster")
            stdout = io.StringIO()
            with patch.object(MCP, "RUNTIME_HOME", runtime), patch.object(MCP, "WRAPPER_SCRIPT", wrapper), patch.object(
                sys, "argv", ["pm_copilot_mcp.py", "--run-folder", str(folder), "--status"],
            ), patch("sys.stdout", stdout):
                self.assertEqual(MCP.main(), 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "awaiting_confirmation")
            self.assertTrue(payload["runtime_restart_required"])


if __name__ == "__main__":
    unittest.main()
