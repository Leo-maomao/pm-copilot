#!/usr/bin/env python3
"""Build a bounded, evidence-oriented multi-agent delegation plan for PM Copilot."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


ROLE_RULES = (
    ("Discovery Agent", ("澄清", "不清楚", "不明确", "探索", "问题", "目标"), "确认目标、用户、范围与缺失决策"),
    ("Requirements Agent", ("需求", "prd", "功能", "用户", "流程", "产品"), "形成用户驱动的范围、规则与可评审需求"),
    ("Research Agent", ("调研", "竞品", "市场", "行业", "对标", "研究"), "收集可核验的外部或已有证据"),
    ("Analytics Agent", ("埋点", "指标", "数据", "kpi", "漏斗", "分析"), "定义指标、事件和验证口径"),
    ("UI Delivery Agent", ("ui", "界面", "交互", "原型", "截图", "流程图", "视觉"), "补齐界面、交互、图示与可读性证据"),
    ("Integration Governance Agent", ("接入", "集成", "mcp", "api", "第三方", "工具", "模型"), "确认外部能力、权限、成本与可用性边界"),
)


@dataclass(frozen=True)
class Worker:
    role: str
    owned_question: str
    validation_expectation: str


def contains_any(request: str, phrases: tuple[str, ...]) -> bool:
    normalized = request.lower()
    return any(phrase.lower() in normalized for phrase in phrases)


def build_plan(request: str, task_mode: str = "auto") -> dict[str, object]:
    """Select only roles that have an independent evidence-producing question."""
    workers = [
        Worker(role, question, "Return evidence, assumptions, open questions, and a validation delta.")
        for role, phrases, question in ROLE_RULES
        if contains_any(request, phrases)
    ]
    if task_mode == "self_improvement":
        workers = [
            Worker("Requirements Agent", "Audit product-document quality failures and identify user-impacting regression cases.", "Link every finding to an artifact contract, source evidence, and regression."),
            Worker("UI Delivery Agent", "Audit PRD visual evidence and asset relevance, excluding runtimes and unrelated images.", "Link every acceptable figure to a same-run source and requirement."),
            Worker("Integration Governance Agent", "Verify runtime, tool, and delegation boundaries before automation changes.", "Reject unsupported execution claims and credential leakage."),
        ]
    elif not workers:
        workers = [Worker("Discovery Agent", "Turn the request into a bounded product goal and identify missing decisions.", "Classify every unknown and name its readiness impact.")]

    requires_review = len(workers) > 1 or any(worker.role == "Requirements Agent" for worker in workers)
    review_worker = Worker(
        "Review Agent",
        "Challenge evidence gaps, user-value gaps, contradictions, and unsupported assumptions in specialist outputs.",
        "Each finding must name evidence, severity, owner, and a concrete correction or accepted risk.",
    )
    worker_roles = {worker.role for worker in workers}
    cross_checks = []
    if "Research Agent" in worker_roles and "Requirements Agent" in worker_roles:
        cross_checks.append("Requirements Agent may use Research claims only when the source and applicability are explicit.")
    if "UI Delivery Agent" in worker_roles and "Requirements Agent" in worker_roles:
        cross_checks.append("UI Delivery Agent checks that each interaction matches the confirmed user rule, not an inferred implementation.")
    if "Analytics Agent" in worker_roles and "Requirements Agent" in worker_roles:
        cross_checks.append("Analytics Agent checks that each required behavior has a measurable user-action boundary.")

    evidence_payload = []
    for index, worker in enumerate(workers):
        evidence_payload.append({
            **asdict(worker),
            "task_id": f"evidence-{index + 1}-{worker.role.lower().replace(' ', '-')}",
            "depends_on": [],
            "input_evidence": ["user_request", "local_context"],
            "output_contract": "structured handoff with source-backed claims, confidence, rejected evidence, and validation delta",
            "max_attempts": 2,
        })
    review_payload = [{
        **asdict(review_worker),
        "task_id": "challenge-1-review-agent",
        "depends_on": [item["task_id"] for item in evidence_payload],
        "input_evidence": ["registered_claims", "worker_artifacts"],
        "output_contract": "targeted cross-review only; each finding references known claim ids and evidence gaps",
        "max_attempts": 2,
    }] if requires_review else []
    return {
        "active": len(workers) > 1,
        "pattern": "parallel_specialists" if len(workers) > 1 else "orchestrator_worker",
        "coordinator": "PM Orchestrator",
        "dispatch_groups": [
            {"phase": "evidence", "workers": evidence_payload},
            {"phase": "challenge", "workers": review_payload},
        ],
        "cross_checks": cross_checks,
        "conflict_protocol": {
            "trigger": "material disagreement, unsupported claim, or high/critical review finding",
            "method": "retain both positions, compare evidence and user impact, then let PM Orchestrator decide or request human input",
            "not_allowed": "majority vote, ungrounded debate, or silently overwriting another role's owned decision",
        },
        "stop_conditions": ["success criteria met", "needs input", "blocked", "no evidence delta", "iteration budget exhausted"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request")
    parser.add_argument("--request-file", type=Path)
    parser.add_argument("--task-mode", default="auto")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    request = args.request or (args.request_file.read_text(encoding="utf-8") if args.request_file else "")
    request = re.sub(r"\s+", " ", request).strip()
    if not request:
        parser.error("provide --request or --request-file")
    plan = build_plan(request, args.task_mode)
    payload = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
