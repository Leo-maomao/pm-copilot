#!/usr/bin/env python3
"""Regression coverage for the compact PRD delivery trace."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import yaml

from run_interactive_request import _runtime_identity
from validate_agent_trace import validate_artifact_lineage, validate_run_log


def trace_for(mode: str = "new_prd") -> dict[str, object]:
    lineage_mode = {
        "new_prd": "new_run",
        "implemented_feature_prd": "implemented_feature_run",
        "prd_revision": "in_place_revision",
        "prd_composition": "composition_run",
    }[mode]
    return {
        "run_id": "prd-2026-09-04",
        "pm_copilot_version": _runtime_identity()["version"],
        "runtime_identity": _runtime_identity(),
        "task": {"raw_request": "生成 PRD"},
        "agent_strategy": {"task_mode": mode, "goal": "生成可评审 PRD"},
        "confirmation": {"status": "confirmed", "scope": ["5.1"], "confirmed_at": "2026-09-04T00:00:00Z"},
        "artifact_lineage": {"mode": lineage_mode, "source_prds": [], "revision_baseline": {}},
        "implemented_feature_prd": {"active": False, "evidence_packet": {}},
        "frontend_figure_evidence": [],
        "specialist_evidence": [],
        "pm_arbitration": {"decisions": []},
        "review": {"status": "passed", "findings": []},
        "validation_results": [{"command": "validate_outputs.py", "status": "passed"}],
        "quality_decision": {"passed": True},
        "final_status": "complete",
    }


class TraceValidationTests(unittest.TestCase):
    def write(self, folder: Path, trace: dict[str, object]) -> Path:
        path = folder / "run-log.yaml"
        path.write_text(yaml.safe_dump(trace, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path

    def test_new_prd_trace_is_minimal_and_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write(Path(temporary), trace_for())
            self.assertEqual(validate_run_log(path)["failures"], [])

    def test_composition_requires_hashed_local_source_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            trace = trace_for("prd_composition")
            lineage = trace["artifact_lineage"]
            assert isinstance(lineage, dict)
            sources = []
            for index in range(1):
                snapshot = folder / "source-material" / f"source-{index}.md"
                snapshot.parent.mkdir(exist_ok=True)
                snapshot.write_text(f"# Source {index}", encoding="utf-8")
                sources.append({
                    "source_id": f"source-{index + 1}",
                    "snapshot_path": str(snapshot.relative_to(folder)),
                    "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
                    "selected_scope": ["5.1"],
                })
            lineage["source_prds"] = sources
            path = self.write(folder, trace)
            self.assertEqual(validate_artifact_lineage(path), [])
            lineage["source_prds"] = []
            self.write(folder, trace)
            self.assertIn("one or more", "\n".join(validate_artifact_lineage(path)))

    def test_revision_requires_selected_ids_and_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            trace = trace_for("prd_revision")
            lineage = trace["artifact_lineage"]
            assert isinstance(lineage, dict)
            lineage["revised_requirement_ids"] = ["5.1"]
            lineage["revision_baseline"] = {"prd_sha256": "a" * 64}
            path = self.write(folder, trace)
            self.assertEqual(validate_artifact_lineage(path), [])

    def test_specialist_evidence_has_no_fixed_count(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            trace = trace_for()
            trace["specialist_evidence"] = [{
                "id": f"specialist-{index}",
                "role": "functional_logic",
                "subject": f"independent question {index}",
                "status": "passed",
                "provider": "codex",
                "model": "gpt-5",
                "output_sha256": "a" * 64,
                "path": f"specialist-evidence/{index}.md",
            } for index in range(12)]
            evidence_root = folder / "specialist-evidence"
            evidence_root.mkdir()
            for index in range(12):
                (evidence_root / f"{index}.md").write_text("evidence", encoding="utf-8")
            trace["pm_arbitration"] = {"decisions": [{"id": "PM-1", "owner": "PM Orchestrator"}]}
            path = self.write(folder, trace)
            self.assertEqual(validate_run_log(path)["failures"], [])

    def test_failed_specialist_requires_error_not_a_synthetic_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            trace = trace_for()
            trace["specialist_evidence"] = [{
                "id": "frontend-1", "role": "frontend_evidence", "subject": "capture empty state",
                "status": "failed", "error": "page did not start", "failure_category": "runtime",
            }]
            trace["pm_arbitration"] = {"decisions": [{"id": "PM-1", "owner": "PM Orchestrator"}]}
            path = self.write(folder, trace)
            self.assertEqual(validate_run_log(path)["failures"], [])


if __name__ == "__main__":
    unittest.main()
