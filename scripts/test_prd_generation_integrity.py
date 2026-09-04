#!/usr/bin/env python3
"""Regression checks for implemented-feature PRD isolation and coverage review."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from validate_agent_trace import validate_implemented_feature_prd_integrity

DEFAULT_IMPLEMENTED_FEATURE = """implemented_feature_prd:
  active: true
  mode: implemented_feature_prd
  screenshots_and_placeholders:
    - target_ref: 5.1
      coverage_decision: not_required
      rationale: 当前需求不涉及用户可见表面。"""


def make_run_log(run_name: str, *, active: bool = True, self_reference: bool = False) -> str:
    reference = f"pm-copilot-outputs/{run_name}/prd.md" if self_reference else "inputs/old-prd.md"
    return f"""task:
  brief_path: {reference}
agent_strategy:
  task_mode: implemented_feature_prd
resume_checkpoint:
  task_mode: implemented_feature_prd
context:
  files_loaded: []
artifact_lineage:
  mode: replacement_run
  historical_artifacts:
    - path: {reference}
      role: comparison_only
      excluded_from_current_facts: true
  output_folder_reset: true
implemented_feature_prd:
  active: {str(active).lower()}
  mode: implemented_feature_prd
  screenshots_and_placeholders:
    - target_ref: 5.1
      coverage_decision: not_required
      rationale: 当前需求不涉及用户可见表面。
requirement_coverage_review:
  - requirement_id: 5.1
    visual_decision: not_required
    visual_rationale: 当前需求不涉及用户可见表面。
    localization_decision: not_needed
    localization_rationale: 当前 locale diff 未变更该状态文案。
    changed_copy_items: []
    tracking_decision: included
    tracking_rationale: 裁剪提交及结果是新用户行为和结果。
    measurable_actions:
      - 裁剪提交
    measurable_outcomes:
      - 裁剪成功
"""


class PrdGenerationIntegrityTest(unittest.TestCase):
    def test_accepts_isolated_covered_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pm-copilot-outputs" / "new-run"
            folder.mkdir(parents=True)
            (folder / "prd.md").write_text("| 5.1 | 裁剪 |\n\n## 六、埋点需求\n", encoding="utf-8")
            log = folder / "run-log.yaml"
            log.write_text(make_run_log("old-run"), encoding="utf-8")
            self.assertEqual(
                validate_implemented_feature_prd_integrity(
                    log, log.read_text(encoding="utf-8"), "implemented_feature_prd"
                ),
                [],
            )

    def test_rejects_self_referenced_or_disarmed_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pm-copilot-outputs" / "same-run"
            folder.mkdir(parents=True)
            (folder / "prd.md").write_text("| 5.1 | 裁剪 |\n\n## 六、埋点需求\n", encoding="utf-8")
            log = folder / "run-log.yaml"
            log.write_text(make_run_log("same-run", active=False, self_reference=True), encoding="utf-8")
            failures = validate_implemented_feature_prd_integrity(
                log, log.read_text(encoding="utf-8"), "implemented_feature_prd"
            )
            self.assertTrue(any("active" in failure for failure in failures))
            self.assertTrue(any("new run folder" in failure for failure in failures))

    def test_rejects_visual_omission_and_commented_tracking_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pm-copilot-outputs" / "new-run"
            folder.mkdir(parents=True)
            (folder / "prd.md").write_text(
                "| 5.1 | 裁剪 |\n\n## 六、埋点需求\n",
                encoding="utf-8",
            )
            log = folder / "run-log.yaml"
            log.write_text(
                make_run_log("old-run").replace(
                    DEFAULT_IMPLEMENTED_FEATURE,
                    """implemented_feature_prd:
  active: true
  mode: implemented_feature_prd
  ui_surfaces:
    - surface: 媒体裁剪节点
  screenshots_and_placeholders:
    - target_ref: 5.1
      surface: 媒体裁剪节点
      coverage_decision: not_required""",
                ).replace(
                    "measurable_actions:\n      - 裁剪提交",
                    "measurable_actions: [] # 裁剪提交",
                ).replace(
                    "measurable_outcomes:\n      - 裁剪成功",
                    "measurable_outcomes: [] # 裁剪成功",
                ).replace(
                    "tracking_decision: included",
                    "tracking_decision: not_needed",
                ).replace(
                    "裁剪提交及结果是新用户行为和结果。",
                    "当前改动未包含事件定义。",
                ),
                encoding="utf-8",
            )
            failures = validate_implemented_feature_prd_integrity(
                log, log.read_text(encoding="utf-8"), "implemented_feature_prd"
            )
            self.assertTrue(any("cannot omit a figure" in failure for failure in failures))
            self.assertTrue(any("inline comment" in failure for failure in failures))
            self.assertTrue(any("event definitions" in failure for failure in failures))

    def test_rejects_untried_visual_capture_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pm-copilot-outputs" / "new-run"
            folder.mkdir(parents=True)
            (folder / "prd.md").write_text("| 5.1 | 裁剪 |\n", encoding="utf-8")
            log = folder / "run-log.yaml"
            log.write_text(
                make_run_log("old-run").replace(
                    DEFAULT_IMPLEMENTED_FEATURE,
                    """implemented_feature_prd:
  active: true
  mode: implemented_feature_prd
  screenshots_and_placeholders:
    - target_ref: 5.1
      coverage_decision: required_placeholder
  visual_capture_recovery:
    - attempt_id: visual-playwright
      method: playwright
      status: skipped
    - attempt_id: visual-devtools
      method: chrome_devtools
      status: skipped
    - attempt_id: visual-computer-use
      method: computer_use
      status: skipped""",
                ).replace("visual_decision: not_required", "visual_decision: required_placeholder"),
                encoding="utf-8",
            )
            failures = validate_implemented_feature_prd_integrity(
                log, log.read_text(encoding="utf-8"), "implemented_feature_prd"
            )
            self.assertTrue(any("existing-preview discovery" in failure for failure in failures))
            self.assertTrue(any("must be attempted, not skipped" in failure for failure in failures))

    def test_accepts_capability_based_capture_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pm-copilot-outputs" / "new-run"
            folder.mkdir(parents=True)
            (folder / "prd.md").write_text(
                "| 5.1 | 裁剪 |\n\n## 六、埋点需求\n",
                encoding="utf-8",
            )
            result_dir = folder / "tool-results" / "visual-capture"
            result_dir.mkdir(parents=True)
            for name in ("preview", "runtime", "state", "playwright", "devtools", "computer-use"):
                (result_dir / f"{name}.txt").write_text("attempted\n", encoding="utf-8")
            log = folder / "run-log.yaml"
            log.write_text(
                make_run_log("old-run").replace(
                    DEFAULT_IMPLEMENTED_FEATURE,
                    """implemented_feature_prd:
  active: true
  mode: implemented_feature_prd
  screenshots_and_placeholders:
    - target_ref: 5.1
      coverage_decision: required_placeholder
      rationale: 裁剪编辑态需要可视审阅。
  visual_runtime_capability:
    runtime_discovery:
      - capability: existing_preview_discovery
        status: failed
        action: 检查当前工作区已有预览地址。
        evidence: 未发现可复用预览。
        result_ref: tool-results/visual-capture/preview.txt
      - capability: project_runtime_activation
        status: blocked
        action: 按项目脚本尝试启动预览。
        evidence: 本地依赖未满足。
        result_ref: tool-results/visual-capture/runtime.txt
      - capability: test_state_recovery
        status: blocked
        action: 尝试准备可复现测试状态。
        evidence: 缺少测试身份。
        result_ref: tool-results/visual-capture/state.txt
  visual_capture_recovery:
    - attempt_id: visual-playwright
      method: playwright
      status: blocked
      action: 使用自动化浏览器打开候选预览。
      evidence: 无可访问运行态。
      result_ref: tool-results/visual-capture/playwright.txt
    - attempt_id: visual-devtools
      method: chrome_devtools
      status: blocked
      action: 检查已认证浏览器会话。
      evidence: 未发现可用会话。
      result_ref: tool-results/visual-capture/devtools.txt
    - attempt_id: visual-computer-use
      method: computer_use
      status: blocked
      action: 尝试手动进入可复现页面。
      evidence: 无可访问运行态。
      result_ref: tool-results/visual-capture/computer-use.txt""",
                ).replace("visual_decision: not_required", "visual_decision: required_placeholder"),
                encoding="utf-8",
            )
            self.assertEqual(
                validate_implemented_feature_prd_integrity(
                    log, log.read_text(encoding="utf-8"), "implemented_feature_prd"
                ),
                [],
            )

    def test_rejects_empty_surface_inventory_for_visual_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pm-copilot-outputs" / "new-run"
            folder.mkdir(parents=True)
            (folder / "prd.md").write_text(
                """| 5.1 | 节点连线开关 |\n\n### 5.1 节点连线开关\n\n| 维度 | 需求说明 |\n| --- | --- |\n| 用户与场景 | 用户编辑画布。 |\n| 需求入口 | 画布工具栏中的节点连线图标。 |\n| 需求详情 | 一、状态<br>1. 用户可切换连线显示。 |\n| 设计与交互 | 图标清晰可见。 |\n\n## 六、埋点需求\n""",
                encoding="utf-8",
            )
            log = folder / "run-log.yaml"
            log.write_text(make_run_log("old-run"), encoding="utf-8")
            failures = validate_implemented_feature_prd_integrity(
                log, log.read_text(encoding="utf-8"), "implemented_feature_prd"
            )
            self.assertTrue(any("cannot omit a figure for a user-facing requirement" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
