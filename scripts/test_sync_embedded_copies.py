#!/usr/bin/env python3
"""Regression checks for safe embedded-copy synchronization."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sync_embedded_copies import discover_copies, protected, sync_copy


class SyncEmbeddedCopiesTest(unittest.TestCase):
    def test_protects_outputs_and_local_context(self) -> None:
        self.assertTrue(protected(Path("outputs/example/prd.md")))
        self.assertTrue(protected(Path("context/product-memory.local.yaml")))
        self.assertFalse(protected(Path("templates/prd-template.md")))

    def test_sync_preserves_protected_destination_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            destination = root / "destination"
            (source / "templates").mkdir(parents=True)
            (source / "outputs" / "example").mkdir(parents=True)
            (source / "templates" / "prd-template.md").write_text("latest", encoding="utf-8")
            (source / "outputs" / "example" / "prd.md").write_text("source", encoding="utf-8")
            (destination / "outputs" / "example").mkdir(parents=True)
            (destination / "outputs" / "example" / "prd.md").write_text("local", encoding="utf-8")
            result = sync_copy(source, destination, True, True)
            self.assertGreater(result.copied, 0)
            self.assertEqual((destination / "templates" / "prd-template.md").read_text(encoding="utf-8"), "latest")
            self.assertEqual((destination / "outputs" / "example" / "prd.md").read_text(encoding="utf-8"), "local")

    def test_discovery_skips_git_internals_and_non_copies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source" / "pm-copilot"
            copy = root / "host" / "pm-copilot"
            git_internal = root / "host" / ".git" / "modules" / "pm-copilot"
            for directory in (source, copy, git_internal):
                directory.mkdir(parents=True)
            (source / "PM_COPILOT.md").write_text("source", encoding="utf-8")
            (copy / "PM_COPILOT.md").write_text("copy", encoding="utf-8")
            (git_internal / "PM_COPILOT.md").write_text("internal", encoding="utf-8")
            self.assertEqual(discover_copies([root], source), [copy])


if __name__ == "__main__":
    unittest.main()
