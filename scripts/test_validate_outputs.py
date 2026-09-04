#!/usr/bin/env python3
"""Regression coverage for PRD-only output validation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from validate_outputs import check_folder, check_prd_output_contract, check_tracking_context


PRD = """# 角色变更确认

## 一、文档说明
已确认范围。

## 二、需求背景
管理员需要降低误操作。

## 四、需求清单
| 编号 | 需求名称 |
| --- | --- |
| 5.1 | 角色变更确认 |

## 五、需求详情
### 5.1 角色变更确认
| 维度 | 需求说明 |
| --- | --- |
| 用户与场景 | 管理员调整成员角色。 |
| 需求入口 | 成员管理页。 |
| 需求详情 | 提交前确认变更。 |
| 设计与交互 | 清晰展示确认和取消。 |
"""


class OutputValidationTests(unittest.TestCase):
    def test_prd_contract_accepts_required_product_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prd.md").write_text(PRD, encoding="utf-8")
            check_prd_output_contract(folder, "zh")

    def test_run_folder_is_not_restricted_to_legacy_output_directory_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "any-prd-run"
            folder.mkdir()
            check_folder(folder, require_run_log=False, staging=True)

    def test_retired_split_delivery_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prototype").mkdir()
            with self.assertRaises(SystemExit):
                check_folder(folder, require_run_log=False, staging=True)

    def test_tracking_section_rejects_raw_sensitive_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prd.md").write_text(PRD + "\n## 七、埋点需求\n| 参数 | 值 |\n| --- | --- |\n| 用户手机号 | 1 |\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                check_tracking_context(folder)


if __name__ == "__main__":
    unittest.main()
