#!/usr/bin/env python3
"""Regression tests for bounded, role-based delegation plans."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_task_ledger import create_ledger, validate
from plan_agent_delegation import build_plan
from run_agent_delegation import run_plan, worker_prompt


class AgentDelegationPlanTest(unittest.TestCase):
    def test_complex_requirement_selects_independent_roles_and_review(self) -> None:
        plan = build_plan("做一个团队项目需求 PRD，补充 UI 交互、埋点和竞品调研")
        evidence = plan["dispatch_groups"][0]["workers"]
        roles = {worker["role"] for worker in evidence}
        self.assertTrue(plan["active"])
        self.assertEqual(plan["pattern"], "parallel_specialists")
        self.assertTrue(plan["execution_decision"]["goal_decomposition_required"])
        self.assertTrue(plan["execution_decision"]["delegation_required_when_runtime_ready"])
        self.assertTrue({"Requirements Agent", "UI Delivery Agent", "Analytics Agent", "Research Agent"} <= roles)
        self.assertEqual(plan["dispatch_groups"][1]["workers"][0]["role"], "Review Agent")

    def test_small_ambiguous_request_uses_discovery_only(self) -> None:
        plan = build_plan("帮我看看这个问题")
        self.assertFalse(plan["active"])
        self.assertEqual(plan["dispatch_groups"][0]["workers"][0]["role"], "Discovery Agent")
        self.assertEqual(plan["dispatch_groups"][1]["workers"], [])
        self.assertTrue(plan["execution_decision"]["clarification_decision_required"])
        self.assertFalse(plan["execution_decision"]["delegation_required_when_runtime_ready"])

    def test_self_improvement_uses_goal_relevant_evidence_roles(self) -> None:
        plan = build_plan("强化 Agent 的运行时委派机制", "self_improvement")
        roles = {worker["role"] for worker in plan["dispatch_groups"][0]["workers"]}
        self.assertTrue(plan["active"])
        self.assertEqual(roles, {"Requirements Agent", "Integration Governance Agent"})
        self.assertLessEqual(len(roles), 3)

    def test_self_improvement_adds_ui_agent_only_for_visual_goal(self) -> None:
        plan = build_plan("强化 UI 原型的视觉证据", "self_improvement")
        roles = {worker["role"] for worker in plan["dispatch_groups"][0]["workers"]}
        self.assertIn("UI Delivery Agent", roles)

    def test_conflict_protocol_rejects_unbounded_battle(self) -> None:
        plan = build_plan("需求和埋点")
        protocol = plan["conflict_protocol"]
        self.assertEqual(
            protocol["canonical_owner"],
            "agents/agent-operating-model.md#conflict-resolution-gate",
        )
        self.assertIn("loop_state.conflict_resolution_status", protocol["record_in"])

    def test_embedded_workspace_is_recorded_and_scopes_worker_prompt(self) -> None:
        with TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "host-project" / "pm-copilot"
            workspace.mkdir(parents=True)
            ledger = create_ledger("强化 Agent", "self_improvement", build_plan("强化 Agent", "self_improvement"), workspace)
            self.assertEqual(ledger["workspace"]["kind"], "embedded_copy")
            self.assertEqual(ledger["workspace"]["display_label"], "host-project/pm-copilot")
            self.assertEqual(validate(ledger), [])
            prompt = worker_prompt("Requirements Agent", "audit", "强化 Agent", ledger["workspace"])
            self.assertIn("host-project/pm-copilot", prompt)
            self.assertIn("same-named PM Copilot", prompt)

    def test_resume_rejects_a_ledger_from_another_copy(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first-project" / "pm-copilot"
            second = root / "second-project" / "pm-copilot"
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            ledger_path = root / "agent-task-ledger.json"
            from agent_task_ledger import write

            write(ledger_path, create_ledger("强化 Agent", "self_improvement", build_plan("强化 Agent", "self_improvement"), first))
            result = run_plan("强化 Agent", "self_improvement", second, lambda *_args, **_kwargs: {}, False, ledger_path, True)
            self.assertEqual(result["status"], "blocked")
            self.assertIn("another PM Copilot workspace", result["reason"])


if __name__ == "__main__":
    unittest.main()
