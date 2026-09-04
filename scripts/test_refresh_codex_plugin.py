from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from refresh_codex_plugin import head_changes_plugin_release, publish_plugin_source, refresh_plugin


class RefreshCodexPluginTests(unittest.TestCase):
    def test_publish_replaces_stale_source_with_recoverable_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            (source / "plugins" / "pm-copilot" / ".codex-plugin").mkdir(parents=True)
            (source / "plugins" / "pm-copilot" / ".codex-plugin" / "plugin.json").write_text("{}")
            target = root / "plugins" / "pm-copilot"
            target.mkdir(parents=True)
            (target / "old.txt").write_text("old")

            result = publish_plugin_source(source, target)

            self.assertEqual(result["status"], "linked")
            self.assertEqual(target.resolve(), (source / "plugins" / "pm-copilot").resolve())
            self.assertTrue(Path(result["backup"]).is_dir())

    def test_refresh_installs_from_personal_marketplace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            (source / "plugins" / "pm-copilot" / ".codex-plugin").mkdir(parents=True)
            (source / "plugins" / "pm-copilot" / ".codex-plugin" / "plugin.json").write_text("{}")
            with patch("refresh_codex_plugin.shutil.which", return_value="/usr/bin/codex"), patch(
                "refresh_codex_plugin.subprocess.run",
                return_value=subprocess.CompletedProcess([], 0, stdout='{"version":"7.0.1"}', stderr=""),
            ) as run:
                result = refresh_plugin(source, root / "plugins" / "pm-copilot")

            self.assertEqual(result["status"], "refreshed")
            self.assertEqual(run.call_args.args[0][-2:], ["pm-copilot@personal", "--json"])

    def test_head_release_detection_requires_version_or_plugin_change(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout="README.md\nVERSION\n", stderr="")
        with patch("refresh_codex_plugin.subprocess.run", return_value=completed):
            self.assertTrue(head_changes_plugin_release(Path(".")))

