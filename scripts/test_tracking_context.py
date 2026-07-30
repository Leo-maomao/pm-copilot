#!/usr/bin/env python3
"""Regression coverage for concise PRD tracking validation."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from validate_outputs import check_tracking_context


class TrackingContextTest(unittest.TestCase):
    def test_prd_event_name_does_not_require_proposed_taxonomy_copy(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            (folder / "prd.md").write_text(
                "## 七、埋点需求\n\n"
                "| 事件 | 事件名称 | 上报时机 | 附加参数 | 备注 |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| 点击登录 | login_click | 用户点击登录按钮时上报。 | / | / |\n\n"
                "event_name: login_click\n",
                encoding="utf-8",
            )
            check_tracking_context(folder)

    def test_prd_tracking_rejects_raw_sensitive_additional_parameter(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            (folder / "prd.md").write_text(
                "## 七、埋点需求\n\n"
                "| 事件 | 事件名称 | 上报时机 | 附加参数 | 备注 |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| 点击登录 | login_click | 用户点击登录按钮时上报。 | 用户手机号 | / |\n",
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                check_tracking_context(folder)


if __name__ == "__main__":
    unittest.main()
