#!/usr/bin/env python3
"""Regression checks for supported PM Copilot output directory layouts."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import yaml

from validate_outputs import (
    check_artifact_lineage_trace,
    check_folder,
    check_implemented_feature_prd_trace,
    check_readiness_trace,
    check_requirement_detail_structure,
    check_requirement_figure_rows,
    check_requirement_detail_media_blocks,
    check_run_log_agent_evidence,
)


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
