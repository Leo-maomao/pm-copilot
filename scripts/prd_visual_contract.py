# -*- coding: utf-8 -*-
"""Machine-readable projection of the PRD visual naming rule.

The active human-readable owner is ``artifacts/prd-contract.md``. Runtime code
imports this projection instead of recreating the controlled placeholder format.
"""

from __future__ import annotations

import re


PLACEHOLDER_BASENAME = "功能-状态"
PLACEHOLDER_FILE_NAME = f"{PLACEHOLDER_BASENAME}.png"
PLACEHOLDER_MARKER = f"占位图：{PLACEHOLDER_FILE_NAME}"

# Real screenshots may use several supported formats; controlled placeholders
# must name a functional area and concrete state and always use PNG.
PLACEHOLDER_NAME_PATTERN = r"[^|<>\n.\-]+-[^|<>\n.\-]+\.png"
PLACEHOLDER_DECLARATION_RE = re.compile(
    rf"占位图[:：]\s*(?P<name>{PLACEHOLDER_NAME_PATTERN})(?=\s*(?:\||<br\s*/?>|$))",
    re.IGNORECASE,
)
PLACEHOLDER_VALUE_RE = re.compile(
    rf"占位图：{PLACEHOLDER_NAME_PATTERN}(?:\s*<br\s*/?>\s*占位图：{PLACEHOLDER_NAME_PATTERN})*$",
    re.IGNORECASE,
)


def is_controlled_placeholder_value(value: str) -> bool:
    """Return whether a table-cell value contains only controlled markers."""
    return bool(PLACEHOLDER_VALUE_RE.fullmatch(value.strip()))
