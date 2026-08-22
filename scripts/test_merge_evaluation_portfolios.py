#!/usr/bin/env python3
"""Regression tests for merging split evaluation evidence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from merge_evaluation_portfolios import merge


class MergePortfolioTest(unittest.TestCase):
    def test_merges_disjoint_complete_partitions(self) -> None:
        cases = [{"case_id": "a"}, {"case_id": "b"}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            roots = [root / "one", root / "two"]
            for folder, case in zip(roots, cases):
                folder.mkdir()
                (folder / "portfolio-run.json").write_text(json.dumps({
                    "plan_snapshot": [case], "cases": {case["case_id"]: {"status": "complete"}},
                }), encoding="utf-8")
            with patch("merge_evaluation_portfolios.portfolio", return_value={"cases": cases}):
                result = merge(roots)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(set(result["cases"]), {"a", "b"})
            self.assertEqual(len(result["source_portfolios"]), 2)

    def test_rejects_overlap_or_missing_active_cases(self) -> None:
        cases = [{"case_id": "a"}, {"case_id": "b"}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("one", "two"):
                folder = root / name
                folder.mkdir()
                (folder / "portfolio-run.json").write_text(json.dumps({
                    "plan_snapshot": [{"case_id": "a"}], "cases": {"a": {"status": "complete"}},
                }), encoding="utf-8")
            with patch("merge_evaluation_portfolios.portfolio", return_value={"cases": cases}):
                with self.assertRaisesRegex(ValueError, "duplicate case"):
                    merge([root / "one", root / "two"])


if __name__ == "__main__":
    unittest.main()
