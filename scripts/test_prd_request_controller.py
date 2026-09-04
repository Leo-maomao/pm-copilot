import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import prd_request_controller
from prd_request_controller import is_prd_request
from run_interactive_request import (
    _build_request_parser,
    _delivery_input_problem,
    _materialize_revision_scope_manifest,
    _resolve_request_plan,
    _validate_staged_revision_scope,
    begin_implemented_feature_append,
    create_state,
    run_prd_request_entry,
)


class PrdRequestControllerTests(unittest.TestCase):
    def _natural_plan(self, argv: list[str]):
        parser = _build_request_parser()
        args = parser.parse_args(argv)
        with patch("run_interactive_request._ensure_runtime_current"):
            return _resolve_request_plan(args, parser, entrypoint="natural")

    def test_natural_prd_requests_route_to_production_controller(self) -> None:
        self.assertTrue(is_prd_request("调用 pm-copilot 生成PRD"))
        self.assertTrue(is_prd_request("帮我写一份产品需求文档"))

    def test_facade_passes_arguments_without_mutating_process_argv(self) -> None:
        original_argv = ["test-runner", "--unchanged"]
        request_argv = ["--request", "生成一个产品需求文档"]
        with patch.object(sys, "argv", original_argv), patch(
            "prd_request_controller.run_prd_request_entry", return_value=0,
        ) as entry:
            self.assertEqual(prd_request_controller.main(request_argv), 0)
            self.assertEqual(sys.argv, original_argv)
        entry.assert_called_once_with(request_argv)

    def test_default_provider_and_new_requirement_are_resolved_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, patch(
            "run_interactive_request.resolved_output_root", return_value=Path(temporary),
        ):
            plan = self._natural_plan(["--request", "生成一个产品需求文档"])
        self.assertEqual(plan.args.provider, "auto")
        self.assertTrue(plan.args.new_requirement)
        self.assertEqual(plan.task_mode, "new_prd")
        self.assertEqual(plan.delivery_variant, "new")

    def test_removed_external_provider_is_rejected_at_argument_parsing(self) -> None:
        with self.assertRaises(SystemExit):
            _build_request_parser().parse_args([
                "--request", "生成一个产品需求文档", "--provider", "legacy-provider",
            ])

    def test_non_prd_request_is_not_routed_to_prd_controller(self) -> None:
        self.assertFalse(is_prd_request("检查一下当前测试结果"))

    def test_revision_flags_resolve_an_in_place_plan(self) -> None:
        plan = self._natural_plan([
            "--request", "更新 PRD 的 5.1 和 5.2",
            "--run-folder", "/tmp/canonical-run", "--revise",
            "--revision-requirement-id", "5.1",
            "--revision-requirement-id", "5.2",
        ])
        self.assertFalse(plan.args.new_requirement)
        self.assertTrue(plan.args.revise)
        self.assertEqual(plan.args.revision_requirement_id, ["5.1", "5.2"])

    def test_append_flag_routes_to_implemented_feature_mode(self) -> None:
        plan = self._natural_plan([
            "--request", "将已实现导出功能追加到当前 PRD",
            "--run-folder", "/tmp/current-prd", "--append-implemented-feature",
        ])
        self.assertFalse(plan.args.new_requirement)
        self.assertEqual(plan.task_mode, "implemented_feature_prd")
        self.assertEqual(plan.delivery_variant, "in_place_revision")

    def test_append_implemented_feature_uses_existing_prd_without_manager_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "current-prd"
            folder.mkdir()
            original = "# 当前 PRD\n\n## 四、需求清单\n\n| 5.1 | 旧功能 |\n\n## 五、需求详情\n\n### 5.1 旧功能\n\n保持不变。\n"
            (folder / "prd.md").write_text(original, encoding="utf-8")
            (folder / "prd.html").write_text("<html></html>\n", encoding="utf-8")
            state = create_state("旧功能", folder)
            state.update({"status": "complete", "termination": "complete"})
            begin_implemented_feature_append(state, "将已实现的导出功能追加到当前 PRD")
            _materialize_revision_scope_manifest(state)

            stage = folder / "stage"
            (stage / ".revision-baseline").mkdir(parents=True)
            (stage / ".revision-baseline" / "prd.md").write_text(original, encoding="utf-8")
            (stage / "prd.md").write_text(
                original.replace("## 五、需求详情", "| 5.2 | 导出 |\n\n## 五、需求详情")
                + "\n### 5.2 导出\n\n用户可以导出结果。\n",
                encoding="utf-8",
            )
            (stage / "assets").mkdir()
            report = _validate_staged_revision_scope(state, stage)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(state["append_requirement_ids"], ["5.2"])

    def test_extraction_input_resolves_a_new_extraction_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, patch(
            "run_interactive_request.resolved_output_root", return_value=Path(temporary),
        ):
            plan = self._natural_plan([
                "--request", "从旧 PRD 提取结算流程生成新 PRD",
                "--extract-from", "/tmp/legacy-prd.md",
            ])
        self.assertTrue(plan.args.new_requirement)
        self.assertEqual(plan.delivery_variant, "compose_to_new")
        self.assertEqual(plan.task_mode, "prd_composition")

    def test_extraction_resume_keeps_the_existing_run_out_of_revision_mode(self) -> None:
        plan = self._natural_plan([
            "--run-folder", "/tmp/extraction-run",
            "--extract-from", "/tmp/legacy-prd.md",
        ])
        self.assertFalse(plan.args.new_requirement)
        self.assertFalse(plan.args.revise)
        self.assertEqual(plan.delivery_variant, "compose_to_new")

    def test_extraction_source_resume_uses_the_facade_without_revise(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "extraction-run"
            folder.mkdir()
            source = root / "legacy-prd.md"
            source.write_text("# 旧 PRD\n\n### 5.7 结算流程\n", encoding="utf-8")
            state = create_state("从旧 PRD 提取结算流程，形成独立 PRD", folder)
            turn = {
                "turn": 1,
                "user_text": state["raw_request"],
                "summary": "已确认提取结算流程",
                "scope": {"goal": "提取结算流程", "in_scope": ["5.7 结算流程"]},
                "assumptions": [],
                "decisions": [],
                "risks": [],
                "buckets": {},
            }
            state.update({
                "status": "needs_input",
                "termination": "needs_input",
                "turns": [turn],
                "confirmed_fact_packet": json.loads(json.dumps(turn)),
                "user_confirmation": {"confirmed": True, "source": "test"},
                "required_input": {
                    "field": "extraction_source",
                    "question": "请提供旧 PRD",
                    "reason": "missing source",
                },
            })
            (folder / "interactive-run.json").write_text(
                json.dumps(state, ensure_ascii=False), encoding="utf-8",
            )

            with patch("run_interactive_request._ensure_runtime_current"), patch("builtins.print"):
                self.assertEqual(
                    run_prd_request_entry([
                        "--run-folder", str(folder), "--extract-from", str(source),
                    ]),
                    3,
                )

            resumed = json.loads((folder / "interactive-run.json").read_text(encoding="utf-8"))
            self.assertEqual(resumed["status"], "awaiting_confirmation")
            self.assertEqual(resumed["delivery_variant"], "compose_to_new")

    def test_natural_implemented_feature_request_selects_evidence_backed_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, patch(
            "run_interactive_request.resolved_output_root", return_value=Path(temporary),
        ):
            plan = self._natural_plan(["--request", "为已实现功能生成 PRD"])
            state = create_state(
                plan.raw_request,
                plan.folder,
                task_mode=plan.task_mode,
                delivery_variant=plan.delivery_variant,
            )
        self.assertTrue(plan.args.new_requirement)
        self.assertEqual(state["task_mode"], "implemented_feature_prd")
        self.assertEqual(state["context_source"]["mode"], "repo-backed")
        self.assertIn("实施证据包", _delivery_input_problem(state) or "")

    def test_natural_implemented_request_collects_evidence_before_confirmation(self) -> None:
        def clarified(state, *_args, **_kwargs):
            state["turns"] = [{
                "turn": 1,
                "user_text": state["raw_request"],
                "summary": "已澄清功能范围",
                "scope": {"goal": "还原功能", "in_scope": ["画布保存"]},
                "assumptions": [],
                "decisions": [],
                "risks": [],
                "buckets": {},
            }]
            state["status"] = "awaiting_confirmation"
            state["termination"] = "human_checkpoint"
            return state

        evidence = {
            "branch_name": "feature/canvas", "diff_commands": ["git diff --name-only HEAD"],
            "changed_files": ["src/canvas.ts"],
            "behavior_evidence": [{"evidence_id": "behavior-1", "observed_behavior": "Canvas saves drafts"}],
            "validation_evidence": [{"command": "test inventory", "status": "observed"}],
            "screenshots_and_placeholders": [],
        }
        with tempfile.TemporaryDirectory() as temporary, patch(
            "run_interactive_request.resolved_output_root", return_value=Path(temporary),
        ), patch("run_interactive_request._ensure_runtime_current"), patch(
            "run_interactive_request.run_intake", side_effect=clarified,
        ), patch(
            "run_interactive_request.collect_implemented_feature_evidence", return_value=evidence,
        ), patch("builtins.print"):
            self.assertEqual(
                run_prd_request_entry(["--request", "为已实现功能生成 PRD"]),
                0,
            )
            folder = next(Path(temporary).iterdir())
            state = json.loads((folder / "interactive-run.json").read_text(encoding="utf-8"))
            self.assertEqual(state["task_mode"], "implemented_feature_prd")
            self.assertEqual(state["status"], "awaiting_confirmation")
            self.assertEqual(state["implemented_feature_evidence"], evidence)
            self.assertEqual(state["implemented_feature_evidence_source"]["collection_mode"], "automatic")


if __name__ == "__main__":
    unittest.main()
