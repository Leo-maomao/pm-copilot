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
    _confirmed_delivery,
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
            return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}

        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个 PRD", Path(temporary))
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
            return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}

        failed = [{"command": "scripts/validate_outputs.py", "status": "failed", "stdout": "missing section", "stderr": ""}]
        passed = [{"command": "scripts/validate_outputs.py", "status": "passed", "stdout": "", "stderr": ""}]
        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个 PRD", Path(temporary))
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            state["agent_calls"] = [
                {"phase": "intake", "provider": "test", "model": "test", "status": "complete"},
                {"phase": "clarification_review", "provider": "test", "model": "test", "status": "complete"},
            ]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            with patch("run_interactive_request._validate_delivery", side_effect=[failed, passed]):
                _confirmed_delivery(state, "test", 1, worker=worker, max_revisions=1)
            self.assertEqual(state["status"], "complete")
            self.assertGreaterEqual(state["revision_loops"], 1)
            self.assertEqual(len(state["agent_calls"]), 10)
            self.assertEqual(state["revision_trace"][-1]["outcome"], "changed")

    def test_delivery_blocks_when_agent_result_has_no_provider_model_evidence(self) -> None:
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
            self.assertEqual(state["status"], "failed")
            self.assertIn("provider/model", state["last_error"])
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


if __name__ == "__main__":
    unittest.main()
