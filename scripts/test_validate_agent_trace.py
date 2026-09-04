#!/usr/bin/env python3
"""Regression tests for trace parsing and durable PRD lineage validation."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from validate_agent_trace import (
    field_has_list_item,
    list_field_values,
    mapping_item_blocks,
    nested_section_text,
    scalar_value,
    validate_artifact_lineage,
    validate_implemented_feature_evidence_packet,
)


class TraceBlockListTests(unittest.TestCase):
    def test_same_indent_sequence_is_a_mapping_value(self) -> None:
        text = "agent_strategy:\n  success_criteria:\n  - complete delivery\n  goal: keep scope bounded\n"
        self.assertTrue(field_has_list_item(text, "success_criteria"))

    def test_nested_section_keeps_same_indent_sequence(self) -> None:
        text = "review_loop:\n  finding_closures:\n  - finding: safety\n    disposition: fixed\n  final_recommendation: blocked\n"
        closures = nested_section_text(text, "finding_closures")
        self.assertEqual(len(mapping_item_blocks(closures, "finding")), 1)

    def test_root_sequence_mapping_blocks_are_all_found(self) -> None:
        text = "- id: DEC-ONE\n  decision: first\n- id: DEC-TWO\n  decision: second\n"
        self.assertEqual(len(mapping_item_blocks(text, "id")), 2)

    def test_folded_plain_scalars_preserve_exact_review_finding(self) -> None:
        text = (
            "critical_or_high_findings:\n"
            "- Required product, engineering, privacy, security, legal, payment, launch, and\n"
            "  independent validation decisions remain unapproved.\n"
            "finding_closures:\n"
            "- finding: Required product, engineering, privacy, security, legal, payment, launch,\n"
            "    and independent validation decisions remain unapproved.\n"
        )
        expected = "Required product, engineering, privacy, security, legal, payment, launch, and independent validation decisions remain unapproved."
        self.assertEqual(list_field_values(text, "critical_or_high_findings"), [expected])
        self.assertEqual(scalar_value(mapping_item_blocks(text, "finding")[0], "finding"), expected)


class ArtifactLineageTests(unittest.TestCase):
    @staticmethod
    def _write_trace(folder: Path, trace: dict[str, object]) -> Path:
        run_log = folder / "run-log.yaml"
        run_log.write_text(
            yaml.safe_dump(trace, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return run_log

    @staticmethod
    def _base_trace(mode: str) -> dict[str, object]:
        return {
            "agent_strategy": {"task_mode": "prd_delivery"},
            "resume_checkpoint": {"task_mode": "prd_delivery"},
            "context": {"source_mode": "brief-only", "product_documents_loaded": []},
            "artifact_lineage": {
                "mode": mode,
                "target_prd_path": "",
                "target_html_path": "",
                "revision_evidence_path": "",
                "revised_requirement_ids": [],
                "source_snapshot_path": "",
                "source_prd_display_name": "",
                "source_prd_sha256": "",
                "selected_source_scope": [],
                "historical_artifacts": [],
                "output_folder_reset": True,
            },
        }

    def test_accepts_new_and_in_place_prd_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            new_log = self._write_trace(folder, self._base_trace("new_run"))
            self.assertEqual(validate_artifact_lineage(new_log), [])

            (folder / "prd.md").write_text("| 5.1 | 修订 |\n", encoding="utf-8")
            (folder / "prd.html").write_text("<html></html>", encoding="utf-8")
            (folder / "revision-evidence.json").write_text(
                json.dumps({
                    "mode": "in_place_revision",
                    "controller_scope_ids": ["5.1"],
                    "deleted_requirement_ids": [],
                    "baseline_requirement_ids": ["5.1"],
                }),
                encoding="utf-8",
            )
            revision = self._base_trace("in_place_revision")
            revision["artifact_lineage"] = {
                "mode": "in_place_revision",
                "target_prd_path": "prd.md",
                "target_html_path": "prd.html",
                "revision_evidence_path": "revision-evidence.json",
                "revised_requirement_ids": ["5.1"],
                "deleted_requirement_ids": [],
                "source_snapshot_path": "",
                "source_prd_display_name": "",
                "source_prd_sha256": "",
                "selected_source_scope": [],
                "historical_artifacts": [{
                    "path": "prd.md",
                    "role": "comparison_only",
                    "excluded_from_current_facts": True,
                }],
                "output_folder_reset": False,
            }
            revision_log = self._write_trace(folder, revision)
            self.assertEqual(validate_artifact_lineage(revision_log), [])

    def test_requires_immutable_extraction_snapshot_and_matching_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = folder / "source-material" / "source-prd.md"
            source.parent.mkdir()
            source.write_text("# 旧 PRD\n\n### 5.7 结算流程\n", encoding="utf-8")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            trace = self._base_trace("extraction_run")
            trace["context"] = {
                "source_mode": "document-backed",
                "product_documents_loaded": ["source-material/source-prd.md"],
            }
            trace["artifact_lineage"] = {
                "mode": "extraction_run",
                "target_prd_path": "",
                "target_html_path": "",
                "revision_evidence_path": "",
                "revised_requirement_ids": [],
                "source_snapshot_path": "source-material/source-prd.md",
                "source_prd_display_name": "legacy-prd.md",
                "source_prd_sha256": digest,
                "selected_source_scope": ["5.7 结算流程"],
                "source_scope_resolution": [{
                    "selector": "5.7 结算流程",
                    "kind": "requirement_id",
                    "matches": ["5.7"],
                }],
                "historical_artifacts": [{
                    "path": "source-material/source-prd.md",
                    "role": "user_provided_input",
                    "excluded_from_current_facts": False,
                }],
                "output_folder_reset": True,
            }
            run_log = self._write_trace(folder, trace)
            self.assertEqual(validate_artifact_lineage(run_log), [])

            trace["artifact_lineage"]["mode"] = "extract_to_new"  # type: ignore[index]
            self.assertEqual(validate_artifact_lineage(self._write_trace(folder, trace)), [])

            trace["artifact_lineage"]["mode"] = "extraction_run"  # type: ignore[index]
            trace["artifact_lineage"]["source_prd_sha256"] = "0" * 64  # type: ignore[index]
            mismatched = self._write_trace(folder, trace)
            failures = validate_artifact_lineage(mismatched)
            self.assertTrue(any("does not match the source snapshot" in failure for failure in failures))

    def test_rejects_extraction_snapshot_outside_the_run_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "run"
            folder.mkdir()
            outside = root / "old-prd.md"
            outside.write_text("# 旧 PRD\n", encoding="utf-8")
            trace = self._base_trace("extraction_run")
            trace["context"] = {
                "source_mode": "document-backed",
                "product_documents_loaded": ["../old-prd.md"],
            }
            trace["artifact_lineage"] = {
                "mode": "extraction_run",
                "source_snapshot_path": "../old-prd.md",
                "source_prd_display_name": "old-prd.md",
                "source_prd_sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
                "selected_source_scope": ["第 5 章"],
                "historical_artifacts": [{
                    "path": "../old-prd.md",
                    "role": "user_provided_input",
                    "excluded_from_current_facts": False,
                }],
                "output_folder_reset": True,
            }
            failures = validate_artifact_lineage(self._write_trace(folder, trace))
            self.assertTrue(any("source_snapshot_path must stay inside the run folder" in failure for failure in failures))

    def test_rejects_fake_new_run_extraction_and_mismatched_resume_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = folder / "source-material" / "source-prd.md"
            source.parent.mkdir()
            source.write_text("# 旧 PRD\n", encoding="utf-8")
            trace = self._base_trace("new_run")
            trace["artifact_lineage"] = {
                "mode": "new_run",
                "source_snapshot_path": "source-material/source-prd.md",
                "source_prd_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "selected_source_scope": ["第 5 章"],
                "historical_artifacts": [{
                    "path": "source-material/source-prd.md",
                    "role": "user_provided_input",
                    "excluded_from_current_facts": False,
                }],
                "output_folder_reset": True,
            }
            trace["resume_checkpoint"] = {"task_mode": "implemented_feature_prd"}
            run_log = self._write_trace(folder, trace)
            failures = validate_artifact_lineage(run_log)
            self.assertTrue(any("not new_run" in failure for failure in failures))
            self.assertTrue(any("resume_checkpoint.task_mode" in failure for failure in failures))

    def test_new_lineage_uses_durable_provenance_not_request_words(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            trace = self._base_trace("new_run")
            trace["task"] = {"raw_request": "请提取这段讨论，生成新的 PRD"}
            trace["scenario"] = "extraction wording in a greenfield request"
            self.assertEqual(validate_artifact_lineage(self._write_trace(folder, trace)), [])
            trace["artifact_lineage"]["deleted_requirement_ids"] = ["5.1"]  # type: ignore[index]
            failures = validate_artifact_lineage(self._write_trace(folder, trace))
            self.assertTrue(any("must not claim in-place" in item for item in failures))

    def test_extraction_scope_requires_unique_snapshot_resolution_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = folder / "source-material" / "source-prd.md"
            source.parent.mkdir()
            source.write_text(
                "### 5.1 共享反馈\n第一处。\n\n### 5.2 共享反馈\n第二处。\n",
                encoding="utf-8",
            )
            digest = hashlib.sha256(source.read_bytes()).hexdigest()

            def extraction_trace(scope: list[str], resolution: list[dict[str, object]]) -> dict[str, object]:
                trace = self._base_trace("extraction_run")
                trace["context"] = {
                    "source_mode": "document-backed",
                    "product_documents_loaded": ["source-material/source-prd.md"],
                }
                trace["artifact_lineage"] = {
                    "mode": "extraction_run",
                    "target_prd_path": "",
                    "target_html_path": "",
                    "revision_evidence_path": "",
                    "revised_requirement_ids": [],
                    "source_snapshot_path": "source-material/source-prd.md",
                    "source_prd_display_name": "legacy.md",
                    "source_prd_sha256": digest,
                    "selected_source_scope": scope,
                    "source_scope_resolution": resolution,
                    "historical_artifacts": [{
                        "path": "source-material/source-prd.md",
                        "role": "user_provided_input",
                        "excluded_from_current_facts": False,
                    }],
                    "output_folder_reset": True,
                }
                return trace

            unknown = validate_artifact_lineage(self._write_trace(
                folder,
                extraction_trace(["9.9"], [{"selector": "9.9", "kind": "requirement_id", "matches": ["9.9"]}]),
            ))
            self.assertTrue(any("absent from the source snapshot" in item for item in unknown))

            ambiguous = validate_artifact_lineage(self._write_trace(
                folder,
                extraction_trace(["共享反馈"], [{"selector": "共享反馈", "kind": "heading", "matches": ["5.1 共享反馈"]}]),
            ))
            self.assertTrue(any("multiple source headings" in item for item in ambiguous))

            tampered = validate_artifact_lineage(self._write_trace(
                folder,
                extraction_trace(["5.1"], [{"selector": "5.1", "kind": "requirement_id", "matches": ["5.2"]}]),
            ))
            self.assertTrue(any("must exactly match" in item for item in tampered))

    def test_in_place_revision_deletion_requires_baseline_and_explicit_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prd.md").write_text("| 5.1 | 保留 |\n", encoding="utf-8")
            (folder / "prd.html").write_text("<html></html>", encoding="utf-8")
            evidence = {
                "mode": "in_place_revision",
                "controller_scope_ids": ["5.1", "5.2"],
                "deleted_requirement_ids": ["5.2"],
                "baseline_requirement_ids": ["5.1", "5.2"],
            }
            (folder / "revision-evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
            trace = self._base_trace("in_place_revision")
            trace["artifact_lineage"] = {
                "mode": "in_place_revision",
                "target_prd_path": "prd.md",
                "target_html_path": "prd.html",
                "revision_evidence_path": "revision-evidence.json",
                "revised_requirement_ids": ["5.1", "5.2"],
                "deleted_requirement_ids": ["5.2"],
                "source_snapshot_path": "",
                "source_prd_display_name": "",
                "source_prd_sha256": "",
                "selected_source_scope": [],
                "historical_artifacts": [{
                    "path": "prd.md",
                    "role": "comparison_only",
                    "excluded_from_current_facts": True,
                }],
                "output_folder_reset": False,
            }
            self.assertEqual(validate_artifact_lineage(self._write_trace(folder, trace)), [])

            evidence["deleted_requirement_ids"] = []
            (folder / "revision-evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
            failures = validate_artifact_lineage(self._write_trace(folder, trace))
            self.assertTrue(any("deleted_requirement_ids must match" in item for item in failures))

    def test_implemented_evidence_packet_requires_hash_and_portable_result_refs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            result = folder / "tool-results" / "implemented-evidence" / "capture.json"
            result.parent.mkdir(parents=True)
            result.write_text('{"capture":"ok"}\n', encoding="utf-8")
            packet_payload = {
                "branch_name": "feature/canvas",
                "changed_files": ["src/canvas.ts"],
                "visual_capture_recovery": [{"result_ref": "tool-results/implemented-evidence/capture.json"}],
            }
            packet = folder / "source-material" / "implemented-feature-evidence.json"
            packet.parent.mkdir()
            packet.write_text(json.dumps(packet_payload), encoding="utf-8")
            trace = {
                "agent_strategy": {"task_mode": "implemented_feature_prd"},
                "implemented_feature_prd": {
                    "active": True,
                    "mode": "implemented_feature_prd",
                    **packet_payload,
                    "evidence_packet": {
                        "path": "source-material/implemented-feature-evidence.json",
                        "sha256": hashlib.sha256(packet.read_bytes()).hexdigest(),
                        "imported_result_refs": ["tool-results/implemented-evidence/capture.json"],
                    },
                },
            }
            run_log = self._write_trace(folder, trace)
            self.assertEqual(validate_implemented_feature_evidence_packet(run_log), [])

            packet.write_text("{}\n", encoding="utf-8")
            failures = validate_implemented_feature_evidence_packet(self._write_trace(folder, trace))
            self.assertTrue(any("does not match the referenced packet" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
