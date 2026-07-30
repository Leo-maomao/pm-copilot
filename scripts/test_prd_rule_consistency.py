#!/usr/bin/env python3
"""Guard active PM Copilot guidance against reintroducing retired PRD rules."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PRDRuleConsistencyTest(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_prd_contract_is_the_authoritative_product_content_rule(self) -> None:
        contract = self.read("artifacts/prd-contract.md")
        self.assertIn("Do not add separate risk, pending-confirmation, acceptance-result", contract)
        self.assertIn("`事件`, `事件名称`, `上报时机`, `附加参数`, and `备注`", contract)
        self.assertIn("占位图：图片名称", contract)
        self.assertIn("Do not create a `待确认` item, risk field, or acceptance-result field", contract)

    def test_active_guidance_excludes_retired_placeholder_and_duplicate_id_rules(self) -> None:
        text = self.read("artifacts/artifact-contracts.md")
        self.assertNotIn("small `位置` and `用途` caption", text)
        self.assertNotIn("Function ID and function name", text)
        self.assertIn("Requirement-detail number and requirement name", text)
        self.assertIn("renumber visible H2 sections consecutively", text)

    def test_tracking_guidance_keeps_detailed_analytics_out_of_the_prd(self) -> None:
        for relative in ("artifacts/tracking-plan-contract.md", "skills/tracking-plan/SKILL.md"):
            text = self.read(relative)
            self.assertIn("事件`、`事件名称`、`上报时机`、`附加参数`、`备注`", text)
            self.assertIn("explicitly requested", text)
            self.assertNotIn("label the table as a proposed taxonomy", text)
            self.assertNotIn("requires analytics or engineering approval", text)

    def test_delivery_guidance_keeps_internal_review_content_out_of_prd(self) -> None:
        for relative in (
            "docs/implemented-feature-prd-workflow.md",
            "docs/direct-use.md",
            "skills/artifact-packaging/SKILL.md",
            "workflow/delivery-check-workflow.md",
        ):
            text = self.read(relative)
            self.assertIn("run-log.yaml", text)
        self.assertIn("Keep assumptions, risks, acceptance criteria, validation", self.read("docs/direct-use.md"))
        self.assertIn("not as PRD content", self.read("workflow/delivery-check-workflow.md"))

    def test_clarification_guidance_does_not_reintroduce_pending_prd_fields(self) -> None:
        text = self.read("workflow/context-loading.md")
        self.assertNotIn("visible assumptions, open questions", text)
        self.assertIn("do not add pending-confirmation, risk, or acceptance-result fields to the PRD", text)


if __name__ == "__main__":
    unittest.main()
