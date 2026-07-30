#!/usr/bin/env python3
"""Score candidate PRDs against portable, source-controlled benchmark expectations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def evaluate_case(case: dict[str, object], candidate_root: Path) -> dict[str, object]:
    case_id = str(case.get("id", "")).strip()
    result: dict[str, object] = {"id": case_id or "<missing>", "passed": False, "failures": []}
    if not case_id:
        result["failures"] = ["invalid_case:missing_id"]
        return result
    for field in ("required_text", "forbidden_text"):
        value = case.get(field, [])
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            result["failures"] = [f"invalid_case:{field}"]
            return result
    prd_path = candidate_root / case_id / "prd.md"
    if not prd_path.is_file():
        result["failures"] = ["missing_prd"]
        return result
    text = prd_path.read_text(encoding="utf-8")
    failures = [f"missing:{item}" for item in case.get("required_text", []) if str(item) not in text]
    failures.extend(f"forbidden:{item}" for item in case.get("forbidden_text", []) if str(item) in text)
    result["failures"] = failures
    result["passed"] = not failures
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate generated PRDs against a deterministic benchmark suite.")
    parser.add_argument("--benchmark-dir", type=Path, default=Path("evals/prd-benchmark/cases"))
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    cases = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(args.benchmark_dir.glob("*.json"))]
    results = [evaluate_case(case, args.candidate_root) for case in cases]
    passed = sum(bool(result["passed"]) for result in results)
    payload = {"total": len(results), "passed": passed, "score": round(passed / len(results), 3) if results else 0, "results": results}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if passed != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
