#!/usr/bin/env python3
"""Regression checks for deterministic output-folder migration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from upgrade_local_outputs import modern_folder_name, remove_ignored_metadata, unique_target, update_references


class UpgradeLocalOutputsTest(unittest.TestCase):
    def test_modernizes_legacy_folder_name(self) -> None:
        self.assertEqual(
            modern_folder_name("membership-auto-renewal-20260526-1804"),
            "membership-auto-renewal-2026-05-26",
        )
        self.assertIsNone(modern_folder_name("membership-auto-renewal-2026-05-26"))

    def test_uses_numeric_suffix_for_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            (parent / "requirement-2026-07-28").mkdir()
            self.assertEqual(unique_target(parent, "requirement-2026-07-28").name, "requirement-2026-07-28-2")

    def test_updates_only_textual_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            markdown = folder / "run-log.yaml"
            markdown.write_text("run_id: old-id\npath: outputs/old-id\n", encoding="utf-8")
            binary = folder / "image.png"
            binary.write_bytes(b"old-id")
            updated = update_references(folder, {"old-id": "new-id"})
            self.assertEqual(updated, 1)
            self.assertIn("new-id", markdown.read_text(encoding="utf-8"))
            self.assertEqual(binary.read_bytes(), b"old-id")

    def test_removes_only_finder_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / ".DS_Store").write_text("metadata", encoding="utf-8")
            (folder / "assets").mkdir()
            (folder / "assets" / ".DS_Store").write_text("metadata", encoding="utf-8")
            (folder / "assets" / "screen.png").write_bytes(b"image")
            self.assertEqual(remove_ignored_metadata(folder), 2)
            self.assertTrue((folder / "assets" / "screen.png").is_file())


if __name__ == "__main__":
    unittest.main()
