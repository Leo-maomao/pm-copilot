import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from collect_implemented_feature_evidence import collect


class CollectImplementedFeatureEvidenceTests(unittest.TestCase):
    def test_collects_changed_files_and_run_local_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "host"
            run = Path(temporary) / "run"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "src").mkdir()
            (root / "src" / "canvas.ts").write_text("export const save = () => true;\n", encoding="utf-8")
            evidence = collect(root, "画布保存", run)

            self.assertIn("src/canvas.ts", evidence["changed_files"])
            self.assertEqual(evidence["collection_provenance"]["result_ref"], "tool-results/implemented-evidence/collection.json")
            report = run / "tool-results" / "implemented-evidence" / "collection.json"
            self.assertTrue(report.is_file())
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["host_project_root"], str(root.resolve()))


if __name__ == "__main__":
    unittest.main()
