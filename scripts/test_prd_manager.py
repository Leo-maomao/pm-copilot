from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from prd_manager import discover_documents, parse_prd


class PrdManagerTests(unittest.TestCase):
    def test_indexes_only_rendered_prds_below_output_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "project-a" / "pm-copilot-outputs" / "run-1"
            run.mkdir(parents=True)
            (run / "prd.html").write_text("<title>通知中心 - 2026-09-04</title><h1>通知中心</h1>", encoding="utf-8")
            (root / "project-a" / "draft.html").write_text("<h1>not an output</h1>", encoding="utf-8")

            documents = discover_documents(root)

            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0].project, "project-a")
            self.assertEqual(documents[0].title, "通知中心")

    def test_ignores_missing_or_empty_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "prd.html"
            self.assertIsNone(parse_prd(path, "project"))
            path.write_text("<title></title>", encoding="utf-8")
            self.assertIsNone(parse_prd(path, "project"))


if __name__ == "__main__":
    unittest.main()
