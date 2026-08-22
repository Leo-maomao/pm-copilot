#!/usr/bin/env python3
"""Regression coverage for safe Pandoc setup behavior."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import setup_prd_renderer


class PRDRendererSetupTest(unittest.TestCase):
    def test_official_install_runs_before_homebrew(self) -> None:
        output = io.StringIO()
        with patch("setup_prd_renderer.find_pandoc", return_value=""), patch(
            "setup_prd_renderer.install_official_binary", return_value=(True, "pandoc=local-bin/pandoc")
        ), patch("setup_prd_renderer.shutil.which", return_value=None), patch(
            "setup_prd_renderer.subprocess.run"
        ) as run, patch("sys.argv", ["setup_prd_renderer.py", "--install"]), redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                setup_prd_renderer.main()
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(run.call_count, 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["status"], "installed")
        self.assertTrue(result["attempted"])

    def test_existing_pandoc_skips_install(self) -> None:
        output = io.StringIO()
        with patch("setup_prd_renderer.find_pandoc", return_value="/opt/bin/pandoc"), patch(
            "setup_prd_renderer.subprocess.run"
        ) as run, patch("sys.argv", ["setup_prd_renderer.py", "--install"]), redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                setup_prd_renderer.main()
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(run.call_count, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "available")


if __name__ == "__main__":
    unittest.main()
