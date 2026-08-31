#!/usr/bin/env python3
"""Regression coverage for adaptive multi-figure PRD rendering."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from render_prd_html import DOCUMENT_CSS, LIGHTBOX_HTML_TEMPLATE, group_requirement_figure_pairs, inject_defaults


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

    def test_explicit_detail_media_block_keeps_left_media_and_right_copy(self) -> None:
        rendered = inject_defaults(
            '<html><head></head><body><table><tr><td>需求详情</td><td>'
            '<div class="prd-detail-media-block"><div class="prd-detail-media">'
            '<img src="./assets/confirm.png" alt="确认弹窗" /></div>'
            '<div class="prd-detail-copy">展示角色变更说明和确认反馈。</div></div>'
            '</td></tr></table></body></html>',
            "# 截图状态 - 2026-08-31",
            Path("."),
        )
        self.assertIn('class="prd-detail-media-block"', rendered)
        self.assertIn('class="prd-detail-media"><img', rendered)
        self.assertIn('class="prd-detail-copy">展示角色变更说明', rendered)

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
