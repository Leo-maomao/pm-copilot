#!/usr/bin/env python3
"""Create one immutable, auditable evaluation result per active case."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from audit_evaluation_portfolio import case_evidence_failures
from plan_evaluation_portfolio import ROOT, portfolio
from portfolio_contract import plan_digest


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _candidate_sort_key(candidate: dict[str, Any]) -> tuple[str, str, str]:
    state = candidate["state"]
    completed_at = max((str(call.get("completed_at", "")) for call in state.get("agent_calls", [])), default="")
    return (completed_at, candidate["manifest_sha256"], candidate["folder"])


def canonicalize(source_root: Path, verify: bool = False, verify_case_ids: set[str] | None = None) -> dict[str, Any]:
    """Select at most one independently valid historical result per active case."""
    cases = portfolio()["cases"]
    active = {case["case_id"]: case for case in cases}
    candidates: dict[str, list[dict[str, Any]]] = {case_id: [] for case_id in active}
    ignored: list[dict[str, str]] = []
    for manifest_path in sorted(source_root.glob("*/scenario-run.json")):
        try:
            state = _load(manifest_path)
        except (OSError, json.JSONDecodeError) as error:
            ignored.append({"folder": str(manifest_path.parent), "reason": f"unreadable manifest: {error}"})
            continue
        case_id = str(state.get("case", {}).get("case_id", ""))
        if case_id not in active:
            continue
        # Structural screening is intentionally cheap. Expensive final
        # validators run only for candidates that could become canonical.
        errors = case_evidence_failures(active[case_id], manifest_path.parent)
        candidate = {
            "folder": str(manifest_path.parent.resolve()),
            "manifest_sha256": _sha256(manifest_path),
            "state": state,
            "errors": errors,
        }
        candidates[case_id].append(candidate)
    selections: dict[str, Any] = {}
    rejections: dict[str, list[dict[str, str]]] = {}
    for case_id, entries in candidates.items():
        valid = sorted((item for item in entries if not item["errors"]), key=_candidate_sort_key, reverse=True)
        if verify and (verify_case_ids is None or case_id in verify_case_ids):
            verified: list[dict[str, Any]] = []
            for item in valid:
                verification_errors = case_evidence_failures(active[case_id], Path(item["folder"]), verify=True)
                if verification_errors:
                    item["errors"] = verification_errors
                else:
                    item["verified_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
                    verified.append(item)
            valid = verified
        rejected = [
            {"folder": item["folder"], "manifest_sha256": item["manifest_sha256"], "reason": "; ".join(item["errors"])}
            for item in entries if item["errors"]
        ]
        if valid:
            selected = valid[0]
            selections[case_id] = {
                "status": "complete",
                "folder": selected["folder"],
                "scenario_manifest_sha256": selected["manifest_sha256"],
                "selection_rule": "latest attributable completion timestamp, then manifest hash and path",
                "verified_at": selected.get("verified_at"),
            }
            rejected.extend({
                "folder": item["folder"], "manifest_sha256": item["manifest_sha256"],
                "reason": "valid duplicate; superseded by deterministic canonical selection",
            } for item in valid[1:])
        else:
            selections[case_id] = {"status": "missing", "folder": "", "scenario_manifest_sha256": ""}
        if verify:
            rejected.extend({
                "folder": item["folder"], "manifest_sha256": item["manifest_sha256"], "reason": "; ".join(item["errors"])
            } for item in entries if item["errors"] and not any(entry["folder"] == item["folder"] for entry in rejected))
        if rejected:
            rejections[case_id] = rejected
    return {
        "schema_version": 1,
        "mode": "evaluation_canonical_index",
        "source_root": str(source_root.resolve()),
        "plan_snapshot": cases,
        "plan_sha256": plan_digest(cases),
        "cases": selections,
        "rejections": rejections,
        "ignored": ignored,
        "summary": {"total": len(cases), "complete": sum(item["status"] == "complete" for item in selections.values())},
        "status": "complete" if all(item["status"] == "complete" for item in selections.values()) else "partial",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT / "outputs")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true", help="rerun final validators for eligible candidates")
    parser.add_argument("--verify-case", action="append", dest="verify_case_ids", help="limit --verify to a known canonical candidate")
    args = parser.parse_args()
    result = canonicalize(args.source_root, args.verify, set(args.verify_case_ids or []) or None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"canonical index: {args.output}")
    print(f"valid active cases: {result['summary']['complete']}/{result['summary']['total']}")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
