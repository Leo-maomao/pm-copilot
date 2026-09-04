#!/usr/bin/env python3
"""Regression coverage for adaptive multi-figure PRD rendering."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from render_prd_html import (
    DOCUMENT_CSS,
    LIGHTBOX_HTML_TEMPLATE,
    group_requirement_figure_pairs,
    inject_defaults,
    renumber_detail_copy,
)


class PRDFigureLayoutTest(unittest.TestCase):
    def test_groups_multiple_image_caption_pairs_in_one_cell(self) -> None:
        html = (
            '<table><tr><td>图示</td><td>'
            '<img src="./assets/menu.png" alt="菜单入口" /><small>菜单入口</small><br>'
            '<img src="./assets/dialog.png" alt="确认弹窗" /><small>确认弹窗</small>'
            '</td></tr></table>'
        )
        grouped = group_requirement_figure_pairs(html)
        self.assertIn('<div class="prd-figure-grid">', grouped)
        self.assertEqual(grouped.count('class="prd-figure-item"'), 2)
        self.assertIn('<small>菜单入口</small>', grouped)
        self.assertIn('<small>确认弹窗</small>', grouped)
        self.assertNotIn('</small><br>', grouped)

    def test_leaves_single_figure_cell_unchanged(self) -> None:
        html = '<td><img src="./assets/menu.png" alt="菜单入口" /><small>菜单入口</small></td>'
        self.assertEqual(group_requirement_figure_pairs(html), html)

    def test_renderer_marks_wide_local_images_without_javascript(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            assets = folder / "assets"
            assets.mkdir()
            (assets / "compact.png").write_bytes(
                b"\x89PNG\r\n\x1a\n" + b"\0\0\0\rIHDR" + (320).to_bytes(4, "big") + (480).to_bytes(4, "big")
            )
            (assets / "wide.png").write_bytes(
                b"\x89PNG\r\n\x1a\n" + b"\0\0\0\rIHDR" + (1600).to_bytes(4, "big") + (900).to_bytes(4, "big")
            )
            html = (
                '<td><img src="./assets/compact.png" alt="紧凑图" /><small>紧凑图</small><br>'
                '<img src="./assets/wide.png" alt="宽图" /><small>宽图</small></td>'
            )
            grouped = group_requirement_figure_pairs(html, folder)
        self.assertIn('<div class="prd-figure-item">', grouped)
        self.assertIn('<div class="prd-figure-item is-wide">', grouped)

    def test_styles_keep_layout_stable_without_javascript(self) -> None:
        self.assertIn('grid-template-columns: repeat(2, minmax(0, 1fr));', DOCUMENT_CSS)
        self.assertIn('.prd-figure-item.is-wide', DOCUMENT_CSS)
        self.assertNotIn('min-height: 140px;', DOCUMENT_CSS)
        self.assertNotIn('naturalWidth', LIGHTBOX_HTML_TEMPLATE)

    def test_pandoc_safe_detail_media_markers_preserve_all_rules(self) -> None:
        markdown = """# 截图状态 - 2026-08-31

## 五、需求详情

### 5.1 图示状态

| 维度 | 需求说明 |
| --- | --- |
| 用户与场景 | 管理员查看状态。 |
| 需求入口 | 管理页入口。 |
| 需求详情 | 图示前规则：展示入口。<br>[[prd-detail-media src=\"./assets/entry.png\" alt=\"入口状态\" copy=\"说明入口状态和操作规则。<br>第二行说明继续操作。\"]]<br>图示中规则：用户确认后继续。<br>[[prd-detail-media src=\"./assets/result.png\" alt=\"结果状态\" copy=\"说明结果状态和恢复反馈。\"]]<br>图示后规则：失败时保留内容并允许重试。 |
| 设计与交互 | 保持清晰反馈。 |
"""
        with TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            (folder / "prd.md").write_text(markdown, encoding="utf-8")
            (folder / "assets").mkdir()
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("render_prd_html.py")), str(folder)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            rendered = (folder / "prd.html").read_text(encoding="utf-8")
        self.assertEqual(rendered.count('class="prd-detail-media-block"'), 2)
        self.assertEqual(rendered.count('class="prd-detail-media"'), 2)
        self.assertEqual(rendered.count('class="prd-detail-copy"'), 2)
        for value in ("entry.png", "result.png", "说明入口状态和操作规则。", "说明结果状态和恢复反馈。", "图示前规则", "图示中规则", "图示后规则"):
            self.assertIn(value, rendered)
        self.assertIn("说明入口状态和操作规则。<br>第二行说明继续操作。", rendered)
        self.assertNotIn("说明入口状态和操作规则。&lt;br&gt;第二行说明继续操作。", rendered)
        self.assertNotIn("prd-inline-media", rendered)
        self.assertNotIn("prd-inline-copy", rendered)
        self.assertNotIn("[[prd-detail-media", rendered)
        self.assertIn("grid-template-columns: 240px minmax(0, 1fr);", rendered)

    def test_detail_media_copy_escapes_html_but_preserves_line_breaks(self) -> None:
        html = (
            "<html><head></head><body><table><tbody>"
            "<tr><td>需求详情</td><td>"
            '[[prd-detail-media src="./assets/example.png" alt="示例" '
            'copy="第一行<br>第二行<script>alert(1)</script>"]]'
            "</td></tr>"
            "</tbody></table></body></html>"
        )
        with TemporaryDirectory() as temporary_directory:
            rendered = inject_defaults(html, "# 示例需求 - 2026-09-04", Path(temporary_directory))
        self.assertIn(
            'class="prd-detail-copy">第一行<br>第二行&lt;script&gt;alert(1)&lt;/script&gt;</div>',
            rendered,
        )
        self.assertNotIn("第一行&lt;br&gt;第二行", rendered)
        self.assertNotIn("<script>alert(1)</script>", rendered)

    def test_renderer_rejects_marker_left_outside_requirement_detail_value_cell(self) -> None:
        marker = '[[prd-detail-media src="./assets/example.png" alt="示例" copy="展示示例状态。"]]'
        malformed_marker = '[[prd-detail-media src="./assets/missing-fields.png"'
        html = (
            "<html><head></head><body><h3>5.1 Example requirement</h3><table>"
            "<thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>"
            "<tr><td>User and scenario</td><td>An administrator views state.</td></tr>"
            "<tr><td>Entry</td><td>Management entry.</td></tr>"
            "<tr><td>Requirement details</td><td>Show state rules.</td></tr>"
            f"<tr><td>Attachment notes</td><td>{marker}<br>{malformed_marker}</td></tr>"
            "</tbody></table></body></html>"
        )
        with TemporaryDirectory() as temporary_directory:
            with self.assertRaises(SystemExit) as failure:
                inject_defaults(html, "# Example requirement - 2026-09-04", Path(temporary_directory))
        self.assertEqual(failure.exception.code, 1)

    def test_renderer_preserves_marker_like_prose_outside_requirement_tables(self) -> None:
        marker = '[[prd-detail-media src="./assets/example.png" alt="示例" copy="展示示例状态。"]]'
        html = (
            "<html><head></head><body>"
            f"<p>格式示例：{marker}</p>"
            f"<table><tr><td>Syntax</td><td>{marker}</td></tr></table>"
            "</body></html>"
        )
        with TemporaryDirectory() as temporary_directory:
            rendered = inject_defaults(html, "# 格式说明 - 2026-09-04", Path(temporary_directory))
        self.assertEqual(rendered.count(marker), 2)

    def test_each_independent_detail_group_restarts_numbering(self) -> None:
        first = renumber_detail_copy("二、入口<br>4. 展示入口。<br>5. 继续操作。")
        second = renumber_detail_copy("三、结果<br>8. 展示结果。")
        self.assertIn("一、入口<br>1.展示入口。<br>2.继续操作。", first)
        self.assertIn("一、结果<br>1.展示结果。", second)

    def test_rendered_document_sets_language_and_accessible_image_preview(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            rendered = inject_defaults(
                '<html><head></head><body><table><tr><td><img src="./assets/menu.png" alt="菜单入口" /></td></tr></table></body></html>',
                "# 菜单入口 - 2026-07-30",
                Path(temporary_directory),
            )
        self.assertIn('<html lang="zh-CN">', rendered)
        self.assertIn('role="dialog"', rendered)
        self.assertIn('aria-modal="true"', rendered)
        self.assertIn("image.setAttribute('tabindex', '0')", rendered)
        self.assertIn("event.key === 'Enter'", rendered)

    def test_reviewed_mapping_pairs_each_image_with_only_its_logic(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            (folder / "prd-media-mapping.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "requirements": [
                            {
                                "title": "5.1 截图状态",
                                "blocks": [
                                    {"asset": "entry.png", "logic_groups": ["一、入口"]},
                                    {"asset": "loading.png", "logic_groups": ["二、加载"]},
                                    {"asset": None, "logic_groups": ["三、失败恢复"]},
                                ],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            html = (
                '<html><head></head><body><h3>5.1 截图状态</h3><table>'
                '<tr><td>需求详情</td><td>一、入口<br>1. 展示入口。<br><br>二、加载<br>1. 显示加载。<br><br>三、失败恢复<br>1. 保留内容。</td></tr>'
                '<tr><td>图示</td><td><img src="./assets/entry.png" /><small>入口</small><br><img src="./assets/loading.png" /><small>加载</small></td></tr>'
                '</table></body></html>'
            )
            rendered = inject_defaults(html, "# 截图状态 - 2026-08-27", folder)
        self.assertEqual(rendered.count('class="prd-detail-media-block"'), 2)
        self.assertEqual(rendered.count('class="prd-detail-text-block"'), 1)
        self.assertIn('entry.png" /></div><div class="prd-detail-copy">一、入口', rendered)
        self.assertIn('loading.png" /></div><div class="prd-detail-copy">一、加载', rendered)
        self.assertNotIn('展示入口。<br><br>二、加载', rendered)
        self.assertNotIn('entry.png" /></div><div class="prd-detail-copy">一、入口<br>1. 展示入口。<br>二、加载', rendered)


if __name__ == "__main__":
    unittest.main()
