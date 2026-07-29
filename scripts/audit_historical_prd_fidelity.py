#!/usr/bin/env python3
"""Review historical PRDs for source-backed scope, version, and figure preservation."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from prd_evidence_upgrade import IMAGE_SUFFIXES, RUNTIME_ASSET_NAMES, discover_output_folders


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_versions(value: str) -> list[tuple[int, int]]:
    return [tuple(int(part) for part in item.split(".")) for item in value]


def audit(folder: Path) -> dict[str, object]:
    prd_path = folder / "prd.md"
    if not prd_path.is_file():
        return {"output": str(folder), "status": "skipped", "findings": ["No PRD found."]}
    prd = read(prd_path)
    run_log = read(folder / "run-log.yaml") if (folder / "run-log.yaml").is_file() else ""
    detail_count = len(re.findall(r"(?m)^###\s+5\.\d+\s+", prd))
    figure_count = len(re.findall(r"\]\(\./assets/[^)]+\)", prd))
    real_assets = [
        item for item in (folder / "assets").glob("*")
        if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES and item.name not in RUNTIME_ASSET_NAMES
    ] if (folder / "assets").is_dir() else []
    requirement_ids = sorted(set(re.findall(r"\bR\d+\b", run_log)))
    logged_versions = parse_versions(re.findall(r"(?i)(?:PRD\s+v|prd\.md[^\n]{0,100}?\bv)(\d+\.\d+)", run_log))
    document_versions = parse_versions(re.findall(r"(?m)^\|\s*v(\d+\.\d+)\s*\|", prd))
    findings: list[str] = []
    if requirement_ids and detail_count < len(requirement_ids):
        findings.append(f"Scope contraction: {detail_count} detail sections for {len(requirement_ids)} source-backed requirements.")
    if logged_versions and (not document_versions or max(document_versions) < max(logged_versions)):
        findings.append("Version-history loss: source-backed requirement changes are absent from the PRD.")
    if len(real_assets) >= 8 and figure_count <= max(1, len(real_assets) // 4):
        findings.append(f"Figure review: {len(real_assets)} real assets but only {figure_count} referenced figures.")
    blocking_findings = [item for item in findings if item.startswith(("Scope contraction", "Version-history loss"))]
    return {
        "output": str(folder),
        "status": "needs_restoration" if blocking_findings else ("needs_visual_review" if findings else "passed"),
        "detail_count": detail_count,
        "source_requirement_count": len(requirement_ids),
        "figure_count": figure_count,
        "real_asset_count": len(real_assets),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", type=Path, nargs="+", default=[Path(__file__).resolve().parents[1]])
    parser.add_argument("--write", action="store_true", help="write tool-results/prd-fidelity-audit.json beside each reviewed PRD")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    reports = [audit(folder) for folder in discover_output_folders(args.roots)]
    if args.write:
        for report in reports:
            folder = Path(str(report["output"]))
            if (folder / "prd.md").is_file():
                results = folder / "tool-results"
                results.mkdir(exist_ok=True)
                (results / "prd-fidelity-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    else:
        for report in reports:
            print(f"{report['status']}: {report['output']}; findings={len(report['findings'])}")
    return 1 if any(report["status"] == "needs_restoration" for report in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
