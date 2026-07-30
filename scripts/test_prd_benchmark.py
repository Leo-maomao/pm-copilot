#!/usr/bin/env python3
"""Regression coverage for deterministic PRD benchmark scoring."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evaluate_prd_benchmark import evaluate_case


class PRDBenchmarkTest(unittest.TestCase):
    def test_scores_required_and_forbidden_content(self) -> None:
        case = {"id": "case", "required_text": ["需求详情"], "forbidden_text": ["拟议"]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "case").mkdir()
            (root / "case" / "prd.md").write_text("需求详情", encoding="utf-8")
            self.assertTrue(evaluate_case(case, root)["passed"])
            (root / "case" / "prd.md").write_text("需求详情\n拟议", encoding="utf-8")
            self.assertEqual(evaluate_case(case, root)["failures"], ["forbidden:拟议"])

    def test_rejects_invalid_case_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(
                evaluate_case({"id": "case", "required_text": "需求详情"}, Path(temporary))["failures"],
                ["invalid_case:required_text"],
            )


if __name__ == "__main__":
    unittest.main()
