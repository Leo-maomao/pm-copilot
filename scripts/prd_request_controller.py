#!/usr/bin/env python3
"""Canonical natural-language PRD request entry point."""

from __future__ import annotations

from typing import Sequence

from run_interactive_request import PRD_MARKERS, is_prd_request, run_prd_request_entry


def main(argv: Sequence[str] | None = None) -> int:
    """Keep the historical facade while sharing the canonical entry parser."""
    return run_prd_request_entry(argv)


if __name__ == "__main__":
    raise SystemExit(main())
