#!/usr/bin/env python3
"""Regression coverage for evidence-gated historical PRD upgrades."""

from __future__ import annotations

import tempfile
import unittest
import subprocess
from pathlib import Path

from prd_evidence_upgrade import (
    discover_output_folders,
    normalize_tracking_identifier,
    normalize_existing_tracking_rows,
    tracking_rows_from_details,
    upgrade_output,
)


PRD = """# 示例需求 - 2026-07-29

## 一、文档说明

### 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 需求来源 | 测试 |

### 2. 版本记录

| 版本 | 日期 | 变更内容 | 负责人 |
| --- | --- | --- | --- |
| v0.1 | 2026-07-29 | 首次创建 | 产品 |

## 二、需求背景

用户需要查看并确认项目创建结果。

## 四、需求清单

| 详情编号 | 需求名称 | 目标用户 | 用户场景 / 触发 | 用户问题或价值 | 需求摘要 | 优先级 | 来源 / 确认状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5.1 | 创建项目 | 项目成员 | 需要新建项目 | 快速完成创建 | 支持创建项目 | P0 | 已确认 |

## 五、需求详情

### 5.1 创建项目

| 维度 | 需求说明 |
| --- | --- |
| 用户与场景 | 项目成员需要新建项目。 |
| 需求入口 | 项目列表的创建项目入口 |
| 需求详情 | 用户点击创建项目，填写名称并提交；成功后展示创建结果。 |
| 设计与交互 | 确认按钮展示“创建项目”。 |
"""


class PRDEvidenceUpgradeTest(unittest.TestCase):
    def create_run(self, root: Path, name: str = "sample-2026-07-29") -> Path:
        folder = root / "outputs" / name
        folder.mkdir(parents=True)
        (folder / "prd.md").write_text(PRD, encoding="utf-8")
        (folder / "run-log.yaml").write_text('language: "zh"\n', encoding="utf-8")
        return folder

    def test_discovers_root_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = self.create_run(root)
            self.assertEqual(discover_output_folders([root]), [folder])

    def test_adds_tracking_from_confirmed_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = self.create_run(root)
            report = upgrade_output(folder, Path.cwd(), True, False)
            prd = (folder / "prd.md").read_text(encoding="utf-8")
            self.assertEqual(report.tracking, "added")
            self.assertIn("## 七、埋点需求", prd)
            self.assertIn("查看项目", prd)
            self.assertIn("project_view", prd)
            self.assertIn("创建项目结果展示", prd)
            self.assertNotIn("prd_5_1", prd)
            self.assertIn("| 事件 | 事件名称 | 上报时机 | 附加参数 | 备注 |", prd)

    def test_adds_same_run_matching_figure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = self.create_run(root)
            assets = folder / "assets"
            assets.mkdir()
            (assets / "创建项目-命名弹窗.png").write_bytes(b"image")
            report = upgrade_output(folder, Path.cwd(), True, False)
            prd = (folder / "prd.md").read_text(encoding="utf-8")
            self.assertEqual(report.figures, 1)
            self.assertIn("./assets/创建项目-命名弹窗.png", prd)
            self.assertIn("位置：创建项目-命名弹窗", prd)

    def test_ignores_runtime_only_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = self.create_run(root)
            assets = folder / "assets"
            assets.mkdir()
            (assets / "mermaid.min.js").write_text("runtime", encoding="utf-8")
            report = upgrade_output(folder, Path.cwd(), True, False)
            self.assertEqual(report.figures, 0)
            self.assertTrue(any(item.startswith("No same-run real visual asset") for item in report.limitations))

    def test_omits_localization_without_visible_copy_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = self.create_run(root)
            (folder / "prd.md").write_text(PRD.replace('“创建项目”', "创建项目"), encoding="utf-8")
            report = upgrade_output(folder, Path.cwd(), True, False)
            self.assertEqual(report.localization, "omitted")
            self.assertNotIn("## 六、多语言需求", (folder / "prd.md").read_text(encoding="utf-8"))

    def test_normalizes_invalid_existing_tracking_identifier(self) -> None:
        self.assertEqual(normalize_tracking_identifier("`ProjectCreated`"), "project_created")
        self.assertEqual(normalize_tracking_identifier("project-created"), "project_created")

    def test_uses_requirement_context_for_generic_followup_events(self) -> None:
        rows = tracking_rows_from_details([
            {
                "number": "5.1",
                "title": "创建项目",
                "entry": "项目列表入口",
                "description": "用户点击创建项目并展示结果。",
                "evidence_id": "E001",
            },
            {
                "number": "5.2",
                "title": "变更预览与确认",
                "entry": "创建项目后进入预览",
                "description": "用户确认变更后展示结果。",
                "evidence_id": "E002",
            },
        ])
        identifiers = {row["id"] for row in rows}
        self.assertIn("project_change_preview_view", identifiers)
        self.assertNotIn("journey_view", identifiers)

    def test_expands_generated_generic_identifier_with_event_context(self) -> None:
        prd = """## 七、埋点需求

| 事件 | 事件名称 | 上报时机 | 附加参数 | 备注 |
| --- | --- | --- | --- | --- |
| 查看框选节点批量连入目标输入点 | node_view | 页面完成首屏展示时 | / | / |
"""
        upgraded = normalize_existing_tracking_rows(prd)
        self.assertIn("node_connection_bulk_input_view", upgraded)

    def test_recompiles_generated_result_event_without_a_generic_action_suffix(self) -> None:
        prd = """## 七、埋点需求

| 事件 | 事件名称 | 上报时机 | 附加参数 | 备注 |
| --- | --- | --- | --- | --- |
| 查看首页内容发现与创作入口结果展示 | result_action_result | 操作结果展示时 | / | / |
"""
        upgraded = normalize_existing_tracking_rows(prd)
        self.assertIn("home_discovery_creation_result_display", upgraded)
        self.assertNotIn("result_action_result", upgraded)

    def test_removes_english_only_legacy_localization_from_chinese_prd(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = self.create_run(root)
            prd = (folder / "prd.md").read_text(encoding="utf-8")
            prd += "\n## 六、多语言需求\n\n```text\nCreate project\nProject created\nOpen project\n```\n"
            (folder / "prd.md").write_text(prd, encoding="utf-8")
            report = upgrade_output(folder, Path.cwd(), True, False)
            self.assertEqual(report.localization, "added")
            upgraded = (folder / "prd.md").read_text(encoding="utf-8")
            self.assertIn("## 六、多语言需求", upgraded)
            self.assertNotIn("Create project", upgraded)

    def test_historical_validation_requires_evidence_artifacts_not_run_log(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = self.create_run(root)
            (folder / "run-log.yaml").unlink()
            report = upgrade_output(folder, Path.cwd(), True, False)
            self.assertEqual(report.status, "upgraded")
            (folder / "prd.html").unlink()
            command = [
                "python3",
                str(Path.cwd() / "scripts" / "validate_outputs.py"),
                str(folder),
                "--historical-prd-upgrade",
            ]
            validated = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(validated.returncode, 0, validated.stdout + validated.stderr)
            (folder / "tool-results" / "prd-evidence-ledger.json").unlink()
            rejected = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertNotEqual(rejected.returncode, 0)
            standard = subprocess.run(command[:-1], text=True, capture_output=True, check=False)
            self.assertNotEqual(standard.returncode, 0)


if __name__ == "__main__":
    unittest.main()
