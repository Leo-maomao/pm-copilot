#!/usr/bin/env python3
"""Regression checks for evidence-backed multi-agent collaboration traces."""

from __future__ import annotations

import unittest

from validate_agent_trace import validate_collaboration_protocol


class AgentCollaborationTraceTest(unittest.TestCase):
    def test_not_required_requires_reason(self) -> None:
        failures = validate_collaboration_protocol(True, "trigger: not_required\nreason: ''\n", {"D1"})
        self.assertIn("collaboration_protocol not_required requires reason", failures)

    def test_material_conflict_requires_complete_arbitration(self) -> None:
        body = """  trigger: material_conflict
  claims:
    - id: C1
  cross_reviews:
    - id: R1
      target_claim_id: C1
      status: resolved
  arbitrations:
    - id: A1
      decision_ref: D1
      outcome: accepted
      owner: PM Orchestrator
"""
        failures = validate_collaboration_protocol(True, body, {"D1"})
        self.assertIn("arbitration requires evidence_compared", failures)

    def test_material_conflict_rejects_unknown_references(self) -> None:
        body = """  trigger: material_conflict
  claims:
    - id: C1
  cross_reviews:
    - id: R1
      target_claim_id: C2
      status: resolved
  arbitrations:
    - id: A1
      evidence_compared:
        - specialist-handoff
      decision_ref: D2
      outcome: accepted
      owner: PM Orchestrator
"""
        failures = validate_collaboration_protocol(True, body, {"D1"})
        self.assertIn("cross_review must target a known claim", failures)
        self.assertIn("arbitration must reference a known decision_record id", failures)

    def test_material_conflict_accepts_evidence_backed_resolution(self) -> None:
        body = """  trigger: material_conflict
  claims:
    - id: C1
  cross_reviews:
    - id: R1
      target_claim_id: C1
      status: resolved
  arbitrations:
    - id: A1
      evidence_compared:
        - requirements-handoff
        - analytics-handoff
      decision_ref: D1
      outcome: accepted
      owner: PM Orchestrator
"""
        self.assertEqual(validate_collaboration_protocol(True, body, {"D1"}), [])


if __name__ == "__main__":
    unittest.main()
