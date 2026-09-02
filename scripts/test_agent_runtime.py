#!/usr/bin/env python3
"""Deterministic regression tests for local Agent Runtime discovery and dispatch."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import agent_runtime
from model_catalog import ModelOption
from runtime_policy import DEFAULT_SEAWORK_MODEL


def runtime(provider: str, status: str = "ready") -> agent_runtime.RuntimeStatus:
    return agent_runtime.RuntimeStatus(
        provider=provider,
        executable=f"/{provider}",
        status=status,
        supports_detached=provider in {"seawork", "seawork-claude"},
        supports_structured_output=True,
        supports_verifier=provider in {"seawork", "seawork-claude"},
        detail="test runtime",
    )


class AgentRuntimeTest(unittest.TestCase):
    def test_auto_uses_the_active_runtime(self) -> None:
        statuses = [runtime("seawork"), runtime("codex"), runtime("claude")]
        with patch("agent_runtime.discover_runtimes", return_value=statuses), patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime("codex", "gpt-5.6", "active test session"),
        ):
            self.assertEqual(agent_runtime.select_runtime().provider, "codex")

    def test_auto_does_not_assume_a_runtime_without_a_session_signal(self) -> None:
        statuses = [runtime("seawork"), runtime("codex"), runtime("claude")]
        with patch("agent_runtime.discover_runtimes", return_value=statuses), patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime(None, None, "no signal"),
        ):
            with self.assertRaisesRegex(RuntimeError, "no active local agent runtime"):
                agent_runtime.select_runtime()

    def test_auto_uses_seawork_for_a_seawork_backed_session(self) -> None:
        statuses = [runtime("seawork"), runtime("codex"), runtime("claude")]
        with patch("agent_runtime.discover_runtimes", return_value=statuses), patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime("seawork", "codex/gpt-5.6", "active test session"),
        ):
            self.assertEqual(agent_runtime.select_runtime().provider, "seawork")

    def test_auto_rejects_an_unavailable_active_runtime(self) -> None:
        statuses = [runtime("seawork", "degraded"), runtime("codex"), runtime("claude")]
        with patch("agent_runtime.discover_runtimes", return_value=statuses), patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime("seawork", None, "active test session"),
        ):
            with self.assertRaisesRegex(RuntimeError, "no active local agent runtime"):
                agent_runtime.select_runtime()

    def test_seawork_session_falls_back_to_its_active_model_family(self) -> None:
        statuses = [runtime("seawork", "degraded"), runtime("codex"), runtime("claude")]
        with patch("agent_runtime.discover_runtimes", return_value=statuses), patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime("seawork", "codex/gpt-5.6-sol", "active test session"),
        ):
            self.assertEqual(agent_runtime.select_runtime().provider, "codex")

    def test_rejects_unverified_adapter(self) -> None:
        statuses = [runtime("opencode", "detected_unverified")]
        with patch("agent_runtime.discover_runtimes", return_value=statuses), patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime("seawork", "codex/gpt-5.6", "active test session"),
        ):
            with self.assertRaisesRegex(RuntimeError, "not ready"):
                agent_runtime.select_runtime("opencode")

    def test_seawork_dry_run_uses_worker_contract(self) -> None:
        statuses = [runtime("seawork")]
        with patch("agent_runtime.discover_runtimes", return_value=statuses):
            result = agent_runtime.execute(
                "seawork", "inspect only", Path.cwd(), 2, "codex/user-model", None, True
            )
        self.assertEqual(result["status"], "planned")
        self.assertEqual(result["provider"], "seawork")
        self.assertIn("--mode", result["command"])
        self.assertIn("[PROMPT REDACTED]", result["command"])

    def test_seawork_requires_a_declared_model(self) -> None:
        command = agent_runtime.build_command(
            "seawork", "/seawork", "inspect", Path.cwd(), 1, "codex/user-model", None, None,
        )
        self.assertEqual(command[command.index("--provider") + 1], "codex/user-model")

    def test_seawork_execution_blocks_without_a_discovered_model(self) -> None:
        with patch("agent_runtime.discover_runtimes", return_value=[runtime("seawork")]), patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime(None, None, "no active model"),
        ), patch("agent_runtime.discover_model_catalog", return_value=([], [])):
            result = agent_runtime.execute("seawork", "inspect only", Path.cwd(), 1, None, None, True)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["failure_category"], "no_available_model")

    def test_seawork_uses_the_discovered_model_before_building_a_command(self) -> None:
        terra = ModelOption(
            "codex/gpt-5.6-terra", "seawork", frozenset({"judgment", "standard"}),
            "seawork-provider-discovery", 2,
        )
        with patch("agent_runtime.discover_runtimes", return_value=[runtime("seawork")]), patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime(None, None, "no active model"),
        ), patch("agent_runtime.discover_model_catalog", return_value=([terra], [])):
            result = agent_runtime.execute("seawork", "inspect only", Path.cwd(), 1, None, None, True)
        self.assertEqual(result["status"], "planned")
        self.assertEqual(result["model"], "codex/gpt-5.6-terra")
        self.assertEqual(result["command"][result["command"].index("--provider") + 1], "codex/gpt-5.6-terra")

    def test_seawork_claude_dry_run_uses_daemon_managed_claude(self) -> None:
        statuses = [runtime("seawork-claude")]
        with patch("agent_runtime.discover_runtimes", return_value=statuses):
            result = agent_runtime.execute(
                "seawork-claude", "inspect only", Path.cwd(), 2, "sonnet", None, True
            )
        self.assertEqual(result["provider"], "seawork-claude")
        self.assertEqual(result["model"], "sonnet")
        self.assertIn("bypassPermissions", result["command"])
        self.assertIn("claude", result["command"])
        self.assertIn("--model", result["command"])

    def test_codex_command_uses_schema_file_and_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            schema = root / "schema.json"
            output = root / "result.txt"
            schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")
            command = agent_runtime.build_command(
                "codex", "/codex", "inspect", root, 2, "gpt-5.4", str(schema), output
            )
        self.assertIn("--output-schema", command)
        self.assertIn("--output-last-message", command)
        self.assertIn("--ephemeral", command)
        self.assertNotIn("--ignore-user-config", command)
        self.assertIn("--skip-git-repo-check", command)
        self.assertEqual(command.count("--disable"), 2)
        self.assertIn("plugins", command)
        self.assertIn("remote_plugin", command)
        self.assertIn('model_reasoning_effort="minimal"', command)
        self.assertIn("gpt-5.4", command)

    def test_codex_environment_isolated_reuses_auth_and_minimizes_config(self) -> None:
        with tempfile.TemporaryDirectory() as source_directory:
            source = Path(source_directory)
            (source / "auth.json").write_text("secret", encoding="utf-8")
            (source / "config.toml").write_text(
                'model_provider = "custom"\n[model_providers.custom]\nbase_url = "https://example.test"\n[plugins.demo]\nenabled = true\n',
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"CODEX_HOME": str(source)}):
                with agent_runtime._isolated_codex_environment() as environment:
                    isolated = Path(environment["CODEX_HOME"])
                    self.assertNotEqual(isolated, source)
                    self.assertTrue((isolated / "auth.json").is_symlink())
                    self.assertFalse((isolated / "config.toml").is_symlink())
                    self.assertEqual(
                        os.path.realpath(isolated / "auth.json"),
                        os.path.realpath(source / "auth.json"),
                    )
                    config = (isolated / "config.toml").read_text(encoding="utf-8")
                    self.assertIn("[model_providers.custom]", config)
                    self.assertIn('model_reasoning_effort = "minimal"', config)
                    self.assertIn("plugins = false", config)
                    self.assertIn("remote_plugin = false", config)
                    self.assertNotIn("plugins.demo", config)
                self.assertFalse(isolated.exists())

    def test_domestic_cli_commands_use_documented_headless_modes(self) -> None:
        expected = {
            "qwen": ["--prompt", "--output-format", "json"],
            "kimi": ["--prompt", "--output-format", "stream-json"],
            "qoder": ["-p", "--output-format", "json"],
            "codebuddy": ["-p"],
        }
        for provider, required_tokens in expected.items():
            command = agent_runtime.build_command(
                provider, f"/{provider}", "inspect", Path.cwd(), 2, None, None, None
            )
            for token in required_tokens:
                self.assertIn(token, command, provider)

    def test_active_domestic_runtime_is_selected(self) -> None:
        statuses = [runtime("qwen"), runtime("codex")]
        with patch("agent_runtime.discover_runtimes", return_value=statuses), patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime("qwen", "qwen3-coder", "active Qwen session"),
        ):
            self.assertEqual(agent_runtime.select_runtime().provider, "qwen")

    def test_redacts_common_credentials(self) -> None:
        cleaned = agent_runtime._clean("token=secret-value authorization: BearerSecret")
        self.assertNotIn("secret-value", cleaned)
        self.assertNotIn("BearerSecret", cleaned)
        self.assertIn("[REDACTED]", cleaned)

    def test_diagnostic_keeps_terminal_failure_and_redacts_it(self) -> None:
        diagnostic = agent_runtime._diagnostic(
            "warning\n" * 500 + "token=terminal-secret\nfinal runtime failure", 300
        )
        self.assertIn("final runtime failure", diagnostic)
        self.assertNotIn("terminal-secret", diagnostic)

    def test_rejects_credentials_in_prompt(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "must not contain credentials"):
            agent_runtime._reject_credential_prompt("api_key=do-not-pass-this")

    def test_allows_authorization_policy_language_without_a_credential(self) -> None:
        agent_runtime._reject_credential_prompt("Client-only authorization: rejected by the security policy.")

    def test_seawork_loop_dry_run_is_bounded_and_redacted(self) -> None:
        with patch("agent_runtime.discover_runtimes", return_value=[runtime("seawork")]), patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime("seawork", "codex/gpt-5.6", "active test session"),
        ):
            result = agent_runtime.execute_loop(
                "worker secret", "verify secret", Path.cwd(), 3, 2, None, "claude/opus", True
            )
        self.assertEqual(result["status"], "planned")
        self.assertIn("--max-iterations", result["command"])
        self.assertIn("[WORKER PROMPT REDACTED]", result["command"])
        self.assertIn("[VERIFIER PROMPT REDACTED]", result["command"])

    def test_timeout_terminates_descendant_processes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            child_pid = Path(temporary_directory) / "child.pid"
            script = (
                "import subprocess, sys, time; "
                "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
                f"open({str(child_pid)!r}, 'w').write(str(child.pid)); "
                "time.sleep(30)"
            )
            with self.assertRaises(subprocess.TimeoutExpired):
                agent_runtime._run([sys.executable, "-c", script], timeout=0.1)
            pid = int(child_pid.read_text(encoding="utf-8"))
            time.sleep(0.1)
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)

    def test_timeout_ends_a_process_that_never_returns_on_its_own(self) -> None:
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            agent_runtime._run(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                timeout=0.1,
            )
        self.assertLess(
            time.monotonic() - started,
            3,
            "the runtime must end a process that never returns on its own",
        )

    def test_write_first_progress_budget_stops_direct_runtime_before_total_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.md"
            with self.assertRaises(subprocess.TimeoutExpired):
                agent_runtime._run(
                    [sys.executable, "-c", "import time; time.sleep(30)"],
                    timeout=30, progress_path=target, no_progress_timeout=0.1,
                )

    def test_stage_target_accepts_dot_prefixed_artifact_and_review_paths(self) -> None:
        artifact = "Write exactly one complete artifact at /tmp/.delivery-stage/example.stage/run-log.yaml.\n"
        review = "Write ONLY one JSON object to /tmp/.delivery-stage/example/.stage-review.json (UTF-8):"
        self.assertEqual(
            agent_runtime._stage_target_from_command(["codex", artifact]),
            Path("/tmp/.delivery-stage/example.stage/run-log.yaml"),
        )
        self.assertEqual(
            agent_runtime._stage_target_from_command(["codex", review]),
            Path("/tmp/.delivery-stage/example/.stage-review.json"),
        )

    def test_written_artifact_bounds_a_stalled_agent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.md"
            script = f"from pathlib import Path; import time; Path({str(target)!r}).write_text('done'); time.sleep(30)"
            started = time.monotonic()
            with self.assertRaises(subprocess.TimeoutExpired):
                agent_runtime._run([sys.executable, "-c", script], timeout=30, progress_path=target, no_progress_timeout=1)
            self.assertLess(time.monotonic() - started, 8)

    def test_keyboard_interrupt_terminates_child_process_group(self) -> None:
        child_pid = None
        with tempfile.TemporaryDirectory() as temporary_directory:
            marker = Path(temporary_directory) / "child.pid"
            script = (
                "import subprocess,sys,time; "
                "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
                f"open({str(marker)!r},'w').write(str(child.pid)); time.sleep(30)"
            )
            with patch("agent_runtime.time.sleep", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    agent_runtime._run([sys.executable, "-c", script], timeout=30)
            # The interrupt may arrive before the child marker is written;
            # when it is written, it must no longer be alive.
            if marker.exists():
                child_pid = int(marker.read_text(encoding="utf-8"))
                with self.assertRaises(ProcessLookupError):
                    os.kill(child_pid, 0)

    def test_run_does_not_leave_stdin_open(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            marker = Path(temporary_directory) / "stdin.txt"
            script = f"import sys; open({str(marker)!r}, 'w').write(sys.stdin.read())"
            result = agent_runtime._run([sys.executable, "-c", script], timeout=2)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(encoding="utf-8"), "")

    def test_seawork_detached_execution_records_agent_id(self) -> None:
        launched = subprocess.CompletedProcess([], 0, "e5fb49d8-5227-4a93-bba3-ded9b613bab5\n", "")
        record = subprocess.CompletedProcess([], 0, '[{"id":"e5fb49d8-5227-4a93-bba3-ded9b613bab5","provider":"claude/sonnet","status":"running"}]', "")
        terminal_record = subprocess.CompletedProcess([], 0, '[{"id":"e5fb49d8-5227-4a93-bba3-ded9b613bab5","provider":"claude/sonnet","status":"idle"}]', "")
        completed = subprocess.CompletedProcess([], 0, "completed", "")
        with patch("agent_runtime.discover_runtimes", return_value=[runtime("seawork-claude")]), patch(
            "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
        ), patch("agent_runtime._run", side_effect=[launched, record, terminal_record, completed]) as run:
            result = agent_runtime.execute("seawork-claude", "inspect only", Path.cwd(), 2, "sonnet", None, False)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["agent_id"], "e5fb49d8-5227-4a93-bba3-ded9b613bab5")
        self.assertIn("--detach", run.call_args_list[0].args[0])
        self.assertEqual(len(run.call_args_list), 3)
        self.assertEqual(result["output"], "Agent e5fb49d8-5227-4a93-bba3-ded9b613bab5 reached terminal control-plane state idle.")

    def test_seawork_codex_model_is_verified_exactly(self) -> None:
        launched = subprocess.CompletedProcess([], 0, "e5fb49d8-5227-4a93-bba3-ded9b613bab5\n", "")
        record = subprocess.CompletedProcess([], 0, '[{"id":"e5fb49d8-5227-4a93-bba3-ded9b613bab5","provider":"codex/gpt-5.6-sol","status":"running"}]', "")
        terminal_record = subprocess.CompletedProcess([], 0, '[{"id":"e5fb49d8-5227-4a93-bba3-ded9b613bab5","provider":"codex/gpt-5.6-sol","status":"idle"}]', "")
        with patch("agent_runtime.discover_runtimes", return_value=[runtime("seawork")]), patch(
            "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
        ), patch("agent_runtime._run", side_effect=[launched, record, terminal_record]) as run:
            result = agent_runtime.execute("seawork", "inspect only", Path.cwd(), 1, "codex/gpt-5.6-sol", None, False)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["requested_model"], "codex/gpt-5.6-sol")
        self.assertEqual(result["actual_model"], "codex/gpt-5.6-sol")
        self.assertEqual(len(run.call_args_list), 3)

    def test_seawork_can_disable_the_first_write_watchdog_for_content_work(self) -> None:
        launched = subprocess.CompletedProcess([], 0, "e5fb49d8-5227-4a93-bba3-ded9b613bab5\n", "")
        record = subprocess.CompletedProcess([], 0, '[{"id":"e5fb49d8-5227-4a93-bba3-ded9b613bab5","provider":"codex/gpt-5.6-terra","status":"running"}]', "")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "run-log.yaml"
            prompt = f"Write exactly one complete artifact at {target}."
            with patch("agent_runtime.discover_runtimes", return_value=[runtime("seawork")]), patch(
                "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
            ), patch("agent_runtime._poll_seawork_terminal", return_value=(True, "idle")) as poll, patch(
                "agent_runtime._run", side_effect=[launched, record]
            ):
                result = agent_runtime.execute(
                    "seawork", prompt, Path(temporary), 5, "codex/gpt-5.6-terra", None, False,
                    first_artifact_seconds=None,
                )
        self.assertEqual(result["status"], "complete")
        self.assertIsNone(poll.call_args.args[5])

    def test_seawork_timeout_retains_unconfirmed_agent_for_manual_recovery(self) -> None:
        launched = subprocess.CompletedProcess([], 0, "e5fb49d8-5227-4a93-bba3-ded9b613bab5\n", "")
        record = subprocess.CompletedProcess([], 0, '[{"id":"e5fb49d8-5227-4a93-bba3-ded9b613bab5","provider":"claude/sonnet","status":"running"}]', "")
        stopped = subprocess.CompletedProcess([], 0, "INTERRUPTED", "")
        running = subprocess.CompletedProcess([], 0, '[{"id":"e5fb49d8-5227-4a93-bba3-ded9b613bab5","status":"running"}]', "")
        timeout = subprocess.TimeoutExpired(["seawork", "wait"], 120)
        with patch("agent_runtime.discover_runtimes", return_value=[runtime("seawork-claude")]), patch(
            "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
        ), patch("agent_runtime._poll_seawork_terminal", return_value=(False, "running")), patch(
            "agent_runtime._run", side_effect=[launched, record, running, stopped, running]
        ):
            result = agent_runtime.execute("seawork-claude", "inspect only", Path.cwd(), 2, "sonnet", None, False)
        self.assertEqual(result["status"], "orphaned")
        self.assertTrue(result["cleanup_blocked"])
        self.assertIn("control-plane state was running", result["error"])

    def test_seawork_accepts_written_artifact_after_terminal_state_refresh(self) -> None:
        launched = subprocess.CompletedProcess([], 0, "e5fb49d8-5227-4a93-bba3-ded9b613bab5\n", "")
        running = subprocess.CompletedProcess([], 0, '[{"id":"e5fb49d8-5227-4a93-bba3-ded9b613bab5","provider":"codex/gpt-5.6-terra","status":"running"}]', "")
        idle = subprocess.CompletedProcess([], 0, '[{"id":"e5fb49d8-5227-4a93-bba3-ded9b613bab5","provider":"codex/gpt-5.6-terra","status":"idle"}]', "")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.md"
            target.write_text("# previous attempt\n", encoding="utf-8")
            prompt = f"Write exactly one complete artifact at {target}."
            follow_up_calls = [running, idle]
            def run_after_launch(command, *args, **kwargs):
                if command[1] == "run":
                    target.write_text("# complete\n", encoding="utf-8")
                    return launched
                return follow_up_calls.pop(0)
            with patch("agent_runtime.discover_runtimes", return_value=[runtime("seawork")]), patch(
                "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
            ), patch("agent_runtime._poll_seawork_terminal", return_value=(False, "running")), patch(
                "agent_runtime._run", side_effect=run_after_launch
            ) as run:
                result = agent_runtime.execute("seawork", prompt, Path(temporary), 1, "codex/gpt-5.6-terra", None, False)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["completion_basis"], "artifact_checkpoint_after_control_plane_refresh")
        self.assertEqual(result["control_plane_refresh_state"], "idle")
        self.assertEqual(len(run.call_args_list), 3)

    def test_idle_seawork_agent_is_safe_after_timeout_stop(self) -> None:
        launched = subprocess.CompletedProcess([], 0, "e5fb49d8-5227-4a93-bba3-ded9b613bab5\n", "")
        record = subprocess.CompletedProcess([], 0, '[{"id":"e5fb49d8-5227-4a93-bba3-ded9b613bab5","provider":"claude/sonnet","status":"running"}]', "")
        running = subprocess.CompletedProcess([], 0, '[{"id":"e5fb49d8-5227-4a93-bba3-ded9b613bab5","status":"running"}]', "")
        stopped = subprocess.CompletedProcess([], 0, "INTERRUPTED", "")
        idle = subprocess.CompletedProcess([], 0, '[{"id":"e5fb49d8-5227-4a93-bba3-ded9b613bab5","status":"idle"}]', "")
        timeout = subprocess.TimeoutExpired(["seawork", "wait"], 120)
        with patch("agent_runtime.discover_runtimes", return_value=[runtime("seawork-claude")]), patch(
            "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
        ), patch("agent_runtime._poll_seawork_terminal", return_value=(False, "running")), patch(
            "agent_runtime._run", side_effect=[launched, record, running, stopped, idle]
        ):
            result = agent_runtime.execute("seawork-claude", "inspect only", Path.cwd(), 2, "sonnet", None, False)
        self.assertEqual(result["status"], "timed_out")
        self.assertNotIn("cleanup_blocked", result)

    def test_seawork_accepts_changed_artifact_when_stop_observes_idle(self) -> None:
        launched = subprocess.CompletedProcess([], 0, "e5fb49d8-5227-4a93-bba3-ded9b613bab5\n", "")
        running = subprocess.CompletedProcess([], 0, '[{"id":"e5fb49d8-5227-4a93-bba3-ded9b613bab5","provider":"codex/gpt-5.6-terra","status":"running"}]', "")
        stopped = subprocess.CompletedProcess([], 0, "INTERRUPTED", "")
        idle = subprocess.CompletedProcess([], 0, '[{"id":"e5fb49d8-5227-4a93-bba3-ded9b613bab5","provider":"codex/gpt-5.6-terra","status":"idle"}]', "")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.md"
            target.write_text("before\n", encoding="utf-8")
            prompt = f"Write exactly one complete artifact at {target}."
            calls = [running, running, stopped, idle]

            def run_after_launch(command, *args, **kwargs):
                if command[1] == "run":
                    target.write_text("after\n", encoding="utf-8")
                    return launched
                return calls.pop(0)

            with patch("agent_runtime.discover_runtimes", return_value=[runtime("seawork")]), patch(
                "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
            ), patch("agent_runtime._poll_seawork_terminal", return_value=(False, "running")), patch(
                "agent_runtime._run", side_effect=run_after_launch
            ):
                result = agent_runtime.execute("seawork", prompt, Path(temporary), 1, "codex/gpt-5.6-terra", None, False)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["completion_basis"], "artifact_checkpoint_after_stop")
        self.assertEqual(result["agent_state_after_stop"], "idle")

    def test_seawork_stops_after_the_write_first_progress_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.md"
            with patch("agent_runtime._seawork_agent_record", return_value=(None, "running")), patch(
                "agent_runtime.time.monotonic", side_effect=[0, 0, 31]
            ), patch("agent_runtime.time.sleep"):
                terminal, status = agent_runtime._poll_seawork_terminal("seawork", "agent", 900, target)
        self.assertFalse(terminal)
        self.assertEqual(status, "no_progress_before_first_artifact")

    def test_seawork_stops_after_repeated_control_plane_failures(self) -> None:
        with patch("agent_runtime._seawork_agent_record", return_value=(None, "could not query Agent state: offline")), patch(
            "agent_runtime.time.sleep"
        ):
            terminal, status = agent_runtime._poll_seawork_terminal("seawork", "agent", 900)
        self.assertFalse(terminal)
        self.assertEqual(status, "control_plane_unavailable")

    def test_transport_and_detached_agent_timeouts_use_fallback(self) -> None:
        self.assertTrue(agent_runtime._requires_direct_codex_fallback({"failure_category": "agent_no_progress"}))
        self.assertTrue(agent_runtime._requires_direct_codex_fallback({"failure_category": "seawork_control_plane_timeout"}))
        self.assertTrue(agent_runtime._requires_direct_codex_fallback({"failure_category": "agent_timeout"}))

    def test_transport_fallback_uses_a_distinct_locally_discovered_model(self) -> None:
        options = [ModelOption("codex/gpt-backup", "seawork", frozenset({"judgment"}), "seawork-provider-discovery", 1)]
        with patch("agent_runtime._transport_fallback_candidates", return_value=[("seawork", "codex/gpt-backup", "seawork-provider-discovery")]), patch(
            "agent_runtime.execute", return_value={"provider": "seawork", "model": "codex/gpt-backup", "status": "complete"},
        ) as execute:
            result = agent_runtime._fallback_from_transport(
                {"provider": "codex", "model": "gpt-primary", "error": "stream disconnected"},
                "write", Path.cwd(), 3, 100, None,
            )
        self.assertEqual(execute.call_args.args[0], "seawork")
        self.assertEqual(execute.call_args.args[4], "codex/gpt-backup")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["fallback_from"]["model"], "gpt-primary")

    def test_transport_candidates_include_an_authenticated_cli_default(self) -> None:
        statuses = [runtime("codex"), runtime("claude")]
        def catalog(provider, cwd):
            if provider == "claude":
                return [ModelOption(None, "claude", frozenset({"configured_default"}), "provider-default")], []
            return [ModelOption("gpt-primary", "codex", frozenset({"standard"}), "test")], []
        with patch("agent_runtime.discover_runtimes", return_value=statuses), patch(
            "agent_runtime.discover_model_catalog", side_effect=catalog,
        ):
            candidates = agent_runtime._transport_fallback_candidates("codex", "gpt-primary", Path.cwd())
        self.assertIn(("claude", None, "provider-default"), candidates)

    def test_direct_codex_no_progress_retains_redacted_terminal_diagnostics(self) -> None:
        timeout = subprocess.TimeoutExpired(["codex"], 30, output="partial", stderr="token=secret upstream stalled")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.md"
            with patch("agent_runtime.discover_runtimes", return_value=[runtime("codex")]), patch(
                "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
            ), patch(
                "agent_runtime.discover_model_catalog",
                return_value=([ModelOption("test-model", "codex", frozenset({"standard"}), "test")], []),
            ), patch("agent_runtime._run", side_effect=timeout):
                result = agent_runtime.execute(
                    "codex", f"Write exactly one complete artifact at {target}.", Path(temporary), 1, None, None, False,
                )
        self.assertEqual(result["failure_category"], "agent_no_progress")
        self.assertIn("no first artifact", result["error"])
        self.assertIn("partial", result["output"])
        self.assertNotIn("secret", result["error"])

    def test_direct_codex_preserves_a_written_artifact_after_post_write_timeout(self) -> None:
        timeout = subprocess.TimeoutExpired(["codex"], 30, output="", stderr="finalizing")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.md"
            with patch("agent_runtime.discover_runtimes", return_value=[runtime("codex")]), patch(
                "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
            ), patch(
                "agent_runtime.discover_model_catalog",
                return_value=([ModelOption("test-model", "codex", frozenset({"standard"}), "test")], []),
            ), patch("agent_runtime._run", side_effect=lambda *args, **kwargs: (target.write_text("complete handoff", encoding="utf-8"), (_ for _ in ()).throw(timeout))[1]):
                result = agent_runtime.execute(
                    "codex", f"Write exactly one complete artifact at {target}.", Path(temporary), 1, None, None, False,
                )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["failure_category"], "agent_post_write_timeout")
        self.assertEqual(result["completion_basis"], "artifact_checkpoint_before_process_timeout")
        self.assertTrue(result["post_write_timeout"])

    def test_direct_codex_does_not_accept_an_unchanged_prebuilt_artifact(self) -> None:
        timeout = subprocess.TimeoutExpired(["codex"], 30, output="", stderr="stalled")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.md"
            target.write_text("scaffold", encoding="utf-8")
            with patch("agent_runtime.discover_runtimes", return_value=[runtime("codex")]), patch(
                "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
            ), patch(
                "agent_runtime.discover_model_catalog",
                return_value=([ModelOption("test-model", "codex", frozenset({"standard"}), "test")], []),
            ), patch("agent_runtime._run", side_effect=timeout):
                result = agent_runtime.execute(
                    "codex", f"Write exactly one complete artifact at {target}.", Path(temporary), 1, None, None, False,
                )
        self.assertEqual(result["status"], "timed_out")
        self.assertEqual(result["failure_category"], "agent_no_progress")

    def test_direct_codex_can_disable_the_first_write_watchdog_for_content_work(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.md"
            observed: dict[str, object] = {}
            def captures_watchdog(*args, **kwargs):
                observed["watchdog"] = kwargs.get("no_progress_timeout")
                return subprocess.CompletedProcess([], 0, "", "")
            with patch("agent_runtime.discover_runtimes", return_value=[runtime("codex")]), patch(
                "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
            ), patch(
                "agent_runtime.discover_model_catalog",
                return_value=([ModelOption("test-model", "codex", frozenset({"standard"}), "test")], []),
            ), patch("agent_runtime._run", side_effect=captures_watchdog):
                agent_runtime.execute(
                    "codex", f"Write exactly one complete artifact at {target}.", Path(temporary), 1,
                    None, None, False, first_artifact_seconds=None,
                )
        self.assertIsNone(observed["watchdog"])


if __name__ == "__main__":
    unittest.main()
