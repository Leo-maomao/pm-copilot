#!/usr/bin/env python3
"""Regression coverage for adaptive multi-figure PRD rendering."""

from __future__ import annotations

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
        self.assertNotIn('naturalWidth', LIGHTBOX_HTML_TEMPLATE)

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


if __name__ == "__main__":
    unittest.main()
