#!/usr/bin/env python3
"""Regression tests for complete evaluation-scenario execution."""

from __future__ import annotations

import tempfile
import unittest
import hashlib
import json
import os
import re
from pathlib import Path
from unittest.mock import patch

from run_evaluation_scenario import SOL_MODEL, TERRA_MODEL, _canonicalize_unparseable_trace_contract, _normalize_trace_contract_fields, confirmation_mode_for, execute_case, failed_check_text, finalize_quality_decision, has_accepted_stage_review, has_required_stage_reviews, install_annotation_contract, load_case, normalize_prd_contract, normalize_trace_structure, prepare_prd_scaffold, prepare_stage_workspace, prd_section_transaction_needed, refresh_annotation_review_after_contract_upgrade, refresh_trace_review_after_finalization, repair_artifact, review_stage_artifact, run_agent_stage, run_folder, stage_model_selection, stage_prompt, stage_quality_prompt, synchronize_case_contract


def fake_worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
    if "Stage Quality Review Agent" in prompt:
        return {"provider": provider, "model": "test", "status": "complete", "output": '{"status":"pass","blocking_findings":[],"acceptance_evidence":["handoff checked"]}', "error": ""}
    marker = "Write exactly one complete artifact at "
    target = Path(prompt.split(marker, 1)[1].split(". Do not modify", 1)[0])
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.name == "run-log.yaml":
        target.write_text("agent_strategy:\n  task_mode: prd_delivery\n", encoding="utf-8")
    else:
        target.write_text("# Complete evaluation artifact\n\nConcrete delivery content.\n", encoding="utf-8")
    return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}


class EvaluationScenarioRunnerTest(unittest.TestCase):
    def test_same_case_uses_one_canonical_run_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = run_folder("decision-first-prd", root)
            first.mkdir()
            self.assertEqual(run_folder("decision-first-prd", root), first)
            self.assertFalse((root / f"{first.name}-2").exists())

    def test_resume_migrates_to_current_fixture_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            case = load_case("offline-sync-conflict-resolution")
            state = {
                "case": {"task_mode": "prd_delivery", "required_artifacts": ["prd.md"]},
                "status": "failed",
                "phases": [
                    {"name": "intake", "status": "complete"},
                    {"name": "discussion", "status": "complete"},
                    {"name": "confirmation", "status": "complete"},
                    {"name": "delivery", "status": "complete", "artifacts": ["prd.md", "prd.html"]},
                    {"name": "validation", "status": "failed"},
                ],
            }
            self.assertTrue(synchronize_case_contract(state, case, folder))
        self.assertEqual(state["case"], case)
        self.assertEqual(state["phases"][3]["artifacts"], ["prd.md", "prototype-web.html", "dev-tasks.yaml", "prd.html"])
        self.assertEqual(state["phases"][3]["status"], "planned")
        self.assertEqual(state["phases"][4]["status"], "planned")
        self.assertEqual(state["status"], "running")

    def test_stage_workspace_includes_only_case_checkpoint_and_curated_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as source_directory, tempfile.TemporaryDirectory() as destination_directory:
            source = Path(source_directory)
            source.joinpath("discussion.md").write_text("discussion", encoding="utf-8")
            destination = Path(destination_directory) / "stage"
            prepare_stage_workspace(source, destination)
            self.assertEqual(destination.joinpath("discussion.md").read_text(encoding="utf-8"), "discussion")
            self.assertTrue(destination.joinpath(".pm-copilot-instructions/artifacts/prd-contract.md").is_file())
            self.assertTrue(destination.joinpath(".pm-copilot-instructions/templates/agent-run-log-template.yaml").is_file())

    def test_positional_run_folder_uses_the_sixth_execute_case_argument(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "canonical-case"
            report = execute_case("decision-first-prd", root, 1, True, "codex", folder)
        self.assertEqual(report["folder"], str(folder))

    def test_ui_annotation_contract_is_installed_without_replacing_page_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            prototype = folder / "prototype-web.html"
            prototype.write_text("<!doctype html><html><body><h1>Model-owned campaign surface</h1></body></html>", encoding="utf-8")
            self.assertTrue(install_annotation_contract(folder))
            completed = prototype.read_text(encoding="utf-8")
            self.assertIn("Model-owned campaign surface", completed)
            self.assertIn("window.annotationConfig = window.annotationConfig", completed)
            self.assertIn("note-group-title", completed)
            self.assertIn('data-annotation-placement', completed)
            self.assertIn('data-draggable="true"', completed)
            self.assertFalse(install_annotation_contract(folder))

    def test_ui_annotation_contract_does_not_override_existing_view_switcher(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            prototype = folder / "prototype-web.html"
            prototype.write_text("<!doctype html><html><body><script>function showView(name) { return name; }</script></body></html>", encoding="utf-8")
            self.assertTrue(install_annotation_contract(folder))
            self.assertEqual(prototype.read_text(encoding="utf-8").count("function showView("), 1)

    def test_prd_review_does_not_require_ui_artifact_when_case_does_not_require_one(self) -> None:
        prompt = stage_quality_prompt(
            load_case("ai-output-human-review-workflow"), Path("/tmp/run"), "delivery", "prd.md", Path("/tmp/review.json"),
        )
        self.assertIn("UI delivery is not a required artifact for this case", prompt)
        self.assertIn("Engineering handoff is not a required artifact for this case", prompt)
        self.assertIn("do not require an API contract", prompt)
        self.assertIn("one concise evidence item", prompt)
        self.assertIn("verify the file is valid JSON", prompt)

    def test_trace_normalization_adds_a_planned_visual_validation_command(self) -> None:
        normalized = _normalize_trace_contract_fields(
            "visual_validation:\n  status: required_later\n  screenshots: []\n  report_path: ''\n  limitation: pending\n"
        )
        self.assertIn("command: python3 scripts/validate_prototype_visual.py <run-folder>", normalized)

    def test_required_stage_reviews_reject_stale_trace_review_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for artifact in ("discussion.md", "confirmed-requirements.md", "prd.md", "run-log.yaml"):
                (folder / artifact).write_text(artifact, encoding="utf-8")
            case = load_case("decision-first-prd")
            state = {"agent_calls": []}
            for phase, artifact in (("discussion", "discussion.md"), ("confirmation", "confirmed-requirements.md"), ("delivery", "prd.md"), ("trace", "run-log.yaml")):
                state["agent_calls"].append({
                    "phase": "stage_quality_review", "reviewed_phase": phase,
                    "artifact": artifact, "review_passed": True, "reviewed_sha256": "stale",
                })
            self.assertFalse(has_required_stage_reviews(state, folder, case))

    def test_trace_normalization_adds_missing_quality_baselines(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "run-log.yaml").write_text("run_id: case-a\n", encoding="utf-8")
            self.assertTrue(normalize_trace_structure(folder))
            normalized = (folder / "run-log.yaml").read_text(encoding="utf-8")
        self.assertIn("quality_thresholds:", normalized)
        self.assertIn("review_scores:", normalized)

    def test_trace_normalization_adds_missing_visual_trace_for_ui_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prototype-web.html").write_text("<!doctype html>", encoding="utf-8")
            (folder / "run-log.yaml").write_text("run_id: case-a\n", encoding="utf-8")
            self.assertTrue(normalize_trace_structure(folder))
            normalized = (folder / "run-log.yaml").read_text(encoding="utf-8")
        self.assertIn("visual_validation:\n  required: true", normalized)
        self.assertIn("command: python3 scripts/validate_prototype_visual.py <run-folder>", normalized)
        self.assertIn("UI Delivery Agent", normalized)
        self.assertIn("design_calibration:", normalized)

    def test_unparseable_trace_gets_missing_controller_owned_quality_section(self) -> None:
        repaired = _canonicalize_unparseable_trace_contract(
            "run_id: case-a\nclarification_questions: [{id: Q1, question: contains: colon}]\n"
        )
        self.assertIn("quality_decision:\n  passed: false", repaired)

    def test_parseable_legacy_trace_backfills_missing_execution_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "run-log.yaml").write_text("run_id: legacy\ntask_mode: prd_delivery\n", encoding="utf-8")
            self.assertTrue(normalize_trace_structure(folder))
            normalized = (folder / "run-log.yaml").read_text(encoding="utf-8")
        self.assertIn("agent_strategy:", normalized)
        self.assertIn("resume_checkpoint:", normalized)
        self.assertIn("replan_triggers:", normalized)

    def test_trace_normalization_uses_one_terminal_path_for_blocked_legacy_loop(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "run-log.yaml").write_text(
                "termination_condition:\n  status: blocked\n"
                "loop_policy:\n  enabled: true\n  human_checkpoint:\n    required_after_iteration: 1\n    status: pending\n"
                "loop_state:\n  conflict_resolution_status: blocked\n"
                "iteration_trace:\n  - iteration: 1\n    next_decision: stop_human_checkpoint\n"
                "loop_summary:\n  stop_reason: human_checkpoint\n",
                encoding="utf-8",
            )
            self.assertTrue(normalize_trace_structure(folder))
            normalized = (folder / "run-log.yaml").read_text(encoding="utf-8")
        self.assertIn("required_after_iteration: 0", normalized)
        self.assertIn("status: not_required", normalized)
        self.assertIn("next_decision: stop_blocked", normalized)
        self.assertIn("stop_reason: blocked", normalized)

    def test_trace_normalization_closes_only_a_historically_superseded_catalog_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "scenario-run.json").write_text(json.dumps({"agent_calls": [
                {"phase": "stage_quality_review", "reviewed_phase": "delivery", "artifact": "catalog.html", "review_passed": False},
                {"phase": "stage_quality_review", "reviewed_phase": "delivery", "artifact": "catalog.html", "review_passed": True},
            ]}), encoding="utf-8")
            (folder / "run-log.yaml").write_text(
                "review_loop:\n"
                "  critical_or_high_findings:\n"
                "  - 'catalog.html stage-quality review recorded review_passed: false; detailed findings are not available in allowed evidence.'\n"
                "  finding_closures:\n"
                "  - finding: 'catalog.html stage-quality review recorded review_passed: false; detailed findings are not available in allowed evidence.'\n"
                "    disposition: fixed\n"
                "  unresolved_findings:\n"
                "  - Catalog HTML review remains unresolved.\n"
                "structured_reference:\n"
                "  attention_points:\n"
                "  - attention_id: attention-html-review\n"
                "quality_decision:\n"
                "  passed: false\n"
                "  rationale: catalog.html has a recorded failed stage-quality review\n",
                encoding="utf-8",
            )
            self.assertTrue(normalize_trace_structure(folder))
            normalized = (folder / "run-log.yaml").read_text(encoding="utf-8")
        self.assertNotIn("Catalog HTML review remains unresolved", normalized)
        self.assertNotIn("attention-html-review", normalized)
        self.assertIn("historical catalog.html review is closed", normalized)

    def test_implemented_feature_legacy_trace_backfills_provenance_and_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prd.md").write_text("### 5.1 Verified behavior\n", encoding="utf-8")
            (folder / "run-log.yaml").write_text("task_mode: implemented_feature_prd\npm_copilot_version: unknown\n", encoding="utf-8")
            self.assertTrue(normalize_trace_structure(folder))
            normalized = (folder / "run-log.yaml").read_text(encoding="utf-8")
        version = (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip()
        self.assertIn(f"pm_copilot_version: {version}", normalized)
        self.assertIn("target_ref: 5.1", normalized)
        self.assertIn("requirement_id: 5.1", normalized)

    def test_ui_annotation_contract_does_not_append_a_second_system_to_native_template(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            prototype = folder / "prototype-web.html"
            prototype.write_text(
                "<script>var annotationConfig = {}; function renderAnnotationMarkers() {} function showView() {}</script>"
                '<button class="annotation-toggle"></button><section class="annotation-dialog"></section>'
                '<section class="annotation-list"><div class="note-group-title"></div></section>',
                encoding="utf-8",
            )
            self.assertTrue(install_annotation_contract(folder))
            completed = prototype.read_text(encoding="utf-8")
            self.assertNotIn("pm-copilot-annotation-contract-v10", completed)
            self.assertNotIn("Campaign scope", completed)
            self.assertIn("pm-copilot-native-annotation-fix-v10", completed)
            self.assertIn("pointerdown", completed)
            self.assertIn("data-active-annotation-id", completed)
            self.assertIn("box-sizing: border-box", completed)
            self.assertFalse(install_annotation_contract(folder))

    def test_ui_annotation_contract_migrates_v9_to_one_canonical_layer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            prototype = folder / "prototype-web.html"
            prototype.write_text(
                "<html><body><script>var annotationConfig = {}; function renderAnnotationMarkers() {} function showView() {}</script>"
                '<button class="annotation-toggle"></button><section class="annotation-dialog"></section>'
                '<section class="annotation-list"><div class="note-group-title"></div></section>'
                "<!-- pm-copilot-native-annotation-fix-v9 --><style>.annotation-list{display:block}</style><script>void 0;</script>"
                "</body></html>",
                encoding="utf-8",
            )
            self.assertTrue(install_annotation_contract(folder))
            completed = prototype.read_text(encoding="utf-8")
        self.assertIn("pm-copilot-annotation-contract-v11", completed)
        self.assertNotIn("pm-copilot-native-annotation-fix-v9", completed)

    def test_annotation_upgrade_carries_only_an_accepted_ui_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            target = folder / "prototype-web.html"
            target.write_text("<!-- pm-copilot-annotation-contract-v11 -->", encoding="utf-8")
            state = {"agent_calls": [{
                "phase": "stage_quality_review", "reviewed_phase": "delivery",
                "artifact": "prototype-web.html", "review_passed": True, "reviewed_sha256": "old",
            }]}
            self.assertTrue(refresh_annotation_review_after_contract_upgrade(state, folder))
            self.assertTrue(state["agent_calls"][0]["controller_annotation_contract_upgrade_after_review"])

    def test_annotation_contract_backfills_portable_boundary_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            prototype = folder / "prototype-web.html"
            prototype.write_text("<html><head></head><body><!-- pm-copilot-annotation-contract-v11 --></body></html>", encoding="utf-8")
            self.assertTrue(install_annotation_contract(folder))
            self.assertIn("portable_html_review_artifact", prototype.read_text(encoding="utf-8"))

    def test_annotation_contract_uses_chinese_toggle_label_for_chinese_page(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            prototype = folder / "prototype-web.html"
            prototype.write_text('<html lang="zh-CN"><head></head><body><!-- pm-copilot-annotation-contract-v11 --><button id="pm-annotation-toggle">Notes</button></body></html>', encoding="utf-8")
            self.assertTrue(install_annotation_contract(folder))
            self.assertIn(">注释</button>", prototype.read_text(encoding="utf-8"))

    def test_annotation_contract_renames_legacy_annotation_handler(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            prototype = folder / "prototype-web.html"
            prototype.write_text("<html><body>function showAnnotation() {}<!-- pm-copilot-annotation-contract-v11 --></body></html>", encoding="utf-8")
            self.assertTrue(install_annotation_contract(folder))
            self.assertIn("function legacyShowAnnotation()", prototype.read_text(encoding="utf-8"))

    def test_explicit_model_is_forwarded_to_each_agent_stage(self) -> None:
        observed_models = []

        def model_worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
            observed_models.append(model)
            return fake_worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit)

        with tempfile.TemporaryDirectory() as temporary:
            execute_case(
                "decision-first-prd", Path(temporary), 1, False,
                execute_worker=model_worker, max_revisions=0, model="gpt-5.6-luna",
            )
        self.assertTrue(observed_models)
        self.assertEqual(set(observed_models), {"gpt-5.6-luna"})

    def test_model_routing_does_not_assume_terra_or_sol(self) -> None:
        with patch.dict(
            os.environ,
            {"PM_COPILOT_MODEL_CATALOG": json.dumps({"models": [
                {"model": "user-fast", "provider": "codex", "capabilities": ["standard"]},
                {"model": "user-judge", "provider": "codex", "capabilities": ["judgment"]},
            ]})},
            clear=False,
        ):
            discussion, discussion_evidence = stage_model_selection("discussion", "discussion.md", None)
            prd, prd_evidence = stage_model_selection("delivery", "prd.md", None)
            review, review_evidence = stage_model_selection("delivery", "prd.md", None, review=True)
        self.assertEqual(discussion, "user-fast")
        self.assertEqual(prd, "user-judge")
        self.assertEqual(review, "user-judge")
        self.assertEqual(discussion_evidence["selection_status"], "selected")
        self.assertEqual(prd_evidence["required_capability"], "judgment")
        self.assertNotIn(prd, {TERRA_MODEL, SOL_MODEL})
        self.assertFalse(prd_evidence["explicit_override"])
        self.assertFalse(review_evidence["explicit_override"])

    def test_missing_model_is_explicitly_blocked_for_real_execution(self) -> None:
        with patch.dict(os.environ, {"PM_COPILOT_MODEL_CATALOG": "[]"}, clear=False):
            with patch("run_evaluation_scenario.discover_model_catalog", return_value=([], [])):
                selected, evidence = stage_model_selection("discussion", "discussion.md", None)
        self.assertIsNone(selected)
        self.assertEqual(evidence["selection_status"], "blocked")

    def test_explicit_model_overrides_adaptive_routing(self) -> None:
        selected, evidence = stage_model_selection("delivery", "prd.md", "codex/gpt-5.6-luna", review=True)
        self.assertEqual(selected, "codex/gpt-5.6-luna")
        self.assertTrue(evidence["explicit_override"])

    def test_budget_exhaustion_is_terminal_without_explicit_force_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case"
            folder.mkdir()
            state = {
                "status": "failed", "revision_stop_reason": "validation budget exhausted",
                "phases": [], "agent_calls": [], "artifacts": {}, "validation": [],
            }
            (folder / "scenario-run.json").write_text(json.dumps(state), encoding="utf-8")
            report = execute_case(
                "decision-first-prd", Path(temporary), 1, False,
                run_folder_path=folder, execute_worker=lambda *args: (_ for _ in ()).throw(AssertionError("no Agent")),
            )
            self.assertEqual(report["status"], "failed")
            self.assertIn("force_retry", report["termination_reason"])

    def test_trace_repair_does_not_rewrite_an_existing_canonical_log(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case"
            folder.mkdir()
            (folder / "run-log.yaml").write_text("agent_strategy:\n  task_mode: prd_delivery\n", encoding="utf-8")
            state = {"phases": [], "agent_calls": [{"phase": "trace", "artifact": "run-log.yaml", "status": "complete"}], "artifacts": {}}
            calls = []
            def must_not_run(*args):
                calls.append(args)
                raise AssertionError("existing trace must not be regenerated")
            self.assertTrue(run_agent_stage(state, load_case("decision-first-prd"), folder, {}, "trace", "run-log.yaml", "codex", 1, must_not_run))
            self.assertEqual(calls, [])

    def test_case_lock_rejects_a_second_controller_for_the_same_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case"
            with patch("run_evaluation_scenario.fcntl.flock", side_effect=BlockingIOError):
                with self.assertRaisesRegex(RuntimeError, "scenario is already running"):
                    execute_case("decision-first-prd", Path(temporary), 1, False, run_folder_path=folder)

    def setUp(self) -> None:
        # Most tests exercise stage persistence and ownership with a deliberately
        # minimal fake trace. Do not let that fixture invoke environment-bound
        # browser/tool preflight through the final delivery validator.
        self.validation = patch(
            "run_evaluation_scenario.validate",
            return_value=[{"command": ["deterministic-test-validation"], "status": "failed", "stdout": "minimal fixture", "stderr": ""}],
        )
        self.validation.start()

    def tearDown(self) -> None:
        self.validation.stop()

    def test_dry_run_plans_every_phase_with_mode_specific_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = execute_case("document-class-reference-prototype", Path(temporary), 1, True)
        self.assertEqual(report["status"], "planned")
        self.assertEqual(report["confirmation_mode"], "evaluation_draft_authorization")
        self.assertFalse(report["human_confirmation"])
        self.assertEqual([phase["name"] for phase in report["phases"]], ["intake", "discussion", "confirmation", "delivery", "validation"])
        self.assertIn("reference.md", report["phases"][3]["artifacts"])
        self.assertNotIn("prd.md", report["phases"][3]["artifacts"])

    def test_safety_case_keeps_complete_staged_delivery_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = execute_case("regulated-health-minor-clarification-gate", Path(temporary), 1, True)
        self.assertEqual(report["status"], "planned")
        self.assertTrue(report["case"]["requires_explicit_confirmation"])
        self.assertEqual(report["phases"][-1]["name"], "validation")

    def test_agent_stage_failure_stops_with_resumable_manifest(self) -> None:
        def failed_worker(*args, **kwargs):
            return {"provider": "test", "model": "test", "status": "timed_out", "output": "", "error": "timeout"}
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case-2026-08-17"
            report = execute_case("decision-first-prd", Path(temporary), 1, False, run_folder_path=folder, execute_worker=failed_worker)
            self.assertEqual(report["status"], "failed")
            self.assertTrue((folder / "scenario-run.json").is_file())
            self.assertEqual(report["phases"][1]["status"], "failed")

    def test_completed_agent_without_assigned_artifact_is_attributed_failure(self) -> None:
        def completed_without_output(*args, **kwargs):
            return {"provider": "test", "model": "test", "status": "complete", "output": "done", "error": ""}
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case"
            folder.mkdir()
            state = {"phases": [{"name": "delivery", "status": "planned"}], "agent_calls": [], "artifacts": {}}
            completed = run_agent_stage(
                state, load_case("decision-first-prd"), folder, {}, "delivery", "prd.md",
                "test", 1, completed_without_output,
            )
            self.assertFalse(completed)
            self.assertFalse((folder / "prd.md").exists())
            call = state["agent_calls"][0]
            self.assertEqual(call["status"], "failed")
            self.assertEqual(call["failure_category"], "agent_no_output")
            self.assertIn("prd.md", call["error"])

    def test_unconfirmed_agent_stop_retains_isolated_workspace(self) -> None:
        def orphaned_worker(*args, **kwargs):
            return {
                "provider": "seawork-claude", "model": "test", "status": "orphaned",
                "error": "Agent exceeded timeout; stop was issued but Seawork still reports running",
                "cleanup_blocked": True, "agent_id": "test-agent-id",
            }
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case"
            folder.mkdir()
            state = {"phases": [{"name": "discussion", "status": "planned"}], "agent_calls": [], "artifacts": {}}
            completed = run_agent_stage(
                state, load_case("decision-first-prd"), folder, {}, "discussion", "discussion.md",
                "seawork-claude", 1, orphaned_worker,
            )
            self.assertFalse(completed)
            call = state["agent_calls"][0]
            self.assertEqual(call["workspace_cleanup_status"], "retained_pending_agent_stop_confirmation")
            self.assertTrue(Path(call["isolated_workspace_path"]).is_dir())

    def test_completed_agent_stage_persists_artifact_evidence_before_next_stage(self) -> None:
        def first_stage_only(*args, **kwargs):
            return fake_worker(*args, **kwargs)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case-2026-08-17"
            report = execute_case("decision-first-prd", Path(temporary), 1, False, run_folder_path=folder, execute_worker=first_stage_only)
            # The fixture's minimal run-log intentionally fails contract validation,
            # but every produced artifact must remain attributable in the manifest.
            self.assertTrue(report["artifacts"]["discussion.md"]["exists"])

    def test_invalid_trace_repair_can_replace_an_invalid_existing_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case"
            folder.mkdir()
            original = "schema_version: 1\nagent_strategy:\n  task_mode: prd_delivery\n"
            (folder / "run-log.yaml").write_text(original, encoding="utf-8")
            state = {
                "phases": [{"name": "trace", "status": "failed"}],
                "agent_calls": [], "artifacts": {},
            }
            def writes_bad_trace(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
                target = Path(prompt.split("Write exactly one complete artifact at ", 1)[1].split(". Do not modify", 1)[0])
                target.write_text("schema_version: 1\n", encoding="utf-8")
                return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}
            with patch("run_evaluation_scenario.subprocess.run") as run:
                run.return_value = __import__("subprocess").CompletedProcess([], 1, "invalid", "")
                done = run_agent_stage(state, load_case("decision-first-prd"), folder, {}, "trace", "run-log.yaml", "codex", 1, writes_bad_trace)
            self.assertTrue(done)
            repaired = (folder / "run-log.yaml").read_text(encoding="utf-8")
            self.assertIn("schema_version: 1", repaired)
            self.assertIn("quality_decision:\n  passed: false", repaired)

    def test_invalid_trace_repair_does_not_replace_a_valid_existing_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case"
            folder.mkdir()
            original = "schema_version: 1\nagent_strategy:\n  task_mode: prd_delivery\n"
            (folder / "run-log.yaml").write_text(original, encoding="utf-8")
            state = {"phases": [{"name": "trace", "status": "failed"}], "agent_calls": [], "artifacts": {}}
            def writes_bad_trace(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
                target = Path(prompt.split("Write exactly one complete artifact at ", 1)[1].split(". Do not modify", 1)[0])
                target.write_text("schema_version: 1\n", encoding="utf-8")
                return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}
            with patch("run_evaluation_scenario.subprocess.run") as run:
                run.side_effect = [
                    __import__("subprocess").CompletedProcess([], 0, "valid", ""),
                    __import__("subprocess").CompletedProcess([], 1, "invalid", ""),
                ]
                done = run_agent_stage(state, load_case("decision-first-prd"), folder, {}, "trace", "run-log.yaml", "codex", 1, writes_bad_trace)
            self.assertFalse(done)
            self.assertEqual((folder / "run-log.yaml").read_text(encoding="utf-8"), original)

    def test_resume_uses_final_validation_before_regenerating_accepted_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case"
            folder.mkdir()
            case = load_case("decision-first-prd")
            state = {
                "status": "running", "language": "zh", "validation": [], "agent_calls": [],
                "phases": [
                    {"name": "intake", "status": "complete"}, {"name": "discussion", "status": "complete"},
                    {"name": "confirmation", "status": "complete"}, {"name": "delivery", "status": "complete", "artifacts": ["prd.md", "prd.html"]},
                    {"name": "validation", "status": "planned"},
                ],
            }
            for artifact in ("discussion.md", "confirmed-requirements.md", "prd.md", "prd.html", "run-log.yaml"):
                (folder / artifact).write_text("complete", encoding="utf-8")
            state["agent_calls"] = [
                {
                    "phase": "stage_quality_review",
                    "reviewed_phase": phase,
                    "artifact": artifact,
                    "review_passed": True,
                    "reviewed_sha256": hashlib.sha256((folder / artifact).read_bytes()).hexdigest(),
                }
                for phase, artifact in (
                    ("discussion", "discussion.md"),
                    ("confirmation", "confirmed-requirements.md"),
                    ("delivery", "prd.md"),
                    ("trace", "run-log.yaml"),
                )
            ]
            (folder / "scenario-run.json").write_text(__import__("json").dumps(state), encoding="utf-8")
            with patch("run_evaluation_scenario.normalize_trace_structure", return_value=False), patch(
                "run_evaluation_scenario.normalize_prd_contract", return_value=False
            ), patch("run_evaluation_scenario.validate", return_value=[{"status": "passed", "command": ["test"]}]), patch(
                "run_evaluation_scenario.finalize_quality_decision", return_value=False
            ):
                report = execute_case("decision-first-prd", Path(temporary), 1, False, run_folder_path=folder, execute_worker=lambda *args: (_ for _ in ()).throw(AssertionError("no Agent expected")))
            self.assertEqual(report["status"], "complete")
            self.assertEqual(report["revision_stop_reason"], "resumed deterministic validation success")

    def test_resume_accepts_current_prd_when_latest_review_passed_after_stage_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case"
            folder.mkdir()
            case = load_case("decision-first-prd")
            prd = folder / "prd.md"
            prd.write_text("complete", encoding="utf-8")
            state = {
                "status": "failed", "language": "zh", "validation": [],
                "agent_calls": [],
                "phases": [
                    {"name": "intake", "status": "complete"}, {"name": "discussion", "status": "complete"},
                    {"name": "confirmation", "status": "complete"}, {"name": "delivery", "status": "failed", "artifacts": ["prd.md", "prd.html"]},
                    {"name": "validation", "status": "failed"},
                ],
            }
            for artifact in ("discussion.md", "confirmed-requirements.md", "prd.html", "run-log.yaml"):
                (folder / artifact).write_text("complete", encoding="utf-8")
            state["agent_calls"] = [
                {
                    "phase": "stage_quality_review",
                    "reviewed_phase": phase,
                    "artifact": artifact,
                    "review_passed": True,
                    "reviewed_sha256": hashlib.sha256((folder / artifact).read_bytes()).hexdigest(),
                }
                for phase, artifact in (
                    ("discussion", "discussion.md"),
                    ("confirmation", "confirmed-requirements.md"),
                    ("delivery", "prd.md"),
                    ("trace", "run-log.yaml"),
                )
            ]
            (folder / "scenario-run.json").write_text(json.dumps(state), encoding="utf-8")
            with patch("run_evaluation_scenario.normalize_trace_structure", return_value=False), patch(
                "run_evaluation_scenario.normalize_prd_contract", return_value=False
            ), patch("run_evaluation_scenario.validate", return_value=[{"status": "passed", "command": ["test"]}]), patch(
                "run_evaluation_scenario.finalize_quality_decision", return_value=False
            ):
                report = execute_case("decision-first-prd", Path(temporary), 1, False, run_folder_path=folder, execute_worker=lambda *args: (_ for _ in ()).throw(AssertionError("no Agent expected")))
            self.assertEqual(report["status"], "complete")

    def test_failed_confirmation_review_blocks_downstream_delivery(self) -> None:
        calls = []

        def reviewer_blocks_confirmation(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
            calls.append(prompt)
            if "Stage Quality Review Agent" in prompt:
                if "Stage: confirmation" in prompt:
                    return {"provider": provider, "model": "test", "status": "complete", "output": '{"status":"needs_revision","blocking_findings":["missing scope boundary"]}', "error": ""}
                return {"provider": provider, "model": "test", "status": "complete", "output": '{"status":"pass","blocking_findings":[],"acceptance_evidence":["handoff checked"]}', "error": ""}
            return fake_worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit)

        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case-2026-08-18"
            report = execute_case("decision-first-prd", Path(temporary), 1, False, run_folder_path=folder, execute_worker=reviewer_blocks_confirmation, max_revisions=0)
            self.assertEqual(report["status"], "failed")
            self.assertFalse((folder / "prd.md").exists())
            self.assertIn("stage quality budget exhausted", report["revision_stop_reason"])

    def test_partial_artifact_is_retried_when_phase_was_not_complete(self) -> None:
        calls = []

        def retrying_worker(*args, **kwargs):
            calls.append(1)
            return fake_worker(*args, **kwargs)

        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case-2026-08-17"
            folder.mkdir()
            (folder / "discussion.md").write_text("partial", encoding="utf-8")
            # A manifest with a non-complete discussion phase is the only
            # authoritative resume signal; the stale file must not be trusted.
            report = execute_case("decision-first-prd", Path(temporary), 1, False, run_folder_path=folder, execute_worker=retrying_worker)
            self.assertGreaterEqual(len(calls), 1)

    def test_agent_cannot_mutate_an_unassigned_artifact(self) -> None:
        def violating_worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
            if "Stage Quality Review Agent" in prompt:
                return fake_worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit)
            result = fake_worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit)
            target = Path(prompt.split("Write exactly one complete artifact at ", 1)[1].split(". Do not modify", 1)[0])
            target.parent.joinpath("foreign.md").write_text("unexpected", encoding="utf-8")
            return result

        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case-2026-08-17"
            report = execute_case("decision-first-prd", Path(temporary), 1, False, run_folder_path=folder, execute_worker=violating_worker)
            self.assertFalse((folder / "foreign.md").exists())
            self.assertTrue(report["agent_calls"][0]["isolated_workspace"])

    def test_validation_failure_revises_the_owned_artifact_before_stopping(self) -> None:
        failed = [
            {"command": ["scripts/validate_outputs.py"], "status": "failed", "stdout": "missing 用户场景", "stderr": ""},
            {"command": ["scripts/validate_agent_trace.py"], "status": "passed", "stdout": "", "stderr": ""},
            {"command": ["scripts/run_delivery_checks.py"], "status": "failed", "stdout": "same output failure", "stderr": ""},
        ]
        passed = [{"command": ["scripts/validate_outputs.py"], "status": "passed", "stdout": "", "stderr": ""}]
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case-2026-08-17"
            with patch("run_evaluation_scenario.validate", side_effect=[failed, passed]):
                report = execute_case("decision-first-prd", Path(temporary), 1, False, run_folder_path=folder, execute_worker=fake_worker, max_revisions=1)
            self.assertEqual(report["status"], "complete")
            self.assertEqual(report["revision_loops"], 1)
            self.assertGreaterEqual(len(report["agent_calls"]), 5)

    def test_quality_decision_missing_passed_field_is_closed_mechanically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "run-log.yaml").write_text("quality_decision:\n  decision: blocked\n", encoding="utf-8")
            checks = [
                {"command": ["scripts/validate_outputs.py"], "status": "failed", "stdout": "FAIL: Quality decision must explicitly pass for final generated artifacts", "stderr": ""},
                {"command": ["scripts/validate_agent_trace.py"], "status": "passed", "stdout": "", "stderr": ""},
            ]
            self.assertTrue(finalize_quality_decision(folder, checks))
            finalized = (folder / "run-log.yaml").read_text(encoding="utf-8")
            self.assertIn("passed: true", finalized)
            self.assertIn("failures: []", finalized)

    def test_reference_contract_failure_returns_to_reference_owner(self) -> None:
        checks = [{"command": ["scripts/validate_outputs.py"], "status": "failed", "stdout": "reference.md structured reference missing source_facts", "stderr": ""}]
        self.assertEqual(repair_artifact(load_case("document-class-reference-prototype"), checks), "reference.md")

    def test_reference_html_failure_is_not_stolen_by_delivery_check_output(self) -> None:
        checks = [
            {"command": ["scripts/validate_outputs.py"], "status": "failed", "stdout": "reference.html missing structured catalog/reference meta marker", "stderr": ""},
            {"command": ["scripts/run_delivery_checks.py"], "status": "failed", "stdout": "validate_prototype_visual.py passed prototype-web.html", "stderr": ""},
        ]
        self.assertEqual(repair_artifact(load_case("document-class-reference-prototype"), checks), "reference.html")

    def test_tracking_csv_contract_failure_returns_to_tracking_owner(self) -> None:
        checks = [{
            "command": ["scripts/validate_outputs.py"], "status": "failed",
            "stdout": "Tracking columns invalid in outputs/example/tracking-plan.csv", "stderr": "",
        }]
        self.assertEqual(repair_artifact(load_case("accessibility-critical-checkout-recovery"), checks), "tracking-plan.csv")

    def test_targeted_repair_feedback_excludes_unrelated_artifacts(self) -> None:
        checks = [{
            "command": ["scripts/run_delivery_checks.py"],
            "status": "failed",
            "stdout": "FAIL: prototype-web.html annotation marker is clipped\nFAIL: Tracking columns invalid in outputs/example/tracking-plan.csv",
            "stderr": "",
        }]
        feedback = failed_check_text(checks, "prototype-web.html")
        self.assertIn("prototype-web.html annotation marker is clipped", feedback)
        self.assertNotIn("tracking-plan.csv", feedback)

    def test_sibling_tracking_failure_does_not_trigger_current_case_repair(self) -> None:
        checks = [{
            "command": ["scripts/validate_repo.py"], "status": "failed",
            "stdout": "FAIL: Tracking columns invalid in outputs/older-case-2026-08-19/tracking-plan.csv",
            "stderr": "", "output_folder": "outputs/decision-first-prd-2026-08-19-6",
        }]
        self.assertIsNone(repair_artifact(load_case("decision-first-prd"), checks, Path("outputs/decision-first-prd-2026-08-19-6")))

    def test_stage_review_reads_json_file_not_seawork_dispatch_text(self) -> None:
        def file_backed_reviewer(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
            review_path = Path(prompt.split("Write ONLY one JSON object to ", 1)[1].split(" (UTF-8)", 1)[0])
            review_path.write_text('{"status":"pass","blocking_findings":[],"acceptance_evidence":["handoff checked"]}', encoding="utf-8")
            return {"provider": provider, "model": "test", "status": "complete", "output": "AGENT ID STATUS completed", "error": ""}

        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "case"
            folder.mkdir()
            (folder / "discussion.md").write_text("# discussion", encoding="utf-8")
            passed, findings = review_stage_artifact({"agent_calls": []}, load_case("decision-first-prd"), folder, "discussion", "discussion.md", "test", 1, file_backed_reviewer)
            self.assertTrue(passed, findings)

    def test_fixture_reviewer_does_not_require_invented_approval(self) -> None:
        prompt = stage_quality_prompt(load_case("regulated-health-minor-clarification-gate"), Path("/tmp/run"), "delivery", "prd.md", Path("/tmp/review.json"))
        self.assertIn("ask the artifact to invent those approvals", prompt)
        self.assertIn("owner, states the blocking phase", prompt)

    def test_prd_review_does_not_assign_renderer_or_trace_outputs_to_prd_agent(self) -> None:
        prompt = stage_quality_prompt(load_case("decision-first-prd"), Path("/tmp/run"), "delivery", "prd.md", Path("/tmp/review.json"))
        self.assertIn("renderer-owned derived", prompt)
        self.assertIn("trace-owned `run-log.yaml`", prompt)
        self.assertIn("do not require the UI file itself", prompt)

    def test_prd_review_accepts_exact_upstream_source_paths_as_provenance(self) -> None:
        prompt = stage_quality_prompt(
            load_case("decision-first-prd"), Path("/tmp/run"), "delivery", "prd.md", Path("/tmp/review.json")
        )
        self.assertIn("exact run-folder-relative paths", prompt)
        self.assertIn("sufficient source provenance", prompt)

    def test_resume_keeps_completed_artifact_when_later_phase_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prd.md").write_text("# retained", encoding="utf-8")
            state = {"phases": [{"name": "delivery", "status": "failed"}], "agent_calls": [{"phase": "delivery", "artifact": "prd.md", "status": "complete"}], "artifacts": {}}
            def must_not_run(*args, **kwargs):
                raise AssertionError("completed artifact must be resumed without another Agent call")
            self.assertTrue(run_agent_stage(state, load_case("decision-first-prd"), folder, {}, "delivery", "prd.md", "test", 1, must_not_run))

    def test_trace_prompt_is_write_first_and_scope_limited(self) -> None:
        prompt = stage_prompt(load_case("decision-first-prd"), Path("/tmp/run"), {}, "trace", "run-log.yaml")
        self.assertIn("write-first, single-file task", prompt)
        self.assertIn("do not research, run validation", prompt)

    def test_stage_prompt_requires_concrete_accountable_owners(self) -> None:
        prompt = stage_prompt(load_case("decision-first-prd"), Path("/tmp/run"), {}, "discussion", "discussion.md")
        self.assertIn("accountable owner identity", prompt)
        self.assertIn("never only a generic role", prompt)

    def test_discussion_prompt_forbids_skill_discovery_before_first_write(self) -> None:
        prompt = stage_prompt(load_case("decision-first-prd"), Path("/tmp/run"), {}, "discussion", "discussion.md")
        self.assertIn("first operation must create", prompt)
        self.assertIn("Do not load, invoke, inspect, or announce any skill", prompt)

    def test_confirmation_prompt_inlines_the_accepted_discussion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "discussion.md").write_text("Accepted scope marker", encoding="utf-8")
            prompt = stage_prompt(load_case("decision-first-prd"), folder, {}, "confirmation", "confirmed-requirements.md")
        self.assertIn("Accepted upstream discussion", prompt)
        self.assertIn("Accepted scope marker", prompt)
        self.assertIn("Do not read or modify it", prompt)

    def test_prd_prompt_inlines_accepted_upstream_records_and_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "discussion.md").write_text("Discussion marker", encoding="utf-8")
            (folder / "confirmed-requirements.md").write_text("Confirmation marker", encoding="utf-8")
            prompt = stage_prompt(load_case("decision-first-prd"), folder, {}, "delivery", "prd.md")
        self.assertIn("Discussion marker", prompt)
        self.assertIn("Confirmation marker", prompt)
        self.assertIn("Applicable PRD contract", prompt)
        self.assertIn("Canonical Structure", prompt)

    def test_prd_scaffold_is_one_editable_target_with_explicit_incomplete_markers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "prd.md"
            self.assertTrue(prepare_prd_scaffold(load_case("decision-first-prd"), target))
            self.assertFalse(prepare_prd_scaffold(load_case("decision-first-prd"), target))
            text = target.read_text(encoding="utf-8")
        self.assertIn("[[TO_BE_COMPLETED", text)
        self.assertIn("Requirement ID", text)

    def test_prd_prompt_requires_a_whole_file_replace_not_a_context_patch(self) -> None:
        prompt = stage_prompt(load_case("decision-first-prd"), Path("/tmp/run"), {}, "delivery", "prd.md")
        self.assertIn("direct whole-file write", prompt)
        self.assertIn("context-matching patch", prompt)

    def test_prd_section_transaction_requires_replacing_its_marker(self) -> None:
        prompt = stage_prompt(
            load_case("decision-first-prd"), Path("/tmp/run"), {}, "delivery", "prd.md",
            "SECTION_TRANSACTION\n[[PRD_SECTION_DOCUMENT]]\nAccepted evidence",
        )
        self.assertIn("Replace exactly the literal\nsection marker `[[PRD_SECTION_DOCUMENT]]`", prompt)
        self.assertIn("Do not retain, quote, or reference that marker", prompt)

    def test_prd_section_transaction_resumes_the_same_incomplete_canonical_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "prd.md"
            self.assertTrue(prd_section_transaction_needed(target))
            target.write_text("# PRD\n\n[[PRD_SECTION_DOCUMENT]]\n", encoding="utf-8")
            self.assertTrue(prd_section_transaction_needed(target))
            target.write_text("# Complete PRD\n", encoding="utf-8")
            self.assertFalse(prd_section_transaction_needed(target))

    def test_stage_prompt_uses_the_resolved_workspace_target(self) -> None:
        folder = Path("/tmp/pm-copilot-stage")
        prompt = stage_prompt(load_case("decision-first-prd"), folder, {}, "delivery", "prd.md")
        self.assertIn(str((folder / "prd.md").resolve()), prompt)


    def test_ui_delivery_prompt_requires_write_first_template_checkpoint(self) -> None:
        prompt = stage_prompt(
            load_case("accessibility-critical-checkout-recovery"), Path("/tmp/run"), {}, "delivery", "prototype-web.html"
        )
        self.assertIn("first action\nmust be to copy it", prompt)
        self.assertIn("Do not read global\nPM_COPILOT files", prompt)
        self.assertIn("project_workspace.py", prompt)

    def test_h5_visual_failure_routes_to_the_h5_artifact(self) -> None:
        checks = [{
            "command": ["scripts/validate_prototype_visual.py"],
            "status": "failed",
            "stdout": "prototype-h5.html: mobile.png has annotation layout issues",
            "stderr": "",
        }]
        self.assertEqual(repair_artifact(load_case("eval-001"), checks), "prototype-h5.html")

    def test_ui_delivery_prompt_requires_concrete_data_provenance(self) -> None:
        prompt = stage_prompt(
            load_case("accessibility-critical-checkout-recovery"), Path("/tmp/run"), {}, "delivery", "prototype-web.html"
        )
        self.assertIn("Concrete prototype data provenance is mandatory", prompt)
        self.assertIn("illustrative fixture data", prompt)
        self.assertIn("proposed targets", prompt)
        self.assertIn("Keep approval scopes executable", prompt)

    def test_ui_delivery_repair_does_not_replace_existing_artifact_from_template(self) -> None:
        prompt = stage_prompt(
            load_case("accessibility-critical-checkout-recovery"), Path("/tmp/run"), {}, "delivery", "prototype-web.html", "fix one button"
        )
        self.assertIn("Preserve every valid section", prompt)
        self.assertNotIn("first action\nmust be to copy it", prompt)

    def test_review_contract_wins_over_nonzero_codex_exit(self) -> None:
        def worker(*args, **kwargs):
            review_path = Path(re.search(r"Write ONLY one JSON object to (.+?) \(UTF-8\)", args[1]).group(1))
            review_path.write_text(json.dumps({"status": "pass", "summary": "ok", "blocking_findings": [], "acceptance_evidence": ["checked"]}), encoding="utf-8")
            return {"status": "failed", "exit_code": 1, "error": "shutdown warning"}
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "discussion.md").write_text("complete", encoding="utf-8")
            state = {"agent_calls": []}
            passed, _ = review_stage_artifact(state, load_case("decision-first-prd"), folder, "discussion", "discussion.md", "codex", 1, worker)
            self.assertTrue(passed)
            self.assertTrue(state["agent_calls"][-1]["nonzero_exit_with_contract"])

    def test_trace_initial_repair_does_not_require_running_a_validator(self) -> None:
        prompt = stage_prompt(
            load_case("decision-first-prd"), Path("/tmp/run"), {}, "trace", "run-log.yaml",
            "Check every required trace-contract field before writing, but do not run validation commands or claim validation evidence; independent final validation occurs in the next stage.",
        )
        self.assertIn("do not run validation commands", prompt)
        self.assertNotIn("Run validate_agent_trace.py", prompt)

    def test_trace_normalization_expands_inline_quality_thresholds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "run-log.yaml").write_text(
                "quality_thresholds: {delivery: 23, prd: 31, metrics_and_tracking: 21, ui_delivery: 24, review_checklist: 15}\n",
                encoding="utf-8",
            )
            self.assertTrue(normalize_trace_structure(folder))
            normalized = (folder / "run-log.yaml").read_text(encoding="utf-8")
            self.assertIn("quality_thresholds:\n  delivery: 23", normalized)
            self.assertIn("  review_checklist: 15", normalized)

    def test_controller_finalization_refreshes_only_accepted_trace_review_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            trace = folder / "run-log.yaml"
            trace.write_text("quality_decision:\n  passed: true\n", encoding="utf-8")
            state = {"agent_calls": [{
                "phase": "stage_quality_review", "reviewed_phase": "trace", "artifact": "run-log.yaml",
                "review_passed": True, "reviewed_sha256": "before",
            }]}
            self.assertTrue(refresh_trace_review_after_finalization(state, folder))
            self.assertTrue(state["agent_calls"][0]["controller_finalization_after_review"])
            self.assertTrue(has_accepted_stage_review(state, folder, "trace", "run-log.yaml"))

    def test_trace_normalization_preserves_sections_after_review_scores(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "run-log.yaml").write_text(
                "review_scores:\n  delivery:\n    score: 1\n"
                "quality_decision:\n  passed: false\n"
                "failures: []\n",
                encoding="utf-8",
            )
            self.assertTrue(normalize_trace_structure(folder))
            normalized = (folder / "run-log.yaml").read_text(encoding="utf-8")
            self.assertIn("quality_decision:\n  passed: false", normalized)
            self.assertIn("failures: []", normalized)

    def test_trace_normalization_expands_flow_style_contract_mappings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "run-log.yaml").write_text(
                "termination_condition: {status: blocked, evidence: pending}\n"
                "loop_policy: {enabled: true, human_checkpoint: {required_after_iteration: 1, status: pending}}\n",
                encoding="utf-8",
            )
            self.assertTrue(normalize_trace_structure(folder))
            normalized = (folder / "run-log.yaml").read_text(encoding="utf-8")
            self.assertIn("termination_condition:\n  status: blocked", normalized)
            self.assertIn("human_checkpoint:\n    required_after_iteration: 1", normalized)

    def test_trace_repair_preserves_valid_contract_and_defers_final_quality_closure(self) -> None:
        prompt = stage_prompt(
            load_case("decision-first-prd"), Path("/tmp/run"), {}, "trace", "run-log.yaml", "missing tool_plan"
        )
        self.assertIn("Preserve every valid section", prompt)
        self.assertIn("Do not rebuild it from the template", prompt)
        self.assertIn("Keep quality_decision: passed: false until", prompt)

    def test_initial_trace_prompt_requires_complete_score_and_memory_contract(self) -> None:
        prompt = stage_prompt(load_case("decision-first-prd"), Path("/tmp/run"), {}, "trace", "run-log.yaml")
        self.assertIn("memory_candidates.none: true", prompt)
        self.assertIn("review_scores with integer score, max_score, and status", prompt)
        self.assertIn("(32), prd (40)", prompt)
        self.assertIn("quality_thresholds exactly to delivery: 23, prd: 31", prompt)
        self.assertIn("metrics_and_tracking: 21, ui_delivery: 24, and review_checklist: 15", prompt)
        self.assertIn(f"confirmation_mode: {confirmation_mode_for(load_case('decision-first-prd'))}", prompt)
        self.assertIn("human_confirmation: false", prompt)
        self.assertIn("artifact_delta as a YAML mapping", prompt)
        self.assertIn("files_created", prompt)
        self.assertIn("commands_run", prompt)
        self.assertIn("selected_path at least one concrete list item", prompt)
        self.assertIn("next_actions at least one concrete owned action", prompt)
        self.assertIn("four required final validators", prompt)

    def test_prd_repair_prompt_retains_required_controlled_visual_placeholders(self) -> None:
        prompt = stage_prompt(
            load_case("decision-first-prd"), Path("/tmp/run"), {}, "delivery", "prd.md",
            repair_errors="invalid content",
        )
        self.assertIn("Retain a controlled required visual placeholder", prompt)
        self.assertNotIn("screenshot placeholders, and", prompt)

    def test_implemented_feature_trace_prompt_projects_placeholder_validator_contract(self) -> None:
        prompt = stage_prompt(load_case("eval-040"), Path("/tmp/run"), {}, "trace", "run-log.yaml")
        self.assertIn("existing_preview_discovery, project_runtime_activation, test_state_recovery", prompt)
        self.assertIn("playwright, chrome_devtools, computer_use", prompt)
        self.assertIn("passed, failed, blocked, not_available", prompt)
        self.assertIn("Each capture record's status must be one of", prompt)
        self.assertIn("non-empty run-folder-relative `result_ref`", prompt.replace("\n", " "))
        self.assertIn("visual figures require manual completion", prompt)
        self.assertIn("readiness.prd_status` to `ready for review`", prompt)

    def test_trace_stage_review_allows_pre_validation_quality_state(self) -> None:
        prompt = stage_quality_prompt(
            load_case("decision-first-prd"), Path("/tmp/run"), "trace", "run-log.yaml", Path("/tmp/review.json")
        )
        self.assertIn("quality_decision.passed is false before final validation", prompt)

    def test_delivery_prompt_selects_the_contract_for_each_handoff_artifact(self) -> None:
        case = load_case("agentic-product-manager-system")
        folder = Path("/tmp/run")
        self.assertIn("artifacts/prd-contract.md", stage_prompt(case, folder, {}, "delivery", "prd.md"))
        self.assertIn("artifacts/dev-task-contract.md", stage_prompt(case, folder, {}, "delivery", "dev-tasks.yaml"))
        self.assertIn("artifacts/launch-decision-contract.md", stage_prompt(case, folder, {}, "delivery", "launch-decision.yaml"))

    def test_prd_prompt_preserves_upstream_downstream_artifact_boundaries(self) -> None:
        prompt = stage_prompt(load_case("decision-first-prd"), Path("/tmp/run"), {}, "delivery", "prd.md")
        self.assertIn("exact identifier", prompt)
        self.assertIn("authoritative run-folder or repository-relative path", prompt)
        self.assertIn("never replace an identified artifact with a vague phrase", prompt)

    def test_completed_review_is_reused_only_for_same_artifact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            artifact = folder / "discussion.md"
            artifact.write_text("first", encoding="utf-8")
            state = {"agent_calls": [{"phase": "stage_quality_review", "reviewed_phase": "discussion", "artifact": "discussion.md", "review_passed": True, "reviewed_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}]}
            self.assertTrue(has_accepted_stage_review(state, folder, "discussion", "discussion.md"))
            artifact.write_text("changed", encoding="utf-8")
            self.assertFalse(has_accepted_stage_review(state, folder, "discussion", "discussion.md"))

    def test_trace_normalizer_removes_disabled_loop_placeholder_without_closing_quality(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "run-log.yaml"
            path.write_text(
                "agent_strategy:\n  success_criteria: []\n"
                "loop_policy:\n  enabled: false\n"
                "loop_state:\n  current_iteration: 1\n"
                "iteration_trace:\n  - iteration: 0\n    outcome: blocked\n"
                "loop_summary:\n  iterations_completed: 1\n"
                "guardrail_events:\n  - type: approval_boundary\n    decision: Drafting only\n"
                "quality_decision:\n  passed: false\n",
                encoding="utf-8",
            )
            self.assertTrue(normalize_trace_structure(Path(temporary)))
            text = path.read_text(encoding="utf-8")
            self.assertIn("success_criteria:\n    -", text)
            self.assertIn("iteration_trace: []", text)
            self.assertIn("current_iteration: 0", text)
            self.assertIn("iterations_completed: 0", text)
            self.assertIn("rationale: Derived from the recorded guardrail decision", text)
            self.assertIn("passed: false", text)

    def test_trace_normalizer_repairs_controller_owned_execution_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "run-log.yaml"
            path.write_text(
                "blockers:\n  - id: B1\n    status: open\n"
                "decision_record:\n  - id: DEC-001\n    decision: Preserve canonical result\n"
                "loop_policy:\n  enabled: false\n"
                "loop_summary:\n  stop_reason: blocked\n"
                "action_closure:\n  critical_path:\n    - action_id: A2\n      source_decision_ids: []\n      source_blocker_ids: [B7]\n",
                encoding="utf-8",
            )
            self.assertTrue(normalize_trace_structure(Path(temporary)))
            normalized = path.read_text(encoding="utf-8")
            self.assertIn("quality_decision:\n  passed: false", normalized)
            self.assertIn("stop_reason: not_applicable", normalized)
            self.assertIn("action_id: ACT-001", normalized)
            self.assertNotIn("- B7", normalized)
            self.assertIn("source_decision_ids:\n    - DEC-001", normalized)
            self.assertIn("content_sources:", normalized)
            self.assertIn("guardrail_events: []", normalized)
            self.assertIn("security_and_audit:", normalized)
            self.assertIn("boundary: Evaluation delivery only", normalized)
            self.assertIn("readiness:\n  prd_status: draft with assumption risk", normalized)
            self.assertIn("agents_used:", normalized)
            self.assertIn("skills_used:", normalized)
            self.assertIn("tools_used:", normalized)
            self.assertIn("external_research:", normalized)
            self.assertIn("agent_transitions:", normalized)
            self.assertIn("scope_decisions:", normalized)
            self.assertIn("surface_decisions:", normalized)
            self.assertIn("Final independent validation has not run.", normalized)

    def test_prd_normalizer_carries_traceable_sources_and_deferred_ui_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "discussion.md").write_text(
                "UI 交付物标识 | `UI-TEAM-PERM-001`\n",
                encoding="utf-8",
            )
            (folder / "prd.md").write_text(
                "| 需求来源 | 原始请求、讨论记录与已确认需求记录；受控确认基线仅允许交付带风险草案。 |\n"
                "| 1.1 title |\n",
                encoding="utf-8",
            )
            self.assertTrue(normalize_prd_contract(folder))
            text = (folder / "prd.md").read_text(encoding="utf-8")
            self.assertIn("`discussion.md`", text)
            self.assertIn("UI-TEAM-PERM-001", text)
            self.assertIn("ui/permission-change/UI-TEAM-PERM-001/index.md", text)


if __name__ == "__main__":
    unittest.main()
