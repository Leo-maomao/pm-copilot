from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sync_plugin_version import sync_plugin_version, versions_are_aligned


class SyncPluginVersionTests(unittest.TestCase):
    def test_sync_uses_repository_version_and_one_cachebuster(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "plugin.json"
            (root / "VERSION").write_text("6.2.17\n", encoding="utf-8")
            manifest.write_text(json.dumps({"version": "4.9.13+codex.old"}), encoding="utf-8")
            self.assertEqual(sync_plugin_version(root, manifest, "release-1"), "6.2.17+codex.release-1")
            self.assertTrue(versions_are_aligned(root, manifest))
