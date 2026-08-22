#!/usr/bin/env python3
"""Regression tests for complete evaluation-scenario planning."""

from __future__ import annotations

import unittest

from plan_evaluation_portfolio import PHASES, plan_case, portfolio, ROOT


class EvaluationPortfolioPlanTest(unittest.TestCase):
    def test_every_active_eval_has_a_raw_request_and_a_completion_policy(self) -> None:
        result = portfolio()
        self.assertGreaterEqual(result["total_cases"], 40)
        self.assertEqual(result["invalid_cases"], [])
        self.assertEqual(result["full_delivery_cases"], result["total_cases"])
        for case in result["cases"]:
            self.assertIn("discussion.md", case["required_artifacts"])
            self.assertIn("confirmed-requirements.md", case["required_artifacts"])
            self.assertIn("run-log.yaml", case["required_artifacts"])

    def test_normal_delivery_requires_the_full_goal_to_validation_path(self) -> None:
        case = plan_case(ROOT / "evals" / "agentic-product-manager-system-eval.md")
        self.assertEqual(case["completion_policy"], "full_delivery")
        self.assertEqual(case["required_phases"], list(PHASES))
        self.assertTrue(case["requires_model_discussion"])
        self.assertTrue(case["requires_agent_execution"])

    def test_safety_case_requires_confirmation_but_still_has_a_full_delivery_path(self) -> None:
        case = plan_case(ROOT / "evals" / "regulated-health-minor-clarification-gate-eval.md")
        self.assertEqual(case["completion_policy"], "full_delivery")
        self.assertEqual(case["required_phases"], list(PHASES))
        self.assertTrue(case["requires_explicit_confirmation"])
        self.assertIn("prd.md", case["completion_evidence"])

    def test_portfolio_scenario_set_expands_into_independent_full_delivery_runs(self) -> None:
        cases = portfolio()["cases"]
        expanded = [case for case in cases if case.get("parent_case_id") == "universal-product-agent-stress-portfolio"]
        self.assertEqual(len(expanded), 10)
        self.assertTrue(all(case["required_phases"] == list(PHASES) for case in expanded))

    def test_structured_reference_keeps_its_non_prd_contract(self) -> None:
        cases = {case["case_id"]: case for case in portfolio()["cases"]}
        reference = cases["document-class-reference-prototype"]
        self.assertEqual(reference["task_mode"], "structured_reference")
        self.assertIn("reference.md", reference["required_artifacts"])
        self.assertNotIn("prd.md", reference["required_artifacts"])
        self.assertNotIn("prd.md", reference["completion_evidence"])

    def test_ui_workflow_skill_references_do_not_turn_ui_delivery_into_self_improvement(self) -> None:
        cases = {case["case_id"]: case for case in portfolio()["cases"]}
        self.assertEqual(cases["ui-from-image-reconstruction"]["task_mode"], "ui_delivery")

    def test_every_required_artifact_is_an_atomic_run_folder_path(self) -> None:
        for case in portfolio()["cases"]:
            for artifact in case["required_artifacts"]:
                self.assertNotIn("*", artifact, case["case_id"])
                self.assertNotIn("<", artifact, case["case_id"])
                self.assertNotEqual(artifact, "assets", case["case_id"])
                self.assertFalse(artifact.startswith("tool-results/"), case["case_id"])

    def test_self_improvement_artifacts_are_concrete_evidence_files(self) -> None:
        cases = {case["case_id"]: case for case in portfolio()["cases"]}
        artifacts = cases["sharingan-skill-absorption-boundary"]["required_artifacts"]
        self.assertIn("proposed-skill/references/absorption-record.md", artifacts)
        self.assertIn("absorption-report.md", artifacts)

    def test_prd_screenshot_evidence_does_not_change_the_task_mode_to_ui(self) -> None:
        case = plan_case(ROOT / "evals" / "decision-first-prd-eval.md")
        self.assertEqual(case["task_mode"], "prd_delivery")
        self.assertIn("prd.html", case["required_artifacts"])

    def test_artifact_expectation_matrix_is_part_of_the_delivery_contract(self) -> None:
        case = plan_case(ROOT / "evals" / "b2b-permission-audit-handoff-eval.md")
        self.assertIn("dev-tasks.yaml", case["required_artifacts"])
        self.assertIn("launch-decision.yaml", case["required_artifacts"])

    def test_ui_requirement_resolves_to_an_independently_reviewable_artifact(self) -> None:
        case = plan_case(ROOT / "evals" / "accessibility-critical-checkout-recovery-eval.md")
        self.assertIn("prototype-web.html", case["required_artifacts"])


if __name__ == "__main__":
    unittest.main()
