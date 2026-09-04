#!/usr/bin/env python3
"""Regression coverage for controller-owned in-place revision scope checks."""

from __future__ import annotations

import unittest

from revision_scope import (
    build_revision_scope_manifest,
    validate_rendered_html_scope,
    validate_revision_scope,
)


BASELINE = """# Canvas PRD

| ID | Requirement |
| --- | --- |
| 5.1 | 节点执行结果 |
| 5.2 | Upload node |

### 5.1 节点执行结果
Old result behavior.
[[prd-detail-media src="./assets/old-result.png" alt="old" copy="old"]]

### 5.2 Upload node
Existing upload behavior.
[[prd-detail-media src="./assets/upload-node.png" alt="upload" copy="upload"]]

## 六、多语言需求
| 文案 | 说明 |
| --- | --- |
| 旧执行结果 | Existing execution copy |
| 上传节点 | Existing upload copy |
"""


UPDATED = """# Canvas PRD

| ID | Requirement |
| --- | --- |
| 5.1 | 节点执行结果 |
| 5.2 | Upload node |

### 5.1 节点执行结果
Execution success and failure rules.
[[prd-detail-media src="./assets/execution-success.png" alt="success" copy="执行成功"]]
[[prd-detail-media src="./assets/execution-failure.png" alt="failure" copy="执行失败"]]

### 5.2 Upload node
Existing upload behavior.
[[prd-detail-media src="./assets/upload-node.png" alt="upload" copy="upload"]]

## 六、多语言需求
| 文案 | 说明 |
| --- | --- |
| 执行成功 | Execution status title |
| 执行失败 | Execution status title |
| 上传节点 | Existing upload copy |
"""


BASELINE_ASSETS = {
    "assets/old-result.png": "old",
    "assets/upload-node.png": "upload",
    "assets/execution-success.png": "success",
    "assets/execution-failure.png": "failure",
}


class RevisionScopeTests(unittest.TestCase):
    def manifest(self) -> dict[str, object]:
        return build_revision_scope_manifest(
            baseline_markdown=BASELINE,
            baseline_assets=BASELINE_ASSETS,
            requirement_ids=["5.1"],
            confirmed_scope_text=(
                "仅更新 5.1 对应多语言文案。5.1 仅保留两张固定顺序图示："
                "./assets/execution-success.png、./assets/execution-failure.png；不引用第三张图。"
            ),
            authority="explicit user confirmation",
        )

    def validate(self, candidate: str = UPDATED, assets: dict[str, str] | None = None) -> dict[str, object]:
        return validate_revision_scope(
            self.manifest(),
            baseline_markdown=BASELINE,
            candidate_markdown=candidate,
            baseline_assets=BASELINE_ASSETS,
            candidate_assets=assets or BASELINE_ASSETS,
        )

    def test_selected_two_images_pass_while_unselected_section_keeps_its_image(self) -> None:
        report = self.validate()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(
            report["selected_requirement_images"],
            {"5.1": ["assets/execution-success.png", "assets/execution-failure.png"]},
        )

    def test_extra_or_wrong_order_selected_image_fails_without_counting_other_sections(self) -> None:
        extra = UPDATED.replace(
            '[[prd-detail-media src="./assets/execution-failure.png" alt="failure" copy="执行失败"]]',
            '[[prd-detail-media src="./assets/execution-failure.png" alt="failure" copy="执行失败"]]\n'
            '[[prd-detail-media src="./assets/old-result.png" alt="extra" copy="extra"]]',
        )
        report = self.validate(extra)
        self.assertEqual(report["status"], "failed")
        self.assertIn("exact-count", "\n".join(report["failures"]))

        reversed_images = UPDATED.replace(
            '[[prd-detail-media src="./assets/execution-success.png" alt="success" copy="执行成功"]]\n'
            '[[prd-detail-media src="./assets/execution-failure.png" alt="failure" copy="执行失败"]]',
            '[[prd-detail-media src="./assets/execution-failure.png" alt="failure" copy="执行失败"]]\n'
            '[[prd-detail-media src="./assets/execution-success.png" alt="success" copy="执行成功"]]',
        )
        report = self.validate(reversed_images)
        self.assertEqual(report["status"], "failed")
        self.assertIn("exact-count", "\n".join(report["failures"]))

    def test_unselected_requirement_and_assets_are_frozen(self) -> None:
        changed_section = UPDATED.replace("Existing upload behavior.", "Changed upload behavior.")
        report = self.validate(changed_section)
        self.assertEqual(report["status"], "failed")
        self.assertIn("protected requirement section 5.2 changed", report["failures"])

        changed_assets = dict(BASELINE_ASSETS)
        changed_assets["assets/upload-node.png"] = "changed"
        report = self.validate(assets=changed_assets)
        self.assertEqual(report["status"], "failed")
        self.assertIn("protected asset changed or was removed: assets/upload-node.png", report["failures"])

    def test_only_linked_localization_rows_may_change(self) -> None:
        report = self.validate()
        self.assertEqual(report["status"], "passed")
        unrelated = UPDATED.replace("Existing upload copy", "Changed upload copy")
        report = self.validate(unrelated)
        self.assertEqual(report["status"], "failed")
        self.assertIn("outside the confirmed revision scope", "\n".join(report["failures"]))

    def test_material_selected_revision_may_append_but_not_rewrite_version_history(self) -> None:
        baseline = """# Canvas PRD

## 一、文档说明

### 2. 版本记录

| 版本 | 日期 | 变更内容 | 负责人 |
| --- | --- | --- | --- |
| v1.0 | 2026-09-01 | 首次创建 | 产品 |

## 四、需求清单

| ID | Requirement |
| --- | --- |
| 5.1 | 节点执行结果 |
| 5.2 | Upload node |

## 五、需求详情

### 5.1 节点执行结果
Old result behavior.

### 5.2 Upload node
Existing upload behavior.
"""
        candidate = baseline.replace(
            "| v1.0 | 2026-09-01 | 首次创建 | 产品 |\n",
            "| v1.0 | 2026-09-01 | 首次创建 | 产品 |\n"
            "| v1.1 | 2026-09-04 | 补充节点执行成功与失败规则 | 产品 |\n",
        ).replace("Old result behavior.", "Execution success and failure rules.")
        manifest = build_revision_scope_manifest(
            baseline_markdown=baseline,
            baseline_assets={},
            requirement_ids=["5.1"],
            confirmed_scope_text="更新 5.1 的节点执行规则。",
            authority="explicit user confirmation",
        )
        report = validate_revision_scope(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=candidate,
            baseline_assets={},
            candidate_assets={},
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(
            report["allowed_version_history_rows"],
            ["| v1.1 | 2026-09-04 | 补充节点执行成功与失败规则 | 产品 |"],
        )

        missing_record = baseline.replace("Old result behavior.", "Execution success and failure rules.")
        report = validate_revision_scope(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=missing_record,
            baseline_assets={},
            candidate_assets={},
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn(
            "material selected requirement change requires an appended version history record",
            report["failures"],
        )

        rewritten = candidate.replace("首次创建", "改写旧记录")
        report = validate_revision_scope(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=rewritten,
            baseline_assets={},
            candidate_assets={},
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn("protected version history rows changed or were reordered", report["failures"])

    def test_version_history_allowance_keeps_other_document_metadata_frozen(self) -> None:
        baseline = """# Canvas PRD

## 一、文档说明

### 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 文档状态 | 可评审 |

### 2. 版本记录

| 版本 | 日期 | 变更内容 | 负责人 |
| --- | --- | --- | --- |
| v1.0 | 2026-09-01 | 首次创建 | 产品 |

### 5.1 节点执行结果
Old result behavior.
"""
        candidate = baseline.replace(
            "| v1.0 | 2026-09-01 | 首次创建 | 产品 |\n",
            "| v1.0 | 2026-09-01 | 首次创建 | 产品 |\n"
            "| v1.1 | 2026-09-04 | 补充节点执行规则 | 产品 |\n",
        ).replace("Old result behavior.", "New result behavior.").replace("可评审", "已发布")
        manifest = build_revision_scope_manifest(
            baseline_markdown=baseline,
            baseline_assets={},
            requirement_ids=["5.1"],
            confirmed_scope_text="更新 5.1 的节点执行规则。",
            authority="explicit user confirmation",
        )
        report = validate_revision_scope(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=candidate,
            baseline_assets={},
            candidate_assets={},
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn("outside the confirmed revision scope", "\n".join(report["failures"]))

    def test_version_history_entry_must_follow_preserved_records(self) -> None:
        baseline = """### 2. Version History

| Version | Date | Change |
| --- | --- | --- |
| v1.0 | 2026-09-01 | Initial |

### 5.1 Result
Old behavior.
"""
        candidate = baseline.replace(
            "| v1.0 | 2026-09-01 | Initial |\n",
            "| v1.1 | 2026-09-04 | Add result state |\n"
            "| v1.0 | 2026-09-01 | Initial |\n",
        ).replace("Old behavior.", "New behavior.")
        manifest = build_revision_scope_manifest(
            baseline_markdown=baseline,
            baseline_assets={},
            requirement_ids=["5.1"],
            confirmed_scope_text="Update 5.1 result behavior.",
            authority="explicit user confirmation",
        )
        report = validate_revision_scope(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=candidate,
            baseline_assets={},
            candidate_assets={},
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn("protected version history rows changed or were reordered", report["failures"])

    def test_version_history_append_rejects_pure_media_only_selected_change(self) -> None:
        baseline = """### 2. 版本记录

| 版本 | 日期 | 变更内容 | 负责人 |
| --- | --- | --- | --- |
| v1.0 | 2026-09-01 | 首次创建 | 产品 |

### 5.1 节点执行结果
保持既有规则。
[[prd-detail-media src="./assets/old-result.png" alt="old" copy="旧图示"]]
"""
        candidate = baseline.replace(
            "| v1.0 | 2026-09-01 | 首次创建 | 产品 |\n",
            "| v1.0 | 2026-09-01 | 首次创建 | 产品 |\n"
            "| v1.1 | 2026-09-04 | 更新节点图示 | 产品 |\n",
        ).replace("old-result.png", "new-result.png").replace("旧图示", "新图示")
        manifest = build_revision_scope_manifest(
            baseline_markdown=baseline,
            baseline_assets={"assets/old-result.png": "old", "assets/new-result.png": "new"},
            requirement_ids=["5.1"],
            confirmed_scope_text="替换 5.1 的图示。",
            authority="explicit user confirmation",
        )
        report = validate_revision_scope(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=candidate,
            baseline_assets={"assets/old-result.png": "old", "assets/new-result.png": "new"},
            candidate_assets={"assets/old-result.png": "old", "assets/new-result.png": "new"},
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn("layout or media-only", "\n".join(report["failures"]))

    def test_version_history_append_requires_complete_record_cells(self) -> None:
        baseline = """### 2. Version History

| Version | Date | Change | Owner |
| --- | --- | --- | --- |
| v1.0 | 2026-09-01 | Initial | PM |

### 5.1 Result
Old behavior.
"""
        candidate = baseline.replace(
            "| v1.0 | 2026-09-01 | Initial | PM |\n",
            "| v1.0 | 2026-09-01 | Initial | PM |\n"
            "| v1.1 | 2026/09/04 | Add result state |  |\n",
        ).replace("Old behavior.", "New behavior.")
        manifest = build_revision_scope_manifest(
            baseline_markdown=baseline,
            baseline_assets={},
            requirement_ids=["5.1"],
            confirmed_scope_text="Update 5.1 result behavior.",
            authority="explicit user confirmation",
        )
        report = validate_revision_scope(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=candidate,
            baseline_assets={},
            candidate_assets={},
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn(
            "appended version history record requires version, date, material change summary, and owner",
            report["failures"],
        )

    def test_rendered_html_images_must_match_markdown_by_requirement(self) -> None:
        report = self.validate()
        matching_html = """
        <h3>5.1 节点执行结果</h3>
        <img src="./assets/execution-success.png"><img src="./assets/execution-failure.png">
        <h3>5.2 Upload node</h3><img src="./assets/upload-node.png">
        """
        self.assertEqual(validate_rendered_html_scope(report, matching_html), [])
        reversed_html = matching_html.replace(
            '<img src="./assets/execution-success.png"><img src="./assets/execution-failure.png">',
            '<img src="./assets/execution-failure.png"><img src="./assets/execution-success.png">',
        )
        self.assertIn("5.1", "\n".join(validate_rendered_html_scope(report, reversed_html)))


if __name__ == "__main__":
    unittest.main()
