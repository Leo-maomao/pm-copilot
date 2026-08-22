#!/usr/bin/env python3
"""Turn PM Copilot evaluation cases into auditable end-to-end run plans."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "evals"
PHASES = ("intake", "discussion", "confirmation", "delivery", "validation")


def normalized_artifact(artifact: str) -> str:
    """Turn an evaluation contract reference into one atomic run-folder artifact.

    Evaluation prose can describe a directory or a family of optional files.
    The staged runner intentionally promotes and reviews exactly one file at a
    time, so those descriptions must resolve to a concrete evidence file rather
    than a literal glob or directory name.
    """
    value = artifact.strip().replace("outputs/<run-id>/", "").rstrip("/")
    aliases = {
        "portable_html": "prototype-web.html",
        "assets": "assets/implementation-evidence.md",
        "skills/<canonical-skill>/references/*": "proposed-skill/references/absorption-record.md",
        "skills/sharingan/references/<absorption-record>.md": "absorption-report.md",
    }
    return aliases.get(value, value)


def task_mode_for(artifacts: list[str], workflow: str, request: str) -> str:
    artifact_signal = " ".join(artifacts).lower()
    request_signal = request.lower()
    signal = " ".join([artifact_signal, workflow, request_signal]).lower()
    # Workflow documents routinely reference skills. Only a requested skill
    # artifact or an explicit absorption request is self-improvement work.
    if "skill.md" in artifact_signal or "skill absorption" in request_signal or "写轮眼吸收" in request_signal:
        return "self_improvement"
    if any(name in signal for name in ("catalog.md", "reference.md", "document-class", "structured reference")):
        return "structured_reference"
    if "prototype" in signal or "clickable annotated ui" in signal or "ui deliverable" in signal:
        return "ui_delivery"
    if "implemented" in signal and "prd" in signal:
        return "implemented_feature_prd"
    if "launch-decision" in signal and "prd.md" not in signal:
        return "launch_readiness"
    if "dev-tasks" in signal and "prd.md" not in signal:
        return "dev_handoff"
    return "prd_delivery"


def delivery_artifacts(artifacts: list[str], workflow: str, request: str) -> list[str]:
    """Add the universal discussion contract without forcing a PRD on every mode."""
    # Tool result files are produced only by the final deterministic validation
    # stage. Treating one as an Agent artifact would ask a model to fabricate
    # evidence for a command it did not run.
    normalized = [
        normalized_artifact(item)
        for item in artifacts
        if not normalized_artifact(item).startswith("tool-results/")
    ]
    if not normalized:
        signal = f"{workflow} {request}".lower()
        if "structured reference" in signal or "catalog" in signal:
            normalized.append("reference.md")
        elif re.search(r"\bui\b", signal) or "原型" in signal or "screenshot" in signal:
            normalized.extend(["prd.md", "prototype-web.html"])
        else:
            normalized.append("prd.md")
    for required in ("discussion.md", "confirmed-requirements.md", "run-log.yaml"):
        if required not in normalized:
            normalized.append(required)
    # The PM Copilot PRD contract requires a browser-readable sibling even when
    # an older evaluation only mentions the Markdown source in prose.
    if "prd.md" in normalized and "prd.html" not in normalized:
        normalized.append("prd.html")
    return normalized


def completion_evidence_for(artifacts: list[str]) -> list[str]:
    """List only evidence that the selected delivery can actually produce."""
    evidence = ["discussion transcript", "confirmed requirements"]
    evidence.extend(item for item in artifacts if item not in {"discussion.md", "confirmed-requirements.md", "run-log.yaml"})
    evidence.extend(["run-log.yaml", "delivery-check report"])
    return list(dict.fromkeys(evidence))


def section(text: str, heading: str) -> str:
    match = re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.MULTILINE)
    if not match:
        return ""
    remaining = text[match.end() :]
    next_heading = re.search(r"^##\s+", remaining, re.MULTILINE)
    return remaining[: next_heading.start() if next_heading else len(remaining)].strip()


def metadata_value(text: str, field: str) -> str:
    match = re.search(rf"^\|\s*{re.escape(field)}\s*\|\s*(.*?)\s*\|$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def code_block(body: str) -> str:
    match = re.search(r"```(?:text|markdown)?\s*\n(.*?)```", body, re.DOTALL)
    return match.group(1).strip() if match else body.strip()


def required_artifact_mentions(text: str) -> list[str]:
    """Extract concrete required artifacts from every authoritative case section.

    Older evaluation cases put delivery obligations in pass criteria or the
    expectation matrix rather than the short Required Artifacts section. Those
    obligations are part of the contract and cannot be silently discarded.
    """
    mentions: list[str] = []
    direct_names = {
        "prd.md", "prd.html", "run-log.yaml", "dev-tasks.yaml", "launch-decision.yaml",
        "tracking-plan.csv", "catalog.md", "catalog.html", "reference.md", "reference.html",
        "prototype-web.html", "portable_html", "SKILL.md",
    }
    for heading in ("Required Artifacts", "Expected Workflow", "Pass Criteria", "Artifact Expectation Matrix"):
        body = section(text, heading)
        for line in body.splitlines():
            line_lower = line.lower()
            if "not required" in line_lower or "do not generate" in line_lower:
                continue
            for artifact in re.findall(r"`([^`]+)`", line):
                output_path = artifact.startswith("outputs/<run-id>/")
                value = artifact.replace("outputs/<run-id>/", "").strip()
                accepted_alias = value in {"assets", "skills/<canonical-skill>/references/*", "skills/sharingan/references/<absorption-record>.md"}
                if (output_path or value in direct_names or accepted_alias) and re.fullmatch(r"[A-Za-z0-9_./<>*-]+(?:\.(?:md|html|yaml|csv))?", value):
                    if value not in mentions:
                        mentions.append(value)
        lower = body.lower()
        # These are explicit required deliverable classes, but are often named
        # without a file path. Resolve each to the portable evidence file the
        # staged runner can assign and independently review.
        if "ui deliverable" in lower and "not required" not in lower and "prototype-web.html" not in mentions:
            mentions.append("prototype-web.html")
    return mentions


def plan_case(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    raw_request = code_block(section(text, "Raw Request"))
    case_id = metadata_value(text, "Case ID") or path.stem.removesuffix("-eval")
    requires_confirmation = any(
        token in raw_request.lower()
        for token in ("privacy", "legal", "compliance", "security", "payment", "medical", "health", "未成年人", "法务", "支付")
    )
    artifacts = required_artifact_mentions(text)
    workflow = section(text, "Expected Workflow")
    resolved_artifacts = delivery_artifacts(artifacts, workflow, raw_request)
    return {
        "case_id": case_id,
        "path": path.relative_to(ROOT).as_posix(),
        "fixture_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "fixture_scope": metadata_value(text, "Fixture Scope") or "unspecified",
        "raw_request": raw_request,
        "completion_policy": "full_delivery",
        "required_phases": list(PHASES),
        "requires_explicit_confirmation": requires_confirmation,
        "requires_model_discussion": True,
        "requires_agent_execution": True,
        "task_mode": task_mode_for(resolved_artifacts, workflow, raw_request),
        "required_artifacts": resolved_artifacts,
        "completion_evidence": completion_evidence_for(resolved_artifacts),
    }


def scenario_set_cases(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    parent_id = metadata_value(text, "Case ID") or path.stem.removesuffix("-eval")
    cases = []
    for line in section(text, "Scenario Set").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6 or not re.fullmatch(r"S\d+", cells[0]):
            continue
        round_id, scenario, product_type, context_mode, pressure, coverage = cells
        raw_request = (
            f"Complete the PM delivery for {scenario}. Product type: {product_type}. "
            f"Context mode: {context_mode}. Primary pressure: {pressure}. "
            f"The delivery must cover: {coverage}."
        )
        artifacts = ["prd.md", "prd.html", "run-log.yaml"]
        cases.append({
            "case_id": f"{parent_id}-{round_id.lower()}",
            "parent_case_id": parent_id,
            "path": path.relative_to(ROOT).as_posix(),
            "raw_request": raw_request,
            "completion_policy": "full_delivery",
            "required_phases": list(PHASES),
            "requires_explicit_confirmation": any(
                term in (pressure + " " + coverage).lower()
                for term in ("payment", "legal", "privacy", "security", "compliance", "minors", "copyright")
            ),
            "requires_model_discussion": True,
            "requires_agent_execution": True,
            "task_mode": task_mode_for(artifacts, "", raw_request),
            "required_artifacts": delivery_artifacts(artifacts, "", raw_request),
            "completion_evidence": completion_evidence_for(delivery_artifacts(artifacts, "", raw_request)),
        })
    return cases


def portfolio() -> dict[str, Any]:
    cases = []
    for path in sorted(EVAL_ROOT.glob("*-eval.md")):
        planned = plan_case(path)
        cases.extend(scenario_set_cases(path) if not planned["raw_request"] else [planned])
    invalid = [case["case_id"] for case in cases if not case["raw_request"]]
    return {
        "schema_version": 1,
        "phases": list(PHASES),
        "total_cases": len(cases),
        "full_delivery_cases": len(cases),
        "invalid_cases": invalid,
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit the full portfolio plan as JSON")
    args = parser.parse_args()
    result = portfolio()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"evaluation cases: {result['total_cases']}")
        print(f"full delivery: {result['full_delivery_cases']}")
        if result["invalid_cases"]:
            print("invalid cases: " + ", ".join(result["invalid_cases"]))
    return 1 if result["invalid_cases"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
