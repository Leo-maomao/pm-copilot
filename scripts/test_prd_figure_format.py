#!/usr/bin/env python3
"""Regression coverage for inline PRD figure captions."""

from __future__ import annotations

import unittest

from format_prd_figures import normalize_row


class PRDFigureFormatTest(unittest.TestCase):
    def test_gives_every_image_an_immediate_caption_and_spaces_multiple_images(self) -> None:
        source = (
            "| 图示 | ![项目列表](./assets/项目列表.png)<br>"
            "![创建项目弹窗](./assets/创建项目弹窗.png)<br>"
            "<small>位置：项目列表；用途：展示创建入口。</small> |"
        )
        match = __import__("re").compile(r"(?m)^(\|\s*(?:图示|截图|需求图|图片)\s*\|\s*)(.*?)(\|\s*)$").match(source)
        self.assertIsNotNone(match)
        normalized = normalize_row(match)
        self.assertIn("![项目列表](./assets/项目列表.png)<small>项目列表</small>", normalized)
        self.assertIn("![创建项目弹窗](./assets/创建项目弹窗.png)<small>创建项目弹窗</small>", normalized)
        self.assertIn("</small><br>![创建项目弹窗]", normalized)

    def test_normalization_is_idempotent(self) -> None:
        source = "| 图示 | ![项目列表](./assets/项目列表.png)<small>项目列表</small> |"
        match = __import__("re").compile(r"(?m)^(\|\s*(?:图示|截图|需求图|图片)\s*\|\s*)(.*?)(\|\s*)$").match(source)
        self.assertEqual(normalize_row(match), source)


if __name__ == "__main__":
    unittest.main()
