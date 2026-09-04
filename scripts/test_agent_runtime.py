from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
