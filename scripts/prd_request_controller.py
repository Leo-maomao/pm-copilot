#!/usr/bin/env python3
"""Canonical v2 natural-language PRD request entry point."""

from __future__ import annotations

from typing import Sequence

from prd_delivery_engine import main as run_prd_request_entry


PRD_MARKERS = ("prd", "产品需求", "需求文档", "产品需求文档")


def is_prd_request(request: str) -> bool:
    return any(marker in request.casefold() for marker in PRD_MARKERS)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the v2 deterministic delivery engine.

    This is the only supported CLI entry point.
    """
    return run_prd_request_entry(argv)


if __name__ == "__main__":
    raise SystemExit(main())
