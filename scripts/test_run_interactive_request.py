#!/usr/bin/env python3
"""Tests for the production interactive clarification gate."""

from __future__ import annotations

import datetime as dt
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run_interactive_request import (
    _atomic_copy,
    _confirmed_delivery,
    _artifact_review_prompt,
    _confirmation_packet,
    _delivery_worker,
    _normalise_trace_runtime_evidence,
    _restart_delivery_attempt,
    _recover_interrupted_delivery,
    _write_json,
    _normalise_intake,
    _run_artifact_agent,
    begin_in_place_revision,
    compact_requirement_numbers,
    create_state,
    main,
    new_requirement_folder,
    run_intake,
    write_discussion,
)


class InteractiveRequestTest(unittest.TestCase):
    def test_nonblocking_questions_do_not_hold_the_clarification_gate(self) -> None:
        intake = _normalise_intake({
            "status": "needs_input",
            "questions": ["请确认由谁负责 PRD 验收"],
            "buckets": {
                "must_answer_before_generation": [],
                "must_confirm_before_development_or_launch": ["上线确认"],
            },
        })
        self.assertEqual(intake["status"], "complete")
        self.assertEqual(intake["questions"], [])

    def test_compact_requirement_numbers_updates_all_references(self) -> None:
        source = "| 5.1 | A |\n| 5.3 | C |\n### 5.1 A\n### 5.3 C\n目标 5.3"
        result = compact_requirement_numbers(source)
        self.assertIn("| 5.2 | C |", result)
        self.assertIn("### 5.2 C", result)
        self.assertIn("目标 5.2", result)
    def test_new_requirement_folder_never_allocates_a_suffixed_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = new_requirement_folder("团队权限", root)
            expected_date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
            self.assertEqual(folder.name, f"interactive-request-{expected_date}")
            folder.mkdir()
            with self.assertRaises(FileExistsError):
                new_requirement_folder("团队权限", root)
            self.assertFalse((root / f"{folder.name}-2").exists())

    def test_revision_reopens_the_same_canonical_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prd.md").write_text("before", encoding="utf-8")
            (folder / "prd.html").write_text("before", encoding="utf-8")
            state = create_state("原需求", folder)
            state.update({"status": "complete", "artifacts": ["prd.md", "prd.html", "run-log.yaml"]})
            revised = begin_in_place_revision(state, "新增一个状态规则")
            self.assertEqual(revised["folder"], str(folder))
            self.assertEqual(revised["status"], "new")
            self.assertEqual(revised["revision_history"][-1]["mode"], "in_place_revision")
            self.assertEqual(revised["revision_history"][-1]["prd_before_sha256"], hashlib.sha256(b"before").hexdigest())

    def test_trace_normalisation_replaces_stale_version_and_asset_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            assets = folder / "assets"
            assets.mkdir()
            asset = assets / "current.png"
            asset.write_bytes(b"current image")
            trace = folder / "run-log.yaml"
            trace.write_text(
                "pm_copilot_version: 5.0.3\nimplemented_feature_prd:\n"
                "  screenshots_and_placeholders:\n"
                "    - target_ref: 5.1\n"
                "      coverage_decision: real_figure\n"
                "      path: assets/current.png\n"
                "      asset_sha256: stale\n",
                encoding="utf-8",
            )
            self.assertEqual(_normalise_trace_runtime_evidence(trace), 1)
            text = trace.read_text(encoding="utf-8")
            active_version = (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip()
            self.assertIn(f"pm_copilot_version: {active_version}", text)
            self.assertIn(hashlib.sha256(b"current image").hexdigest(), text)

    def test_stream_disconnect_retries_once_and_preserves_the_failure_reason(self) -> None:
        calls = []

        def worker(*args, **kwargs):
            calls.append(args)
            return {"provider": "test", "model": "test", "status": "failed", "output": "", "error": "stream disconnected"}

        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个 PRD", Path(temporary))
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            self.assertFalse(_run_artifact_agent(state, "run-log.yaml", "test", 15, worker=worker))
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0][3], 3)
            self.assertIn("stream disconnected", state["last_error"])

    def test_delivery_worker_disables_the_first_artifact_watchdog(self) -> None:
        with patch("run_interactive_request.execute", return_value={"status": "complete"}) as execute:
            _delivery_worker("test", "write", Path.cwd(), 15, None, None, False, 8000)
        self.assertIsNone(execute.call_args.kwargs["first_artifact_seconds"])

    def test_atomic_copy_replaces_the_complete_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = folder / "source.txt"
            destination = folder / "destination.txt"
            source.write_text("new trace", encoding="utf-8")
            destination.write_text("old trace", encoding="utf-8")
            _atomic_copy(source, destination)
            self.assertEqual(destination.read_text(encoding="utf-8"), "new trace")

    def test_recovery_attempt_discards_stale_stage_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个 PRD", Path(temporary))
            state.update({
                "resume_from_status": "recovery_required",
                "delivery_stages": {"run-log.yaml": {"review_status": "passed", "artifact_status": "promoted"}},
                "validation": [{"status": "failed"}],
                "artifacts": ["discussion.md", "prd.md", "run-log.yaml"],
                "recovery": {"status": "retry_required"},
                "revision_stop_reason": "validation budget exhausted",
            })
            _restart_delivery_attempt(state)
            self.assertEqual(state["delivery_stages"], {})
            self.assertEqual(state["validation"], [])
            self.assertEqual(state["artifacts"], ["discussion.md"])
            self.assertNotIn("recovery", state)
            self.assertEqual(state["delivery_attempts"][-1]["prior_status"], "recovery_required")

    def test_nonexistent_run_folder_cannot_create_a_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "would-be-copy"
            with patch.object(sys, "argv", ["run_interactive_request.py", "--run-folder", str(missing), "--dry-run"]):
                with self.assertRaises(SystemExit):
                    main()
            self.assertFalse(missing.exists())
    def test_material_unknown_stops_before_confirmation(self) -> None:
        responses = [
            '{"status":"needs_input","summary":"目标尚不明确","questions":["目标用户是谁？"],"buckets":{"must_answer_before_generation":["target user"]}}',
            '{"status":"complete","summary":"目标用户已明确","questions":[],"buckets":{"must_answer_before_generation":[]},"scope":{"goal":"降低流失","users":["付费用户"],"in_scope":["提醒"],"out_of_scope":["改价"],"platform":"Web"}}',
            '{"status":"complete","summary":"独立复核通过","questions":[],"blockers":[],"coverage":{"goal":"covered","users":"covered","scope":"covered","success_evidence":"covered","constraints_and_risk":"covered"}}',
        ]

        def worker(*args, **kwargs):
            return {"provider": "test", "model": "test", "status": "complete", "output": responses.pop(0), "error": ""}

        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个留存提醒", Path(temporary))
            state = run_intake(state, "test", 1, worker=worker)
            self.assertEqual(state["status"], "needs_input")
            self.assertEqual(state["termination"], "needs_input")
            state = run_intake(state, "test", 1, worker=worker, answers="付费用户，Web，先做提醒")
            self.assertEqual(state["status"], "awaiting_confirmation")
            write_discussion(Path(temporary), state)
            self.assertTrue((Path(temporary) / "discussion.md").is_file())

    def test_incomplete_coverage_cannot_pass_clarification_review(self) -> None:
        responses = [
            '{"status":"complete","summary":"初步完成","questions":[],"buckets":{"must_answer_before_generation":[]}}',
            '{"status":"complete","summary":"未提供覆盖证明","questions":[],"blockers":[],"coverage":{"goal":"covered"}}',
        ]

        def worker(*args, **kwargs):
            return {"provider": "test", "model": "test", "status": "complete", "output": responses.pop(0), "error": ""}

        with tempfile.TemporaryDirectory() as temporary:
            state = run_intake(create_state("做一个 PRD", Path(temporary)), "test", 1, worker=worker)
            self.assertEqual(state["status"], "needs_input")
            self.assertIn("未证明", state["turns"][-1]["buckets"]["must_answer_before_generation"][0])

    def test_independent_review_blocks_premature_confirmation(self) -> None:
        responses = [
            '{"status":"complete","summary":"初步完成","questions":[],"buckets":{"must_answer_before_generation":[]},"scope":{"goal":"降低流失"}}',
            '{"status":"needs_input","summary":"缺少验收边界","questions":["留存提升以什么口径验收？"],"blockers":["success metric"]}',
        ]

        def worker(*args, **kwargs):
            return {"provider": "test", "model": "test", "status": "complete", "output": responses.pop(0), "error": ""}

        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个留存提醒", Path(temporary))
            state = run_intake(state, "test", 1, worker=worker)
            self.assertEqual(state["status"], "needs_input")
            self.assertEqual(state["termination"], "needs_input")
            self.assertIn("留存提升", state["turns"][-1]["questions"][0])

    def test_delivery_is_not_allowed_without_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个 PRD", Path(temporary))
            (Path(temporary) / "prd.html").write_text("<!doctype html><html></html>", encoding="utf-8")
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            state["status"] = "awaiting_confirmation"
            _confirmed_delivery(state, "test", 1, worker=lambda *args: self.fail("worker must not run"))
            self.assertEqual(state["status"], "awaiting_confirmation")
            self.assertEqual(state["termination"], "human_checkpoint")
            self.assertIn("Explicit user confirmation", state["last_error"])

    def test_confirmed_delivery_records_each_agent_stage(self) -> None:
        def worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
            if "Clarification Review Agent" in prompt:
                return {"provider": provider, "model": "test", "status": "complete", "output": '{"status":"complete","blockers":[],"questions":[]}', "error": ""}
            if "Stage Quality Review Agent" in prompt:
                return {"provider": provider, "model": "test", "status": "complete", "output": '{"status":"pass","blocking_findings":[],"acceptance_evidence":["contract checked"]}', "error": ""}
            marker = "Write one complete artifact at "
            target = Path(prompt.split(marker, 1)[1].split(".\n", 1)[0])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# artifact\n", encoding="utf-8")
            if target.name == "prd.md":
                target.with_name("prd.html").write_text("<!doctype html><html></html>", encoding="utf-8")
            return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}

        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个 PRD", Path(temporary))
            (Path(temporary) / "prd.html").write_text("<!doctype html><html></html>", encoding="utf-8")
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            state["agent_calls"] = [
                {"phase": "intake", "provider": "test", "model": "test", "status": "complete"},
                {"phase": "clarification_review", "provider": "test", "model": "test", "status": "complete"},
            ]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            with patch("run_interactive_request._validate_delivery", return_value=[{"status": "passed"}]):
                _confirmed_delivery(state, "test", 1, worker=worker)
            self.assertEqual(state["status"], "complete")
            self.assertEqual(len(state["agent_calls"]), 8)
            self.assertTrue((Path(temporary) / "prd.md").is_file())

    def test_confirmed_delivery_revises_after_failed_validation(self) -> None:
        writes = 0

        def worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
            nonlocal writes
            if "Clarification Review Agent" in prompt:
                return {"provider": provider, "model": "test", "status": "complete", "output": '{"status":"complete","blockers":[],"questions":[]}', "error": ""}
            if "Stage Quality Review Agent" in prompt:
                return {"provider": provider, "model": "test", "status": "complete", "output": '{"status":"pass","blocking_findings":[],"acceptance_evidence":["contract checked"]}', "error": ""}
            target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
            target.parent.mkdir(parents=True, exist_ok=True)
            writes += 1
            target.write_text(f"# artifact {writes}\n", encoding="utf-8")
            if target.name == "prd.md":
                target.with_name("prd.html").write_text("<!doctype html><html></html>", encoding="utf-8")
            return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}

        failed = [{"command": "scripts/validate_outputs.py", "status": "failed", "stdout": "missing section", "stderr": ""}]
        passed = [{"command": "scripts/validate_outputs.py", "status": "passed", "stdout": "", "stderr": ""}]
        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个 PRD", Path(temporary))
            (Path(temporary) / "prd.html").write_text("<!doctype html><html></html>", encoding="utf-8")
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            state["agent_calls"] = [
                {"phase": "intake", "provider": "test", "model": "test", "status": "complete"},
                {"phase": "clarification_review", "provider": "test", "model": "test", "status": "complete"},
            ]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            with patch("run_interactive_request._validate_delivery", side_effect=[failed, passed, passed]):
                _confirmed_delivery(state, "test", 1, worker=worker, max_revisions=1)
            self.assertEqual(state["status"], "complete")
            self.assertGreaterEqual(state["revision_loops"], 1)
            self.assertEqual(len(state["agent_calls"]), 10)
            self.assertEqual(state["revision_trace"][-1]["outcome"], "changed")

    def test_delivery_exposes_retry_recovery_when_agent_evidence_is_missing(self) -> None:
        def unauthenticated_worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
            marker = "Write one complete artifact at "
            target = Path(prompt.split(marker, 1)[1].split(".\n", 1)[0])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# artifact\n", encoding="utf-8")
            return {"status": "complete", "output": "written", "error": ""}

        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个 PRD", Path(temporary))
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            state["agent_calls"] = [
                {"phase": "intake", "provider": "test", "model": "test", "status": "complete"},
                {"phase": "clarification_review", "provider": "test", "model": "test", "status": "complete"},
            ]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            _confirmed_delivery(state, "test", 1, worker=unauthenticated_worker)
            self.assertEqual(state["status"], "recovery_required")
            self.assertIn("provider/model", state["last_error"])
            self.assertEqual(state["recovery"]["failed_stage"], "confirmed-requirements.md")
            self.assertEqual(state["recovery"]["retry_entry"], "--confirm")
            self.assertIn("--confirm --provider test", state["recovery"]["retry_action"])
            self.assertEqual(state["recovery"]["completed_artifacts"][0]["artifact"], "confirmed-requirements.md")
            self.assertFalse((Path(temporary) / "prd.md").exists())

    def test_delivery_agent_uses_project_staging_directory_as_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pm-copilot-outputs" / "example"
            folder.mkdir(parents=True)
            state = create_state("做一个 PRD", folder)
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]

            def worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
                target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
                self.assertEqual(cwd, target.parent)
                self.assertNotEqual(cwd, Path(__file__).resolve().parents[1])
                target.write_text("# confirmed\n", encoding="utf-8")
                return {"provider": "test", "model": "test", "status": "complete", "output": "written", "error": ""}

            self.assertTrue(_run_artifact_agent(state, "confirmed-requirements.md", "test", 1, worker=worker))
            self.assertTrue((folder / "confirmed-requirements.md").is_file())

    def test_run_log_promotes_canonical_path_not_staging_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pm-copilot-outputs" / "example"
            folder.mkdir(parents=True)
            state = create_state("做一个 PRD", folder)
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]

            def worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
                target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
                target.write_text(f"context:\n  folder: {cwd}\n", encoding="utf-8")
                return {"provider": "test", "model": "test", "status": "complete", "output": "written", "error": ""}

            self.assertTrue(_run_artifact_agent(state, "run-log.yaml", "test", 1, worker=worker))
            promoted = (folder / "run-log.yaml").read_text(encoding="utf-8")
            self.assertIn(str(folder.resolve()), promoted)
            self.assertNotIn(".example.stage-", promoted)

    def test_delivery_checkpoint_survives_interruption_after_artifact_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            state_path = folder / "interactive-run.json"
            state = create_state("做一个 PRD", folder)
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            _write_json(state_path, state)

            def interrupted_worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
                if "Stage Quality Review Agent" in prompt:
                    raise KeyboardInterrupt("simulated controller interruption")
                target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("# confirmed\n", encoding="utf-8")
                return {"provider": "test", "model": "test", "status": "complete", "output": "written", "error": ""}

            with self.assertRaises(KeyboardInterrupt):
                _confirmed_delivery(state, "test", 1, worker=interrupted_worker, state_path=state_path)
            persisted = __import__("json").loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "delivery")
            self.assertTrue(persisted["user_confirmation"]["confirmed"])
            self.assertIn("confirmed-requirements.md", persisted["artifacts"])
            self.assertEqual(persisted["delivery_stages"]["confirmed-requirements.md"]["artifact_status"], "promoted")

    def test_legacy_interrupted_delivery_is_not_reported_as_awaiting_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "run"
            folder.mkdir()
            state = create_state("做一个 PRD", folder)
            state["status"] = "awaiting_confirmation"
            state["termination"] = "human_checkpoint"
            (folder / "confirmed-requirements.md").write_text("# partial\n", encoding="utf-8")
            (folder.parent / ".run.stage-abandoned").mkdir()
            self.assertTrue(_recover_interrupted_delivery(state, folder))
            self.assertEqual(state["status"], "recovery_required")
            self.assertEqual(state["termination"], "interrupted")
            self.assertIn("confirmed-requirements.md", state["recovery"]["promoted_artifacts"])

    def test_stage_review_uses_full_confirmed_evidence_and_keeps_later_gates_nonblocking(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("创建独立 PRD", Path(temporary))
            state["turns"] = [{
                "user_text": "确认来源：/tmp/source/prd.md；端口 ID 由开发前确认。",
                "summary": "已确认迁移来源，端口契约后置。",
                "scope": {"goal": "迁移需求"}, "assumptions": [], "risks": [],
            }]
            prompt = _artifact_review_prompt(state, "confirmed-requirements.md", Path(temporary) / "review.json")
            self.assertIn("/tmp/source/prd.md", prompt)
            self.assertIn("not PRD\ngeneration blockers", prompt)

    def test_confirmation_packet_uses_only_final_confirmed_turn(self) -> None:
        state = create_state("旧请求", Path("/tmp/example"))
        state["turns"] = [
            {"user_text": "旧范围", "summary": "旧结论", "scope": {"goal": "旧"}, "assumptions": [], "decisions": [], "risks": [], "buckets": {}},
            {"user_text": "最终范围", "summary": "最终结论", "scope": {"goal": "新"}, "assumptions": [], "decisions": ["最终决定"], "risks": [], "buckets": {}},
        ]
        packet = _confirmation_packet(state)
        self.assertEqual(packet["final_user_message"], "最终范围")
        self.assertEqual(packet["scope"], {"goal": "新"})


if __name__ == "__main__":
    unittest.main()
