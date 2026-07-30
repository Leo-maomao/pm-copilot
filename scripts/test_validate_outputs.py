#!/usr/bin/env python3
"""Regression checks for supported PM Copilot output directory layouts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from validate_outputs import check_folder


class ValidateOutputsTest(unittest.TestCase):
    def test_accepts_embedded_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "outputs" / "sample-2026-07-30"
            run.mkdir(parents=True)
            check_folder(run, require_run_log=False)

    def test_accepts_visible_global_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "pm-copilot-outputs" / "sample-2026-07-30"
            run.mkdir(parents=True)
            check_folder(run, require_run_log=False)

    def test_rejects_unknown_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "documents" / "sample-2026-07-30"
            run.mkdir(parents=True)
            with self.assertRaises(SystemExit):
                check_folder(run, require_run_log=False)


if __name__ == "__main__":
    unittest.main()
