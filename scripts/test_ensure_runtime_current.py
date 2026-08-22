import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ensure_runtime_current import ensure_current


class EnsureRuntimeCurrentTests(unittest.TestCase):
    def test_newer_source_auto_syncs_clean_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            runtime = root / "runtime"
            skills = root / "skills"
            source.mkdir()
            runtime.mkdir()
            (source / "VERSION").write_text("6.2.0\n", encoding="utf-8")
            (runtime / "VERSION").write_text("6.1.0\n", encoding="utf-8")
            (runtime / "install-state.json").write_text(json.dumps({
                "source_root": str(source), "manifest_file": "install-manifest.json",
            }), encoding="utf-8")
            digest = hashlib.sha256(b"6.1.0\n").hexdigest()
            (runtime / "install-manifest.json").write_text(json.dumps({"files": {"VERSION": digest}}), encoding="utf-8")
            with patch("ensure_runtime_current._sync_from_source", return_value={"status": "synced", "version": "6.2.0"}) as sync:
                result = ensure_current(runtime, skills, require_current=True)
            self.assertEqual(result["status"], "synced")
            sync.assert_called_once_with(source, runtime.resolve(), skills.resolve())

    def test_local_runtime_changes_block_automatic_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            runtime = root / "runtime"
            skills = root / "skills"
            source.mkdir()
            runtime.mkdir()
            (source / "VERSION").write_text("6.2.0\n", encoding="utf-8")
            (runtime / "VERSION").write_text("6.1.0\n", encoding="utf-8")
            (runtime / "custom.txt").write_text("edited", encoding="utf-8")
            (runtime / "install-state.json").write_text(json.dumps({
                "source_root": str(source), "manifest_file": "install-manifest.json",
            }), encoding="utf-8")
            (runtime / "install-manifest.json").write_text(json.dumps({"files": {
                "VERSION": hashlib.sha256(b"6.1.0\n").hexdigest(),
                "custom.txt": hashlib.sha256(b"original").hexdigest(),
            }}), encoding="utf-8")
            result = ensure_current(runtime, skills, require_current=True)
            self.assertEqual(result["status"], "blocked_local_changes")
            self.assertIn("custom.txt", result["changed_files"])


if __name__ == "__main__":
    unittest.main()
