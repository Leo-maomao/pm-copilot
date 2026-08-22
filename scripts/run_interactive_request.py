#!/usr/bin/env python3
"""Run the production, user-driven PM Copilot clarification gate.

This entry point deliberately does not use ``evals/scenario-confirmations.json``.
It persists a resumable conversation, asks the local Agent for only the next
branch-changing questions, and refuses downstream generation until the user
has explicitly confirmed the clarified scope.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from agent_runtime import execute
from runtime_limits import DEFAULT_EXECUTION_TIMEOUT_MINUTES, DEFAULT_INTERACTIVE_MAX_REVISIONS


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs"
DEFAULT_MAX_REVISIONS = DEFAULT_INTERACTIVE_MAX_REVISIONS
CLARIFICATION_COVERAGE_AREAS = (
    "goal", "users", "scope", "success_evidence", "constraints_and_risk",
)


def _artifact_digest(path: Path) -> str | None:
    """Return a content digest so a repair loop cannot mistake no-op work for progress."""
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record_revision(
    state: dict[str, Any], artifact: str, before: str | None, after: str | None,
    outcome: str,
) -> None:
    state.setdefault("revision_trace", []).append({
        "artifact": artifact,
        "before_sha256": before,
        "after_sha256": after,
        "outcome": outcome,
        "at": dt.datetime.now(dt.timezone.utc).isoformat(),
    })


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value[:48] or "interactive-request"


def new_requirement_folder(request: str, root: Path = OUTPUT_ROOT) -> Path:
    """Allocate a canonical folder only for an explicitly new requirement."""
    stem = f"{_slug(request)}-{dt.datetime.now(dt.timezone.utc):%Y-%m-%d}"
    folder = root / stem
    if folder.exists():
        raise FileExistsError(
            f"Canonical PRD folder already exists: {folder}. Use --run-folder {folder} "
            "to revise that requirement; do not create a suffixed copy."
        )
    return folder


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _agent_call_has_evidence(result: dict[str, Any]) -> bool:
    """Require attributable runtime evidence before a call can advance a gate."""
    provider = str(result.get("provider", "")).strip()
    model = str(result.get("model", "")).strip()
    if not provider or not model or model in {"configured default", "unknown", "None"}:
        return False
    return result.get("status") == "complete"


def _record_agent_call(
    state: dict[str, Any], result: dict[str, Any], *, phase: str, artifact: str | None = None,
) -> bool:
    record = {**result, "phase": phase}
    if artifact:
        record["artifact"] = artifact
    state.setdefault("agent_calls", []).append(record)
    return _agent_call_has_evidence(record)


def _required_production_evidence(state: dict[str, Any]) -> tuple[bool, str]:
    """Prove every required production stage used an attributable Agent."""
    calls = state.get("agent_calls", [])
    required = {
        ("intake", None),
        ("clarification_review", None),
        ("delivery", "confirmed-requirements.md"),
        ("delivery", "prd.md"),
        ("delivery", "run-log.yaml"),
        ("stage_quality_review", "confirmed-requirements.md"),
        ("stage_quality_review", "prd.md"),
        ("stage_quality_review", "run-log.yaml"),
    }
    for phase, artifact in required:
        matching = [
            call for call in calls
            if call.get("phase") == phase and (artifact is None or call.get("artifact") == artifact)
        ]
        if not matching:
            return False, f"missing required Agent evidence: {phase}/{artifact or 'request'}"
        if not any(_agent_call_has_evidence(call) for call in matching):
            return False, f"required Agent evidence is not attributable: {phase}/{artifact or 'request'}"
    return True, "all required production Agent stages are attributable"


def _extract_json(text: str) -> dict[str, Any]:
    """Accept plain JSON or a fenced JSON response without hiding failures."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("Agent did not return a JSON intake envelope")
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("Agent intake envelope must be an object")
    return value


def _normalise_intake(value: dict[str, Any]) -> dict[str, Any]:
    status = str(value.get("status", "needs_input"))
    if status not in {"needs_input", "complete", "failed"}:
        status = "needs_input"
    questions = value.get("questions", [])
    if not isinstance(questions, list):
        questions = [str(questions)]
    questions = [str(item).strip() for item in questions if str(item).strip()]
    buckets = value.get("buckets", {})
    if not isinstance(buckets, dict):
        buckets = {}
    must = buckets.get("must_answer_before_generation", value.get("must_answer_before_generation", []))
    if not isinstance(must, list):
        must = [str(must)] if must else []
    # A model may return complete without an empty blocking bucket. The
    # blocking bucket is authoritative: generation is unsafe while it is non-empty.
    must = [str(item).strip() for item in must if str(item).strip()]
    if must:
        status = "needs_input"
    return {
        "status": status,
        "summary": str(value.get("summary", "")).strip(),
        "questions": questions,
        "buckets": {
            "must_answer_before_generation": must,
            "can_draft_with_stated_assumption": buckets.get("can_draft_with_stated_assumption", value.get("can_draft_with_stated_assumption", [])),
            "must_confirm_before_development_or_launch": buckets.get("must_confirm_before_development_or_launch", value.get("must_confirm_before_development_or_launch", [])),
        },
        "scope": value.get("scope", {}),
        "assumptions": value.get("assumptions", []),
        "decisions": value.get("decisions", []),
        "risks": value.get("risks", []),
    }


def _normalise_clarification_review(value: dict[str, Any]) -> dict[str, Any]:
    """Normalise a second-agent gate without letting malformed output pass it."""
    status = str(value.get("status", "needs_input")).strip().lower()
    questions = value.get("questions", [])
    blockers = value.get("blockers", [])
    coverage = value.get("coverage", {})
    if not isinstance(questions, list):
        questions = [questions]
    if not isinstance(blockers, list):
        blockers = [blockers]
    questions = [str(item).strip() for item in questions if str(item).strip()]
    blockers = [str(item).strip() for item in blockers if str(item).strip()]
    if not isinstance(coverage, dict):
        coverage = {}
    missing_coverage = [
        area for area in CLARIFICATION_COVERAGE_AREAS
        if str(coverage.get(area, "")).strip().lower() != "covered"
    ]
    if missing_coverage:
        blockers.append(
            "独立澄清复核未证明以下必要条件已覆盖：" + "、".join(missing_coverage)
        )
    # Only an explicit pass with no undisclosed blocker can advance to the
    # human confirmation checkpoint. A reviewer cannot make an ambiguous
    # request look complete by omitting the status field.
    passed = status == "complete" and not blockers and not questions
    if not passed and not questions:
        questions = ["请补充当前范围中仍会改变方案、验收或风险判断的关键信息。"]
    return {
        "status": "complete" if passed else "needs_input",
        "summary": str(value.get("summary", "")).strip(),
        "questions": questions,
        "blockers": blockers,
        "coverage": coverage,
        "conflicts": value.get("conflicts", []),
    }


def intake_prompt(state: dict[str, Any], answers: str | None) -> str:
    transcript = "\n".join(
        f"Turn {turn['turn']}:\nUser request/answers:\n{turn['user_text']}\nAgent result:\n{turn.get('summary', '')}"
        for turn in state.get("turns", [])
    )
    latest = f"\nLatest user answer:\n{answers}" if answers else ""
    return f"""You are the PM Orchestrator's production requirement-intake agent.
The user request is ambiguous by default. Work from first principles: identify the
goal, necessary conditions, current blocker, most direct question, and proof needed
to move to the next phase. Ask only questions that materially change scope,
success criteria, platform, permissions, compliance, measurement, or delivery risk.
Never treat silence, a fixture, or your own assumption as user confirmation.

Return ONLY one JSON object with this shape:
{{
  "status": "needs_input" | "complete",
  "summary": "what is currently understood",
  "questions": ["branch-changing question with why it matters"],
  "buckets": {{
    "must_answer_before_generation": [],
    "can_draft_with_stated_assumption": [],
    "must_confirm_before_development_or_launch": []
  }},
  "scope": {{"goal":"", "users":[], "in_scope":[], "out_of_scope":[], "platform":""}},
  "assumptions": [], "decisions": [], "risks": []
}}
Put every unresolved material unknown in exactly one bucket. If any
must_answer_before_generation item remains, status MUST be needs_input and the
questions list MUST contain the corresponding questions.

Initial user request:
{state['raw_request']}

Conversation so far:
{transcript or '(no previous turns)'}
{latest}
"""


def clarification_review_prompt(state: dict[str, Any], intake: dict[str, Any], review_path: Path) -> str:
    transcript = "\n".join(
        f"Turn {turn['turn']} user input: {turn['user_text']}\n"
        f"Intake conclusion: {turn.get('summary', '')}"
        for turn in state.get("turns", [])
    )
    return f"""You are the independent Clarification Review Agent for a production PM run.
Challenge the Intake Agent's conclusion from first principles. The request may
not advance merely because another model said it is complete. Identify every
unresolved fact that can materially change the user outcome, scope boundary,
non-goal, acceptance evidence, platform/delivery surface, owner/permission,
metric, or material risk. Do not ask preference or implementation questions
that cannot change the next product decision.

Write ONLY one JSON object to {review_path} (UTF-8):
{{
  "status": "needs_input" | "complete",
  "summary": "coverage judgment",
  "questions": ["one next branch-changing question with why it matters"],
  "blockers": ["unresolved material decision"],
  "coverage": {{"goal":"covered|missing", "users":"covered|missing", "scope":"covered|missing", "success_evidence":"covered|missing", "constraints_and_risk":"covered|missing"}},
  "conflicts": []
}}
Use status complete only when every material unknown is either answered by the
user, explicitly accepted as a stated draft assumption, or assigned to the
development/launch confirmation bucket. When status is needs_input, include a
question for each blocker. User silence and model inference are never answers.
For status complete, set every coverage field to exactly covered. Missing,
unknown, or partial coverage is a blocker, not a pass.

Original request:\n{state['raw_request']}

Conversation:\n{transcript or '(no conversation yet)'}

Intake conclusion to challenge:\n{json.dumps(intake, ensure_ascii=False)}
"""


def run_clarification_review(
    state: dict[str, Any], intake: dict[str, Any], provider: str, timeout: int,
    worker: Callable[..., dict[str, Any]] = execute,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=".clarification-review-") as review_dir:
        review_path = Path(review_dir) / "clarification-review.json"
        result = worker(provider, clarification_review_prompt(state, intake, review_path), ROOT, timeout, None, None, False, 8000)
        review_text = review_path.read_text(encoding="utf-8") if review_path.is_file() else ""
    result["phase"] = "clarification_review"
    if not _record_agent_call(state, result, phase="clarification_review"):
        return {"status": "failed", "blockers": ["Clarification Review Agent call has no attributable provider/model evidence"]}
    if result.get("status") != "complete":
        return {
            "status": "needs_input",
            "summary": "独立澄清复核未能完成，不能跳过需求澄清。",
            "questions": ["请确认是否继续并补充会影响范围、验收或风险的背景。"],
            "blockers": [result.get("error", "Clarification Review Agent failed")],
            "coverage": {},
            "conflicts": [],
        }
    try:
        raw_review = review_text or result.get("output", "")
        return _normalise_clarification_review(_extract_json(raw_review))
    except (ValueError, json.JSONDecodeError) as error:
        return {
            "status": "needs_input",
            "summary": "独立澄清复核没有返回可验证结论。",
            "questions": ["请补充会影响方案边界与验收方式的关键信息。"],
            "blockers": [str(error)],
            "coverage": {},
            "conflicts": [],
        }


def run_intake(
    state: dict[str, Any], provider: str, timeout: int,
    worker: Callable[..., dict[str, Any]] = execute, answers: str | None = None,
) -> dict[str, Any]:
    result = worker(provider, intake_prompt(state, answers), ROOT, timeout, None, None, False, 8000)
    result_record = {**result, "turn": len(state.get("turns", [])) + 1}
    if not _record_agent_call(state, result_record, phase="intake"):
        state["status"] = "failed"
        state["termination"] = "failed"
        state["last_error"] = "Intake Agent call has no attributable provider/model evidence"
        return state
    if result.get("status") != "complete":
        state["status"] = "failed"
        state["termination"] = "failed"
        state["last_error"] = result.get("error", "intake Agent failed")
        return state
    try:
        intake = _normalise_intake(_extract_json(result.get("output", "")))
    except (ValueError, json.JSONDecodeError) as error:
        state["status"] = "failed"
        state["termination"] = "failed"
        state["last_error"] = str(error)
        return state
    user_text = answers or state["raw_request"]
    state.setdefault("turns", []).append({
        "turn": len(state.get("turns", [])) + 1,
        "user_text": user_text,
        "summary": intake["summary"],
        "questions": intake["questions"],
        "buckets": intake["buckets"],
        "scope": intake["scope"],
        "assumptions": intake["assumptions"],
        "decisions": intake["decisions"],
        "risks": intake["risks"],
    })
    state["current_intake"] = intake
    if intake["status"] == "needs_input":
        state["status"] = "needs_input"
        state["termination"] = "needs_input"
    else:
        review = run_clarification_review(state, intake, provider, timeout, worker)
        state["clarification_review"] = review
        if review["status"] == "failed":
            state["status"] = "failed"
            state["termination"] = "failed"
            state["last_error"] = "Independent clarification review has no attributable Agent evidence"
        elif review["status"] == "needs_input":
            # The independent reviewer owns this gate. Preserve its blockers in
            # the final turn so a resumed run asks the same unresolved branch.
            state["turns"][-1]["questions"] = review["questions"]
            state["turns"][-1]["buckets"]["must_answer_before_generation"] = review["blockers"] or review["questions"]
            state["status"] = "needs_input"
            state["termination"] = "needs_input"
        else:
            state["status"] = "awaiting_confirmation"
            state["termination"] = "human_checkpoint"
    return state


def write_discussion(folder: Path, state: dict[str, Any]) -> None:
    latest = state["turns"][-1]
    lines = ["# 需求讨论记录", "", "## 用户原始需求", state["raw_request"], "", "## 讨论结论", latest["summary"] or "（用户与 PM Copilot 已完成当前轮讨论）", "", "## 已明确范围"]
    scope = latest.get("scope", {})
    for label, key in (("目标", "goal"), ("用户", "users"), ("范围内", "in_scope"), ("范围外", "out_of_scope"), ("平台", "platform")):
        value = scope.get(key, "")
        if isinstance(value, list):
            value = "、".join(str(item) for item in value)
        lines.append(f"- {label}：{value or '未提供'}")
    lines += ["", "## 对话轮次"]
    for turn in state["turns"]:
        lines += [f"### 第 {turn['turn']} 轮", f"用户：{turn['user_text']}", f"PM Copilot：{turn['summary']}", ""]
    folder.joinpath("discussion.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def create_state(raw_request: str, folder: Path) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mode": "interactive",
        "folder": str(folder),
        "raw_request": raw_request,
        "status": "new",
        "termination": "running",
        "turns": [],
        "agent_calls": [],
        "artifacts": [],
        "user_confirmation": None,
        "revision_history": [],
    }


def begin_in_place_revision(state: dict[str, Any], request: str) -> dict[str, Any]:
    """Reopen one canonical PRD folder without creating a competing delivery."""
    if state.get("mode") != "interactive":
        raise ValueError("run folder is not an interactive production run")
    request = request.strip()
    if not request:
        raise ValueError("a revision request is required")
    folder = Path(str(state["folder"]))
    state.setdefault("revision_history", []).append({
        "at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "request": request,
        "prd_before_sha256": _artifact_digest(folder / "prd.md"),
        "html_before_sha256": _artifact_digest(folder / "prd.html"),
        "mode": "in_place_revision",
    })
    state["revision_request"] = request
    state["raw_request"] = request
    state["turns"] = []
    state["user_confirmation"] = None
    state["status"] = "new"
    state["termination"] = "running"
    state["artifacts"] = [item for item in state.get("artifacts", []) if item in {"prd.md", "prd.html", "run-log.yaml"}]
    return state


def _artifact_prompt(state: dict[str, Any], artifact: str, repair_errors: str = "") -> str:
    latest = state["turns"][-1]
    role = "Requirements" if artifact != "run-log.yaml" else "Orchestrator Trace"
    target = Path(state["folder"]) / artifact
    return f"""You are the accountable PM Copilot {role} Agent in a production interactive run.
The user explicitly confirmed the clarified requirements below. Use only this
conversation as product evidence; do not invent approvals, metrics, policy, or
regulated decisions. Write one complete artifact at {target}.
Do not modify any other file and do not return until the file exists.

Original request: {state['raw_request']}
Clarified scope: {json.dumps(latest.get('scope', {}), ensure_ascii=False)}
Discussion summary: {latest.get('summary', '')}
Assumptions: {json.dumps(latest.get('assumptions', []), ensure_ascii=False)}
Risks: {json.dumps(latest.get('risks', []), ensure_ascii=False)}

Artifact requirements:
- confirmed-requirements.md: facts, explicit user-confirmed scope, non-goals, success criteria, constraints, acceptance evidence, assumptions, risks, and unresolved items. Never call model inference user confirmation.
- prd.md: complete Chinese PRD with exact headings `## 一、文档说明`, `## 二、需求背景`, `## 四、需求清单`, `## 五、需求详情`; include detail IDs mapped one-to-one, and omit empty optional sections.
- run-log.yaml: use templates/agent-run-log-template.yaml, fill concrete fields, record this interactive user confirmation, real Agent calls, validation commands, separate PRD/engineering/launch readiness, and truthful termination state.
""" + (f"\nRepair these validator findings in this artifact only:\n{repair_errors}" if repair_errors else "")


def _run_artifact_agent(
    state: dict[str, Any], artifact: str, provider: str, timeout: int,
    worker: Callable[..., dict[str, Any]] = execute, repair_errors: str = "",
) -> bool:
    target = Path(state["folder"]) / artifact
    target.parent.mkdir(parents=True, exist_ok=True)
    real_folder = Path(state["folder"]).resolve()
    with tempfile.TemporaryDirectory(prefix=f".{real_folder.name}.stage-", dir=str(real_folder.parent)) as stage_name:
        stage_folder = Path(stage_name) / real_folder.name
        shutil.copytree(real_folder, stage_folder)
        stage_state = {**state, "folder": str(stage_folder)}
        stage_target = stage_folder / artifact
        result = worker(provider, _artifact_prompt(stage_state, artifact, repair_errors), ROOT, timeout, None, None, False, 8000)
        if result.get("status") == "complete" and stage_target.is_file() and stage_target.stat().st_size > 0:
            shutil.copy2(stage_target, target)
    result["isolated_workspace"] = True
    result["promoted_artifact"] = artifact if target.is_file() else None
    attributable = _record_agent_call(state, result, phase="delivery", artifact=artifact)
    if not attributable:
        state["last_error"] = f"{artifact} Agent call has no attributable provider/model evidence"
    return attributable and target.is_file() and target.stat().st_size > 0


def _artifact_review_prompt(state: dict[str, Any], artifact: str, review_path: Path) -> str:
    target = Path(state["folder"]) / artifact
    return f"""You are the independent Stage Quality Review Agent in a production PM run.
Read only {target}. Check whether this single artifact is complete, internally
consistent with the user-confirmed scope, and sufficient for its immediate
downstream consumer. Do not edit any file. Do not treat file existence or a
previous Agent's success as acceptance. Reject unsupported approvals, invented
facts, missing scope/non-goals/acceptance evidence, or an artifact that would
force the next stage to guess.

Write ONLY one JSON object to {review_path} (UTF-8):
{{"status":"pass"|"needs_revision","summary":"", "blocking_findings":["specific repair"], "acceptance_evidence":["checked condition"]}}
Use pass only when blocking_findings is empty and acceptance_evidence proves
the artifact's required handoff conditions. Empty proof is needs_revision.

Original request: {state['raw_request']}
Confirmed scope: {json.dumps(state['turns'][-1].get('scope', {}), ensure_ascii=False)}
Artifact under review: {artifact}
"""


def _review_artifact(
    state: dict[str, Any], artifact: str, provider: str, timeout: int,
    worker: Callable[..., dict[str, Any]] = execute,
) -> tuple[bool, str]:
    real_folder = Path(state["folder"]).resolve()
    with tempfile.TemporaryDirectory(prefix=f".{real_folder.name}.review-", dir=str(real_folder.parent)) as review_dir:
        review_folder = Path(review_dir) / real_folder.name
        shutil.copytree(real_folder, review_folder)
        review_path = review_folder / ".stage-review.json"
        result = worker(provider, _artifact_review_prompt({**state, "folder": str(review_folder)}, artifact, review_path), ROOT, timeout, None, None, False, 8000)
        review_text = review_path.read_text(encoding="utf-8") if review_path.is_file() else ""
    result["phase"] = "stage_quality_review"
    result["artifact"] = artifact
    attributable = _record_agent_call(state, result, phase="stage_quality_review", artifact=artifact)
    if not attributable:
        return False, "Stage Quality Review Agent call has no attributable provider/model evidence"
    if result.get("status") != "complete":
        return False, result.get("error", "Stage Quality Review Agent failed")
    try:
        review = _extract_json(review_text or result.get("output", ""))
    except (ValueError, json.JSONDecodeError) as error:
        return False, f"Stage Quality Review Agent returned invalid JSON: {error}"
    findings = review.get("blocking_findings", [])
    if not isinstance(findings, list):
        findings = [findings]
    findings = [str(item).strip() for item in findings if str(item).strip()]
    acceptance_evidence = review.get("acceptance_evidence", [])
    if not isinstance(acceptance_evidence, list):
        acceptance_evidence = [acceptance_evidence]
    acceptance_evidence = [str(item).strip() for item in acceptance_evidence if str(item).strip()]
    review_status = str(review.get("status", "")).strip().lower()
    if review_status == "needs_revision" and not findings:
        return False, "Stage Quality Review Agent returned needs_revision without specific blocking_findings"
    if review_status == "pass" and not acceptance_evidence:
        return False, "Stage Quality Review Agent returned pass without acceptance_evidence"
    passed = review_status == "pass" and not findings
    return passed, "\n".join(findings) or str(review.get("summary", "stage review rejected artifact"))


def _deliver_artifact_to_quality_gate(
    state: dict[str, Any], artifact: str, provider: str, timeout: int,
    worker: Callable[..., dict[str, Any]] = execute, max_revisions: int = DEFAULT_MAX_REVISIONS,
) -> bool:
    target = Path(state["folder"]) / artifact
    if not _run_artifact_agent(state, artifact, provider, timeout, worker):
        return False
    for revision in range(max_revisions + 1):
        passed, findings = _review_artifact(state, artifact, provider, timeout, worker)
        if passed:
            return True
        if revision >= max_revisions:
            state["revision_stop_reason"] = f"{artifact} stage quality budget exhausted"
            state["last_error"] = findings
            return False
        before = _artifact_digest(target)
        if not _run_artifact_agent(state, artifact, provider, timeout, worker, findings[-6000:]):
            state["revision_stop_reason"] = f"{artifact} stage quality repair failed"
            state["last_error"] = findings
            return False
        after = _artifact_digest(target)
        if before == after:
            _record_revision(state, artifact, before, after, "no_progress")
            state["revision_stop_reason"] = f"{artifact} stage quality repair made no artifact change"
            state["last_error"] = findings
            return False
        _record_revision(state, artifact, before, after, "changed")
        state["revision_loops"] = state.get("revision_loops", 0) + 1
    return False


def _validate_delivery(folder: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    commands = [
        [sys.executable, "scripts/render_prd_html.py", str(folder)],
        [sys.executable, "scripts/validate_outputs.py", str(folder), "--language", "zh"],
        [sys.executable, "scripts/validate_agent_trace.py", str(folder)],
        [sys.executable, "scripts/run_delivery_checks.py", str(folder), "--language", "zh"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        checks.append({
            "command": " ".join(command[1:]),
            "status": "passed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "stdout": result.stdout[-3000:],
            "stderr": result.stderr[-2000:],
        })
    return checks


def _confirmed_delivery(
    state: dict[str, Any], provider: str, timeout: int,
    worker: Callable[..., dict[str, Any]] = execute, max_revisions: int = DEFAULT_MAX_REVISIONS,
) -> None:
    confirmation = state.get("user_confirmation")
    if not isinstance(confirmation, dict) or confirmation.get("confirmed") is not True:
        state["status"] = "awaiting_confirmation"
        state["termination"] = "human_checkpoint"
        state["last_error"] = "Explicit user confirmation is required before delivery"
        return
    folder = Path(state["folder"])
    for artifact in ("confirmed-requirements.md", "prd.md", "run-log.yaml"):
        if not _deliver_artifact_to_quality_gate(state, artifact, provider, timeout, worker, max_revisions):
            state["status"] = "failed"
            state["termination"] = "failed"
            state.setdefault("last_error", f"delivery Agent failed to produce {artifact}")
            return
    all_checks: list[dict[str, Any]] = []
    final_checks: list[dict[str, Any]] = []
    for revision in range(max_revisions + 1):
        checks = _validate_delivery(folder)
        all_checks.extend(checks)
        final_checks = checks
        if all(check["status"] == "passed" for check in checks):
            break
        if revision >= max_revisions:
            state["revision_stop_reason"] = "validation budget exhausted"
            break
        trace_failed = any("validate_agent_trace.py" in check["command"] and check["status"] != "passed" for check in checks)
        artifact = "run-log.yaml" if trace_failed else "prd.md"
        errors = "\n\n".join(f"{check['command']}:\n{check.get('stdout', '')}\n{check.get('stderr', '')}" for check in checks if check["status"] != "passed")
        target = folder / artifact
        before = _artifact_digest(target)
        if not _run_artifact_agent(state, artifact, provider, timeout, worker, errors[-6000:]):
            state["revision_stop_reason"] = "repair Agent failed"
            break
        after = _artifact_digest(target)
        if before == after:
            _record_revision(state, artifact, before, after, "no_progress")
            state["revision_stop_reason"] = f"validation repair made no {artifact} change"
            break
        _record_revision(state, artifact, before, after, "changed")
        # A validator repair creates a new artifact version. The review that
        # accepted the prior bytes is no longer evidence for this version.
        passed, findings = _review_artifact(state, artifact, provider, timeout, worker)
        if not passed:
            state["revision_stop_reason"] = f"validation repair for {artifact} was rejected by stage quality review"
            state["last_error"] = findings
            break
        state["revision_loops"] = revision + 1
    state["validation"] = all_checks
    state["artifacts"] = ["discussion.md", "confirmed-requirements.md", "prd.md", "prd.html", "run-log.yaml"]
    if final_checks and all(check["status"] == "passed" for check in final_checks):
        evidence_ok, evidence_reason = _required_production_evidence(state)
        if evidence_ok:
            state["status"] = "complete"
            state["termination"] = "complete"
        else:
            state["status"] = "blocked"
            state["termination"] = "blocked"
            state["last_error"] = evidence_reason
    else:
        state["status"] = "failed"
        state["termination"] = "failed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", help="initial user request")
    parser.add_argument("--request-file")
    parser.add_argument("--run-folder", type=Path)
    parser.add_argument("--new-requirement", action="store_true", help="create one explicitly new independent requirement")
    parser.add_argument("--revise", action="store_true", help="revise the canonical PRD in --run-folder")
    parser.add_argument("--answers", help="the user's answer for the current needs_input state")
    parser.add_argument("--confirm", action="store_true", help="explicitly confirm the clarified scope")
    parser.add_argument("--provider", default="codex", help="Agent runtime; use seawork only when its remote model or scheduler is required")
    parser.add_argument("--timeout-minutes", type=int, default=DEFAULT_EXECUTION_TIMEOUT_MINUTES)
    parser.add_argument("--max-revisions", type=int, default=DEFAULT_MAX_REVISIONS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.timeout_minutes < 1:
        parser.error("--timeout-minutes must be at least 1")
    if args.max_revisions < 0:
        parser.error("--max-revisions cannot be negative")
    if args.request_file:
        raw_request = Path(args.request_file).expanduser().read_text(encoding="utf-8").strip()
    else:
        raw_request = (args.request or "").strip()
    if args.new_requirement and args.revise:
        parser.error("--new-requirement and --revise cannot be used together")
    if args.new_requirement and args.run_folder:
        parser.error("--new-requirement creates its own canonical folder; do not pass --run-folder")
    if args.revise and not args.run_folder:
        parser.error("--revise requires --run-folder for the canonical PRD")
    folder = args.run_folder
    if folder is None and raw_request and args.new_requirement:
        try:
            folder = new_requirement_folder(raw_request)
        except FileExistsError as error:
            parser.error(str(error))
    if folder is None:
        parser.error("provide --run-folder for an existing canonical PRD, or use --new-requirement for a new independent requirement")
    folder = folder.resolve()
    if args.new_requirement and folder.exists():
        parser.error(f"canonical PRD folder already exists: {folder}")
    if not args.new_requirement and not folder.exists():
        parser.error(f"canonical PRD folder not found: {folder}; only --new-requirement may create a PRD folder")
    if args.revise and not folder.is_dir():
        parser.error(f"canonical PRD folder not found: {folder}")
    folder.mkdir(parents=True, exist_ok=True)
    state_path = folder / "interactive-run.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else create_state(raw_request, folder)
    if state.get("mode") != "interactive":
        parser.error("run folder is not an interactive production run")
    if args.revise:
        if state.get("status") not in {"complete", "failed"}:
            parser.error("canonical PRD is already active; resume it without --revise")
        try:
            state = begin_in_place_revision(state, raw_request)
        except ValueError as error:
            parser.error(str(error))
    if args.dry_run:
        state["status"] = "planned"
        _write_json(state_path, state)
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0
    if state["status"] in {"new", "needs_input"}:
        if state["status"] == "needs_input" and not args.answers:
            print(json.dumps({"status": "needs_input", "questions": state["turns"][-1].get("questions", [])}, ensure_ascii=False, indent=2))
            return 3
        state = run_intake(state, args.provider, args.timeout_minutes, answers=args.answers)
        if state["status"] == "awaiting_confirmation":
            write_discussion(folder, state)
            state["artifacts"] = ["discussion.md"]
            print("需求已澄清，请检查 discussion.md；确认无误后使用 --confirm 进入 PRD 生成。")
        elif state["status"] == "needs_input":
            print(json.dumps({"status": "needs_input", "questions": state["turns"][-1]["questions"], "run_folder": str(folder)}, ensure_ascii=False, indent=2))
        _write_json(state_path, state)
        return 3 if state["status"] == "needs_input" else 0
    if state["status"] == "awaiting_confirmation":
        if not args.confirm:
            print("仍在等待用户明确确认；未生成 PRD。请使用 --confirm。")
            return 3
        state["user_confirmation"] = {"confirmed": True, "at": dt.datetime.now(dt.timezone.utc).isoformat(), "source": "explicit --confirm"}
        state["status"] = "confirmed"
        state["termination"] = "running"
        _confirmed_delivery(state, args.provider, args.timeout_minutes, max_revisions=args.max_revisions)
        _write_json(state_path, state)
        print(json.dumps({"status": state["status"], "run_folder": str(folder), "artifacts": state.get("artifacts", []), "validation": state.get("validation", [])}, ensure_ascii=False, indent=2))
        return 0 if state["status"] == "complete" else 1
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
