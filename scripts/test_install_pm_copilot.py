#!/usr/bin/env python3
"""Regression coverage for isolated global PM Copilot installation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from install_pm_copilot import install


class InstallPmCopilotTest(unittest.TestCase):
    def test_installs_runtime_and_skill_without_project_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime_home = root / "runtime"
            skills_home = root / "skills"
            state = install(runtime_home, skills_home)
            self.assertEqual(state["runtime_home"], str(runtime_home.resolve()))
            self.assertTrue((runtime_home / "PM_COPILOT.md").is_file())
            self.assertTrue((skills_home / "pm-copilot").is_symlink())
            self.assertFalse((runtime_home / "outputs").exists())
            self.assertFalse((runtime_home / "tool-results").exists())
            self.assertEqual(state["source_root"], str(Path(__file__).resolve().parents[1]))
            self.assertIn("source_commit", state)
            self.assertTrue((runtime_home / "install-manifest.json").is_file())

    def test_rejects_runtime_inside_source_checkout(self) -> None:
        source_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                install(source_root / ".pm-copilot-runtime", Path(temporary) / "skills")


if __name__ == "__main__":
    unittest.main()
