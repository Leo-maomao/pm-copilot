#!/usr/bin/env python3
"""Regression coverage for embedded and global PM Copilot project workspaces."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from project_workspace import resolve


class ProjectWorkspaceTest(unittest.TestCase):
    def test_global_mode_creates_visible_project_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            context = resolve(project, ensure=True)
            self.assertEqual(context["mode"], "global")
            self.assertEqual(Path(context["workspace"]), (project / "pm-copilot-outputs").resolve())
            self.assertEqual(Path(context["output_root"]), (project / "pm-copilot-outputs").resolve())
            self.assertTrue((project / "pm-copilot-outputs").is_dir())
            self.assertFalse((project / ".pm-copilot").exists())

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

    def test_migrates_legacy_hidden_outputs_to_visible_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            legacy_run = project / ".pm-copilot" / "outputs" / "sample-2026-07-30"
            legacy_run.mkdir(parents=True)
            (legacy_run / "prd.md").write_text("# 示例", encoding="utf-8")
            (legacy_run / "tool-results").mkdir()
            (legacy_run / "tool-results" / "ledger.json").write_text(
                '{"output": "' + str((project / ".pm-copilot" / "outputs").resolve()) + '"}',
                encoding="utf-8",
            )
            (project / ".pm-copilot" / "config.yaml").write_text(
                "# Optional: output_root: docs/prd\n", encoding="utf-8"
            )
            context = resolve(project, ensure=True)
            migrated_run = project / "pm-copilot-outputs" / "sample-2026-07-30"
            self.assertEqual(Path(context["output_root"]), (project / "pm-copilot-outputs").resolve())
            self.assertEqual((migrated_run / "prd.md").read_text(encoding="utf-8"), "# 示例")
            self.assertIn(
                str((project / "pm-copilot-outputs").resolve()),
                (migrated_run / "tool-results" / "ledger.json").read_text(encoding="utf-8"),
            )
            self.assertFalse((project / ".pm-copilot").exists())


if __name__ == "__main__":
    unittest.main()
