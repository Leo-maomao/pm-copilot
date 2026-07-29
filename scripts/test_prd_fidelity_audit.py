#!/usr/bin/env python3
"""Regression checks for historical PRD scope-preservation review."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from audit_historical_prd_fidelity import audit


def prd(detail_count: int, versions: str) -> str:
    details = "\n".join(
        f"### 5.{index} 需求{index}\n\n| 维度 | 需求说明 |\n| --- | --- |\n| 用户与场景 | 用户场景。 |\n| 需求入口 | 入口。 |\n| 需求详情 | 明确规则。 |\n| 设计与交互 | 明确反馈。 |\n"
        for index in range(1, detail_count + 1)
    )
    return f"# 历史需求\n\n## 一、文档说明\n\n### 1. 文档信息\n\n| 项目 | 内容 |\n| --- | --- |\n| 文档状态 | 可评审 |\n\n### 2. 版本记录\n\n{versions}\n\n## 五、需求详情\n\n{details}"


class HistoricalPrdFidelityAuditTest(unittest.TestCase):
    def test_flags_scope_and_version_loss(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prd.md").write_text(prd(3, "| v1.0 | 2026-07-01 | 首次创建 |"), encoding="utf-8")
            (folder / "run-log.yaml").write_text(
                'related_requirement_ids: ["R1", "R2", "R3", "R4"]\nresult: "prd.md updated with v1.2 version record."\n',
                encoding="utf-8",
            )
            report = audit(folder)
            self.assertEqual(report["status"], "needs_restoration")
            self.assertEqual(len(report["findings"]), 2)

    def test_accepts_preserved_scope_and_version_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prd.md").write_text(
                prd(4, "| v1.0 | 2026-07-01 | 首次创建 |\n| v1.2 | 2026-07-02 | 需求变更 |"),
                encoding="utf-8",
            )
            (folder / "run-log.yaml").write_text(
                'related_requirement_ids: ["R1", "R2", "R3", "R4"]\nresult: "prd.md updated with v1.2 version record."\n',
                encoding="utf-8",
            )
            self.assertEqual(audit(folder)["status"], "passed")

    def test_detects_unquoted_requirement_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prd.md").write_text(prd(3, "| v1.0 | 2026-07-01 | 首次创建 |"), encoding="utf-8")
            (folder / "run-log.yaml").write_text("related_requirement_ids: [R1, R2, R3, R4]\n", encoding="utf-8")
            self.assertEqual(audit(folder)["status"], "needs_restoration")


if __name__ == "__main__":
    unittest.main()
