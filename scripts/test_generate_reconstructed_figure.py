from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import generate_reconstructed_figure as figures


class ReconstructedFigureTests(unittest.TestCase):
    def test_writes_isolated_page_and_promotes_a_real_capture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)

            def capture(*_args, **_kwargs):
                screenshot = folder / "reconstructions/审批提醒-默认.png"
                screenshot.parent.mkdir(parents=True, exist_ok=True)
                screenshot.write_bytes(b"captured")
                return subprocess.CompletedProcess([], 0, "captured", "")

            with patch.object(sys, "argv", [
                "generate_reconstructed_figure.py", "--run-folder", str(folder),
                "--asset-name", "审批提醒-默认.png", "--title", "审批提醒", "--state", "默认",
            ]), patch("generate_reconstructed_figure.subprocess.run", side_effect=capture):
                self.assertEqual(figures.main(), 0)

            self.assertTrue((folder / "reconstructions/审批提醒-默认.html").is_file())
            self.assertTrue((folder / "reconstructions/审批提醒-默认.png").is_file())
            self.assertFalse((folder / "visual-review").exists())
            self.assertEqual((folder / "assets/审批提醒-默认.png").read_bytes(), b"captured")
            report = json.loads((folder / "tool-results/reconstructed-figures/审批提醒-默认.json").read_text())
            self.assertEqual(report["capture_status"], "passed")

    def test_retains_a_failure_report_without_an_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            with patch.object(sys, "argv", [
                "generate_reconstructed_figure.py", "--run-folder", str(folder),
                "--asset-name", "审批提醒-默认.png", "--title", "审批提醒", "--state", "默认",
            ]), patch(
                "generate_reconstructed_figure.subprocess.run",
                return_value=subprocess.CompletedProcess([], 2, "", "browser unavailable"),
            ):
                self.assertEqual(figures.main(), 2)

            self.assertFalse((folder / "assets/审批提醒-默认.png").exists())
            report = json.loads((folder / "tool-results/reconstructed-figures/审批提醒-默认.json").read_text())
            self.assertEqual(report["capture_status"], "failed")


if __name__ == "__main__":
    unittest.main()
