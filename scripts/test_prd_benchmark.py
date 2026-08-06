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

    def test_dialog_grouping_case_rejects_fragmented_dialog_requirement(self) -> None:
        repository_root = Path(__file__).resolve().parents[1]
        case_path = repository_root / "evals/prd-benchmark/cases/dialog-requirement-grouping.json"
        case = json.loads(case_path.read_text(encoding="utf-8"))
        source_candidate = (
            repository_root / "evals/prd-benchmark/candidates" / str(case["id"]) / "prd.md"
        ).read_text(encoding="utf-8")
        self.assertTrue(evaluate_case(case, repository_root / "evals/prd-benchmark/candidates")["passed"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / str(case["id"])
            candidate.mkdir()
            candidate.joinpath("prd.md").write_text(
                source_candidate.replace(
                    "## 五、需求详情",
                    "| 5.2 | 弹窗校验提示 | 团队管理员 | 提交角色变更 | 理解校验失败原因 | 在确认弹窗内展示校验提示 | P0 | 用户确认 |\n\n## 五、需求详情",
                )
                + "\n\n### 5.2 弹窗校验提示\n\n| 维度 | 需求说明 |\n| --- | --- |\n| 用户与场景 | 团队管理员提交角色变更。 |\n| 需求入口 | 角色变更确认弹窗。 |\n| 需求详情 | 展示校验提示。 |\n| 设计与交互 | 在弹窗内展示反馈。 |\n",
                encoding="utf-8",
            )
            result = evaluate_case(case, root)
            self.assertFalse(result["passed"])
            self.assertEqual(result["failures"], ["forbidden:| 5.2 |", "forbidden:### 5.2 "])

    def test_localization_case_rejects_joined_labels(self) -> None:
        repository_root = Path(__file__).resolve().parents[1]
        case_path = repository_root / "evals/prd-benchmark/cases/localization-and-tracking.json"
        case = json.loads(case_path.read_text(encoding="utf-8"))
        candidates = repository_root / "evals/prd-benchmark/candidates"
        self.assertTrue(evaluate_case(case, candidates)["passed"])
        source_candidate = (candidates / str(case["id"]) / "prd.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / str(case["id"])
            candidate.mkdir()
            candidate.joinpath("prd.md").write_text(
                source_candidate.replace(
                    "积分管理\n订阅管理\n订单管理",
                    "积分管理 / 订阅管理 / 订单管理",
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                evaluate_case(case, root)["failures"],
                ["forbidden:积分管理 / 订阅管理 / 订单管理"],
            )


if __name__ == "__main__":
    unittest.main()
