#!/usr/bin/env python3
"""Merge disjoint evaluation portfolio manifests into one auditable full run."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from plan_evaluation_portfolio import portfolio


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _load_manifest(root: Path) -> tuple[dict[str, Any], str]:
    path = root / "portfolio-run.json"
    if not path.is_file():
        raise ValueError(f"missing portfolio manifest: {path}")
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid portfolio manifest: {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"portfolio manifest is not an object: {path}")
    return value, hashlib.sha256(raw).hexdigest()


def merge(roots: list[Path]) -> dict[str, Any]:
    if not roots:
        raise ValueError("provide at least one portfolio root")
    expected_cases = portfolio()["cases"]
    expected = {case["case_id"]: case for case in expected_cases}
    merged_cases: dict[str, Any] = {}
    observed_plan: dict[str, dict[str, Any]] = {}
    sources: list[dict[str, str]] = []
    errors: list[str] = []
    for root in roots:
        manifest, manifest_sha256 = _load_manifest(root)
        snapshot = manifest.get("plan_snapshot")
        cases = manifest.get("cases")
        if not isinstance(snapshot, list) or not isinstance(cases, dict):
            raise ValueError(f"portfolio manifest lacks a plan snapshot or case map: {root}")
        sources.append({"root": str(root.resolve()), "manifest_sha256": manifest_sha256})
        for case in snapshot:
            if not isinstance(case, dict) or not isinstance(case.get("case_id"), str):
                errors.append(f"{root}: invalid case in plan snapshot")
                continue
            case_id = case["case_id"]
            if case_id in observed_plan:
                errors.append(f"duplicate case across portfolio roots: {case_id}")
            observed_plan[case_id] = case
        for case_id, summary in cases.items():
            if case_id in merged_cases:
                errors.append(f"duplicate case summary across portfolio roots: {case_id}")
            merged_cases[case_id] = summary
    unknown = sorted(set(observed_plan) - set(expected))
    missing = sorted(set(expected) - set(observed_plan))
    drifted = sorted(case_id for case_id, case in observed_plan.items() if expected.get(case_id) != case)
    extra_summaries = sorted(set(merged_cases) - set(observed_plan))
    missing_summaries = sorted(set(observed_plan) - set(merged_cases))
    if unknown:
        errors.append("unknown cases: " + ", ".join(unknown))
    if missing:
        errors.append("missing active cases: " + ", ".join(missing))
    if drifted:
        errors.append("fixture provenance drift: " + ", ".join(drifted))
    if extra_summaries:
        errors.append("summaries outside source plans: " + ", ".join(extra_summaries))
    if missing_summaries:
        errors.append("missing summaries for source plan cases: " + ", ".join(missing_summaries))
    if errors:
        raise ValueError("; ".join(errors))
    completed = all(isinstance(summary, dict) and summary.get("status") == "complete" for summary in merged_cases.values())
    return {
        "schema_version": 1,
        "mode": "evaluation",
        "purpose": "merged full-portfolio evidence; source confirmations remain evaluation-only",
        "source_portfolios": sources,
        "total_cases": len(expected_cases),
        "plan_snapshot": expected_cases,
        "plan_sha256": _digest(expected_cases),
        "cases": {case_id: merged_cases[case_id] for case_id in sorted(merged_cases)},
        "status": "complete" if completed else "failed",
        "merged_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portfolio_roots", nargs="+", type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        state = merge(args.portfolio_roots)
    except ValueError as error:
        parser.error(str(error))
    args.output_root.mkdir(parents=True, exist_ok=True)
    target = args.output_root / "portfolio-run.json"
    target.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": state["status"], "output_root": str(args.output_root), "total_cases": state["total_cases"]}, ensure_ascii=False))
    return 0 if state["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
