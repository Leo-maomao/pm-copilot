#!/usr/bin/env python3
"""Canonical natural-language PRD request entry point."""

from __future__ import annotations

import argparse
import sys

from run_interactive_request import main as interactive_main


PRD_MARKERS = (
    "prd", "产品需求", "需求文档", "产品需求文档", "生成需求", "写需求",
)


def is_prd_request(request: str) -> bool:
    lowered = request.casefold()
    return any(marker.casefold() in lowered for marker in PRD_MARKERS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--provider", default="codex")
    parser.add_argument("--timeout-minutes", type=int, default=15)
    parser.add_argument("--max-revisions", type=int, default=3)
    args = parser.parse_args()
    if not is_prd_request(args.request):
        parser.error("request is not classified as a PRD request")
    sys.argv = [
        "run_interactive_request.py", "--new-requirement", "--request", args.request,
        "--provider", args.provider, "--timeout-minutes", str(args.timeout_minutes),
        "--max-revisions", str(args.max_revisions),
    ]
    return interactive_main()


if __name__ == "__main__":
    raise SystemExit(main())
