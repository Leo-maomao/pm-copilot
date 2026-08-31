#!/usr/bin/env python3
"""Regression checks for supported PM Copilot output directory layouts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from validate_outputs import (
    check_folder,
    check_requirement_detail_structure,
    check_requirement_figure_rows,
    check_requirement_detail_media_blocks,
    check_run_log_agent_evidence,
)


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

    def test_run_log_requires_attributable_provider_model_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "run-log.yaml").write_text(
                "agent_execution_evidence:\n"
                "  - phase: delivery\n"
                "    artifact: prd.md\n"
                "    provider: codex\n"
                "    model: gpt-5.6\n"
                "    status: complete\n",
                encoding="utf-8",
            )
            check_run_log_agent_evidence(folder)
            (folder / "run-log.yaml").write_text(
                "agent_execution_evidence:\n"
                "  - phase: delivery\n"
                "    artifact: prd.md\n"
                "    provider: codex\n"
                "    model: unknown\n"
                "    status: complete\n",
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                check_run_log_agent_evidence(folder)

    def test_requirement_detail_images_require_media_block(self) -> None:
        ordinary = """## 需求详情

### 5.1 截图状态

| 维度 | 需求说明 |
| --- | --- |
| 需求详情 | <img src=\"./assets/state.png\" alt=\"状态\" /> |
"""
        with self.assertRaises(SystemExit):
            check_requirement_detail_media_blocks(ordinary)
        compliant = ordinary.replace(
            '<img src="./assets/state.png" alt="状态" />',
            '<div class="prd-detail-media-block"><div class="prd-detail-media"><img src="./assets/state.png" alt="状态" /></div><div class="prd-detail-copy">展示状态与恢复操作。</div></div>',
        )
        check_requirement_detail_media_blocks(compliant)


if __name__ == "__main__":
    unittest.main()
