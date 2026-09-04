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


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPOSITORY_ROOT / "plugins" / "pm-copilot" / "scripts" / "pm_copilot_mcp.py"
SPEC = importlib.util.spec_from_file_location("pm_copilot_mcp", MODULE_PATH)
assert SPEC and SPEC.loader
MCP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MCP)


class PmCopilotMcpTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_home = patch.object(MCP, "RUNTIME_HOME", REPOSITORY_ROOT)
        self.controller = patch.object(
            MCP,
            "CONTROLLER",
            REPOSITORY_ROOT / "scripts" / "run_interactive_request.py",
        )
        self.runtime_home.start()
        self.controller.start()

    def tearDown(self) -> None:
        self.controller.stop()
        self.runtime_home.stop()

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

    def write_runtime(
        self,
        root: Path,
        runtime_version: str,
        wrapper_version: str,
        *,
        manifest: bool = True,
        canonical_plugin_version: str | None = None,
        wrapper_contents: str = "# cached wrapper\n",
        canonical_wrapper_contents: str | None = None,
    ) -> tuple[Path, Path]:
        runtime = root / "repository"
        runtime.mkdir()
        (runtime / ".git").mkdir()
        (runtime / "PM_COPILOT.md").write_text("# PM Copilot\n", encoding="utf-8")
        (runtime / "VERSION").write_text(f"{runtime_version}\n", encoding="utf-8")
        runtime_controller = runtime / "scripts" / "run_interactive_request.py"
        runtime_controller.parent.mkdir()
        runtime_controller.write_text("# controller\n", encoding="utf-8")
        plugin_root = (
            root / ".codex" / "plugins" / "cache" / "personal" / "pm-copilot" / wrapper_version
        )
        wrapper = plugin_root / "scripts" / "pm_copilot_mcp.py"
        wrapper.parent.mkdir(parents=True)
        wrapper.write_text(wrapper_contents, encoding="utf-8")
        if manifest:
            manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
            manifest_path.parent.mkdir()
            manifest_path.write_text(json.dumps({"version": wrapper_version}), encoding="utf-8")

        canonical_version = canonical_plugin_version or wrapper_version
        canonical_wrapper = runtime / "plugins" / "pm-copilot" / "scripts" / "pm_copilot_mcp.py"
        canonical_wrapper.parent.mkdir(parents=True)
        canonical_wrapper.write_text(
            canonical_wrapper_contents if canonical_wrapper_contents is not None else wrapper_contents,
            encoding="utf-8",
        )
        canonical_manifest = runtime / "plugins" / "pm-copilot" / ".codex-plugin" / "plugin.json"
        canonical_manifest.parent.mkdir()
        canonical_manifest.write_text(json.dumps({"version": canonical_version}), encoding="utf-8")
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

    def test_plugin_config_forwards_only_the_explicit_repository_selection(self) -> None:
        config = json.loads(
            (REPOSITORY_ROOT / "plugins" / "pm-copilot" / ".mcp.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            config["mcpServers"]["pm-copilot"]["env_vars"],
            ["PM_COPILOT_REPOSITORY"],
        )

    def test_legacy_runtime_environment_variable_cannot_select_a_checkout(self) -> None:
        with patch.dict(
            MCP.os.environ,
            {"PM_COPILOT_HOME": "/tmp/legacy-runtime"},
            clear=True,
        ):
            self.assertIsNone(MCP._selected_runtime_home())

    def test_status_reports_missing_checkout_without_falling_back_to_the_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.write_state(folder)
            with patch.object(MCP, "RUNTIME_HOME", None), patch.object(MCP, "CONTROLLER", None):
                summary = MCP.run_summary(str(folder))
                result = MCP.confirm_delivery(str(folder))

            self.assertTrue(summary["ok"])
            self.assertFalse(summary["runtime_provenance"]["selection"]["configured"])
            self.assertFalse(summary["runtime_provenance"]["selection"]["checkout_valid"])
            self.assertIn("PM_COPILOT_REPOSITORY", summary["runtime_provenance"]["selection"]["error"])
            self.assertFalse(result["ok"])
            self.assertEqual(result["error_code"], "checkout_not_configured")

    def test_invalid_or_cached_directory_cannot_be_used_as_a_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "run"
            folder.mkdir()
            self.write_state(folder)
            arbitrary_directory = root / "arbitrary-working-directory"
            arbitrary_directory.mkdir()
            cached_directory = root / ".codex" / "plugins" / "cache" / "personal" / "pm-copilot" / "6.2.112"
            cached_directory.mkdir(parents=True)

            for invalid_runtime, expected_error in (
                (arbitrary_directory, "must point to a PM Copilot repository checkout"),
                (cached_directory, "not a Codex plugin cache"),
            ):
                with patch.object(MCP, "RUNTIME_HOME", invalid_runtime), patch.object(
                    MCP, "CONTROLLER", invalid_runtime / "scripts" / "run_interactive_request.py",
                ), patch.object(MCP.subprocess, "run") as execute:
                    result = MCP.confirm_delivery(str(folder))

                self.assertFalse(result["ok"])
                self.assertEqual(result["error_code"], "checkout_invalid")
                self.assertIn(expected_error, result["error"])
                execute.assert_not_called()

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
            provenance = summary["runtime_provenance"]
            self.assertEqual(provenance["wrapper"]["script_path"], str(wrapper.resolve()))
            self.assertEqual(provenance["wrapper"]["plugin_version"], "6.2.104+codex.cachebuster")
            self.assertEqual(provenance["wrapper"]["plugin_version_source"], "plugin_manifest")
            self.assertTrue(provenance["wrapper"]["is_persistent_cache"])
            self.assertEqual(provenance["canonical_runtime"]["path"], str(runtime.resolve()))
            self.assertEqual(provenance["canonical_runtime"]["version"], "6.2.104")
            self.assertEqual(
                provenance["canonical_runtime"]["plugin"]["plugin_version"],
                "6.2.104+codex.cachebuster",
            )
            self.assertTrue(provenance["dispatch"]["current"])
            self.assertEqual(provenance["dispatch"]["mismatch_reasons"], [])

    def test_status_flags_stale_deleted_cache_wrapper_from_its_path_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "run"
            folder.mkdir()
            self.write_state(folder)
            runtime, wrapper = self.write_runtime(
                root,
                "6.2.104",
                "6.2.103+codex.cachebuster",
                manifest=False,
                canonical_plugin_version="6.2.104+codex.current",
            )
            wrapper.unlink()
            with patch.object(MCP, "RUNTIME_HOME", runtime), patch.object(MCP, "WRAPPER_SCRIPT", wrapper):
                summary = MCP.run_summary(str(folder))
            self.assertTrue(summary["runtime_restart_required"])
            self.assertEqual(summary["runtime_provenance"]["wrapper"]["plugin_version"], "6.2.103+codex.cachebuster")
            self.assertEqual(summary["runtime_provenance"]["wrapper"]["plugin_version_source"], "cache_path")
            self.assertIn(
                "loaded_wrapper_content_unavailable",
                summary["runtime_provenance"]["dispatch"]["mismatch_reasons"],
            )

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
            runtime = root / "repository"
            runtime.mkdir()
            (runtime / ".git").mkdir()
            (runtime / "PM_COPILOT.md").write_text("# PM Copilot\n", encoding="utf-8")
            (runtime / "VERSION").write_text("6.2.104\n", encoding="utf-8")
            runtime_controller = runtime / "scripts" / "run_interactive_request.py"
            runtime_controller.parent.mkdir()
            runtime_controller.write_text("# controller\n", encoding="utf-8")
            canonical_wrapper = runtime / "plugins" / "pm-copilot" / "scripts" / "pm_copilot_mcp.py"
            canonical_wrapper.parent.mkdir(parents=True)
            canonical_wrapper.write_text("# canonical bridge\n", encoding="utf-8")
            canonical_manifest = runtime / "plugins" / "pm-copilot" / ".codex-plugin" / "plugin.json"
            canonical_manifest.parent.mkdir()
            canonical_manifest.write_text(json.dumps({"version": "6.2.104+codex.current"}), encoding="utf-8")
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

    def test_stale_cached_wrapper_blocks_confirm_before_controller_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "run"
            folder.mkdir()
            self.write_state(folder)
            runtime, wrapper = self.write_runtime(
                root,
                "6.2.104",
                "6.2.103+codex.old",
                canonical_plugin_version="6.2.104+codex.current",
            )
            controller = folder / "controller.py"
            controller.write_text("# mocked controller\n", encoding="utf-8")
            with patch.object(MCP, "RUNTIME_HOME", runtime), patch.object(MCP, "WRAPPER_SCRIPT", wrapper), patch.object(
                MCP, "CONTROLLER", controller,
            ), patch.object(MCP.subprocess, "run") as execute:
                result = MCP.confirm_delivery(str(folder))

            self.assertFalse(result["ok"])
            self.assertEqual(result["error_code"], "restart_required")
            self.assertTrue(result["runtime_restart_required"])
            self.assertIn("wrapper_build_mismatch", result["runtime_provenance"]["dispatch"]["mismatch_reasons"])
            self.assertIn("reload/restart the PM Copilot plugin once", result["error"])
            execute.assert_not_called()

    def test_stale_cached_wrapper_blocks_answer_before_controller_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "run"
            folder.mkdir()
            self.write_state(folder, status="needs_input", termination="needs_input")
            runtime, wrapper = self.write_runtime(
                root,
                "6.2.104",
                "6.2.103+codex.old",
                canonical_plugin_version="6.2.104+codex.current",
            )
            controller = folder / "controller.py"
            controller.write_text("# mocked controller\n", encoding="utf-8")
            with patch.object(MCP, "RUNTIME_HOME", runtime), patch.object(MCP, "WRAPPER_SCRIPT", wrapper), patch.object(
                MCP, "CONTROLLER", controller,
            ), patch.object(MCP.subprocess, "run") as execute:
                result = MCP.submit_answer(str(folder), "继续")

            self.assertFalse(result["ok"])
            self.assertEqual(result["error_code"], "restart_required")
            execute.assert_not_called()

    def test_same_semver_different_cache_build_blocks_controller_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "run"
            folder.mkdir()
            self.write_state(folder)
            runtime, wrapper = self.write_runtime(
                root,
                "6.2.104",
                "6.2.104+codex.old-build",
                canonical_plugin_version="6.2.104+codex.new-build",
            )
            controller = folder / "controller.py"
            controller.write_text("# mocked controller\n", encoding="utf-8")
            with patch.object(MCP, "RUNTIME_HOME", runtime), patch.object(MCP, "WRAPPER_SCRIPT", wrapper), patch.object(
                MCP, "CONTROLLER", controller,
            ), patch.object(MCP.subprocess, "run") as execute:
                result = MCP.confirm_delivery(str(folder))

            self.assertFalse(result["ok"])
            self.assertIn("wrapper_build_mismatch", result["runtime_provenance"]["dispatch"]["mismatch_reasons"])
            self.assertIn("wrapper_manifest_mismatch", result["runtime_provenance"]["dispatch"]["mismatch_reasons"])
            execute.assert_not_called()

    def test_same_build_different_wrapper_content_blocks_controller_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "run"
            folder.mkdir()
            self.write_state(folder)
            runtime, wrapper = self.write_runtime(
                root,
                "6.2.104",
                "6.2.104+codex.same-build",
                wrapper_contents="# old cached bridge\n",
                canonical_wrapper_contents="# new canonical bridge\n",
            )
            controller = folder / "controller.py"
            controller.write_text("# mocked controller\n", encoding="utf-8")
            with patch.object(MCP, "RUNTIME_HOME", runtime), patch.object(MCP, "WRAPPER_SCRIPT", wrapper), patch.object(
                MCP, "CONTROLLER", controller,
            ), patch.object(MCP.subprocess, "run") as execute:
                result = MCP.confirm_delivery(str(folder))

            self.assertFalse(result["ok"])
            self.assertIn("wrapper_content_mismatch", result["runtime_provenance"]["dispatch"]["mismatch_reasons"])
            execute.assert_not_called()

    def test_matching_cached_identity_allows_controller_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "run"
            folder.mkdir()
            self.write_state(folder)
            runtime, wrapper = self.write_runtime(root, "6.2.104", "6.2.104+codex.current")
            controller = folder / "controller.py"
            controller.write_text("# mocked controller\n", encoding="utf-8")
            completed = type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            with patch.object(MCP, "RUNTIME_HOME", runtime), patch.object(MCP, "WRAPPER_SCRIPT", wrapper), patch.object(
                MCP, "CONTROLLER", controller,
            ), patch.object(MCP.subprocess, "run", return_value=completed) as execute:
                result = MCP.confirm_delivery(str(folder))

            self.assertTrue(result["ok"])
            self.assertFalse(result["runtime_restart_required"])
            execute.assert_called_once()

    def test_stale_cached_status_is_diagnostic_and_never_invokes_controller(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "run"
            folder.mkdir()
            self.write_state(folder)
            runtime, wrapper = self.write_runtime(
                root,
                "6.2.104",
                "6.2.103+codex.old",
                canonical_plugin_version="6.2.104+codex.current",
            )
            with patch.object(MCP, "RUNTIME_HOME", runtime), patch.object(MCP, "WRAPPER_SCRIPT", wrapper), patch.object(
                MCP.subprocess, "run",
            ) as execute:
                result = MCP.run_summary(str(folder))

            self.assertTrue(result["ok"])
            self.assertTrue(result["runtime_restart_required"])
            self.assertFalse(result["runtime_provenance"]["dispatch"]["current"])
            execute.assert_not_called()

    def test_confirm_forwards_confirmed_needs_input_to_the_controller(self) -> None:
        """Only the controller can distinguish a legacy repair pause from real input."""
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.write_state(
                folder,
                status="needs_input",
                termination="needs_input",
                user_confirmation={"confirmed": True},
                required_input={"field": "input_assets", "question": "重新附加图片"},
            )
            expected = {"ok": True, "status": "needs_input", "controller_exit_code": 3}
            with patch.object(MCP, "_invoke", return_value=expected) as invoke:
                result = MCP.confirm_delivery(str(folder))

            self.assertEqual(result, expected)
            invoke.assert_called_once_with(str(folder), ["--confirm"])

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

    def test_status_recovers_a_dead_controller_lease_and_persists_the_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "run"
            folder.mkdir()
            self.write_state(
                folder,
                status="delivery",
                termination="running",
                controller_pid=12345,
                user_confirmation={"confirmed": True},
                artifacts=["discussion.md", "confirmed-requirements.md"],
            )
            (folder / "confirmed-requirements.md").write_text("# confirmed\n", encoding="utf-8")
            (folder / "prd.md").write_text("# PRD\n", encoding="utf-8")

            with patch.object(MCP, "_controller_pid_alive", return_value=False) as pid_alive:
                first = MCP.run_summary(str(folder))

            self.assertTrue(first["ok"])
            self.assertEqual(first["status"], "recovery_required")
            self.assertEqual(first["termination"], "interrupted")
            self.assertEqual(first["recovery"]["status"], "retry_required")
            self.assertEqual(first["recovery"]["controller_pid"], 12345)
            self.assertEqual(first["recovery"]["retry_entry"], "--confirm")
            self.assertEqual(
                first["recovery"]["promoted_artifacts"],
                ["confirmed-requirements.md", "prd.md"],
            )
            pid_alive.assert_called_once()

            persisted_path = folder / "interactive-run.json"
            persisted = json.loads(persisted_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "recovery_required")
            self.assertEqual(persisted["termination"], "interrupted")
            self.assertEqual(persisted["recovery"], first["recovery"])

            second = MCP.run_summary(str(folder))
            self.assertEqual(second["status"], "recovery_required")
            self.assertEqual(second["recovery"], first["recovery"])
            self.assertEqual(
                json.loads(persisted_path.read_text(encoding="utf-8"))["recovery"],
                first["recovery"],
            )

    def test_status_leaves_an_active_controller_lease_running(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "run"
            folder.mkdir()
            self.write_state(
                folder,
                status="delivery",
                termination="running",
                controller_pid=12345,
                user_confirmation={"confirmed": True},
            )

            with patch.object(MCP, "_controller_pid_alive", return_value=True) as pid_alive:
                summary = MCP.run_summary(str(folder))

            self.assertEqual(summary["status"], "delivery")
            self.assertEqual(summary["termination"], "running")
            self.assertIsNone(summary["recovery"])
            pid_alive.assert_called_once()
            persisted = json.loads((folder / "interactive-run.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "delivery")
            self.assertEqual(persisted["termination"], "running")

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
