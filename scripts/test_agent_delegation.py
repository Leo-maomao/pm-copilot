#!/usr/bin/env python3
"""Regression tests for bounded, role-based delegation plans."""

from __future__ import annotations

import unittest

from plan_agent_delegation import build_plan


class AgentDelegationPlanTest(unittest.TestCase):
    def test_complex_requirement_selects_independent_roles_and_review(self) -> None:
        plan = build_plan("做一个团队项目需求 PRD，补充 UI 交互、埋点和竞品调研")
        evidence = plan["dispatch_groups"][0]["workers"]
        roles = {worker["role"] for worker in evidence}
        self.assertTrue(plan["active"])
        self.assertEqual(plan["pattern"], "parallel_specialists")
        self.assertTrue({"Requirements Agent", "UI Delivery Agent", "Analytics Agent", "Research Agent"} <= roles)
        self.assertEqual(plan["dispatch_groups"][1]["workers"][0]["role"], "Review Agent")

    def test_small_ambiguous_request_uses_discovery_only(self) -> None:
        plan = build_plan("帮我看看这个问题")
        self.assertFalse(plan["active"])
        self.assertEqual(plan["dispatch_groups"][0]["workers"][0]["role"], "Discovery Agent")
        self.assertEqual(plan["dispatch_groups"][1]["workers"], [])

    def test_self_improvement_uses_review_and_runtime_governance(self) -> None:
        plan = build_plan("强化 Agent", "self_improvement")
        roles = {worker["role"] for worker in plan["dispatch_groups"][0]["workers"]}
        self.assertTrue(plan["active"])
        self.assertEqual(roles, {"Review Agent", "Integration Governance Agent"})

    def test_conflict_protocol_rejects_unbounded_battle(self) -> None:
        plan = build_plan("需求和埋点")
        self.assertIn("not_allowed", plan["conflict_protocol"])
        self.assertIn("PM Orchestrator", plan["conflict_protocol"]["method"])


if __name__ == "__main__":
    unittest.main()
