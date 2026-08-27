#!/usr/bin/env python3
"""Guard active PM Copilot guidance against reintroducing retired PRD rules."""

from __future__ import annotations

import unittest
from pathlib import Path

from prd_visual_contract import PLACEHOLDER_MARKER, is_controlled_placeholder_value


ROOT = Path(__file__).resolve().parents[1]


class PRDRuleConsistencyTest(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_prd_contract_is_the_authoritative_product_content_rule(self) -> None:
        contract = self.read("artifacts/prd-contract.md")
        self.assertIn("Do not add separate risk, pending-confirmation, acceptance-result", contract)
        self.assertIn("`事件`, `事件名称`, `上报时机`, `附加参数`, and `备注`", contract)
        self.assertIn("占位图：功能-状态.png", contract)
        self.assertIn("every group heading and every numbered rule on its own explicit `<br>` line", contract)
        self.assertIn("Keep adjacent groups continuous with exactly one `<br>`", contract)
        self.assertIn("The detail table may use only", contract)
        self.assertIn("A user-provided video is playback evidence", contract)
        self.assertIn("fixed image column", contract)
        self.assertIn("Do not create a `待确认` item, risk field, or acceptance-result field", contract)
        self.assertIn("Never show “拟议”", contract)
        self.assertIn("development-only scaffolding", contract)
        self.assertIn("User-confirmed launch goals and explicit product decisions override observed implementation", contract)
        self.assertIn("Requirement granularity is defined by a user outcome", contract)
        self.assertIn("Visual coverage records states separately but never creates or requires a requirement row", contract)
        self.assertIn("smallest localizable copy unit", contract)
        self.assertIn("never permits joining copy values", contract)
        self.assertIn("Do not join separate labels, menu items, tabs, buttons, or messages", contract)
        self.assertIn("Keep the core document, background, requirement list, and requirement-detail section numbers stable", contract)

    def test_implemented_feature_guidance_applies_contract_boundaries(self) -> None:
        skill = self.read("skills/prd-writing/SKILL.md")
        workflow = self.read("docs/implemented-feature-prd-workflow.md")
        template = self.read("templates/implemented-feature-prd-template.md")
        requirements_agent = self.read("agents/requirements-agent.md")
        self.assertIn("evidence boundary and requirement-granularity rules", skill)
        self.assertIn("Coverage items are visual evidence, not requirement items", skill)
        self.assertIn("Implemented-Feature Evidence Boundary", workflow)
        self.assertIn("evidence-boundary and requirement-granularity rules", workflow)
        self.assertIn("Each independently usable visible string has its own pure-text line", workflow)
        self.assertIn("同一页面或弹窗内服务同一目标", template)
        self.assertIn("独立条目不得用 / 合并", template)
        self.assertIn("ask for a decision before generation; do not put it in the PRD", skill)
        self.assertIn("add it to the PRD as `待确认`", skill)
        self.assertIn("[已确认 / 已观察]", template)
        self.assertNotIn("[已确认 / 已观察 / 待确认]", template)
        self.assertIn("ask for a decision before drafting and do not add it to the PRD", requirements_agent)
        self.assertIn("Keep speculative content and unresolved decisions in the run trace", requirements_agent)
        self.assertIn("Define requirement boundaries by independently decided user outcomes", requirements_agent)
        self.assertIn("exclude local self-test, demo, screenshot staging", requirements_agent)
        self.assertNotIn("Mark required decision fields as `待确认`", requirements_agent)

    def test_active_guidance_excludes_retired_placeholder_and_duplicate_id_rules(self) -> None:
        text = self.read("artifacts/artifact-contracts.md")
        self.assertNotIn("small `位置` and `用途` caption", text)
        self.assertNotIn("Function ID and function name", text)
        self.assertIn("Requirement-detail number and requirement name", text)
        self.assertIn("Keep the core PRD section numbers stable", text)
        for relative in (
            "PM_COPILOT.md",
            "agents/requirements-agent.md",
            "docs/implemented-feature-prd-workflow.md",
            "prompts/prompt-system.md",
            "tools/validation-tooling.md",
        ):
            guidance = self.read(relative)
            self.assertIn("占位图：功能-状态.png", guidance)
            self.assertNotIn("small `位置` and `用途` caption", guidance)
            self.assertNotIn("位置：...；用途：...", guidance)

    def test_implemented_feature_template_is_complete_but_deletes_empty_blocks(self) -> None:
        template = self.read("templates/implemented-feature-prd-template.md")
        self.assertIn("删除本次没有真实内容的整章、流程图块和图示行", template)
        self.assertIn("#### 用户流程图", template)
        self.assertIn("#### 操作流程图", template)
        self.assertIn("prd-detail-media", template)
        self.assertNotIn("占位图：[功能]-[状态].png", template)
        self.assertIn("一、主流程<br>1.", template)
        self.assertIn("## 六、多语言需求", template)
        self.assertIn("## 七、埋点需求", template)

    def test_prd_numbering_rule_keeps_core_sections_stable(self) -> None:
        contract = self.read("artifacts/prd-contract.md")
        for relative in ("artifacts/artifact-contracts.md", "templates/implemented-feature-prd-template.md", "skills/prd-writing/SKILL.md"):
            guidance = self.read(relative)
            self.assertNotIn("renumber visible H2 sections consecutively", guidance)
        self.assertIn("需求清单和需求详情保留稳定的 `四`、`五` 编号", self.read("templates/implemented-feature-prd-template.md"))
        self.assertIn("when `多语言需求` is omitted but `埋点需求` is present, it is `## 六、埋点需求`", contract)

    def test_every_prd_delivery_requires_html(self) -> None:
        for relative in ("PM_COPILOT.md", "workflow/delivery-check-workflow.md", "docs/implemented-feature-prd-workflow.md"):
            self.assertIn("prd.html", self.read(relative))
        workflow = self.read("docs/implemented-feature-prd-workflow.md")
        self.assertIn("Every PRD delivery requires `prd.html`", workflow)
        self.assertNotIn("exception to the general PRD rule", workflow)

    def test_prompt_keeps_internal_review_content_out_of_prd(self) -> None:
        for relative in ("PM_COPILOT.md", "prompts/prompt-system.md", "docs/direct-use.md"):
            guidance = self.read(relative)
            self.assertIn("run trace", guidance)
        prompt = self.read("prompts/prompt-system.md")
        self.assertIn("Keep risks, review findings, validation results, clarified answers, and assumptions in the run trace", prompt)
        self.assertNotIn("PRD validation results", prompt)
        self.assertNotIn("flows, risks, review findings, validation results, clarified answers, and assumptions inside `prd.md`", self.read("PM_COPILOT.md"))

    def test_controlled_placeholder_projection_matches_contract_and_rejects_other_formats(self) -> None:
        contract = self.read("artifacts/prd-contract.md")
        workflow = self.read("docs/implemented-feature-prd-workflow.md")
        self.assertIn(PLACEHOLDER_MARKER, contract)
        self.assertNotIn("占位图：图片名称", workflow)
        self.assertTrue(is_controlled_placeholder_value("占位图：成员管理-角色变更确认.png"))
        self.assertFalse(is_controlled_placeholder_value("占位图：成员管理-角色变更确认.jpg"))
        self.assertFalse(is_controlled_placeholder_value("占位图：角色变更确认.png"))

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
