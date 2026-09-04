#!/usr/bin/env python3
"""Regression checks for supported PM Copilot output directory layouts."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from validate_outputs import (
    _contains_unlocalized_english_copy,
    _proven_preserved_legacy_requirement_ids,
    check_artifact_lineage_trace,
    check_chinese_prd,
    check_folder,
    check_implemented_feature_prd_trace,
    check_readiness_trace,
    check_requirement_detail_structure,
    check_requirement_figure_rows,
    check_requirement_detail_media_blocks,
    check_run_log_agent_evidence,
    extract_yaml_block,
    probable_english_copy_lines,
    yaml_list_field_has_values,
)
from revision_scope import requirement_sections


class ValidateOutputsTest(unittest.TestCase):
    @staticmethod
    def _write_readiness_trace(
        folder: Path,
        *,
        quality_passed: str = "false",
        validation_status: str = "pending",
        final_status: str = "deterministic trace ready for validation",
    ) -> None:
        folder.joinpath("run-log.yaml").write_text(
            "pm_copilot_revision: controller-deterministic-trace\n"
            "readiness:\n"
            "  prd_status: ready for engineering\n"
            "  engineering_handoff_status: not_generated\n"
            "  launch_status: not applicable\n"
            "  engineering_blockers: []\n"
            "  launch_blockers: []\n"
            "review_scores: []\n"
            "quality_thresholds: []\n"
            "termination_condition:\n"
            "  status: degraded\n"
            "quality_decision:\n"
            f"  passed: {quality_passed}\n"
            "validation_results:\n"
            "  - command: validate_outputs.py\n"
            f"    status: {validation_status}\n"
            "failures: []\n"
            f"final_status: {final_status}\n",
            encoding="utf-8",
        )

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

    def test_staging_accepts_explicit_controller_pre_final_readiness_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = (
                Path(temporary)
                / ".sample-2026-07-30.delivery-stage"
                / "sample-2026-07-30"
            )
            folder.mkdir(parents=True)
            self._write_readiness_trace(folder)
            check_readiness_trace(folder, staging=True)

    def test_staging_accepts_safe_dump_controller_pre_final_trace(self) -> None:
        """The controller emits root-level YAML list items without indentation."""
        trace = {
            "pm_copilot_revision": "controller-deterministic-trace",
            "readiness": {
                "prd_status": "ready for engineering",
                "engineering_handoff_status": "not_generated",
                "launch_status": "not applicable",
                "engineering_blockers": [],
                "launch_blockers": [],
            },
            "review_scores": [],
            "quality_thresholds": [],
            "termination_condition": {"status": "degraded"},
            "quality_decision": {"passed": False},
            "validation_results": [{"command": "validate_outputs.py", "status": "pending"}],
            "failures": [],
            "final_status": "deterministic trace ready for validation",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staged = root / ".sample-2026-07-30.delivery-stage" / "sample-2026-07-30"
            canonical = root / "pm-copilot-outputs" / "sample-2026-07-30"
            staged.mkdir(parents=True)
            canonical.mkdir(parents=True)
            content = yaml.safe_dump(trace, allow_unicode=True, sort_keys=False)
            self.assertIn("validation_results:\n- command:", content)
            for folder in (staged, canonical):
                (folder / "run-log.yaml").write_text(content, encoding="utf-8")

            check_readiness_trace(staged, staging=True)
            with self.assertRaises(SystemExit):
                check_readiness_trace(canonical)

    def test_yaml_list_helpers_accept_safe_dump_indentationless_children(self) -> None:
        content = yaml.safe_dump({
            "agent_execution_evidence": [{"phase": "delivery", "status": "complete"}],
            "source_files": ["src/page.tsx"],
        }, allow_unicode=True, sort_keys=False)
        self.assertIn("agent_execution_evidence:\n- phase:", content)
        self.assertIn("source_files:\n- src/page.tsx", content)
        self.assertIn("- phase: delivery", extract_yaml_block(content, "agent_execution_evidence"))
        self.assertTrue(yaml_list_field_has_values(content, "source_files"))

    def test_pre_final_controller_trace_is_rejected_in_canonical_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pm-copilot-outputs" / "sample-2026-07-30"
            folder.mkdir(parents=True)
            self._write_readiness_trace(folder)
            with self.assertRaises(SystemExit):
                check_readiness_trace(folder)

    def test_staging_rejects_pre_final_trace_outside_delivery_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pm-copilot-outputs" / "sample-2026-07-30"
            folder.mkdir(parents=True)
            self._write_readiness_trace(folder)
            with self.assertRaises(SystemExit):
                check_readiness_trace(folder, staging=True)

    def test_staging_requires_all_controller_pre_final_markers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = (
                Path(temporary)
                / ".sample-2026-07-30.delivery-stage"
                / "sample-2026-07-30"
            )
            folder.mkdir(parents=True)
            self._write_readiness_trace(folder, validation_status="passed")
            with self.assertRaises(SystemExit):
                check_readiness_trace(folder, staging=True)

    def test_canonical_quality_decision_requires_its_own_passed_field(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pm-copilot-outputs" / "sample-2026-07-30"
            folder.mkdir(parents=True)
            self._write_readiness_trace(folder, quality_passed="false")
            with folder.joinpath("run-log.yaml").open("a", encoding="utf-8") as handle:
                handle.write("unrelated_check:\n  passed: true\n")
            with self.assertRaises(SystemExit):
                check_readiness_trace(folder)

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

    def test_in_place_revision_preserves_only_proven_legacy_detail_media(self) -> None:
        text = """## 五、需求详情

### 5.1 已选中需求

[[prd-detail-media src="./assets/selected.png" alt="selected" copy="已选中需求"]]

### 5.2 未选中历史需求

![历史图示](assets/legacy.png)<small>历史图示</small>
"""
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            sections = requirement_sections(text)
            evidence = {
                "mode": "in_place_revision",
                "controller_scope_ids": ["5.1"],
                "scope_validation": {"status": "passed"},
                "scope_manifest": {
                    "requirement_ids": ["5.1"],
                    "baseline": {"requirement_sections": {
                        requirement_id: {"sha256": section["sha256"]}
                        for requirement_id, section in sections.items()
                    }},
                },
            }
            (folder / "revision-evidence.json").write_text(
                json.dumps(evidence, ensure_ascii=False), encoding="utf-8",
            )
            run_log = yaml.safe_dump({"artifact_lineage": {
                "mode": "in_place_revision",
                "revised_requirement_ids": ["5.1"],
                "revision_evidence_path": "revision-evidence.json",
            }}, allow_unicode=True, sort_keys=False)
            (folder / "run-log.yaml").write_text(run_log, encoding="utf-8")

            preserved = _proven_preserved_legacy_requirement_ids(folder, run_log, text)
            self.assertEqual(preserved, {"5.2"})
            check_requirement_detail_media_blocks(
                text, preserved_legacy_requirement_ids=preserved,
            )

            changed_unselected = text.replace("未选中历史需求", "被修改的历史需求")
            self.assertEqual(
                _proven_preserved_legacy_requirement_ids(folder, run_log, changed_unselected),
                set(),
            )
            with self.assertRaises(SystemExit):
                check_requirement_detail_media_blocks(changed_unselected)

            selected_legacy = text.replace(
                '[[prd-detail-media src="./assets/selected.png" alt="selected" copy="已选中需求"]]',
                '![新图示](assets/selected.png)<small>新图示</small>',
            )
            with self.assertRaises(SystemExit):
                check_requirement_detail_media_blocks(
                    selected_legacy, preserved_legacy_requirement_ids=preserved,
                )

    def test_chinese_localization_allows_structural_identifier_labels_only(self) -> None:
        self.assertFalse(_contains_unlocalized_english_copy("Task ID"))
        self.assertFalse(_contains_unlocalized_english_copy("Task ID 已复制"))
        self.assertFalse(_contains_unlocalized_english_copy("URL 已复制"))
        self.assertFalse(_contains_unlocalized_english_copy("Task ID\n任务 ID 已复制"))
        self.assertTrue(_contains_unlocalized_english_copy("Save changes"))
        self.assertTrue(_contains_unlocalized_english_copy("Task ID copied"))
        self.assertTrue(_contains_unlocalized_english_copy("Task ID\nSave changes"))
        self.assertEqual(
            probable_english_copy_lines("Task ID\nOrder ID\nUser ID"),
            [],
        )
        self.assertEqual(
            probable_english_copy_lines("Task ID\nSave changes"),
            ["Save changes"],
        )

    def test_in_place_revision_preserves_only_proven_legacy_figure_field(self) -> None:
        """An untouched legacy 图示 row is not a license for changed content."""
        text = """# 更新节点结果提示 - 2026-09-04

## 一、文档说明

### 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 需求来源 | 用户确认的节点结果提示改动 |
| 目标用户 | 画布创作者 |
| 影响范围 | 节点结果提示 |
| 文档状态 | 可评审 |
| 文档负责人 | 产品 |

### 2. 版本记录

| 版本 | 日期 | 变更内容 | 负责人 |
| --- | --- | --- |
| v1.0 | 2026-09-04 | 更新节点结果提示 | 产品 |

## 二、需求背景

用户需要清晰查看节点执行结果。

## 四、需求清单

| 详情编号 | 需求名称 | 目标用户 | 用户场景 / 触发 | 用户问题或价值 | 需求摘要 | 优先级 | 来源 / 确认状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5.1 | 节点结果提示 | 画布创作者 | 查看节点结果 | 结果状态可发现 | 显示执行结果 | P0 | 用户确认 |
| 5.2 | 历史上传节点 | 音频用户 | 查看上传节点 | 保留历史图示 | 保留既有内容 | P1 | 已有 PRD |

## 五、需求详情

### 5.1 节点结果提示

| 维度 | 需求说明 |
| --- | --- |
| 用户与场景 | 画布创作者查看执行结果。 |
| 需求入口 | 节点状态入口。 |
| 需求详情 | 显示清晰的执行结果。 |
| 设计与交互 | 状态可点击且不遮挡画布。 |

### 5.2 历史上传节点

| 维度 | 需求说明 |
| --- | --- |
| 用户与场景 | 音频用户查看上传节点。 |
| 需求入口 | 上传节点。 |
| 需求详情 | 保留当前行为。 |
| 设计与交互 | 保留当前布局。 |
| 图示 | 历史上传节点图示。 |
"""
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            sections = requirement_sections(text)
            evidence = {
                "mode": "in_place_revision",
                "controller_scope_ids": ["5.1"],
                "scope_validation": {"status": "passed"},
                "scope_manifest": {
                    "requirement_ids": ["5.1"],
                    "baseline": {"requirement_sections": {
                        requirement_id: {"sha256": section["sha256"]}
                        for requirement_id, section in sections.items()
                    }},
                },
            }
            (folder / "revision-evidence.json").write_text(
                json.dumps(evidence, ensure_ascii=False), encoding="utf-8",
            )
            (folder / "run-log.yaml").write_text(
                yaml.safe_dump({"artifact_lineage": {
                    "mode": "in_place_revision",
                    "revised_requirement_ids": ["5.1"],
                    "revision_evidence_path": "revision-evidence.json",
                }}, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            (folder / "prd.md").write_text(text, encoding="utf-8")

            check_chinese_prd(folder)

            changed = text.replace("保留当前行为。", "被改写的历史行为。")
            (folder / "prd.md").write_text(changed, encoding="utf-8")
            with self.assertRaises(SystemExit):
                check_chinese_prd(folder)

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

    def test_run_log_agent_evidence_accepts_safe_dump_root_list(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            trace = {
                "agent_execution_evidence": [{
                    "phase": "delivery",
                    "artifact": "prd.md",
                    "provider": "codex",
                    "model": "gpt-5.6",
                    "status": "complete",
                    "error": "",
                }],
            }
            content = yaml.safe_dump(trace, allow_unicode=True, sort_keys=False)
            self.assertIn("agent_execution_evidence:\n- phase:", content)
            (folder / "run-log.yaml").write_text(content, encoding="utf-8")
            check_run_log_agent_evidence(folder)

    def test_output_validation_rejects_fake_new_run_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = folder / "source-material" / "source-prd.md"
            source.parent.mkdir()
            source.write_text("# 旧 PRD\n", encoding="utf-8")
            folder.joinpath("run-log.yaml").write_text(
                yaml.safe_dump({
                    "agent_strategy": {"task_mode": "prd_delivery"},
                    "resume_checkpoint": {"task_mode": "prd_delivery"},
                    "artifact_lineage": {
                        "mode": "new_run",
                        "output_folder_reset": True,
                        "source_snapshot_path": "source-material/source-prd.md",
                        "source_prd_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "selected_source_scope": ["第 5 章"],
                        "historical_artifacts": [{
                            "path": "source-material/source-prd.md",
                            "role": "user_provided_input",
                            "excluded_from_current_facts": False,
                        }],
                    },
                }, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                check_artifact_lineage_trace(folder)

    def test_output_validation_rejects_inactive_implemented_feature_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            folder.joinpath("run-log.yaml").write_text(
                "agent_strategy:\n"
                "  task_mode: implemented_feature_prd\n"
                "implemented_feature_prd:\n"
                "  active: false\n"
                "  mode: implemented_feature_prd\n",
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                check_implemented_feature_prd_trace(folder)

    def test_output_validation_rejects_tampered_implemented_evidence_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            packet = folder / "source-material" / "implemented-feature-evidence.json"
            packet.parent.mkdir()
            packet.write_text('{"branch_name":"feature/canvas"}\n', encoding="utf-8")
            folder.joinpath("run-log.yaml").write_text(
                yaml.safe_dump({
                    "agent_strategy": {"task_mode": "implemented_feature_prd"},
                    "implemented_feature_prd": {
                        "active": True,
                        "mode": "implemented_feature_prd",
                        "branch_name": "feature/canvas",
                        "evidence_packet": {
                            "path": "source-material/implemented-feature-evidence.json",
                            "sha256": "0" * 64,
                            "imported_result_refs": [],
                        },
                    },
                }, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                check_implemented_feature_prd_trace(folder)

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
            '[[prd-detail-media src="./assets/state.png" alt="状态" copy="展示状态与恢复操作。"]]',
        )
        check_requirement_detail_media_blocks(compliant)
        reset_required = compliant.replace(
            'copy="展示状态与恢复操作。"',
            'copy="二、状态说明<br>1. 展示状态与恢复操作。"',
        )
        with self.assertRaises(SystemExit):
            check_requirement_detail_media_blocks(reset_required)
        with self.assertRaises(SystemExit):
            check_requirement_detail_media_blocks(compliant.replace("[[prd-detail-media", '<div class="prd-detail-media-block">[[prd-detail-media'))


if __name__ == "__main__":
    unittest.main()
