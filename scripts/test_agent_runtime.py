#!/usr/bin/env python3
"""Deterministic regression tests for local Agent Runtime discovery and dispatch."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agent_runtime


def runtime(provider: str, status: str = "ready") -> agent_runtime.RuntimeStatus:
    return agent_runtime.RuntimeStatus(
        provider=provider,
        executable=f"/{provider}",
        status=status,
        supports_detached=provider == "seawork",
        supports_structured_output=True,
        supports_verifier=provider == "seawork",
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
                "auto", "inspect only", Path.cwd(), 2, None, None, True
            )
        self.assertEqual(result["status"], "planned")
        self.assertEqual(result["provider"], "seawork")
        self.assertIn("--mode", result["command"])
        self.assertIn("[PROMPT REDACTED]", result["command"])

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
        self.assertIn("gpt-5.4", command)

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

    def test_rejects_credentials_in_prompt(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "must not contain credentials"):
            agent_runtime._reject_credential_prompt("api_key=do-not-pass-this")

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


if __name__ == "__main__":
    unittest.main()
