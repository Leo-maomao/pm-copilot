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
    def setUp(self) -> None:
        agent_runtime._reset_seawork_circuit()

    def tearDown(self) -> None:
        agent_runtime._reset_seawork_circuit()

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

    def test_auto_prefers_direct_codex_for_an_equivalent_seawork_session(self) -> None:
        statuses = [runtime("seawork"), runtime("codex"), runtime("claude")]
        with patch("agent_runtime.discover_runtimes", return_value=statuses), patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime("seawork", "codex/gpt-5.6", "active test session"),
        ):
            self.assertEqual(agent_runtime.select_runtime().provider, "codex")

    def test_active_runtime_uses_verified_direct_model_cache_without_seawork_listing(self) -> None:
        cwd = Path.cwd()
        agent_runtime._remember_direct_codex_model(cwd, "gpt-5.6-terra", "verified")
        with patch("agent_runtime._parent_commands", return_value=['model_provider="seawork"']), patch(
            "agent_runtime._run"
        ) as run, patch(
            "agent_runtime._ready_direct_codex_runtime", return_value=runtime("codex"),
        ):
            active = agent_runtime.active_runtime(cwd)
        self.assertEqual(active.runtime, "codex")
        self.assertEqual(active.model, "gpt-5.6-terra")
        self.assertIn("verified", active.source)
        self.assertFalse(any(call.args[0][:2] == ["seawork", "ls"] for call in run.call_args_list))

    def test_active_runtime_skips_all_seawork_control_plane_probes_while_circuit_is_open(self) -> None:
        cwd = Path.cwd()
        agent_runtime._open_seawork_circuit()
        with patch("agent_runtime._parent_commands", return_value=['model_provider="seawork"']), patch(
            "agent_runtime._declared_direct_codex_model", return_value=None,
        ), patch("agent_runtime._which", return_value="/seawork"), patch(
            "agent_runtime._run", side_effect=AssertionError("Seawork must not be probed while its circuit is open"),
        ):
            active = agent_runtime.active_runtime(cwd)
        self.assertEqual(active.runtime, "seawork")
        self.assertIsNone(active.model)
        self.assertIn("suppressed", active.source)

    def test_auto_selection_uses_direct_codex_without_runtime_discovery_while_circuit_is_open(self) -> None:
        agent_runtime._open_seawork_circuit()
        with patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime("seawork", None, "active Seawork session"),
        ), patch("agent_runtime._ready_direct_codex_runtime", return_value=runtime("codex")), patch(
            "agent_runtime.discover_runtimes", side_effect=AssertionError("Seawork discovery must be suppressed"),
        ):
            self.assertEqual(agent_runtime.select_runtime("auto").provider, "codex")

    def test_explicit_codex_runtime_probe_does_not_query_seawork(self) -> None:
        def which(name: str) -> str | None:
            if name == "seawork":
                raise AssertionError("explicit Codex selection must not probe Seawork")
            return "/codex" if name == "codex" else None

        with patch("agent_runtime._which", side_effect=which), patch(
            "agent_runtime._probe", return_value=(True, "Codex exec available"),
        ):
            selected = agent_runtime.select_runtime("codex")
        self.assertEqual(selected.provider, "codex")
        self.assertEqual(selected.status, "ready")

    def test_active_runtime_keeps_seawork_when_configured_codex_is_not_ready(self) -> None:
        with patch("agent_runtime._parent_commands", return_value=['model_provider="seawork"']), patch(
            "agent_runtime._declared_direct_codex_model", return_value="gpt-5.6-terra",
        ), patch("agent_runtime._ready_direct_codex_runtime", return_value=None):
            active = agent_runtime.active_runtime(Path.cwd())
        self.assertEqual(active.runtime, "seawork")
        statuses = [runtime("seawork"), runtime("codex", "degraded")]
        with patch("agent_runtime.active_runtime", return_value=active), patch(
            "agent_runtime.discover_runtimes", return_value=statuses,
        ):
            self.assertEqual(agent_runtime.select_runtime("auto").provider, "seawork")

    def test_explicit_seawork_remains_an_operator_override(self) -> None:
        statuses = [runtime("seawork"), runtime("codex"), runtime("claude")]
        with patch("agent_runtime.discover_runtimes", return_value=statuses), patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime("seawork", "codex/gpt-5.6", "active test session"),
        ):
            self.assertEqual(agent_runtime.select_runtime("seawork").provider, "seawork")

    def test_auto_keeps_seawork_when_the_active_model_is_not_direct_codex_equivalent(self) -> None:
        statuses = [runtime("seawork"), runtime("codex"), runtime("claude")]
        with patch("agent_runtime.discover_runtimes", return_value=statuses), patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime("seawork", "claude/sonnet", "active test session"),
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

    def test_auto_codex_first_execution_keeps_the_equivalent_model_and_is_not_a_failure_fallback(self) -> None:
        statuses = [runtime("seawork"), runtime("codex")]
        terra = ModelOption("gpt-5.6-terra", "codex", frozenset({"standard"}), "provider-config")
        with patch("agent_runtime.discover_runtimes", return_value=statuses), patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime("seawork", "codex/gpt-5.6-terra", "active test session"),
        ), patch("agent_runtime.discover_model_catalog", return_value=([terra], [])):
            result = agent_runtime.execute("auto", "write", Path.cwd(), 2, None, None, True)
        self.assertEqual(result["provider"], "codex")
        self.assertEqual(result["model"], "gpt-5.6-terra")
        self.assertNotIn("fallback_used", result)
        self.assertIn("Codex-first", result["runtime_selection_reason"])

    def test_open_circuit_keeps_auto_equivalent_codex_on_the_normal_direct_route(self) -> None:
        agent_runtime._open_seawork_circuit()
        terra = ModelOption("gpt-5.6-terra", "codex", frozenset({"standard"}), "provider-config")
        completed = subprocess.CompletedProcess([], 0, "", "")
        with patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime("seawork", "codex/gpt-5.6-terra", "active test session"),
        ), patch("agent_runtime.select_runtime", return_value=runtime("codex")), patch(
            "agent_runtime.discover_model_catalog", return_value=([terra], [])
        ), patch("agent_runtime._run", return_value=completed), patch(
            "agent_runtime._attempt_direct_codex_fallback"
        ) as fallback:
            result = agent_runtime.execute("auto", "write", Path.cwd(), 2, None, None, False)
        self.assertEqual(result["provider"], "codex")
        self.assertEqual(result["status"], "complete")
        self.assertNotIn("fallback_used", result)
        self.assertIn("Codex-first", result["runtime_selection_reason"])
        fallback.assert_not_called()

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

    def test_run_cleans_temporary_output_when_process_start_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = iter([root / "stdout.txt", root / "stderr.txt"])

            def temporary_file(*_args, **_kwargs):
                return next(paths).open("w+")

            with patch("agent_runtime.tempfile.NamedTemporaryFile", side_effect=temporary_file), patch(
                "agent_runtime.subprocess.Popen", side_effect=OSError("process start rejected")
            ):
                with self.assertRaisesRegex(OSError, "process start rejected"):
                    agent_runtime._run(["unavailable-runtime"], timeout=1)
            self.assertFalse((root / "stdout.txt").exists())
            self.assertFalse((root / "stderr.txt").exists())

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

    def test_seawork_agent_record_uses_narrow_inspect_query(self) -> None:
        agent_id = "e5fb49d8-5227-4a93-bba3-ded9b613bab5"
        inspected = subprocess.CompletedProcess(
            [], 0,
            json.dumps({"id": agent_id, "provider": "codex/gpt-5.6-terra", "status": "running"}),
            "",
        )
        with patch("agent_runtime._run", return_value=inspected) as run:
            record, status = agent_runtime._seawork_agent_record("seawork", agent_id)
        self.assertEqual(status, "running")
        self.assertEqual(record["provider"], "codex/gpt-5.6-terra")
        self.assertEqual(
            run.call_args.args[0],
            ["seawork", "inspect", agent_id, "--json"],
        )
        self.assertNotIn("ls", run.call_args.args[0])

    def test_seawork_agent_record_treats_unavailable_or_malformed_inspect_as_control_plane_failure(self) -> None:
        agent_id = "e5fb49d8-5227-4a93-bba3-ded9b613bab5"
        unavailable = subprocess.CompletedProcess(
            [], 1,
            '{"error":{"code":"DAEMON_NOT_RUNNING","message":"transport closed"}}',
            "",
        )
        malformed = subprocess.CompletedProcess([], 0, "not-json", "")
        with patch("agent_runtime._run", side_effect=[unavailable, malformed]):
            record, unavailable_status = agent_runtime._seawork_agent_record("seawork", agent_id)
            malformed_record, malformed_status = agent_runtime._seawork_agent_record("seawork", agent_id)
        self.assertIsNone(record)
        self.assertIsNone(malformed_record)
        self.assertTrue(unavailable_status.startswith("could not query Agent state:"), unavailable_status)
        self.assertTrue(malformed_status.startswith("could not query Agent state:"), malformed_status)

    def test_seawork_initial_control_plane_failure_is_not_a_model_mismatch(self) -> None:
        agent_id = "e5fb49d8-5227-4a93-bba3-ded9b613bab5"
        launched = subprocess.CompletedProcess([], 0, f"{agent_id}\n", "")
        unavailable = subprocess.CompletedProcess(
            [], 1,
            '{"error":{"code":"DAEMON_NOT_RUNNING","message":"transport closed"}}',
            "",
        )
        command = [
            "seawork", "run", "--provider", "codex/gpt-5.6-terra",
            "Write exactly one complete artifact at /tmp/seawork-control-plane.md.",
        ]
        with patch("agent_runtime._run", side_effect=[launched, unavailable]) as run:
            result = agent_runtime._execute_seawork(
                command, "seawork", Path.cwd(), 3,
                {"provider": "seawork", "model": "codex/gpt-5.6-terra"}, 100, None,
            )
        self.assertEqual(result["status"], "orphaned")
        self.assertEqual(result["failure_category"], "seawork_control_plane_unavailable")
        self.assertNotIn("model mismatch", result["error"].lower())
        self.assertEqual(len(run.call_args_list), 2)
        self.assertTrue(all("ls" not in call.args[0] for call in run.call_args_list))

    def test_seawork_missing_agent_converges_without_an_unverified_stop(self) -> None:
        agent_id = "e5fb49d8-5227-4a93-bba3-ded9b613bab5"
        launched = subprocess.CompletedProcess([], 0, f"{agent_id}\n", "")
        command = [
            "seawork", "run", "--provider", "codex/gpt-5.6-terra",
            "Write exactly one complete artifact at /tmp/seawork-missing-agent.md.",
        ]
        with patch("agent_runtime._run", return_value=launched) as run, patch(
            "agent_runtime._seawork_agent_record", return_value=(None, "missing"),
        ):
            result = agent_runtime._execute_seawork(
                command, "seawork", Path.cwd(), 3,
                {"provider": "seawork", "model": "codex/gpt-5.6-terra"}, 100, None,
            )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_category"], "seawork_agent_missing")
        self.assertEqual(result["agent_state_after_stop"], "missing")
        self.assertNotIn("cleanup_blocked", result)
        self.assertEqual(run.call_count, 1)

    def test_model_mismatch_stop_converges_when_agent_is_deleted(self) -> None:
        agent_id = "e5fb49d8-5227-4a93-bba3-ded9b613bab5"
        launched = subprocess.CompletedProcess([], 0, f"{agent_id}\n", "")
        mismatched = subprocess.CompletedProcess(
            [], 0,
            json.dumps({"id": agent_id, "provider": "codex/gpt-5.6-sol", "status": "running"}),
            "",
        )
        stopped = subprocess.CompletedProcess([], 0, "stopped", "")
        missing = subprocess.CompletedProcess([], 1, "", "agent_not_found")
        command = [
            "seawork", "run", "--provider", "codex/gpt-5.6-terra",
            "Write exactly one complete artifact at /tmp/seawork-model-mismatch.md.",
        ]
        with patch("agent_runtime._run", side_effect=[launched, mismatched, stopped, missing]):
            result = agent_runtime._execute_seawork(
                command, "seawork", Path.cwd(), 3,
                {"provider": "seawork", "model": "codex/gpt-5.6-terra"}, 100, None,
            )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["agent_state_after_stop"], "missing")
        self.assertNotIn("cleanup_blocked", result)

    def test_seawork_missing_agent_is_immediately_safe_for_a_local_fallback(self) -> None:
        failed = {
            "provider": "seawork",
            "model": "codex/gpt-5.6-terra",
            "agent_id": "e5fb49d8-5227-4a93-bba3-ded9b613bab5",
            "failure_category": "seawork_agent_missing",
            "agent_state_after_stop": "missing",
        }
        self.assertTrue(agent_runtime._opens_seawork_circuit(failed))
        self.assertTrue(agent_runtime._safe_to_direct_codex_fallback(failed))

    def test_seawork_health_cache_is_short_lived_and_only_caches_healthy_daemons(self) -> None:
        with patch("agent_runtime._probe", side_effect=[
            (True, "Connected Daemon reachable"),
            (True, "Connected Daemon reachable"),
        ]) as probe, patch("agent_runtime.time.monotonic", side_effect=[100.0, 100.01, 101.0, 102.1, 102.11]):
            self.assertTrue(agent_runtime._seawork_daemon_health("seawork")[0])
            self.assertTrue(agent_runtime._seawork_daemon_health("seawork")[0])
            self.assertTrue(agent_runtime._seawork_daemon_health("seawork")[0])
        self.assertEqual(probe.call_count, 2)

    def test_seawork_health_cache_starts_after_a_slow_probe(self) -> None:
        with patch("agent_runtime._probe", return_value=(True, "Connected Daemon reachable")) as probe, patch(
            "agent_runtime.time.monotonic", side_effect=[100.0, 103.0, 103.1],
        ):
            self.assertTrue(agent_runtime._seawork_daemon_health("seawork")[0])
            self.assertTrue(agent_runtime._seawork_daemon_health("seawork")[0])
        self.assertEqual(probe.call_count, 1)

    def test_seawork_health_does_not_cache_an_unavailable_daemon(self) -> None:
        with patch("agent_runtime._probe", side_effect=[
            (False, "daemon unreachable"),
            (True, "Connected Daemon reachable"),
        ]) as probe, patch("agent_runtime.time.monotonic", side_effect=[100.0, 100.1, 100.11]):
            self.assertFalse(agent_runtime._seawork_daemon_health("seawork")[0])
            self.assertTrue(agent_runtime._seawork_daemon_health("seawork")[0])
        self.assertEqual(probe.call_count, 2)

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

            def write_target_on_launch(command, *args, **kwargs):
                if command[1] == "run":
                    target.write_text("run_id: current-attempt\n", encoding="utf-8")
                    return launched
                return record

            with patch("agent_runtime.discover_runtimes", return_value=[runtime("seawork")]), patch(
                "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
            ), patch("agent_runtime._poll_seawork_terminal", return_value=(True, "idle")) as poll, patch(
                "agent_runtime._run", side_effect=write_target_on_launch
            ):
                result = agent_runtime.execute(
                    "seawork", prompt, Path(temporary), 5, "codex/gpt-5.6-terra", None, False,
                    first_artifact_seconds=None,
                )
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["artifact_checkpoint"])
        self.assertIsNone(poll.call_args.args[5])

    def test_idle_seawork_agent_without_artifact_change_fails(self) -> None:
        agent_id = "e5fb49d8-5227-4a93-bba3-ded9b613bab5"
        launched = subprocess.CompletedProcess([], 0, f"{agent_id}\n", "")
        running = subprocess.CompletedProcess(
            [], 0,
            json.dumps([{"id": agent_id, "provider": "codex/gpt-5.6-terra", "status": "running"}]),
            "",
        )
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.md"
            target.write_text("old staged artifact\n", encoding="utf-8")
            prompt = f"Write exactly one complete artifact at {target}."
            with patch("agent_runtime._run", side_effect=[launched, running]), patch(
                "agent_runtime._poll_seawork_terminal", return_value=(True, "idle")
            ):
                result = agent_runtime._execute_seawork(
                    ["seawork", "run", "--provider", "codex/gpt-5.6-terra", prompt],
                    "seawork", Path(temporary), 3,
                    {"provider": "seawork", "model": "codex/gpt-5.6-terra"}, 100, None,
                )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_category"], "agent_no_progress")
        self.assertFalse(result["artifact_checkpoint"])
        self.assertIn("without changing its promised artifact", result["error"])

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
        ), patch(
            "agent_runtime._attempt_safe_seawork_fallback", side_effect=lambda result, *_args: result,
        ):
            result = agent_runtime.execute("seawork-claude", "inspect only", Path.cwd(), 2, "sonnet", None, False)
        self.assertEqual(result["status"], "timed_out")
        self.assertNotIn("cleanup_blocked", result)

    def test_seawork_stop_after_timeout_never_accepts_a_partially_changed_artifact(self) -> None:
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
                    return launched
                if command[1] == "stop":
                    # Model a write that lands only while the timed-out
                    # Agent is being stopped. This is indistinguishable from
                    # a partial artifact and must never be promoted.
                    target.write_text("partial after timeout\n", encoding="utf-8")
                return calls.pop(0)

            with patch("agent_runtime.discover_runtimes", return_value=[runtime("seawork")]), patch(
                "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
            ), patch("agent_runtime._poll_seawork_terminal", return_value=(False, "running")), patch(
                "agent_runtime._run", side_effect=run_after_launch
            ), patch(
                "agent_runtime._attempt_safe_seawork_fallback", side_effect=lambda result, *_args: result,
            ) as fallback:
                result = agent_runtime.execute("seawork", prompt, Path(temporary), 1, "codex/gpt-5.6-terra", None, False)
        self.assertEqual(result["status"], "timed_out")
        self.assertEqual(result["failure_category"], "agent_timeout")
        self.assertNotIn("completion_basis", result)
        self.assertTrue(result["artifact_checkpoint"])
        self.assertTrue(result["artifact_checkpoint_after_stop"])
        self.assertIsNotNone(result["artifact_sha256_after_stop"])
        self.assertEqual(result["control_plane_terminal_state"], "idle")
        self.assertEqual(result["agent_state_after_stop"], "idle")
        self.assertIn("not accepted as completion", result["error"])
        fallback.assert_called_once()

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

    def test_seawork_error_is_a_terminal_state(self) -> None:
        with patch("agent_runtime._seawork_agent_record", return_value=(None, "error")):
            terminal, status = agent_runtime._poll_seawork_terminal("seawork", "agent", 900)
            stopped_terminal, stopped_status = agent_runtime._seawork_agent_is_terminal("seawork", "agent")
        self.assertTrue(terminal)
        self.assertEqual(status, "error")
        self.assertTrue(stopped_terminal)
        self.assertEqual(stopped_status, "error")

    def test_seawork_missing_agent_stops_polling_immediately(self) -> None:
        with patch("agent_runtime._seawork_agent_record", return_value=(None, "missing")), patch(
            "agent_runtime.time.sleep", side_effect=AssertionError("missing Agent must not be polled again"),
        ):
            terminal, status = agent_runtime._poll_seawork_terminal("seawork", "agent", 900)
        self.assertFalse(terminal)
        self.assertEqual(status, "missing")

    def test_transport_and_detached_agent_timeouts_use_fallback(self) -> None:
        self.assertTrue(agent_runtime._requires_direct_codex_fallback({"failure_category": "agent_no_progress"}))
        self.assertTrue(agent_runtime._requires_direct_codex_fallback({"failure_category": "seawork_control_plane_timeout"}))
        self.assertTrue(agent_runtime._requires_direct_codex_fallback({"failure_category": "agent_timeout"}))
        self.assertTrue(agent_runtime._requires_direct_codex_fallback({"failure_category": "seawork_agent_error"}))
        self.assertTrue(agent_runtime._requires_direct_codex_fallback({"failure_category": "seawork_agent_missing"}))
        self.assertTrue(agent_runtime._requires_direct_codex_fallback({"failure_category": "seawork_launch_error"}))

    def test_unattributed_seawork_failure_uses_a_ready_direct_catalog_model(self) -> None:
        failed = {
            "provider": "seawork", "model": None, "status": "blocked",
            "failure_category": "seawork_runtime_unhealthy", "dispatch_proven_not_started": True,
            "error": "daemon unavailable",
        }
        catalog = [
            ModelOption("gpt-5.6-terra", "codex", frozenset({"standard"}), "provider-config", 1),
        ]
        direct = {"provider": "codex", "model": "gpt-5.6-terra", "status": "complete", "error": ""}
        with patch("agent_runtime._ready_direct_codex_runtime", return_value=runtime("codex")), patch(
            "agent_runtime.discover_model_catalog", return_value=(catalog, []),
        ), patch("agent_runtime.execute", return_value=direct) as execute:
            result = agent_runtime._attempt_direct_codex_fallback(
                failed, "write", Path.cwd(), 3, None, 100, None,
            )
        self.assertTrue(result["fallback_used"])
        self.assertEqual(execute.call_args.args[4], "gpt-5.6-terra")
        self.assertEqual(result["fallback_selection_source"], "direct-codex-catalog")

    def test_direct_codex_fallback_keeps_the_explicit_seawork_model(self) -> None:
        failed = {
            "provider": "seawork",
            "model": "codex/gpt-5.6-terra",
            "status": "timed_out",
            "failure_category": "agent_no_progress",
            "agent_id": "e5fb49d8-5227-4a93-bba3-ded9b613bab5",
            "agent_state_after_stop": "idle",
            "transport_duration_seconds": 4.2,
            "error": "no first artifact",
        }
        direct = {"provider": "codex", "model": "gpt-5.6-terra", "status": "complete", "error": ""}
        catalog = [ModelOption("gpt-5.6-sol", "codex", frozenset({"standard"}), "provider-config")]
        with patch("agent_runtime.discover_runtimes", return_value=[runtime("codex")]), patch(
            "agent_runtime.discover_model_catalog", return_value=(catalog, [])
        ), patch("agent_runtime.execute", return_value=direct) as execute:
            result = agent_runtime._attempt_direct_codex_fallback(
                failed, "write", Path.cwd(), 3, None, 100, None,
            )
        self.assertTrue(result["fallback_used"])
        self.assertEqual(execute.call_args.args[0], "codex")
        self.assertEqual(execute.call_args.args[4], "gpt-5.6-terra")
        self.assertEqual(result["fallback_selection_source"], "seawork-discovered-or-operator-selected")
        self.assertEqual(result["fallback_from"]["transport_duration_seconds"], 4.2)

    def test_rejected_matching_direct_model_uses_one_distinct_declared_model(self) -> None:
        failed = {
            "provider": "seawork", "model": "codex/gpt-5.6-terra", "status": "timed_out",
            "failure_category": "agent_no_progress", "error": "no first artifact",
        }
        rejected = {
            "provider": "codex", "model": "gpt-5.6-terra", "status": "failed",
            "error": "requested model is unsupported",
        }
        completed = {"provider": "codex", "model": "gpt-5.6-sol", "status": "complete", "error": ""}
        with patch(
            "agent_runtime._matching_ready_direct_codex",
            return_value=("gpt-5.6-terra", "seawork-discovered-or-operator-selected", []),
        ), patch(
            "agent_runtime._distinct_ready_direct_codex",
            return_value=("gpt-5.6-sol", "direct-codex-catalog-distinct", []),
        ), patch("agent_runtime.execute", side_effect=[rejected, completed]) as execute:
            result = agent_runtime._attempt_direct_codex_fallback(
                failed, "write", Path.cwd(), 3, None, 100, None,
            )
        self.assertTrue(result["fallback_used"])
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(execute.call_args_list[1].args[4], "gpt-5.6-sol")
        self.assertEqual(result["fallback_selection_source"], "direct-codex-catalog-distinct")
        self.assertEqual([item["model"] for item in result["fallback_attempts"]], ["gpt-5.6-terra", "gpt-5.6-sol"])

    def test_explicit_unhealthy_seawork_uses_one_direct_fallback(self) -> None:
        fallback = {"provider": "codex", "model": "gpt-5.6-terra", "status": "complete", "error": ""}
        with patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime(None, None, "test"),
        ), patch("agent_runtime.select_runtime", side_effect=RuntimeError("daemon unreachable")), patch(
            "agent_runtime._attempt_direct_codex_fallback", return_value=fallback,
        ) as attempt:
            result = agent_runtime.execute(
                "seawork", "write", Path.cwd(), 3, "codex/gpt-5.6-terra", None, False,
            )
        self.assertEqual(result["provider"], "codex")
        source = attempt.call_args.args[0]
        self.assertEqual(source["failure_category"], "seawork_runtime_unhealthy")
        self.assertGreaterEqual(source["circuit_cooldown_seconds"], 0)

    def test_terminal_seawork_transport_failure_opens_circuit_before_direct_fallback(self) -> None:
        terra = ModelOption(
            "codex/gpt-5.6-terra", "seawork", frozenset({"judgment", "standard"}),
            "seawork-provider-discovery", 2,
        )
        failed = {
            "provider": "seawork", "model": "codex/gpt-5.6-terra", "status": "timed_out",
            "failure_category": "agent_no_progress", "agent_id": "e5fb49d8-5227-4a93-bba3-ded9b613bab5",
            "agent_state_after_stop": "idle", "error": "no first artifact",
        }
        fallback = {"provider": "codex", "model": "gpt-5.6-terra", "status": "complete", "error": ""}
        with patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime(None, None, "test"),
        ), patch("agent_runtime.select_runtime", return_value=runtime("seawork")), patch(
            "agent_runtime.discover_model_catalog", return_value=([terra], []),
        ), patch("agent_runtime._execute_seawork", return_value=failed), patch(
            "agent_runtime._attempt_direct_codex_fallback", return_value=fallback,
        ) as attempt:
            result = agent_runtime.execute(
                "seawork", "write", Path.cwd(), 3, "codex/gpt-5.6-terra", None, False,
            )
        self.assertEqual(result["provider"], "codex")
        source = attempt.call_args.args[0]
        self.assertEqual(source["failure_category"], "agent_no_progress")
        self.assertIn("transport_duration_seconds", source)
        self.assertGreater(source["circuit_cooldown_seconds"], 0)

    def test_seawork_claude_terminal_failure_opens_circuit_and_uses_safe_fallback(self) -> None:
        sonnet = ModelOption("sonnet", "seawork-claude", frozenset({"judgment"}), "test")
        failed = {
            "provider": "seawork-claude", "model": "claude/sonnet", "status": "failed",
            "failure_category": "seawork_agent_error",
            "agent_id": "e5fb49d8-5227-4a93-bba3-ded9b613bab5",
            "agent_state_after_stop": "idle", "error": "stream disconnected",
        }
        fallback = {"provider": "claude", "model": "sonnet", "status": "complete", "error": ""}
        with patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime(None, None, "test"),
        ), patch("agent_runtime.select_runtime", return_value=runtime("seawork-claude")), patch(
            "agent_runtime.discover_model_catalog", return_value=([sonnet], []),
        ), patch("agent_runtime._execute_seawork", return_value=failed), patch(
            "agent_runtime._attempt_safe_seawork_fallback", return_value=fallback,
        ) as attempt:
            result = agent_runtime.execute(
                "seawork-claude", "write", Path.cwd(), 3, "sonnet", None, False,
            )
        self.assertEqual(result["provider"], "claude")
        self.assertGreater(agent_runtime._seawork_circuit_remaining(), 0)
        self.assertEqual(attempt.call_args.args[0]["provider"], "seawork-claude")

    def test_orphaned_seawork_agent_never_shares_a_target_with_direct_fallback(self) -> None:
        orphaned = {
            "provider": "seawork", "model": "codex/gpt-5.6-terra", "status": "orphaned",
            "failure_category": "seawork_control_plane_unavailable",
            "agent_id": "e5fb49d8-5227-4a93-bba3-ded9b613bab5", "cleanup_blocked": True,
        }
        self.assertFalse(agent_runtime._safe_to_direct_codex_fallback(orphaned))

    def test_open_circuit_skips_a_second_seawork_launch(self) -> None:
        agent_runtime._open_seawork_circuit()
        fallback = {"provider": "codex", "model": "gpt-5.6-terra", "status": "complete", "error": ""}
        with patch(
            "agent_runtime.active_runtime",
            return_value=agent_runtime.ActiveRuntime(None, None, "test"),
        ), patch("agent_runtime.select_runtime") as select, patch(
            "agent_runtime._attempt_direct_codex_fallback", return_value=fallback,
        ) as attempt:
            result = agent_runtime.execute(
                "seawork", "write", Path.cwd(), 3, "codex/gpt-5.6-terra", None, False,
            )
        self.assertEqual(result["provider"], "codex")
        select.assert_not_called()
        self.assertEqual(attempt.call_args.args[0]["failure_category"], "seawork_circuit_open")

    def test_seawork_detached_launch_timeout_blocks_same_workspace_fallback(self) -> None:
        timeout = subprocess.TimeoutExpired(["seawork", "run"], 30)
        model = ModelOption("codex/gpt-primary", "seawork", frozenset({"judgment"}), "test")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.md"
            prompt = f"Write exactly one complete artifact at {target}."
            with patch("agent_runtime.discover_runtimes", return_value=[runtime("seawork")]), patch(
                "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
            ), patch("agent_runtime.discover_model_catalog", return_value=([model], [])), patch(
                "agent_runtime._run", side_effect=timeout
            ), patch("agent_runtime._attempt_direct_codex_fallback") as fallback:
                result = agent_runtime.execute(
                    "seawork", prompt, Path(temporary), 3, "codex/gpt-primary", None, False,
                )
        self.assertEqual(result["status"], "orphaned")
        self.assertEqual(result["failure_category"], "seawork_launch_unconfirmed")
        self.assertTrue(result["cleanup_blocked"])
        self.assertFalse(result["launch_acknowledged"])
        self.assertNotIn("agent_id", result)
        self.assertFalse(agent_runtime._safe_to_direct_codex_fallback(result))
        fallback.assert_not_called()

    def test_synchronous_seawork_stream_timeout_blocks_same_workspace_fallback(self) -> None:
        timeout = subprocess.TimeoutExpired(["seawork", "run"], 30, stderr="stream disconnected")
        model = ModelOption("codex/gpt-primary", "seawork", frozenset({"judgment"}), "test")
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            target = workspace / "review.json"
            schema = workspace / "schema.json"
            schema.write_text('{"type":"object"}\n', encoding="utf-8")
            prompt = f"Write ONLY one JSON object to {target}."
            with patch("agent_runtime.discover_runtimes", return_value=[runtime("seawork")]), patch(
                "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
            ), patch("agent_runtime.discover_model_catalog", return_value=([model], [])), patch(
                "agent_runtime._run", side_effect=timeout
            ), patch("agent_runtime._attempt_direct_codex_fallback") as fallback:
                result = agent_runtime.execute(
                    "seawork", prompt, workspace, 3, "codex/gpt-primary", str(schema), False,
                )
        self.assertEqual(result["status"], "orphaned")
        self.assertEqual(result["failure_category"], "seawork_stream_unconfirmed")
        self.assertTrue(result["cleanup_blocked"])
        self.assertFalse(result["dispatch_proven_not_started"])
        self.assertFalse(agent_runtime._safe_to_direct_codex_fallback(result))
        fallback.assert_not_called()

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

    def test_terminal_non_codex_seawork_failure_uses_distinct_local_provider(self) -> None:
        failed = {
            "provider": "seawork-claude", "model": "claude/sonnet", "status": "failed",
            "failure_category": "seawork_agent_error",
            "agent_id": "e5fb49d8-5227-4a93-bba3-ded9b613bab5",
            "agent_state_after_stop": "idle", "error": "stream disconnected",
        }
        fallback = {"provider": "claude", "model": "opus", "status": "complete", "error": ""}

        def candidates(*_args, **kwargs):
            self.assertEqual(set(kwargs["excluded_providers"]), {"seawork", "seawork-claude"})
            return [("claude", "opus", "direct-claude-catalog")]

        with patch("agent_runtime._attempt_direct_codex_fallback", return_value=failed), patch(
            "agent_runtime._transport_fallback_candidates", side_effect=candidates,
        ), patch("agent_runtime.execute", return_value=fallback) as execute:
            result = agent_runtime._attempt_safe_seawork_fallback(
                failed, "write", Path.cwd(), 3, None, 100, None,
            )
        self.assertTrue(result["fallback_used"])
        self.assertEqual(execute.call_args.args[0], "claude")
        self.assertEqual(result["fallback_from"]["failure_category"], "seawork_agent_error")

    def test_transport_fallback_skips_an_upstream_rejected_model(self) -> None:
        candidates = [
            ("seawork", "codex/rejected", "seawork-provider-discovery"),
            ("seawork", "codex/usable", "seawork-provider-discovery"),
        ]
        with patch("agent_runtime._transport_fallback_candidates", return_value=candidates), patch(
            "agent_runtime.execute", side_effect=[
                {"provider": "seawork", "model": "codex/rejected", "status": "failed", "error": "Agent terminal state: error"},
                {"provider": "seawork", "model": "codex/usable", "status": "complete", "error": ""},
            ],
        ) as execute:
            result = agent_runtime._fallback_from_transport(
                {"provider": "seawork", "model": "codex/primary", "error": "stream disconnected"},
                "write", Path.cwd(), 3, 100, None,
            )
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(result["model"], "codex/usable")
        self.assertEqual([item["status"] for item in result["fallback_attempts"]], ["failed", "complete"])

    def test_transport_fallback_uses_last_known_catalog_when_probe_is_unavailable(self) -> None:
        failed = {
            "provider": "seawork",
            "model": "codex/gpt-5.6-terra",
            "available_models": ["codex/gpt-5.6-terra", "codex/gpt-5.6-luna"],
            "status": "failed",
            "failure_category": "seawork_agent_error",
            "error": "Agent terminal state: error",
        }
        with patch("agent_runtime.discover_runtimes", return_value=[]), patch(
            "agent_runtime.execute",
            return_value={"provider": "seawork", "model": "codex/gpt-5.6-luna", "status": "complete", "error": ""},
        ) as execute:
            result = agent_runtime._fallback_from_transport(
                failed, "write", Path.cwd(), 3, 100, None,
            )
        self.assertTrue(result["fallback_used"])
        self.assertEqual(execute.call_args.args[0], "seawork")
        self.assertEqual(execute.call_args.args[4], "codex/gpt-5.6-luna")
        self.assertEqual(result["fallback_selection_source"], "failed-call-model-catalog")

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

    def test_direct_codex_normal_exit_without_artifact_change_fails(self) -> None:
        completed = subprocess.CompletedProcess([], 0, "completed", "")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.md"
            target.write_text("old staged artifact\n", encoding="utf-8")
            with patch("agent_runtime.discover_runtimes", return_value=[runtime("codex")]), patch(
                "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
            ), patch(
                "agent_runtime.discover_model_catalog",
                return_value=([ModelOption("test-model", "codex", frozenset({"standard"}), "test")], []),
            ), patch("agent_runtime._run", return_value=completed):
                result = agent_runtime.execute(
                    "codex", f"Write exactly one complete artifact at {target}.", Path(temporary), 1,
                    "test-model", None, False, allow_transport_fallback=False,
                )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_category"], "agent_no_output")
        self.assertFalse(result["artifact_checkpoint"])
        self.assertIn("without changing its promised artifact", result["error"])

    def test_direct_codex_timeout_retries_distinct_model_after_cleanup(self) -> None:
        timeout = subprocess.TimeoutExpired(["codex"], 30, output="", stderr="stalled")
        models = [
            ModelOption("gpt-primary", "codex", frozenset({"standard"}), "test"),
            ModelOption("gpt-backup", "codex", frozenset({"standard"}), "test"),
        ]
        events: list[str] = []
        cleanup_confirmed = False
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.md"
            prompt = f"Write exactly one complete artifact at {target}."

            def run_after_cleanup(command, *args, **kwargs):
                nonlocal cleanup_confirmed
                model = command[command.index("--model") + 1]
                if model == "gpt-primary":
                    events.append("initial-process-cleaned-up")
                    cleanup_confirmed = True
                    raise timeout
                self.assertEqual(model, "gpt-backup")
                self.assertTrue(cleanup_confirmed, "the alternate model must wait for initial process cleanup")
                events.append("distinct-model-dispatched")
                target.write_text("new staged artifact\n", encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, "completed", "")

            with patch("agent_runtime.discover_runtimes", return_value=[runtime("codex")]), patch(
                "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
            ), patch("agent_runtime.discover_model_catalog", return_value=(models, [])), patch(
                "agent_runtime._distinct_ready_direct_codex",
                return_value=("gpt-backup", "direct-codex-catalog-distinct", []),
            ), patch("agent_runtime._run", side_effect=run_after_cleanup):
                result = agent_runtime.execute(
                    "codex", prompt, Path(temporary), 1, "gpt-primary", None, False,
                )
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["model"], "gpt-backup")
        self.assertEqual(result["fallback_selection_source"], "direct-codex-catalog-distinct")
        self.assertEqual(events, ["initial-process-cleaned-up", "distinct-model-dispatched"])

    def test_direct_codex_timeout_with_unconfirmed_cleanup_does_not_retry(self) -> None:
        timeout = subprocess.TimeoutExpired(["codex"], 30, output="", stderr="stalled")
        timeout.cleanup_blocked = True
        model = ModelOption("gpt-primary", "codex", frozenset({"standard"}), "test")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact.md"
            prompt = f"Write exactly one complete artifact at {target}."
            with patch("agent_runtime.discover_runtimes", return_value=[runtime("codex")]), patch(
                "agent_runtime.active_runtime", return_value=agent_runtime.ActiveRuntime(None, None, "test")
            ), patch("agent_runtime.discover_model_catalog", return_value=([model], [])), patch(
                "agent_runtime._run", side_effect=timeout
            ), patch("agent_runtime._retry_distinct_direct_codex") as retry:
                result = agent_runtime.execute(
                    "codex", prompt, Path(temporary), 1, "gpt-primary", None, False,
                )
        self.assertEqual(result["status"], "orphaned")
        self.assertEqual(result["failure_category"], "agent_cleanup_unconfirmed")
        self.assertTrue(result["cleanup_blocked"])
        retry.assert_not_called()

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
