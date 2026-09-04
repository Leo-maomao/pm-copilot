#!/usr/bin/env python3
"""Regression coverage for controller-owned in-place revision scope checks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from revision_scope import (
    asset_digests,
    build_revision_scope_manifest,
    constrain_revision_markdown,
    is_content_asset_relative_path,
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

    def test_asset_inventory_excludes_hidden_and_platform_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            (assets / "visible.png").write_bytes(b"visible")
            (assets / ".DS_Store").write_bytes(b"finder")
            (assets / ".hidden.png").write_bytes(b"hidden")
            (assets / "Thumbs.db").write_bytes(b"explorer")
            (assets / ".metadata").mkdir()
            (assets / ".metadata" / "nested.png").write_bytes(b"metadata")

            digests = asset_digests(root)

        self.assertEqual(set(digests), {"assets/visible.png"})
        self.assertTrue(is_content_asset_relative_path("visible.png"))
        self.assertFalse(is_content_asset_relative_path(".DS_Store"))
        self.assertFalse(is_content_asset_relative_path(".hidden.png"))
        self.assertFalse(is_content_asset_relative_path(".metadata/nested.png"))
        self.assertFalse(is_content_asset_relative_path("Thumbs.db"))

    def test_asset_inventory_rejects_symbolic_links_before_scope_validation(self) -> None:
        """A staged asset link must never be dereferenced outside the run folder."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            outside_file = root / "outside.png"
            outside_file.write_bytes(b"outside")
            try:
                (assets / "linked-file.png").symlink_to(outside_file)
            except OSError as error:
                self.skipTest(f"symbolic links are unavailable in this environment: {error}")

            with self.assertRaisesRegex(ValueError, r"symbolic link: assets/linked-file\.png"):
                asset_digests(root)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            outside_directory = root / "outside-assets"
            outside_directory.mkdir()
            (outside_directory / "outside.png").write_bytes(b"outside")
            try:
                (assets / "linked-directory").symlink_to(outside_directory, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"symbolic links are unavailable in this environment: {error}")

            with self.assertRaisesRegex(ValueError, r"symbolic link: assets/linked-directory"):
                asset_digests(root)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside_directory = root / "outside-assets"
            outside_directory.mkdir()
            (outside_directory / "outside.png").write_bytes(b"outside")
            try:
                (root / "assets").symlink_to(outside_directory, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"symbolic links are unavailable in this environment: {error}")

            with self.assertRaisesRegex(ValueError, r"asset directory must not be a symbolic link"):
                asset_digests(root)

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

    def test_selected_requirement_old_asset_can_be_removed_when_replaced(self) -> None:
        assets = dict(BASELINE_ASSETS)
        assets.pop("assets/old-result.png")
        report = self.validate(assets=assets)
        self.assertEqual(report["status"], "passed")

    def test_unselected_requirement_asset_cannot_be_removed(self) -> None:
        assets = dict(BASELINE_ASSETS)
        assets.pop("assets/upload-node.png")
        report = self.validate(assets=assets)
        self.assertEqual(report["status"], "failed")
        self.assertIn("protected asset changed or was removed: assets/upload-node.png", report["failures"])

    def test_only_linked_localization_rows_may_change(self) -> None:
        report = self.validate()
        self.assertEqual(report["status"], "passed")
        unrelated = UPDATED.replace("Existing upload copy", "Changed upload copy")
        report = self.validate(unrelated)
        self.assertEqual(report["status"], "failed")
        self.assertIn("outside the confirmed revision scope", "\n".join(report["failures"]))

    def test_constrained_merge_keeps_current_style_copy_rows_when_legacy_label_changes(self) -> None:
        """A label rename must not make the controller retain stale user copy.

        The real PRD table uses a visible-copy column plus usage location and
        parameters.  ``任务编号：{taskId}`` becoming ``Task ID`` has no matching
        first cell, but the parameter/usage cells still give the controller a
        deterministic ownership anchor.
        """
        baseline = """# Canvas PRD

## 四、需求清单
| 详情编号 | 需求名称 | 需求摘要 |
| --- | --- | --- |
| 5.1 | 节点错误与 TaskID 展示 | 旧错误详情层 |
| 5.2 | 上传音频节点 | 保留上传规则 |

## 五、需求详情
### 5.1 节点错误与 TaskID 展示
| 维度 | 需求说明 |
| --- | --- |
| 需求详情 | 节点执行失败时展示旧错误详情。 |

### 5.2 上传音频节点
| 维度 | 需求说明 |
| --- | --- |
| 需求详情 | 保留上传节点原有规则。 |

## 六、多语言需求
| 文案 | 使用位置 | 参数 |
| --- | --- | --- |
| 失败 | 节点标题栏失败状态 | / |
| 执行失败 | 错误详情标题 | / |
| 任务编号：{taskId} | 错误详情第一行 | {taskId} |
| 复制成功 | TaskID 复制反馈 | / |
| 宫格排列 | 整理菜单 | / |
"""
        candidate = """# Canvas PRD

## 四、需求清单
| 详情编号 | 需求名称 | 需求摘要 |
| --- | --- | --- |
| 5.1 | 节点执行结果提示 | 成功和失败状态图标与结果弹窗 |
| 5.2 | 被错误改写的上传节点 | 不应跨范围改写 |

## 五、需求详情
### 5.1 节点执行结果提示
| 维度 | 需求说明 |
| --- | --- |
| 需求详情 | 成功和失败均显示状态图标；成功显示 Task ID，失败显示 Task ID 与失败原因。Task ID 缺失时显示任务 ID 暂未返回；复制失败时显示复制失败，请重试；失败原因为空时显示节点执行失败，请稍后重试。 |

### 5.2 上传音频节点
| 维度 | 需求说明 |
| --- | --- |
| 需求详情 | 被错误改写的上传规则。 |

## 六、多语言需求
| 文案 | 使用位置 | 参数 |
| --- | --- | --- |
| 执行成功 | 成功结果弹窗标题 | / |
| 执行失败 | 失败结果弹窗标题 | / |
| Task ID | 成功和失败结果弹窗 | {taskId} |
| 失败原因 | 失败结果弹窗 | / |
| Task ID 已复制 | Task ID 复制成功反馈 | / |
| 复制失败，请重试 | Task ID 复制失败反馈 | / |
| 任务 ID 暂未返回 | Task ID 缺失提示 | / |
| 节点执行失败，请稍后重试 | 空失败原因提示 | / |
| 宫格排列 | 被错误改写的整理菜单 | / |
"""
        manifest = build_revision_scope_manifest(
            baseline_markdown=baseline,
            baseline_assets={},
            requirement_ids=["5.1"],
            confirmed_scope_text="仅更新 5.1 对应中文用户可见文案。",
            authority="explicit user confirmation",
        )

        merged = constrain_revision_markdown(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=candidate,
        )

        self.assertEqual(merged["status"], "merged")
        markdown = str(merged["markdown"])
        self.assertIn("| 5.1 | 节点执行结果提示 | 成功和失败状态图标与结果弹窗 |", markdown)
        self.assertIn("| 5.2 | 上传音频节点 | 保留上传规则 |", markdown)
        self.assertIn("| 需求详情 | 保留上传节点原有规则。 |", markdown)
        self.assertIn("| Task ID | 成功和失败结果弹窗 | {taskId} |", markdown)
        self.assertNotIn("任务编号：{taskId}", markdown)
        self.assertIn("| 宫格排列 | 整理菜单 | / |", markdown)
        self.assertNotIn("被错误改写的整理菜单", markdown)

        report = validate_revision_scope(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=markdown,
            baseline_assets={},
            candidate_assets={},
        )
        self.assertEqual(report["status"], "passed", report["failures"])

    def test_constrained_merge_synchronizes_a_mirrored_pure_text_checklist(self) -> None:
        """A retained checklist must follow the same authorized copy-table delta."""
        baseline = """# Canvas PRD

### 5.1 节点执行结果
节点执行失败时展示失败信息和复制反馈。

### 5.2 节点整理
保留既有整理和下载命名规则。

## 六、多语言需求
```text
执行失败
复制成功
宫格排列
无标题
```

| 文案 | 使用位置 | 参数 |
| --- | --- | --- |
| 执行失败 | 5.1 失败结果标题 | / |
| 复制成功 | 5.1 Task ID 复制反馈 | / |
| 宫格排列 | 5.2 整理菜单 | / |
| 无标题 | 5.2 下载文件名兜底 | / |
"""
        candidate = """# Canvas PRD

### 5.1 节点执行结果
执行成功、执行失败和 Task ID 均展示结果弹窗；复制成功时显示 Task ID 已复制。

### 5.2 节点整理
被错误改写的整理和下载命名规则。

## 六、多语言需求
```text
执行失败
复制成功
宫格排列
无标题
```

| 文案 | 使用位置 | 参数 |
| --- | --- | --- |
| 执行成功 | 5.1 成功结果标题 | / |
| 执行失败 | 5.1 失败结果标题 | / |
| Task ID | 5.1 结果弹窗标签 | / |
| Task ID 已复制 | 5.1 Task ID 复制反馈 | / |
| 宫格排列 | 被错误改写的整理菜单 | / |
| 无标题 | 5.2 下载文件名兜底 | / |
"""
        manifest = build_revision_scope_manifest(
            baseline_markdown=baseline,
            baseline_assets={},
            requirement_ids=["5.1"],
            confirmed_scope_text="仅更新 5.1 对应中文用户可见文案。",
            authority="explicit user confirmation",
        )

        merged = constrain_revision_markdown(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=candidate,
        )

        self.assertEqual(merged["status"], "merged", merged["failures"])
        markdown = str(merged["markdown"])
        self.assertIn(
            "```text\n执行成功\n执行失败\nTask ID\nTask ID 已复制\n宫格排列\n无标题\n```",
            markdown,
        )
        self.assertNotIn("复制成功\n宫格排列", markdown)
        self.assertIn("| 宫格排列 | 5.2 整理菜单 | / |", markdown)
        self.assertNotIn("被错误改写的整理菜单", markdown)

        report = validate_revision_scope(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=markdown,
            baseline_assets={},
            candidate_assets={},
        )
        self.assertEqual(report["status"], "passed", report["failures"])

        changed_unselected_checklist = markdown.replace(
            "宫格排列\n无标题\n```", "被错误改写的宫格排列\n无标题\n```", 1,
        )
        report = validate_revision_scope(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=changed_unselected_checklist,
            baseline_assets={},
            candidate_assets={},
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn("outside the confirmed revision scope", "\n".join(report["failures"]))

    def test_constrained_merge_preserves_unmatched_localization_rows_between_selected_rows(self) -> None:
        baseline = """| 5.1 | 保存状态 |
| 5.2 | 上传状态 |

### 5.1 保存状态
保存成功和保存失败均提供反馈。

### 5.2 上传状态
保留上传反馈。

## 六、多语言需求
| 文案 | 使用位置 | 参数 |
| --- | --- | --- |
| 保存成功 | 5.1 保存反馈 | / |
| 上传完成 | 5.2 上传反馈 | / |
| 保存失败 | 5.1 保存错误 | / |
"""
        candidate = """| 5.1 | 保存状态 |
| 5.2 | 上传状态 |

### 5.1 保存状态
保存成功和保存失败均提供明确反馈与重试入口。

### 5.2 上传状态
被错误改写的上传反馈。

## 六、多语言需求
| 文案 | 使用位置 | 参数 |
| --- | --- | --- |
| 保存成功 | 5.1 保存完成反馈 | / |
| 上传完成 | 被错误改写的上传反馈 | / |
| 保存失败 | 5.1 保存失败反馈 | / |
"""
        manifest = build_revision_scope_manifest(
            baseline_markdown=baseline,
            baseline_assets={},
            requirement_ids=["5.1"],
            confirmed_scope_text="仅更新 5.1 对应中文用户可见文案。",
            authority="explicit user confirmation",
        )

        merged = constrain_revision_markdown(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=candidate,
        )

        self.assertEqual(merged["status"], "merged")
        markdown = str(merged["markdown"])
        self.assertIn("| 保存成功 | 5.1 保存完成反馈 | / |", markdown)
        self.assertIn("| 保存失败 | 5.1 保存失败反馈 | / |", markdown)
        self.assertIn("| 上传完成 | 5.2 上传反馈 | / |", markdown)
        self.assertNotIn("被错误改写的上传反馈", markdown)

    def test_constrained_merge_matches_copy_table_by_identity_after_preceding_table_is_deleted(self) -> None:
        """A removed unrelated table must not shift a later table's ownership."""
        baseline = """# Canvas PRD

### 5.1 Foo Key flow
The visible copy is `Foo Key`.

## Copy collection A
| Copy Key | Usage | Parameters |
| --- | --- | --- |
| Foo Key | Feature A status | / |
| Stable A | Feature A helper | / |

## Copy collection B
| Copy Key | Usage | Parameters |
| --- | --- | --- |
| Foo Key | Feature B status | / |
| Stable B | Feature B helper | / |
"""
        candidate = """# Canvas PRD

### 5.1 Foo Key flow
The visible copy is `Foo Key v2`.

## Copy collection B
| Copy Key | Usage | Parameters |
| --- | --- | --- |
| Foo Key v2 | Feature B status | / |
| Stable B | Feature B helper | / |
"""
        manifest = build_revision_scope_manifest(
            baseline_markdown=baseline,
            baseline_assets={},
            requirement_ids=["5.1"],
            confirmed_scope_text="Update 5.1 Foo Key copy.",
            authority="explicit user confirmation",
        )

        merged = constrain_revision_markdown(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=candidate,
        )

        self.assertEqual(merged["status"], "merged", merged["failures"])
        markdown = str(merged["markdown"])
        self.assertIn("| Foo Key | Feature A status | / |", markdown)
        self.assertIn("| Stable A | Feature A helper | / |", markdown)
        self.assertIn("| Foo Key v2 | Feature B status | / |", markdown)
        self.assertNotIn("| Foo Key v2 | Feature A status | / |", markdown)

        report = validate_revision_scope(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=markdown,
            baseline_assets={},
            candidate_assets={},
        )
        self.assertEqual(report["status"], "passed", report["failures"])

    def test_constrained_merge_rejects_ambiguous_duplicate_copy_rows(self) -> None:
        """Identical rows have no safe position-based identity during a rename."""
        baseline = """# Canvas PRD

### 5.1 Foo Key flow
The visible copy is `Foo Key`.

## Copy collection
| Copy Key | Usage | Parameters |
| --- | --- | --- |
| Foo Key | Shared destination | / |
| Foo Key | Shared destination | / |
"""
        candidate = """# Canvas PRD

### 5.1 Foo Key flow
The visible copy is `Foo Key v2`.

## Copy collection
| Copy Key | Usage | Parameters |
| --- | --- | --- |
| Foo Key v2 | Shared destination | / |
| Foo Key | Shared destination | / |
"""
        manifest = build_revision_scope_manifest(
            baseline_markdown=baseline,
            baseline_assets={},
            requirement_ids=["5.1"],
            confirmed_scope_text="Update 5.1 Foo Key copy.",
            authority="explicit user confirmation",
        )

        merged = constrain_revision_markdown(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=candidate,
        )

        self.assertEqual(merged["status"], "failed")
        self.assertIn("baseline row anchor is ambiguous", "\n".join(merged["failures"]))
        markdown = str(merged["markdown"])
        self.assertIn("| Foo Key | Shared destination | / |", markdown)
        self.assertNotIn("| Foo Key v2 | Shared destination | / |", markdown)

    def test_constrained_merge_allows_only_an_explicitly_confirmed_selected_deletion(self) -> None:
        baseline = """| 5.1 | 保留能力 |
| 5.2 | 待删除能力 |
| 5.3 | 保留能力二 |

### 5.1 保留能力
保留规则。

### 5.2 待删除能力
待删除规则。

### 5.3 保留能力二
保留规则二。
"""
        candidate = """| 5.1 | 保留能力 |
| 5.3 | 保留能力二 |

### 5.1 保留能力
保留规则。

### 5.3 保留能力二
保留规则二。
"""
        manifest = build_revision_scope_manifest(
            baseline_markdown=baseline,
            baseline_assets={},
            requirement_ids=["5.2"],
            confirmed_scope_text="用户确认：删除需求 5.2，保留其他需求。",
            authority="explicit user confirmation",
        )

        self.assertEqual(manifest["deleted_requirement_ids"], ["5.2"])
        merged = constrain_revision_markdown(
            manifest, baseline_markdown=baseline, candidate_markdown=candidate,
        )

        self.assertEqual(merged["status"], "merged", merged["failures"])
        self.assertEqual(merged["markdown"], candidate)
        report = validate_revision_scope(
            manifest,
            baseline_markdown=baseline,
            candidate_markdown=str(merged["markdown"]),
            baseline_assets={},
            candidate_assets={},
        )
        self.assertEqual(report["status"], "passed", report["failures"])

        unconfirmed = build_revision_scope_manifest(
            baseline_markdown=baseline,
            baseline_assets={},
            requirement_ids=["5.2"],
            confirmed_scope_text="仅更新需求 5.2 的文案。",
            authority="explicit user confirmation",
        )
        rejected = constrain_revision_markdown(
            unconfirmed, baseline_markdown=baseline, candidate_markdown=candidate,
        )
        self.assertEqual(rejected["status"], "failed")
        self.assertIn("absent from the candidate", "\n".join(rejected["failures"]))

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
