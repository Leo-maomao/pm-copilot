#!/usr/bin/env python3
"""Regression coverage for embedded and global PM Copilot project workspaces."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from project_workspace import resolve


class ProjectWorkspaceTest(unittest.TestCase):
    def test_global_mode_creates_hidden_project_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            context = resolve(project, ensure=True)
            self.assertEqual(context["mode"], "global")
            self.assertEqual(Path(context["output_root"]), (project / ".pm-copilot" / "outputs").resolve())
            self.assertTrue((project / ".pm-copilot" / "config.yaml").is_file())

    def test_embedded_mode_preserves_legacy_output_location(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            (project / "pm-copilot").mkdir()
            (project / "pm-copilot" / "PM_COPILOT.md").write_text("# PM Copilot", encoding="utf-8")
            context = resolve(project, ensure=True)
            self.assertEqual(context["mode"], "embedded")
            self.assertEqual(Path(context["output_root"]), (project / "pm-copilot" / "outputs").resolve())

    def test_rejects_output_location_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            workspace = project / ".pm-copilot"
            workspace.mkdir()
            (workspace / "config.yaml").write_text("output_root: ../outside\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                resolve(project)


if __name__ == "__main__":
    unittest.main()
