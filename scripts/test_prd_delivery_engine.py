#!/usr/bin/env python3
"""End-to-end contract tests for the v2 deterministic PRD engine."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "scripts" / "prd_request_controller.py"


class PrdDeliveryEngineTest(unittest.TestCase):
    def run_controller(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(CONTROLLER), *args], cwd=ROOT, text=True, capture_output=True, check=False)

    def deliver(self, folder: Path, *start_args: str) -> dict[str, object]:
        completed = self.run_controller(*start_args, "--run-folder", str(folder))
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "complete")
        validation = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_outputs.py"), str(folder)], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
        for name in ("prd.md", "prd.html", "run-log.yaml", "assets"):
            self.assertTrue((folder / name).exists(), name)
        return payload

    def test_new_implemented_composition_and_revision_deliver_in_one_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.deliver(root / "new", "--request", "为审批人增加审批提醒功能", "--new-requirement")

            evidence = root / "evidence.json"
            evidence.write_text('{"observed": "导出功能"}', encoding="utf-8")
            self.deliver(root / "implemented", "--request", "已实现导出功能，生成 PRD", "--new-requirement", "--implemented-evidence", str(evidence))

            source = root / "source.md"
            source.write_text("# 旧 PRD\n\n### 5.1 结算流程\n", encoding="utf-8")
            self.deliver(root / "composition", "--request", "组合结算流程生成 PRD", "--new-requirement", "--extract-from", str(source))

            revision = root / "revision"
            revision.mkdir()
            baseline = (root / "new" / "prd.md").read_text(encoding="utf-8").replace("一、主流程", "一、旧主流程", 1)
            revision.joinpath("prd.md").write_text(baseline, encoding="utf-8")
            self.deliver(revision, "--request", "更新审批提醒的失败反馈", "--revise", "--revision-requirement-id", "5.1")

    def test_missing_product_context_asks_once_before_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "needs-input"
            result = self.run_controller("--request", "生成", "--new-requirement", "--run-folder", str(folder))
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["status"], "needs_input")
            answered = self.run_controller("--run-folder", str(folder), "--answers", "面向审批人，在审批任务到期前提醒并支持重试")
            self.assertEqual(answered.returncode, 0, answered.stdout + answered.stderr)
            completed = answered
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_revision_reexecutes_completed_run_and_reuses_matching_figure_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "revision"
            self.deliver(folder, "--request", "生成“字幕擦除”功能 PRD", "--new-requirement")
            asset = folder / "assets" / "字幕擦除-入口.png"
            asset.write_bytes(bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                "0000000d49444154789c6360f8cfc000000401010018dd8db00000000049454e44ae426082"
            ))
            self.deliver(folder, "--request", "更新字幕擦除的失败反馈", "--revise", "--revision-requirement-id", "5.1")
            markdown = (folder / "prd.md").read_text(encoding="utf-8")
            trace = (folder / "run-log.yaml").read_text(encoding="utf-8")
            self.assertIn('[[prd-detail-media src="./assets/字幕擦除-入口.png"', markdown)
            self.assertIn("revised_requirement_ids:\n  - '5.1'", trace)
            self.assertIn('src="./assets/字幕擦除-入口.png"', (folder / "prd.html").read_text(encoding="utf-8"))

    def test_path_only_revision_requests_one_scope_question(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "revision"
            self.deliver(folder, "--request", "生成字幕擦除功能 PRD", "--new-requirement")
            result = self.run_controller(
                "--request", f"请用当前任务绑定的最新 PM Copilot 修订现有 PRD，目标: {folder / 'prd.md'}",
                "--run-folder", str(folder), "--revise", "--revision-requirement-id", "5.1",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "needs_input")
            self.assertIn("标题和章节位置", payload["questions"][0])

    def test_assets_selectors_and_append_share_the_same_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            asset = root / "review.png"
            asset.write_bytes(bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                "0000000d49444154789c6360f8cfc000000401010018dd8db00000000049454e44ae426082"
            ))
            first = root / "first.md"
            second = root / "second.md"
            first.write_text("# A\n\n### 5.1 入口\n", encoding="utf-8")
            second.write_text("# B\n\n### 5.2 结果\n", encoding="utf-8")
            folder = root / "composition"
            self.deliver(folder, "--request", "组合入口和结果生成 PRD", "--new-requirement", "--extract-from", str(first), "--extract-from", str(second), "--extract-selector", "5.1", "--extract-selector", "5.2", "--asset", str(asset))
            self.assertTrue((folder / "assets" / "review.png").is_file())
            baseline = (folder / "prd.md").read_text(encoding="utf-8")
            (folder / "prd.md").write_text(baseline + "\n## 六、埋点需求\n\n| 事件 | 事件名称 | 上报时机 | 附加参数 | 备注 |\n| --- | --- | --- | --- | --- |\n", encoding="utf-8")
            self.deliver(
                folder,
                "--request", "将当前已实现的“字幕擦除”功能合并追加到此。该功能位于视频结果节点顶部工具栏，入口位置在“片段”。",
                "--append-implemented-feature", "--asset", str(asset),
            )
            markdown = (folder / "prd.md").read_text(encoding="utf-8")
            self.assertIn("### 5.2 组合来源 second.md 中的 结果", markdown)
            self.assertIn("### 5.3 字幕擦除", markdown)
            self.assertLess(markdown.index("### 5.2 组合来源 second.md 中的 结果"), markdown.index("### 5.3 字幕擦除"))
            self.assertLess(markdown.index("### 5.3 字幕擦除"), markdown.index("## 六、埋点需求"))
            self.assertLess(markdown.index("| 5.2 | 组合来源 second.md 中的 结果 |"), markdown.index("| 5.3 | 字幕擦除 |"))
            self.assertIn("# 组合入口和结果、字幕擦除 -", markdown)
            self.assertIn("| 需求来源 | 组合入口和结果生成 PRD；追加已实现功能：字幕擦除 |", markdown)
            self.assertIn("| 影响范围 | 组合入口和结果、字幕擦除 |", markdown)
            self.assertIn("| v0.2 |", markdown)
            self.assertIn("新增已实现功能：字幕擦除", markdown)
            self.assertIn('[[prd-detail-media src="./assets/review.png"', markdown)
            html = (folder / "prd.html").read_text(encoding="utf-8")
            self.assertIn('class="prd-detail-media-block"', html)
            self.assertIn('src="./assets/review.png"', html)


if __name__ == "__main__":
    unittest.main()
