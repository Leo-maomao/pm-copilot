from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from agent_runtime import execute


class CodexRuntimeTests(unittest.TestCase):
    def test_rejects_non_codex_runtime_requests(self) -> None:
        result = execute("legacy-provider", "draft", Path.cwd(), 1, None, None, True)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["failure_category"], "unsupported_runtime")

    def test_dry_run_uses_only_codex_with_redacted_prompt(self) -> None:
        with patch("agent_runtime.shutil.which", return_value="/usr/local/bin/codex"):
            result = execute("auto", "private prompt", Path.cwd(), 1, "codex/gpt-5.6", None, True)
        self.assertEqual(result["status"], "planned")
        self.assertEqual(result["provider"], "codex")
        self.assertEqual(result["model"], "gpt-5.6")
        self.assertNotIn("private prompt", result["command"])

    def test_default_model_is_explicit_and_attributable(self) -> None:
        with patch("agent_runtime.shutil.which", return_value="/usr/local/bin/codex"):
            result = execute("auto", "draft", Path.cwd(), 1, None, None, True)
        self.assertEqual(result["model"], "gpt-5.6-terra")
        self.assertIn("--model", result["command"])

    def test_timeout_terminates_the_entire_codex_process_group(self) -> None:
        process = Mock(pid=1234)
        process.poll.return_value = None
        process.communicate.side_effect = [
            __import__("subprocess").TimeoutExpired(["codex"], 60, output="partial"),
            ("", ""),
        ]
        with patch("agent_runtime.shutil.which", return_value="/usr/local/bin/codex"), patch(
            "agent_runtime.subprocess.Popen", return_value=process,
        ) as launch, patch("agent_runtime.os.killpg") as killpg:
            result = execute("auto", "draft", Path.cwd(), 1, None, None, False)

        self.assertEqual(result["status"], "timed_out")
        launch.assert_called_once()
        self.assertTrue(launch.call_args.kwargs["start_new_session"])
        killpg.assert_called_once_with(1234, __import__("signal").SIGTERM)


if __name__ == "__main__":
    unittest.main()
