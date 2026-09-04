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
    parser.add_argument("--provider", default="auto")
    parser.add_argument("--timeout-minutes", type=int, default=15)
    parser.add_argument("--max-revisions", type=int, default=3)
    parser.add_argument("--run-folder", help="existing canonical PRD folder to revise")
    parser.add_argument("--revise", action="store_true", help="revise the existing PRD in place")
    parser.add_argument("--extract-from", help="source Markdown/text PRD for a new extraction delivery")
    parser.add_argument(
        "--revision-requirement-id", action="append", default=[],
        help="existing requirement ID to modify; repeat for multiple IDs",
    )
    parser.add_argument(
        "--implemented-evidence", help="JSON file containing the verified implemented-feature evidence packet",
    )
    args = parser.parse_args()
    if not is_prd_request(args.request):
        parser.error("request is not classified as a PRD request")
    if args.revise and not args.run_folder:
        parser.error("--revise requires --run-folder")
    if args.run_folder and not args.revise:
        parser.error("--run-folder identifies an existing canonical PRD; add --revise for an in-place update")
    if args.extract_from and args.revise:
        parser.error("--extract-from cannot be combined with --revise")
    if args.implemented_evidence and args.revise:
        parser.error("--implemented-evidence cannot be combined with --revise")
    if args.extract_from and args.implemented_evidence:
        parser.error("--extract-from and --implemented-evidence select different PRD delivery modes")
    if args.revision_requirement_id and not args.run_folder:
        parser.error("--revision-requirement-id requires --run-folder")
    if args.revision_requirement_id and (args.extract_from or args.implemented_evidence):
        parser.error("--revision-requirement-id cannot be combined with a new PRD delivery mode")
    sys.argv = [
        "run_interactive_request.py", "--request", args.request,
        "--provider", args.provider, "--timeout-minutes", str(args.timeout_minutes),
        "--max-revisions", str(args.max_revisions),
    ]
    if args.run_folder:
        sys.argv += ["--run-folder", args.run_folder]
    if args.revise:
        sys.argv += ["--revise"]
    elif not args.run_folder:
        sys.argv.insert(1, "--new-requirement")
    if args.extract_from:
        sys.argv += ["--extract-from", args.extract_from]
    for requirement_id in args.revision_requirement_id:
        sys.argv += ["--revision-requirement-id", requirement_id]
    if args.implemented_evidence:
        sys.argv += ["--implemented-evidence", args.implemented_evidence]
    return interactive_main()


if __name__ == "__main__":
    raise SystemExit(main())
