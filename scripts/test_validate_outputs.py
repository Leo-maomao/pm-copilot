#!/usr/bin/env python3
"""Regression checks for supported PM Copilot output directory layouts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from validate_outputs import check_folder, check_requirement_detail_structure, check_requirement_figure_rows


class ValidateOutputsTest(unittest.TestCase):
    def test_accepts_embedded_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "outputs" / "sample-2026-07-30"
            run.mkdir(parents=True)
            check_folder(run, require_run_log=False)

    def test_accepts_visible_global_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "pm-copilot-outputs" / "sample-2026-07-30"
            run.mkdir(parents=True)
            check_folder(run, require_run_log=False)

    def test_rejects_unknown_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "documents" / "sample-2026-07-30"
            run.mkdir(parents=True)
            with self.assertRaises(SystemExit):
                check_folder(run, require_run_log=False)

    def test_english_requirement_detail_uses_its_own_localized_contract(self) -> None:
        text = """## Requirement Details

### 5.1 Shipping Selection

| Field | Details |
|---|---|
| User and scenario | Checkout customer selects shipping. |
| Entry | Checkout review. |
| Requirement details | Show selection and total. |
| Design and interaction | Use accessible controls. |
"""
        check_requirement_detail_structure(text, "en")

    def test_requirement_figure_placeholder_requires_png_function_state_format(self) -> None:
        valid = """| 维度 | 需求说明 |
| --- | --- |
| 用户与场景 | 管理员修改成员角色。 |
| 需求入口 | 成员管理页。 |
| 需求详情 | 展示确认操作。 |
| 设计与交互 | 提供取消操作。 |
| 图示 | 占位图：成员管理-角色变更确认.png |
"""
        check_requirement_figure_rows(valid)

        with self.assertRaises(SystemExit):
            check_requirement_figure_rows(valid.replace(".png", ".jpg"))


if __name__ == "__main__":
    unittest.main()
