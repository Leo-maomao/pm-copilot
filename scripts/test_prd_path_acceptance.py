#!/usr/bin/env python3
"""Deterministic end-to-end acceptance coverage for the supported PRD paths.

Every case exercises the production staging, rendering, trace, validation, and
promotion path. The only replacement is a local worker that writes a known
valid artifact and an independent local review response; no test reaches an
external provider.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from run_interactive_request import (
    _confirmed_delivery,
    begin_in_place_revision,
    create_state,
    register_extraction_source,
    register_implemented_feature_evidence,
)
from test_prd_contract import PASS_PRD
from validate_agent_trace import (
    validate_artifact_lineage,
    validate_implemented_feature_evidence_packet,
)


IMPLEMENTED_ASSET_PATH = "assets/role-change-confirmation.png"
IMPLEMENTED_ASSET_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlT8gAAAABJRU5ErkJggg=="
)
IMPLEMENTED_ASSET_SHA256 = hashlib.sha256(IMPLEMENTED_ASSET_BYTES).hexdigest()


IMPLEMENTED_FEATURE_EVIDENCE = {
    "branch_name": "feature/role-change-confirmation",
    "diff_commands": ["git diff --stat"],
    "changed_files": ["src/member-role.ts"],
    "behavior_evidence": [{
        "evidence_id": "behavior-1",
        "observed_behavior": "团队管理员确认高风险角色变更后，系统才会保存变更。",
        "related_requirement_ids": ["5.1"],
        "coverage_status": "covered",
    }],
    "screenshots_and_placeholders": [{
        "target_ref": "5.1",
        "coverage_decision": "real_figure",
        "rationale": "角色变更确认是需要由产品和研发共同核验的用户可见交互。",
        "path": IMPLEMENTED_ASSET_PATH,
        "capture_source": "deterministic acceptance fixture",
        "asset_sha256": IMPLEMENTED_ASSET_SHA256,
    }],
    "validation_evidence": [{"command": "npm test", "status": "passed"}],
    "completeness_check": {
        "implementation_behaviors_checked": ["高风险角色变更需要明确确认。"],
        "represented_in_prd": ["5.1"],
        "unresolved_product_intent": ["无"],
    },
}


IMPLEMENTED_PRD = PASS_PRD.replace(
    "<br>4. 成员为空时展示空状态。 |",
    "<br>4. 成员为空时展示空状态。"
    "<br>[[prd-detail-media src=\"./assets/role-change-confirmation.png\" alt=\"角色变更确认\" "
    "copy=\"一、确认信息<br>1. 展示变更前后角色和确认反馈。\"]] |",
).replace(
    "评估入口访问与后续角色变更转化。",
    "评估入口访问与后续角色变更转化；关联需求：5.1。",
).replace(
    "评估高危角色变更意图。",
    "评估高危角色变更意图；关联需求：5.1。",
).replace(
    "区分成功与可恢复失败。",
    "区分成功与可恢复失败；关联需求：5.1。",
).replace(
    "评估成员信息浏览深度。",
    "评估成员信息浏览深度；关联需求：5.1。",
)


COMPOSED_PRD = PASS_PRD.replace(
    "团队管理员调整成员角色时容易误操作，需要在关键变更前获得清晰反馈并能恢复。",
    "团队管理员调整成员角色时容易误操作，需要在关键变更前获得清晰反馈并能恢复。"
    "角色变更需要在保存前确认。本次角色变更需要记录。",
)


PROTECTED_DETAIL = """### 5.2 受保护的成员提醒

| 维度 | 需求说明 |
| --- | --- |
| 用户与场景 | 团队管理员查看成员提醒时，需要保留既有提醒规则。 |
| 需求入口 | 团队管理员在成员管理页打开提醒区域。 |
| 需求详情 | 展示既有成员提醒；提醒规则保持不变。 |
| 设计与交互 | 保留当前提醒顺序和可读性。 |

"""


REVISION_BASELINE = PASS_PRD.replace(
    "| 5.1 | 角色变更确认 | 团队管理员 | 在成员页修改高危角色 | 降低误操作 | 高危角色变更需要确认与可恢复反馈 | P0 | 用户确认 |",
    "| 5.1 | 角色变更确认 | 团队管理员 | 在成员页修改高危角色 | 降低误操作 | 高危角色变更需要确认与可恢复反馈 | P0 | 用户确认 |\n"
    "| 5.2 | 受保护的成员提醒 | 团队管理员 | 在成员页查看提醒 | 保留既有规则 | 既有提醒保持不变 | P1 | 用户确认 |",
).replace("## 六、多语言需求", PROTECTED_DETAIL + "## 六、多语言需求")


UNSCOPED_REVISION_CANDIDATE = REVISION_BASELINE.replace(
    "| 5.1 | 角色变更确认 |",
    "| 5.1 | 角色变更二次确认 |",
).replace(
    "### 5.1 角色变更确认",
    "### 5.1 角色变更二次确认",
).replace(
    "2. 系统展示确认信息。",
    "2. 系统先展示变更影响摘要，管理员确认后才可保存。",
).replace(
    "展示既有成员提醒；提醒规则保持不变。",
    "未经确认地改写受保护提醒。",
).replace(
    "| v0.1 | 2026-07-10 | 首次创建 | 产品 |",
    "| v0.1 | 2026-07-10 | 首次创建 | 产品 |\n"
    "| v0.2 | 2026-09-04 | 更新角色变更确认反馈 | 产品 |",
)


class PrdPathAcceptanceTests(unittest.TestCase):
    def _confirm(
        self,
        state: dict[str, object],
        *,
        goal: str,
        in_scope: list[str],
        out_of_scope: list[str] | None = None,
    ) -> None:
        turn = {
            "turn": 1,
            "user_text": "确认固定验收样例。",
            "summary": goal,
            "scope": {
                "goal": goal,
                "in_scope": in_scope,
                "out_of_scope": out_of_scope or [],
            },
            "assumptions": [],
            "decisions": [],
            "risks": [],
            "buckets": {},
        }
        state.update({
            "turns": [turn],
            "confirmed_fact_packet": copy.deepcopy(turn),
            "user_confirmation": {
                "confirmed": True,
                "source": "acceptance fixture",
                "at": "2026-09-04T00:00:00Z",
            },
            "status": "awaiting_confirmation",
            "termination": "human_checkpoint",
        })

    @staticmethod
    def _seed_required_pre_delivery_evidence(state: dict[str, object]) -> None:
        state["agent_calls"] = [
            {"phase": "intake", "provider": "test", "model": "test", "status": "complete"},
            {"phase": "clarification_review", "provider": "test", "model": "test", "status": "complete"},
        ]

    def _run_completed_delivery(
        self,
        state: dict[str, object],
        markdown: str,
    ) -> tuple[Path, dict[str, object], list[str]]:
        """Run the real delivery controller with only write/review calls faked locally."""
        self._seed_required_pre_delivery_evidence(state)
        worker_calls: list[str] = []

        def worker(
            provider: str,
            prompt: str,
            cwd: Path,
            _timeout: int,
            _model: str | None,
            *_args: object,
        ) -> dict[str, str]:
            self.assertEqual(provider, "test")
            if "Stage Quality Review Agent" in prompt:
                review_path = Path(prompt.split("Write ONLY one JSON object to ", 1)[1].split(" (UTF-8):", 1)[0])
                review = {
                    "status": "pass",
                    "summary": "fixture reviewed the isolated artifact",
                    "blocking_findings": [],
                    "acceptance_evidence": ["fixture artifact reviewed"],
                }
                if state.get("delivery_variant") == "in_place_revision":
                    review["revision_findings"] = []
                review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
                worker_calls.append(f"review:{review_path.name}")
                return {
                    "provider": "test", "model": "test", "status": "complete",
                    "output": "", "error": "",
                }

            target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
            self.assertEqual(target.parent, cwd)
            self.assertNotEqual(target.name, "run-log.yaml", "run-log.yaml must remain controller materialized")
            if target.name == "prd.md":
                target.write_text(markdown, encoding="utf-8")
            elif target.name == "confirmed-requirements.md":
                target.write_text("# 已确认需求\n\n固定验收范围。\n", encoding="utf-8")
            else:
                self.fail(f"unexpected fake-worker artifact: {target.name}")
            worker_calls.append(f"write:{target.name}")
            return {
                "provider": "test", "model": "test", "status": "complete",
                "output": "fixture artifact written", "error": "",
            }

        with patch(
            "run_interactive_request.execute",
            side_effect=AssertionError("acceptance tests must not invoke an external agent runtime"),
        ) as execute:
            _confirmed_delivery(state, "test", 1, worker=worker, max_revisions=0, interactive_timeout=5)
        execute.assert_not_called()

        canonical = Path(str(state["folder"]))
        failed_checks = "\n".join(
            " ".join(str(check.get(field, "")) for field in ("command", "stdout", "stderr"))
            for check in state.get("validation", [])
            if isinstance(check, dict) and check.get("status") != "passed"
        )
        self.assertEqual(state["status"], "complete", state.get("last_error") or failed_checks)
        self.assertEqual(state["termination"], "complete")
        self.assertEqual(
            state["artifacts"],
            ["discussion.md", "confirmed-requirements.md", "prd.md", "prd.html", "run-log.yaml", "assets/"],
        )
        self.assertTrue(all(check.get("status") == "passed" for check in state["validation"]))
        for validator in (
            "render_prd_html.py",
            "validate_outputs.py",
            "validate_agent_trace.py",
            "run_delivery_checks.py",
        ):
            self.assertTrue(any(
                validator in str(check.get("command", "")) and check.get("status") == "passed"
                for check in state["validation"]
            ), f"missing passing final validator: {validator}")
        self.assertEqual(worker_calls.count("write:confirmed-requirements.md"), 1)
        self.assertEqual(worker_calls.count("write:prd.md"), 1)
        self.assertFalse(any("run-log.yaml" in call and call.startswith("write:") for call in worker_calls))
        for artifact in ("prd.md", "prd.html", "run-log.yaml"):
            self.assertTrue((canonical / artifact).is_file(), f"missing promoted {artifact}")

        trace = yaml.safe_load((canonical / "run-log.yaml").read_text(encoding="utf-8"))
        self.assertIsInstance(trace, dict)
        self.assertTrue(any(
            call.get("artifact") == "run-log.yaml"
            and call.get("execution_mode") == "deterministic_trace_materialization"
            for call in state["agent_calls"]
            if isinstance(call, dict)
        ))
        self.assertFalse(any(
            call.get("provider") == "legacy-provider"
            for call in state["agent_calls"]
            if isinstance(call, dict)
        ))
        return canonical, trace, worker_calls

    def test_new_prd_completes_full_local_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            canonical = Path(temporary) / "pm-copilot-outputs" / "role-confirmation-2026-09-04"
            canonical.mkdir(parents=True)
            state = create_state("为团队管理员生成角色变更确认 PRD", canonical)
            self._confirm(state, goal="明确角色变更确认", in_scope=["5.1 角色变更确认"])

            promoted, trace, _ = self._run_completed_delivery(state, PASS_PRD)

            self.assertEqual(trace["artifact_lineage"]["mode"], "new_run")
            self.assertEqual(trace["artifact_lineage"]["mode"], "new_run")
            self.assertEqual(trace["artifact_lineage"]["revised_requirement_ids"], [])
            self.assertEqual(validate_artifact_lineage(promoted / "run-log.yaml"), [])
            self.assertIn("## 五、需求详情", (promoted / "prd.md").read_text(encoding="utf-8"))
            self.assertIn("<!doctype html", (promoted / "prd.html").read_text(encoding="utf-8").lower())

    def test_implemented_feature_requires_immutable_evidence_then_completes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            blocked_folder = root / "pm-copilot-outputs" / "implemented-missing-evidence-2026-09-04"
            blocked_folder.mkdir(parents=True)
            blocked = create_state(
                "将已实现的角色变更确认还原为 PRD",
                blocked_folder,
                task_mode="implemented_feature_prd",
            )
            self._confirm(blocked, goal="还原已实现功能", in_scope=["5.1 角色变更确认"])
            dispatched = False

            def unexpected_worker(*_args: object) -> dict[str, str]:
                nonlocal dispatched
                dispatched = True
                return {"provider": "test", "model": "test", "status": "complete", "output": "", "error": ""}

            _confirmed_delivery(blocked, "test", 1, worker=unexpected_worker)
            self.assertFalse(dispatched, "implemented-feature delivery must stop before a writer without evidence")
            self.assertEqual(blocked["status"], "needs_input")
            self.assertEqual(blocked["required_input"]["field"], "implementation_evidence")

            canonical = root / "pm-copilot-outputs" / "implemented-role-confirmation-2026-09-04"
            canonical.mkdir(parents=True)
            evidence_source = root / "implemented-feature-evidence.json"
            evidence_source.write_text(json.dumps(IMPLEMENTED_FEATURE_EVIDENCE), encoding="utf-8")
            state = create_state(
                "将已实现的角色变更确认还原为 PRD",
                canonical,
                task_mode="implemented_feature_prd",
            )
            register_implemented_feature_evidence(state, evidence_source)
            asset = canonical / IMPLEMENTED_ASSET_PATH
            asset.parent.mkdir(parents=True, exist_ok=True)
            asset.write_bytes(IMPLEMENTED_ASSET_BYTES)
            self._confirm(state, goal="还原已实现功能", in_scope=["5.1 角色变更确认"])

            promoted, trace, _ = self._run_completed_delivery(state, IMPLEMENTED_PRD)
            packet = promoted / "source-material" / "implemented-feature-evidence.json"
            descriptor = state["implemented_feature_evidence_source"]

            self.assertEqual(state["task_mode"], "implemented_feature_prd")
            self.assertEqual(json.loads(packet.read_text(encoding="utf-8")), IMPLEMENTED_FEATURE_EVIDENCE)
            self.assertEqual((promoted / IMPLEMENTED_ASSET_PATH).read_bytes(), IMPLEMENTED_ASSET_BYTES)
            self.assertEqual(descriptor["packet_path"], "source-material/implemented-feature-evidence.json")
            self.assertEqual(descriptor["packet_sha256"], hashlib.sha256(packet.read_bytes()).hexdigest())
            self.assertEqual(trace["agent_strategy"]["task_mode"], "implemented_feature_prd")
            self.assertEqual(validate_artifact_lineage(promoted / "run-log.yaml"), [])
            self.assertEqual(validate_implemented_feature_evidence_packet(promoted / "run-log.yaml"), [])

    def test_in_place_revision_promotes_only_confirmed_requirement_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            canonical = Path(temporary) / "pm-copilot-outputs" / "member-role-2026-09-04"
            canonical.mkdir(parents=True)
            (canonical / "prd.md").write_text(REVISION_BASELINE, encoding="utf-8")
            (canonical / "prd.html").write_text("<!doctype html><html><body>baseline</body></html>\n", encoding="utf-8")
            state = create_state("既有成员管理 PRD", canonical)
            begin_in_place_revision(state, "仅更新需求 5.1 的确认反馈", selectors=["5.1"])
            self._confirm(
                state,
                goal="仅更新需求 5.1 的确认反馈",
                in_scope=["5.1"],
                out_of_scope=["5.2"],
            )

            promoted, trace, _ = self._run_completed_delivery(state, UNSCOPED_REVISION_CANDIDATE)
            final_markdown = (promoted / "prd.md").read_text(encoding="utf-8")
            revision_evidence = json.loads((promoted / "revision-evidence.json").read_text(encoding="utf-8"))

            self.assertEqual(state["delivery_variant"], "in_place_revision")
            self.assertEqual(trace["artifact_lineage"]["mode"], "in_place_revision")
            self.assertEqual(trace["artifact_lineage"]["revised_requirement_ids"], ["5.1"])
            self.assertIn("系统先展示变更影响摘要", final_markdown)
            self.assertIn("### 5.2 受保护的成员提醒", final_markdown)
            self.assertIn("展示既有成员提醒；提醒规则保持不变。", final_markdown)
            self.assertNotIn("未经确认地改写受保护提醒。", final_markdown)
            self.assertEqual(state["revision_scope_validation"]["status"], "passed")
            self.assertEqual(revision_evidence["controller_scope_ids"], ["5.1"])
            self.assertEqual(validate_artifact_lineage(promoted / "run-log.yaml"), [])

    def test_multiple_source_extraction_completes_with_plural_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "pm-copilot-outputs" / "composed-role-policy-2026-09-04"
            canonical.mkdir(parents=True)
            source_one = root / "role-confirmation.md"
            source_two = root / "change-audit.md"
            source_one.write_text(
                "# 角色确认来源\n\n"
                "### 5.1 角色变更确认\n"
                "角色变更需要在保存前确认。\n\n"
                "### 5.2 未选择的旧规则\n"
                "不要带入这条未选择的旧规则。\n",
                encoding="utf-8",
            )
            source_two.write_text(
                "# 变更记录来源\n\n"
                "### 6.1 角色变更记录\n"
                "本次角色变更需要记录。\n\n"
                "### 6.2 未选择的审计规则\n"
                "不要带入这条未选择的审计规则。\n",
                encoding="utf-8",
            )
            state = create_state(
                "从两份旧 PRD 提取已选需求，形成新的角色变更 PRD",
                canonical,
                task_mode="prd_composition",
                delivery_variant="compose_to_new",
            )
            register_extraction_source(state, source_one)
            register_extraction_source(state, source_two)
            self._confirm(
                state,
                goal="组合两份旧 PRD 中已确认的角色变更需求",
                in_scope=["source-1: 5.1", "source-2: 6.1"],
                out_of_scope=["source-1: 5.2", "source-2: 6.2"],
            )

            promoted, trace, _ = self._run_completed_delivery(state, COMPOSED_PRD)
            final_markdown = (promoted / "prd.md").read_text(encoding="utf-8")
            sources = state["extraction_sources"]
            lineage_sources = trace["artifact_lineage"]["source_prds"]

            self.assertEqual(state["task_mode"], "prd_composition")
            self.assertEqual(state["delivery_variant"], "compose_to_new")
            self.assertEqual(trace["artifact_lineage"]["mode"], "composition_run")
            self.assertEqual([source["source_id"] for source in sources], ["source-1", "source-2"])
            self.assertEqual([source["source_id"] for source in lineage_sources], ["source-1", "source-2"])
            self.assertEqual([source["selected_scope"] for source in lineage_sources], [["5.1"], ["6.1"]])
            self.assertEqual(
                [source["scope_resolution"] for source in lineage_sources],
                [
                    [{"selector": "5.1", "kind": "requirement_id", "matches": ["5.1"]}],
                    [{"selector": "6.1", "kind": "requirement_id", "matches": ["6.1"]}],
                ],
            )
            for descriptor, lineage_source in zip(sources, lineage_sources):
                snapshot = promoted / descriptor["snapshot_path"]
                self.assertTrue(snapshot.is_file())
                self.assertEqual(lineage_source["snapshot_path"], descriptor["snapshot_path"])
                self.assertEqual(lineage_source["sha256"], hashlib.sha256(snapshot.read_bytes()).hexdigest())
                self.assertIn(
                    descriptor["snapshot_path"],
                    [source["snapshot_path"] for source in trace["artifact_lineage"]["source_prds"]],
                )
            self.assertIn("角色变更需要在保存前确认。", final_markdown)
            self.assertIn("本次角色变更需要记录。", final_markdown)
            self.assertNotIn("不要带入这条未选择的旧规则。", final_markdown)
            self.assertNotIn("不要带入这条未选择的审计规则。", final_markdown)
            self.assertEqual(validate_artifact_lineage(promoted / "run-log.yaml"), [])


if __name__ == "__main__":
    unittest.main()
