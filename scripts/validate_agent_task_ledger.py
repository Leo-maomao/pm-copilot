#!/usr/bin/env python3
"""Validate a persisted PM Copilot multi-agent task ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_task_ledger import load, validate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    ledger = load(args.ledger)
    failures = validate(ledger, args.ledger.parent)
    result = {"status": "passed" if not failures else "failed", "failures": failures}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"agent task ledger validation {result['status']}: {args.ledger}")
    if not args.json:
        for failure in failures:
            print(f"FAIL: {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
