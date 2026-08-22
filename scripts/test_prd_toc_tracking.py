#!/usr/bin/env python3
"""Regression coverage for PRD HTML table-of-contents tracking."""

from pathlib import Path
import unittest


class PRDTOCTrackingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = Path(__file__).with_name("render_prd_html.py").read_text()

    def test_toc_links_keep_full_titles_without_active_state_reflow(self) -> None:
        toc_css = self.source.split("#TOC a {", 1)[1].split("}", 1)[0]
        self.assertIn("font-weight: 400", toc_css)
        self.assertIn("box-sizing: border-box", toc_css)
        self.assertIn("width: calc(100% + 12px)", toc_css)
        self.assertIn("overflow-wrap: anywhere", toc_css)
        self.assertIn("word-break: break-word", toc_css)
        self.assertIn("#TOC a *", self.source)
        active_css = self.source.split("#TOC a.is-active {", 1)[1].split("}", 1)[0]
        self.assertNotIn("font-weight", active_css)

    def test_toc_and_document_reserve_matching_layout_widths(self) -> None:
        self.assertIn("padding: 40px 56px 80px 308px", self.source)
        self.assertIn("width: 252px", self.source)

    def test_active_heading_uses_last_heading_past_fixed_threshold(self) -> None:
        self.assertIn("const threshold = 32;", self.source)
        self.assertIn("section.getBoundingClientRect().top <= threshold", self.source)
        self.assertIn("window.addEventListener('scroll', scheduleUpdate", self.source)
        self.assertNotIn("visible[0]?.target?.id", self.source)


if __name__ == "__main__":
    unittest.main()
