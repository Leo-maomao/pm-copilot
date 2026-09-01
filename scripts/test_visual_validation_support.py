#!/usr/bin/env python3
"""Regression coverage for shared visual-validation browser discovery."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

import preflight_tools
import setup_visual_validation
import validate_prototype_visual
from visual_validation_support import (
    PLAYWRIGHT_BROWSER_PATTERNS,
    SYSTEM_BROWSER_CANDIDATES,
    installed_browser_channel,
    playwright_cache_roots,
)


class VisualValidationSupportTests(unittest.TestCase):
    def test_callers_share_cache_discovery_and_patterns(self) -> None:
        self.assertIs(preflight_tools.playwright_cache_roots, playwright_cache_roots)
        self.assertIs(setup_visual_validation.playwright_cache_roots, playwright_cache_roots)
        self.assertIs(validate_prototype_visual.playwright_cache_roots, playwright_cache_roots)
        self.assertIs(setup_visual_validation.installed_browser_channel, installed_browser_channel)
        self.assertIs(validate_prototype_visual.installed_browser_channel, installed_browser_channel)
        self.assertIs(setup_visual_validation.SYSTEM_BROWSER_CANDIDATES, SYSTEM_BROWSER_CANDIDATES)
        self.assertIs(validate_prototype_visual.SYSTEM_BROWSER_CANDIDATES, SYSTEM_BROWSER_CANDIDATES)
        self.assertIs(preflight_tools.PLAYWRIGHT_BROWSER_PATTERNS, PLAYWRIGHT_BROWSER_PATTERNS)
        self.assertIs(setup_visual_validation.PLAYWRIGHT_BROWSER_PATTERNS, PLAYWRIGHT_BROWSER_PATTERNS)
        self.assertIs(validate_prototype_visual.PLAYWRIGHT_BROWSER_PATTERNS, PLAYWRIGHT_BROWSER_PATTERNS)

    def test_cache_roots_preserve_environment_and_platform_paths(self) -> None:
        with patch.dict(os.environ, {
            "PLAYWRIGHT_BROWSERS_PATH": "/tmp/pw-cache",
            "LOCALAPPDATA": "/tmp/local-app-data",
        }, clear=False), patch("visual_validation_support.Path.home", return_value=Path("/tmp/home")):
            self.assertEqual(
                playwright_cache_roots(),
                [
                    Path("/tmp/pw-cache"),
                    Path("/tmp/home/Library/Caches/ms-playwright"),
                    Path("/tmp/home/.cache/ms-playwright"),
                    Path("/tmp/local-app-data/ms-playwright"),
                ],
            )

    def test_setup_detects_an_executable_managed_browser(self) -> None:
        with patch.object(setup_visual_validation, "playwright_cache_roots", return_value=[Path("/tmp/cache")]), \
             patch.object(setup_visual_validation.Path, "is_dir", return_value=True), \
             patch.object(setup_visual_validation.Path, "glob", return_value=[Path("/tmp/cache/chrome")]), \
             patch.object(setup_visual_validation.Path, "is_file", return_value=True), \
             patch("setup_visual_validation.os.access", return_value=True):
            self.assertTrue(setup_visual_validation.has_playwright_managed_browser())


if __name__ == "__main__":
    unittest.main()
