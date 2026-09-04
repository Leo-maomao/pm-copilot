#!/usr/bin/env python3
"""Focused regression coverage for repository static-source checks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import validate_repo


class ValidateRepoTest(unittest.TestCase):
    def test_utf8_runtime_source_requires_a_declared_encoding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "scripts" / "run_interactive_request.py"
            source.parent.mkdir()
            source.write_text('print("utf8")\n', encoding="utf-8")
            with patch.object(validate_repo, "ROOT", root), patch.object(
                validate_repo, "UTF8_RUNTIME_SOURCES", ("scripts/run_interactive_request.py",),
            ):
                with self.assertRaises(SystemExit):
                    validate_repo.check_runtime_source_encoding()
            source.write_text('# -*- coding: utf-8 -*-\nprint("utf8")\n', encoding="utf-8")
            with patch.object(validate_repo, "ROOT", root), patch.object(
                validate_repo, "UTF8_RUNTIME_SOURCES", ("scripts/run_interactive_request.py",),
            ):
                validate_repo.check_runtime_source_encoding()

    def test_runtime_install_metadata_is_exempt_only_from_fixture_path_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "install-state.json").write_text(
                '{"source_root":"/' + "Users" + '/example/Desktop/pm-copilot"}',
                encoding="utf-8",
            )
            with patch.object(validate_repo, "ROOT", root):
                validate_repo.check_reference_fixture_boundary()

    def test_non_metadata_local_path_still_fails_fixture_path_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "runtime-note.yaml").write_text(
                "source_root: /" + "Users" + "/example/Desktop/pm-copilot\n",
                encoding="utf-8",
            )
            with patch.object(validate_repo, "ROOT", root):
                with self.assertRaises(SystemExit):
                    validate_repo.check_reference_fixture_boundary()


if __name__ == "__main__":
    unittest.main()
