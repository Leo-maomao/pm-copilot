#!/usr/bin/env python3
"""Tests for the production interactive clarification gate."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from validate_agent_trace import validate_artifact_lineage
from run_interactive_request import (
    _active_runtime_version,
    _artifact_digest,
    _atomic_copy,
    _artifact_prompt,
    _confirmed_delivery,
    _confirmed_scope_fingerprint,
    _artifact_review_prompt,
    _confirmation_packet,
    _delivery_worker,
    _deliver_artifact_to_quality_gate,
    _delivery_input_problem,
    _discard_non_content_assets,
    _ensure_runtime_current,
    _finalize_deterministic_trace,
    _materialize_controller_trace,
    _materialize_revision_evidence,
    _materialize_revision_scope_manifest,
    _migrate_stale_internal_scope_clarification,
    _migrate_legacy_confirmed_revision_scope,
    _normalise_trace_runtime_evidence,
    _prepare_delivery_workspace,
    _promote_delivery_workspace,
    _rollback_delivery_promotion,
    _revision_scope_violation,
    _restart_delivery_attempt,
    _retry_failure_guard_decision,
    _recover_interrupted_delivery,
    _review_artifact,
    _retry_reuse_cache_folder,
    _snapshot_reusable_delivery_artifacts,
    _trace_lineage,
    _validate_staged_revision_scope,
    _write_json,
    _normalise_intake,
    _request_looks_like_extraction,
    _run_artifact_agent,
    apply_revision_requirement_ids,
    begin_in_place_revision,
    clarification_review_prompt,
    compact_requirement_numbers,
    create_state,
    main,
    new_requirement_folder,
    register_extraction_source,
    register_input_assets,
    register_implemented_feature_evidence,
    run_intake,
    write_discussion,
)


class InteractiveRequestTest(unittest.TestCase):
    def _eligible_retry_reuse_state(self, root: Path) -> tuple[dict[str, object], Path, Path]:
        canonical = root / "pm-copilot-outputs" / "example"
        workspace = canonical.parent / ".example.delivery-stage" / canonical.name
        canonical.mkdir(parents=True)
        workspace.mkdir(parents=True)
        artifacts = {
            "confirmed-requirements.md": "# Confirmed requirements\n",
            "prd.md": "# Staged PRD\n\n### 5.1 Staged requirement\n",
            "prd.html": "<!doctype html><html><body>staged</body></html>\n",
            "run-log.yaml": "unverified: trace\n",
        }
        for name, content in artifacts.items():
            (workspace / name).write_text(content, encoding="utf-8")
        state = create_state("Create a reusable PRD", canonical)
        state["confirmed_fact_packet"] = {
            "summary": "Confirmed scope", "scope": {"goal": "Reusable delivery", "in_scope": ["5.1"]},
            "assumptions": [], "risks": [],
        }
        state["delivery_workspace"] = str(workspace)
        fingerprint = _confirmed_scope_fingerprint(state)
        version = _active_runtime_version()
        stages: dict[str, dict[str, object]] = {}
        for artifact in ("confirmed-requirements.md", "prd.md"):
            digest = hashlib.sha256((workspace / artifact).read_bytes()).hexdigest()
            stages[artifact] = {
                "artifact_status": "promoted",
                "review_status": "passed",
                "artifact_sha256": digest,
                "reviewed_sha256": digest,
                "scope_fingerprint": fingerprint,
                "pm_copilot_version": version,
            }
        state["delivery_stages"] = stages
        return state, canonical, workspace

    def _in_place_review_state(self, root: Path) -> tuple[dict[str, object], Path, Path]:
        """Build a selected-section revision with an attested baseline asset."""
        canonical = root / "canonical"
        assets = canonical / "assets"
        assets.mkdir(parents=True)
        (assets / "selected.png").write_bytes(b"selected image")
        baseline = (
            "| 5.1 | Selected behavior |\n| 5.2 | Protected behavior |\n\n"
            "### 5.1 Selected behavior\n"
            "Selected exact copy remains visible.\n"
            "[[prd-detail-media src=\"./assets/selected.png\" alt=\"selected\" copy=\"Selected exact copy\"]]\n\n"
            "### 5.2 Protected behavior\n"
            "Protected exact copy remains visible.\n"
        )
        html = "<html><body>baseline</body></html>\n"
        (canonical / "prd.md").write_text(baseline, encoding="utf-8")
        (canonical / "prd.html").write_text(html, encoding="utf-8")
        state = create_state("仅更新 5.1", canonical)
        state.update({
            "delivery_variant": "in_place_revision",
            "revision_requirement_ids": ["5.1"],
            "revision_history": [{
                "mode": "in_place_revision",
                "request": "仅更新 5.1",
                "prd_before_sha256": hashlib.sha256(baseline.encode("utf-8")).hexdigest(),
                "html_before_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
                "baseline_requirement_ids": ["5.1", "5.2"],
            }],
            "confirmed_fact_packet": {
                "summary": "仅更新 5.1", "scope": {"goal": "仅更新 5.1", "in_scope": ["5.1"]},
                "assumptions": [], "decisions": [], "risks": [],
            },
            "user_confirmation": {"confirmed": True, "source": "test"},
        })
        _materialize_revision_scope_manifest(state)
        workspace = _prepare_delivery_workspace(state)
        state["delivery_stages"] = {"prd.md": {"artifact_status": "promoted"}}
        return state, canonical, workspace

    def test_global_runtime_sync_restarts_the_controller_before_argument_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime_root = Path(temporary)
            (runtime_root / "install-state.json").write_text("{}", encoding="utf-8")
            with patch("run_interactive_request.ROOT", runtime_root), patch(
                "run_interactive_request.ensure_current", return_value={"status": "synced"},
            ), patch("run_interactive_request.os.execv") as execute, patch.object(
                sys, "argv", ["run_interactive_request.py", "--confirm"],
            ):
                _ensure_runtime_current()
        self.assertEqual(execute.call_args.args[0], sys.executable)
        self.assertEqual(execute.call_args.args[1][1:], [str(Path(__file__).resolve().with_name("run_interactive_request.py")), "--confirm"])

    def test_delivery_workspace_drops_metadata_without_mutating_canonical_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "example"
            assets = canonical / "assets"
            assets.mkdir(parents=True)
            (canonical / "prd.md").write_text("# Existing PRD\n", encoding="utf-8")
            (assets / "visible.png").write_bytes(b"visible")
            (assets / ".DS_Store").write_bytes(b"finder")
            (assets / ".private.png").write_bytes(b"hidden")
            (assets / "Thumbs.db").write_bytes(b"explorer")
            state = create_state("更新 PRD", canonical)

            workspace = _prepare_delivery_workspace(state)

            self.assertTrue((canonical / "assets" / ".DS_Store").is_file())
            self.assertTrue((canonical / "assets" / ".private.png").is_file())
            self.assertTrue((workspace / "assets" / "visible.png").is_file())
            self.assertFalse((workspace / "assets" / ".DS_Store").exists())
            self.assertFalse((workspace / "assets" / ".private.png").exists())
            self.assertFalse((workspace / "assets" / "Thumbs.db").exists())

    def test_writer_cannot_mutate_real_delivery_assets_outside_its_stage(self) -> None:
        """A staged PRD may promote, but direct writes to the real tree must not."""
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "delivery"
            assets = workspace / "assets"
            assets.mkdir(parents=True)
            baseline_prd = "# Baseline PRD\n\n### 5.1 Existing requirement\nOld rule.\n"
            baseline_asset = b"baseline image bytes"
            (workspace / "prd.md").write_text(baseline_prd, encoding="utf-8")
            (assets / "image.png").write_bytes(baseline_asset)
            state = create_state("更新现有 PRD", workspace)
            state.update({
                "delivery_workspace": str(workspace),
                "turns": [{
                    "summary": "已确认更新范围",
                    "scope": {"goal": "更新 5.1"},
                    "assumptions": [],
                    "risks": [],
                }],
            })

            def writer(provider, prompt, cwd, *args):
                target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
                self.assertEqual(target, cwd / "prd.md")
                target.write_text(
                    "# Updated PRD\n\n### 5.1 Existing requirement\nUpdated rule.\n",
                    encoding="utf-8",
                )
                # Simulate a worker which knows the real path and ignores its
                # working-directory boundary while completing the staged write.
                (assets / "image.png").write_bytes(b"mutated outside stage")
                return {
                    "provider": provider,
                    "model": "test",
                    "status": "complete",
                    "output": "staged artifact written",
                    "error": "",
                }

            self.assertTrue(_run_artifact_agent(state, "prd.md", "test", 1, worker=writer))

            self.assertIn("Updated rule.", (workspace / "prd.md").read_text(encoding="utf-8"))
            self.assertEqual((assets / "image.png").read_bytes(), baseline_asset)
            self.assertEqual(state["delivery_stages"]["prd.md"]["artifact_status"], "promoted")

    def test_reviewer_cannot_mutate_real_delivery_artifact_outside_review_workspace(self) -> None:
        """Review output is useful only when the real delivery tree is restored first."""
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "delivery"
            workspace.mkdir()
            baseline_prd = "# Baseline PRD\n\n### 5.1 Existing requirement\nBaseline rule.\n"
            (workspace / "prd.md").write_text(baseline_prd, encoding="utf-8")
            state = create_state("审查现有 PRD", workspace)
            state.update({
                "delivery_workspace": str(workspace),
                "turns": [{
                    "summary": "已确认审查范围",
                    "scope": {"goal": "审查 5.1"},
                    "assumptions": [],
                    "risks": [],
                }],
            })

            def reviewer(provider, prompt, cwd, *args):
                review_path = Path(prompt.split("Write ONLY one JSON object to ", 1)[1].split(" (UTF-8):", 1)[0])
                self.assertEqual(review_path, cwd / ".stage-review.json")
                review_path.write_text(
                    json.dumps({
                        "status": "pass",
                        "summary": "reviewed staged copy",
                        "blocking_findings": [],
                        "acceptance_evidence": ["5.1 staged copy reviewed"],
                    }),
                    encoding="utf-8",
                )
                (workspace / "prd.md").write_text("# Mutated outside review workspace\n", encoding="utf-8")
                return {
                    "provider": provider,
                    "model": "test",
                    "status": "complete",
                    "output": "review written",
                    "error": "",
                }

            passed, _ = _review_artifact(state, "prd.md", "test", 1, worker=reviewer)

            self.assertTrue(passed)
            self.assertEqual((workspace / "prd.md").read_text(encoding="utf-8"), baseline_prd)
            self.assertEqual(state["delivery_stages"]["prd.md"]["review_status"], "passed")

    def test_reviewer_cannot_accept_a_stale_review_file_from_real_delivery_workspace(self) -> None:
        """Every review attempt needs a response written after that attempt starts."""
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "delivery"
            workspace.mkdir()
            (workspace / "prd.md").write_text(
                "# Baseline PRD\n\n### 5.1 Existing requirement\nBaseline rule.\n",
                encoding="utf-8",
            )
            stale_review = {
                "status": "pass",
                "summary": "old pass which must not be reused",
                "blocking_findings": [],
                "acceptance_evidence": ["old review evidence"],
            }
            (workspace / ".stage-review.json").write_text(json.dumps(stale_review), encoding="utf-8")
            state = create_state("审查现有 PRD", workspace)
            state.update({
                "delivery_workspace": str(workspace),
                "turns": [{
                    "summary": "已确认审查范围",
                    "scope": {"goal": "审查 5.1"},
                    "assumptions": [],
                    "risks": [],
                }],
            })

            def reviewer(provider, prompt, cwd, *args):
                # The Agent call itself completed, but it did not produce a
                # response for this particular review attempt.
                self.assertEqual(cwd / ".stage-review.json", Path(
                    prompt.split("Write ONLY one JSON object to ", 1)[1].split(" (UTF-8):", 1)[0],
                ))
                return {
                    "provider": provider,
                    "model": "test",
                    "status": "complete",
                    "output": "",
                    "error": "",
                }

            passed, _ = _review_artifact(state, "prd.md", "test", 1, worker=reviewer)

            self.assertFalse(passed)
            self.assertEqual(state["delivery_stages"]["prd.md"]["review_status"], "failed")

    def test_in_place_scope_ignores_metadata_omitted_from_the_staged_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "example"
            assets = canonical / "assets"
            assets.mkdir(parents=True)
            baseline = "| 5.1 | Result |\n\n### 5.1 Result\nExisting rule.\n"
            html = "<html>baseline</html>\n"
            (canonical / "prd.md").write_text(baseline, encoding="utf-8")
            (canonical / "prd.html").write_text(html, encoding="utf-8")
            (assets / "result.png").write_bytes(b"content")
            (assets / ".DS_Store").write_bytes(b"finder")
            state = create_state("仅更新 5.1", canonical)
            state.update({
                "delivery_variant": "in_place_revision",
                "revision_requirement_ids": ["5.1"],
                "revision_history": [{
                    "mode": "in_place_revision",
                    "request": "仅更新 5.1",
                    "prd_before_sha256": hashlib.sha256(baseline.encode("utf-8")).hexdigest(),
                    "html_before_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
                }],
                "confirmed_fact_packet": {
                    "scope": {"goal": "仅更新 5.1"},
                    "decisions": [], "assumptions": [], "risks": [],
                },
            })

            manifest = _materialize_revision_scope_manifest(state)
            workspace = _prepare_delivery_workspace(state)
            report = _validate_staged_revision_scope(state, workspace)

            self.assertEqual(set(manifest["baseline"]["assets"]), {"assets/result.png"})
            self.assertEqual(report["status"], "passed")
            self.assertFalse((workspace / "assets" / ".DS_Store").exists())

    def test_non_content_asset_cleanup_keeps_only_deliverable_asset_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            assets = folder / "assets"
            (assets / ".finder").mkdir(parents=True)
            (assets / ".finder" / "nested.png").write_bytes(b"metadata")
            (assets / "visible.png").write_bytes(b"visible")
            (assets / "desktop.ini").write_bytes(b"explorer")

            discarded = _discard_non_content_assets(folder)

            self.assertEqual(discarded, [".finder", ".finder/nested.png", "desktop.ini"])
            self.assertTrue((assets / "visible.png").is_file())
            self.assertFalse((assets / ".finder").exists())
            self.assertFalse((assets / "desktop.ini").exists())

    def test_nonblocking_questions_do_not_hold_the_clarification_gate(self) -> None:
        intake = _normalise_intake({
            "status": "needs_input",
            "questions": ["请确认由谁负责 PRD 验收"],
            "buckets": {
                "must_answer_before_generation": [],
                "must_confirm_before_development_or_launch": ["上线确认"],
            },
        })
        self.assertEqual(intake["status"], "complete")
        self.assertEqual(intake["questions"], [])

    def test_compact_requirement_numbers_updates_all_references(self) -> None:
        source = "| 5.1 | A |\n| 5.3 | C |\n### 5.1 A\n### 5.3 C\n目标 5.3"
        result = compact_requirement_numbers(source)
        self.assertIn("| 5.2 | C |", result)
        self.assertIn("### 5.2 C", result)
        self.assertIn("目标 5.2", result)
    def test_new_requirement_folder_never_allocates_a_suffixed_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = new_requirement_folder("团队权限", root)
            expected_date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
            self.assertEqual(folder.name, f"interactive-request-{expected_date}")
            folder.mkdir()
            with self.assertRaises(FileExistsError):
                new_requirement_folder("团队权限", root)
            self.assertFalse((root / f"{folder.name}-2").exists())

    def test_extraction_intent_recognizes_new_prd_requests_in_english_and_chinese(self) -> None:
        extraction_requests = (
            "Extract requirements 5.3 through 5.10 from the existing PRD into a new independent PRD.",
            "Create a standalone PRD from a section of the legacy product requirements document.",
            "将已有 PRD 中的画布优化章节拆分为一份新的独立 PRD。",
            "把旧的部分内容提取到新的 PRD 下。",
            "把旧 PRD 的结算内容单独整理成一份新需求文档。",
        )
        for request in extraction_requests:
            with self.subTest(request=request):
                self.assertTrue(_request_looks_like_extraction(request))

        for request in (
            "Update requirement 5.3 in the existing PRD.",
            "为一个全新的画布能力创建 PRD。",
        ):
            with self.subTest(request=request):
                self.assertFalse(_request_looks_like_extraction(request))

    def test_revision_reopens_the_same_canonical_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prd.md").write_text("before", encoding="utf-8")
            (folder / "prd.html").write_text("before", encoding="utf-8")
            state = create_state("原需求", folder)
            state.update({"status": "complete", "artifacts": ["prd.md", "prd.html", "run-log.yaml"]})
            revised = begin_in_place_revision(state, "新增一个状态规则")
            self.assertEqual(revised["folder"], str(folder))
            self.assertEqual(revised["status"], "new")
            self.assertEqual(revised["revision_history"][-1]["mode"], "in_place_revision")
            self.assertEqual(revised["revision_history"][-1]["prd_before_sha256"], hashlib.sha256(b"before").hexdigest())

    def test_revision_id_extraction_ignores_css_decimal_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prd.md").write_text(
                "| 5.1 | 状态提示 |\n### 5.1 状态提示\n颜色 rgba(0, 0, 0, 0.12)，位置 13.97px\n",
                encoding="utf-8",
            )
            state = create_state("原需求", folder)
            revised = begin_in_place_revision(state, "修改需求 5.1 的状态提示，保留 rgba(0, 0, 0, 0.12) 和 13.97px")
            self.assertEqual(revised["revision_requirement_ids"], ["5.1"])

    def test_revision_never_reuses_scope_ids_from_a_prior_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prd.md").write_text(
                "| 5.1 | 状态提示 |\n| 5.2 | 其他能力 |\n### 5.1 状态提示\n### 5.2 其他能力\n",
                encoding="utf-8",
            )
            (folder / "prd.html").write_text("<html></html>\n", encoding="utf-8")
            (folder / "run-log.yaml").write_text(
                "artifact_lineage:\n  mode: in_place_revision\n  revised_requirement_ids:\n    - '5.1'\n",
                encoding="utf-8",
            )
            state = create_state("原需求", folder)
            state["status"] = "complete"
            revised = begin_in_place_revision(state, "更新 PRD 的错误文案")
            self.assertEqual(revised["revision_requirement_ids"], [])
            revised["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            revised["user_confirmation"] = {"confirmed": True, "source": "test"}

            _confirmed_delivery(
                revised,
                "test",
                1,
                worker=lambda *args: self.fail("ambiguous revision must not dispatch an Agent"),
            )

            self.assertEqual(revised["status"], "needs_input")
            self.assertEqual(revised["required_input"]["field"], "revision_selector")
            self.assertEqual(revised["agent_calls"], [])

    def test_new_delivery_ignores_retained_revision_history_for_staging_and_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            canonical = Path(temporary) / "canonical"
            canonical.mkdir()
            (canonical / "prd.md").write_text("# Previous PRD\n", encoding="utf-8")
            (canonical / "prd.html").write_text("<html>previous</html>\n", encoding="utf-8")
            (canonical / "revision-evidence.json").write_text(
                '{"scope_validation":{"report_path":"tool-results/missing.json"}}\n',
                encoding="utf-8",
            )
            state = create_state("创建新的需求文档", canonical)
            state.update({
                "revision_history": [{
                    "mode": "in_place_revision",
                    "request": "旧的 5.1 修订",
                    "prd_before_sha256": _artifact_digest(canonical / "prd.md"),
                    "html_before_sha256": _artifact_digest(canonical / "prd.html"),
                }],
                "turns": [{
                    "summary": "已确认新需求", "scope": {"goal": "创建新 PRD", "in_scope": ["新需求"]},
                    "assumptions": [], "risks": [], "buckets": {},
                }],
                "user_confirmation": {"confirmed": True, "source": "test"},
            })
            state.pop("delivery_variant")
            workspace = _prepare_delivery_workspace(state)
            self.assertFalse((workspace / ".revision-baseline").exists())
            self.assertFalse((workspace / "revision-evidence.json").exists())

            def worker(provider, prompt, cwd, *args):
                target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
                target.write_text("# New PRD\n", encoding="utf-8")
                return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}

            self.assertTrue(_run_artifact_agent(state, "prd.md", "test", 1, worker=worker))
            self.assertTrue(_run_artifact_agent(state, "run-log.yaml", "test", 1, worker=worker))
            self.assertFalse((workspace / "revision-evidence.json").exists())

    def test_revision_source_drift_pauses_before_staging_or_agent_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            original_prd = "| 5.1 | 状态提示 |\n### 5.1 状态提示\n"
            original_html = "<html>before</html>\n"
            (folder / "prd.md").write_text(original_prd, encoding="utf-8")
            (folder / "prd.html").write_text(original_html, encoding="utf-8")
            state = create_state("原需求", folder)
            state["status"] = "complete"
            revised = begin_in_place_revision(state, "修改需求 5.1 的状态提示")
            (folder / "prd.md").write_text("| 5.1 | 被其他人更新 |\n### 5.1 被其他人更新\n", encoding="utf-8")
            revised["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            revised["user_confirmation"] = {"confirmed": True, "source": "test"}

            _confirmed_delivery(
                revised,
                "test",
                1,
                worker=lambda *args: self.fail("source drift must stop before Agent dispatch"),
            )

            self.assertEqual(revised["status"], "needs_input")
            self.assertEqual(revised["required_input"]["field"], "revision_source_drift")
            self.assertEqual(revised["agent_calls"], [])
            self.assertIn("被其他人更新", (folder / "prd.md").read_text(encoding="utf-8"))

    def test_explicit_revision_selector_rejects_unknown_requirement_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prd.md").write_text("| 5.1 | 状态提示 |\n### 5.1 状态提示\n", encoding="utf-8")
            state = create_state("原需求", folder)
            with self.assertRaisesRegex(ValueError, "not present in the canonical PRD"):
                apply_revision_requirement_ids(state, ["5.9"])

    def test_implemented_evidence_file_sets_implemented_feature_mode(self) -> None:
        evidence = {
            "branch_name": "feature/canvas",
            "diff_commands": ["git diff --stat"],
            "changed_files": ["src/canvas.ts"],
            "behavior_evidence": [{"evidence_id": "behavior-1", "observed_behavior": "Canvas saves drafts"}],
            "validation_evidence": [{"command": "pnpm test", "status": "passed"}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = folder / "implemented-evidence.json"
            source.write_text(json.dumps(evidence), encoding="utf-8")
            state = create_state("为已实现功能生成 PRD", folder)
            register_implemented_feature_evidence(state, source)
            self.assertEqual(state["task_mode"], "implemented_feature_prd")
            self.assertEqual(state["delivery_variant"], "new")
            self.assertEqual(state["context_source"]["mode"], "repo-backed")
            self.assertEqual(state["implemented_feature_evidence"], evidence)
            self.assertEqual(
                state["implemented_feature_evidence_source"]["sha256"],
                hashlib.sha256(source.read_bytes()).hexdigest(),
            )
            packet = folder / "source-material" / "implemented-feature-evidence.json"
            self.assertEqual(json.loads(packet.read_text(encoding="utf-8")), evidence)
            self.assertEqual(
                state["implemented_feature_evidence_source"]["packet_path"],
                "source-material/implemented-feature-evidence.json",
            )
            self.assertEqual(
                state["implemented_feature_evidence_source"]["packet_sha256"],
                hashlib.sha256(packet.read_bytes()).hexdigest(),
            )

    def test_implemented_evidence_packages_local_result_references(self) -> None:
        evidence = {
            "branch_name": "feature/canvas",
            "diff_commands": ["git diff --stat"],
            "changed_files": ["src/canvas.ts"],
            "behavior_evidence": [{"evidence_id": "behavior-1", "observed_behavior": "Canvas saves drafts"}],
            "validation_evidence": [{"command": "pnpm test", "status": "passed"}],
            "visual_runtime_capability": {
                "runtime_discovery": [{
                    "capability": "existing_preview_discovery",
                    "result_ref": "tool-results/discovery.json",
                }],
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "evidence-bundle"
            result = bundle / "tool-results" / "discovery.json"
            result.parent.mkdir(parents=True)
            result.write_text('{"preview":"not found"}\n', encoding="utf-8")
            source = bundle / "implemented-evidence.json"
            source.write_text(json.dumps(evidence), encoding="utf-8")
            folder = root / "canonical"
            folder.mkdir()
            state = create_state("为已实现功能生成 PRD", folder)

            register_implemented_feature_evidence(state, source)

            imported = "tool-results/implemented-evidence/tool-results/discovery.json"
            self.assertEqual(
                state["implemented_feature_evidence"]["visual_runtime_capability"]["runtime_discovery"][0]["result_ref"],
                imported,
            )
            self.assertEqual(
                (folder / imported).read_text(encoding="utf-8"),
                '{"preview":"not found"}\n',
            )
            self.assertEqual(state["implemented_feature_evidence_source"]["imported_result_refs"], [imported])

    def test_implemented_evidence_packet_is_copied_to_staging_and_bounds_the_prd_prompt(self) -> None:
        evidence = {
            "branch_name": "feature/canvas",
            "diff_commands": ["git diff --stat"],
            "changed_files": ["src/canvas.ts"],
            "behavior_evidence": [{"evidence_id": "behavior-1", "observed_behavior": "Canvas saves drafts"}],
            "validation_evidence": [{"command": "pnpm test", "status": "passed"}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "evidence-bundle" / "implemented-evidence.json"
            source.parent.mkdir()
            source.write_text(json.dumps(evidence), encoding="utf-8")
            folder = root / "canonical"
            folder.mkdir()
            state = create_state("为已实现功能生成 PRD", folder)
            state["turns"] = [{
                "summary": "已确认", "scope": {"goal": "还原已实现功能", "in_scope": ["画布保存"]},
                "assumptions": [], "risks": [], "buckets": {},
            }]
            register_implemented_feature_evidence(state, source)

            workspace = _prepare_delivery_workspace(state)
            packet_relative = "source-material/implemented-feature-evidence.json"
            staged_packet = workspace / packet_relative
            self.assertTrue(staged_packet.is_file())
            self.assertEqual(json.loads(staged_packet.read_text(encoding="utf-8")), evidence)
            self.assertEqual(
                hashlib.sha256(staged_packet.read_bytes()).hexdigest(),
                state["implemented_feature_evidence_source"]["packet_sha256"],
            )

            prompt = _artifact_prompt(state, "prd.md")
            self.assertIn(packet_relative, prompt)
            self.assertIn("Use only that packet as observed implementation", prompt)
            self.assertIn("do not inspect repository files", prompt)

    def test_implemented_evidence_packet_hash_mismatch_stops_before_a_writer_runs(self) -> None:
        evidence = {
            "branch_name": "feature/canvas",
            "diff_commands": ["git diff --stat"],
            "changed_files": ["src/canvas.ts"],
            "behavior_evidence": [{"evidence_id": "behavior-1", "observed_behavior": "Canvas saves drafts"}],
            "validation_evidence": [{"command": "pnpm test", "status": "passed"}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = folder / "input.json"
            source.write_text(json.dumps(evidence), encoding="utf-8")
            state = create_state("为已实现功能生成 PRD", folder)
            state["turns"] = [{
                "summary": "已确认", "scope": {"goal": "还原已实现功能", "in_scope": ["画布保存"]},
                "assumptions": [], "risks": [], "buckets": {},
            }]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            register_implemented_feature_evidence(state, source)
            (folder / "source-material" / "implemented-feature-evidence.json").write_text(
                "{}\n", encoding="utf-8",
            )
            worker_called = False

            def worker(*args, **kwargs):
                nonlocal worker_called
                worker_called = True
                self.fail("a changed implementation-evidence packet must stop before delivery")

            _confirmed_delivery(state, "codex", 1, worker=worker)

            self.assertFalse(worker_called)
            self.assertEqual(state["status"], "needs_input")
            self.assertEqual(state["required_input"]["field"], "implementation_evidence")
            self.assertIn("哈希不一致", state["last_error"])

    def test_implemented_evidence_missing_imported_result_stops_before_a_writer_runs(self) -> None:
        evidence = {
            "branch_name": "feature/canvas",
            "diff_commands": ["git diff --stat"],
            "changed_files": ["src/canvas.ts"],
            "behavior_evidence": [{"evidence_id": "behavior-1", "observed_behavior": "Canvas saves drafts"}],
            "validation_evidence": [{"command": "pnpm test", "status": "passed"}],
            "visual_runtime_capability": {
                "runtime_discovery": [{"result_ref": "tool-results/discovery.json"}],
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "evidence-bundle" / "implemented-evidence.json"
            result = source.parent / "tool-results" / "discovery.json"
            result.parent.mkdir(parents=True)
            result.write_text('{"preview":"not found"}\n', encoding="utf-8")
            source.write_text(json.dumps(evidence), encoding="utf-8")
            folder = root / "canonical"
            folder.mkdir()
            state = create_state("为已实现功能生成 PRD", folder)
            state["turns"] = [{
                "summary": "已确认", "scope": {"goal": "还原已实现功能", "in_scope": ["画布保存"]},
                "assumptions": [], "risks": [], "buckets": {},
            }]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            register_implemented_feature_evidence(state, source)
            imported = folder / "tool-results" / "implemented-evidence" / "tool-results" / "discovery.json"
            imported.unlink()
            worker_called = False

            def worker(*args, **kwargs):
                nonlocal worker_called
                worker_called = True
                self.fail("a missing imported result_ref must stop before delivery")

            _confirmed_delivery(state, "codex", 1, worker=worker)

            self.assertFalse(worker_called)
            self.assertEqual(state["status"], "needs_input")
            self.assertEqual(state["required_input"]["field"], "implementation_evidence")
            self.assertIn("结果文件不存在", state["last_error"])

    def test_controller_trace_records_the_canonical_implemented_evidence_packet(self) -> None:
        evidence = {
            "branch_name": "feature/canvas",
            "diff_commands": ["git diff --stat"],
            "changed_files": ["src/canvas.ts"],
            "behavior_evidence": [{"evidence_id": "behavior-1", "observed_behavior": "Canvas saves drafts"}],
            "validation_evidence": [{"command": "pnpm test", "status": "passed"}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = folder / "input.json"
            source.write_text(json.dumps(evidence), encoding="utf-8")
            (folder / "prd.md").write_text("# 已实现功能\n\n### 5.1 保存草稿\n", encoding="utf-8")
            state = create_state("为已实现功能生成 PRD", folder)
            state["turns"] = [{
                "summary": "已确认", "scope": {"goal": "还原已实现功能", "in_scope": ["画布保存"]},
                "assumptions": [], "risks": [], "buckets": {},
            }]
            register_implemented_feature_evidence(state, source)

            self.assertTrue(_run_artifact_agent(state, "run-log.yaml", "codex", 1))

            trace = yaml.safe_load((folder / "run-log.yaml").read_text(encoding="utf-8"))
            packet = trace["implemented_feature_prd"]["evidence_packet"]
            self.assertEqual(packet["path"], "source-material/implemented-feature-evidence.json")
            self.assertEqual(packet["sha256"], state["implemented_feature_evidence_source"]["packet_sha256"])
            self.assertIn(packet["path"], trace["context"]["files_loaded"])

    def test_implemented_evidence_rejects_result_references_outside_its_bundle(self) -> None:
        evidence = {
            "branch_name": "feature/canvas",
            "diff_commands": ["git diff --stat"],
            "changed_files": ["src/canvas.ts"],
            "behavior_evidence": [{"evidence_id": "behavior-1", "observed_behavior": "Canvas saves drafts"}],
            "validation_evidence": [{"command": "pnpm test", "status": "passed"}],
            "visual_capture_recovery": [{"result_ref": "../unrelated.json"}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "evidence-bundle"
            bundle.mkdir()
            (root / "unrelated.json").write_text('{"private":"do not import"}\n', encoding="utf-8")
            source = bundle / "implemented-evidence.json"
            source.write_text(json.dumps(evidence), encoding="utf-8")
            folder = root / "canonical"
            folder.mkdir()
            state = create_state("为已实现功能生成 PRD", folder)

            with self.assertRaisesRegex(ValueError, "must stay inside the evidence bundle"):
                register_implemented_feature_evidence(state, source)

            self.assertNotIn("implemented_feature_evidence", state)
            self.assertFalse((folder / "tool-results").exists())

    def test_cli_extraction_source_recovers_confirmed_needs_input_to_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "extraction-run"
            folder.mkdir()
            source = Path(temporary) / "legacy-prd.md"
            source.write_text("# 旧 PRD\n\n### 5.7 结算流程\n", encoding="utf-8")
            state = create_state("从旧 PRD 提取结算流程，形成独立 PRD", folder)
            turn = {
                "turn": 1, "user_text": state["raw_request"], "summary": "已确认提取结算流程",
                "scope": {"goal": "提取结算流程", "in_scope": ["5.7 结算流程"]},
                "assumptions": [], "decisions": [], "risks": [], "buckets": {},
            }
            state.update({
                "status": "needs_input", "termination": "needs_input", "turns": [turn],
                "confirmed_fact_packet": json.loads(json.dumps(turn)),
                "user_confirmation": {"confirmed": True, "source": "test"},
                "required_input": {"field": "extraction_source", "question": "请提供旧 PRD", "reason": "missing source"},
            })
            _write_json(folder / "interactive-run.json", state)
            with patch("run_interactive_request._ensure_runtime_current"), patch.object(
                sys, "argv", [
                    "run_interactive_request.py", "--run-folder", str(folder), "--extract-from", str(source),
                ],
            ), patch("builtins.print"):
                self.assertEqual(main(), 3)
            resumed = json.loads((folder / "interactive-run.json").read_text(encoding="utf-8"))
            self.assertEqual(resumed["status"], "awaiting_confirmation")
            self.assertEqual(resumed["termination"], "human_checkpoint")
            self.assertEqual(resumed["extraction_source"]["display_name"], "legacy-prd.md")
            self.assertTrue((folder / "source-material" / "source-prd.md").is_file())

    def test_cli_implemented_evidence_recovers_confirmed_needs_input_to_confirmation(self) -> None:
        evidence = {
            "branch_name": "feature/canvas",
            "diff_commands": ["git diff --stat"],
            "changed_files": ["src/canvas.ts"],
            "behavior_evidence": [{"evidence_id": "behavior-1", "observed_behavior": "Canvas saves drafts"}],
            "validation_evidence": [{"command": "pnpm test", "status": "passed"}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "implemented-run"
            folder.mkdir()
            source = Path(temporary) / "implemented-evidence.json"
            source.write_text(json.dumps(evidence), encoding="utf-8")
            state = create_state("为已实现功能生成 PRD", folder)
            turn = {
                "turn": 1, "user_text": state["raw_request"], "summary": "已确认功能范围",
                "scope": {"goal": "还原已实现功能", "in_scope": ["画布保存"]},
                "assumptions": [], "decisions": [], "risks": [], "buckets": {},
            }
            state.update({
                "task_mode": "implemented_feature_prd",
                "context_source": {"mode": "repo-backed", "files_loaded": []},
                "status": "needs_input", "termination": "needs_input", "turns": [turn],
                "confirmed_fact_packet": json.loads(json.dumps(turn)),
                "user_confirmation": {"confirmed": True, "source": "test"},
                "required_input": {"field": "implementation_evidence", "question": "请提供实施证据", "reason": "missing evidence"},
            })
            _write_json(folder / "interactive-run.json", state)
            with patch("run_interactive_request._ensure_runtime_current"), patch.object(
                sys, "argv", [
                    "run_interactive_request.py", "--run-folder", str(folder), "--implemented-evidence", str(source),
                ],
            ), patch("builtins.print"):
                self.assertEqual(main(), 3)
            resumed = json.loads((folder / "interactive-run.json").read_text(encoding="utf-8"))
            self.assertEqual(resumed["status"], "awaiting_confirmation")
            self.assertEqual(resumed["implemented_feature_evidence"], evidence)
            self.assertEqual(resumed["context_source"]["mode"], "repo-backed")

    def test_cli_revision_selector_recovers_confirmed_needs_input_to_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "revision-run"
            folder.mkdir()
            (folder / "prd.md").write_text("| 5.1 | 状态提示 |\n### 5.1 状态提示\n", encoding="utf-8")
            state = create_state("更新现有 PRD", folder)
            turn = {
                "turn": 1, "user_text": state["raw_request"], "summary": "已确认需要修订",
                "scope": {"goal": "更新状态提示", "in_scope": ["状态提示"]},
                "assumptions": [], "decisions": [], "risks": [], "buckets": {},
            }
            state.update({
                "delivery_variant": "in_place_revision",
                "revision_history": [{"request": state["raw_request"], "mode": "in_place_revision"}],
                "status": "needs_input", "termination": "needs_input", "turns": [turn],
                "confirmed_fact_packet": json.loads(json.dumps(turn)),
                "user_confirmation": {"confirmed": True, "source": "test"},
                "required_input": {"field": "revision_selector", "question": "请指定需求 ID", "reason": "missing selector"},
            })
            _write_json(folder / "interactive-run.json", state)
            with patch("run_interactive_request._ensure_runtime_current"), patch.object(
                sys, "argv", [
                    "run_interactive_request.py", "--run-folder", str(folder),
                    "--revision-requirement-id", "5.1",
                ],
            ), patch("builtins.print"):
                self.assertEqual(main(), 3)
            resumed = json.loads((folder / "interactive-run.json").read_text(encoding="utf-8"))
            self.assertEqual(resumed["status"], "awaiting_confirmation")
            self.assertEqual(resumed["revision_requirement_ids"], ["5.1"])
            self.assertEqual(resumed["revision_scope_manifest"]["authority"], "explicit command-line selector")

    def test_cli_confirm_migrates_stale_writer_scope_question_without_answers(self) -> None:
        """A legacy writer violation is controller repair work, not new intake."""
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "revision-run"
            folder.mkdir()
            (folder / "prd.md").write_text(
                "| 5.1 | 状态提示 |\n\n### 5.1 状态提示\n旧规则。\n",
                encoding="utf-8",
            )
            turn = {
                "turn": 1,
                "user_text": "仅更新第 5.1 节",
                "summary": "已确认修订范围",
                "scope": {"goal": "更新第 5.1 节", "in_scope": ["5.1"]},
                "questions": ["检测到超范围修改，是否授权扩展章节？"],
                "assumptions": [],
                "decisions": [],
                "risks": [],
                "buckets": {"must_answer_before_generation": ["检测到超范围修改，是否授权扩展章节？"]},
            }
            state = create_state("仅更新第 5.1 节", folder)
            state.update({
                "delivery_variant": "in_place_revision",
                "revision_requirement_ids": ["5.1"],
                "revision_history": [{"request": "仅更新第 5.1 节", "mode": "in_place_revision"}],
                "status": "needs_input",
                "termination": "needs_input",
                "turns": [turn],
                "confirmed_fact_packet": json.loads(json.dumps(turn)),
                "user_confirmation": {"confirmed": True, "source": "test"},
                "scope_clarification": {
                    "artifact": "prd.md",
                    "question": "检测到超范围修改，是否授权扩展章节？",
                    "violation": "protected requirement section 5.2 changed",
                },
            })
            _write_json(folder / "interactive-run.json", state)

            with patch("run_interactive_request._ensure_runtime_current"), patch(
                "run_interactive_request._confirmed_delivery"
            ) as deliver, patch("run_interactive_request.run_intake", side_effect=AssertionError(
                "legacy writer scope question must not reopen intake"
            )), patch.object(
                sys, "argv", ["run_interactive_request.py", "--run-folder", str(folder), "--confirm"],
            ), patch("builtins.print"):
                self.assertEqual(main(), 1)

            self.assertTrue(deliver.called)
            resumed = json.loads((folder / "interactive-run.json").read_text(encoding="utf-8"))
            self.assertEqual(resumed["status"], "confirmed")
            self.assertNotIn("scope_clarification", resumed)
            self.assertNotIn("required_input", resumed)
            self.assertEqual(resumed["termination"], "running")
            self.assertEqual(resumed["turns"][-1]["questions"], [])
            self.assertEqual(resumed["turns"][-1]["buckets"]["must_answer_before_generation"], [])

    def test_stale_scope_migration_preserves_real_delivery_input(self) -> None:
        """A legacy scope question must not erase an independently unresolved decision."""
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "revision-run"
            folder.mkdir()
            state = create_state("仅更新第 5.1 节", folder)
            stale_question = "检测到超范围修改，是否授权扩展章节？"
            user_question = "请确认是否包含历史数据迁移。"
            state.update({
                "delivery_variant": "in_place_revision",
                "revision_requirement_ids": ["5.1"],
                "status": "needs_input",
                "termination": "needs_input",
                "turns": [{
                    "questions": [stale_question, user_question],
                    "buckets": {"must_answer_before_generation": [stale_question, user_question]},
                }],
                "user_confirmation": {"confirmed": True, "source": "test"},
                "scope_clarification": {
                    "artifact": "prd.md",
                    "question": stale_question,
                    "violation": "protected requirement section changed",
                },
            })

            self.assertFalse(_migrate_stale_internal_scope_clarification(state))
            self.assertEqual(state["status"], "needs_input")
            self.assertIn("scope_clarification", state)
            self.assertEqual(state["turns"][-1]["questions"], [stale_question, user_question])

    def test_stale_scope_migration_preserves_controller_owned_required_input(self) -> None:
        """A real controller input field is never treated as a stale scope pause."""
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "revision-run"
            folder.mkdir()
            state = create_state("仅更新第 5.1 节", folder)
            stale_question = "检测到超范围修改，是否授权扩展章节？"
            state.update({
                "delivery_variant": "in_place_revision",
                "revision_requirement_ids": ["5.1"],
                "status": "needs_input",
                "termination": "needs_input",
                "turns": [{
                    "questions": [stale_question],
                    "buckets": {"must_answer_before_generation": [stale_question]},
                }],
                "user_confirmation": {"confirmed": True, "source": "test"},
                "required_input": {
                    "field": "input_assets",
                    "question": "请重新附加输入图片。",
                    "reason": "asset snapshot is missing",
                },
                "scope_clarification": {
                    "artifact": "prd.md",
                    "question": stale_question,
                    "violation": "protected requirement section changed",
                },
            })

            self.assertFalse(_migrate_stale_internal_scope_clarification(state))
            self.assertEqual(state["required_input"]["field"], "input_assets")

    def test_stale_scope_migration_preserves_active_clarification_review(self) -> None:
        """A reviewer-owned clarification pause remains a real human checkpoint."""
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "revision-run"
            folder.mkdir()
            state = create_state("仅更新第 5.1 节", folder)
            stale_question = "检测到超范围修改，是否授权扩展章节？"
            state.update({
                "delivery_variant": "in_place_revision",
                "revision_requirement_ids": ["5.1"],
                "status": "needs_input",
                "termination": "needs_input",
                "turns": [{
                    "questions": [stale_question],
                    "buckets": {"must_answer_before_generation": [stale_question]},
                }],
                "user_confirmation": {"confirmed": True, "source": "test"},
                "clarification_review": {
                    "status": "needs_input",
                    "questions": ["请明确数据保留范围。"],
                    "blockers": ["数据保留范围会改变验收标准。"],
                },
                "scope_clarification": {
                    "artifact": "prd.md",
                    "question": stale_question,
                    "violation": "protected requirement section changed",
                },
            })

            self.assertFalse(_migrate_stale_internal_scope_clarification(state))
            self.assertEqual(state["status"], "needs_input")
            self.assertIn("scope_clarification", state)

    def test_stale_scope_migration_requires_a_durable_turn(self) -> None:
        """An incomplete legacy record must fail closed instead of clearing input."""
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "revision-run"
            folder.mkdir()
            state = create_state("仅更新第 5.1 节", folder)
            state.update({
                "delivery_variant": "in_place_revision",
                "revision_requirement_ids": ["5.1"],
                "status": "needs_input",
                "termination": "needs_input",
                "turns": [],
                "user_confirmation": {"confirmed": True, "source": "test"},
                "scope_clarification": {
                    "artifact": "prd.md",
                    "question": "检测到超范围修改，是否授权扩展章节？",
                    "violation": "protected requirement section changed",
                },
            })

            self.assertFalse(_migrate_stale_internal_scope_clarification(state))
            self.assertEqual(state["status"], "needs_input")
            self.assertIn("scope_clarification", state)

    def test_answer_routes_confirmed_revision_selector_without_reopening_intake(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "revision-run"
            folder.mkdir()
            (folder / "prd.md").write_text("| 5.1 | 状态提示 |\n### 5.1 状态提示\n", encoding="utf-8")
            turn = {
                "turn": 1, "user_text": "更新状态提示", "summary": "已确认需要修订",
                "scope": {"goal": "更新第 5.1 节", "in_scope": ["5.1 状态提示"]},
                "assumptions": [], "decisions": [], "risks": [], "buckets": {},
            }
            state = create_state("更新现有 PRD", folder)
            state.update({
                "delivery_variant": "in_place_revision",
                "revision_history": [{"request": state["raw_request"], "mode": "in_place_revision"}],
                "status": "needs_input", "termination": "needs_input", "turns": [turn],
                "confirmed_fact_packet": json.loads(json.dumps(turn)),
                "user_confirmation": {"confirmed": True, "source": "test"},
                "required_input": {"field": "revision_selector", "question": "请指定需求 ID", "reason": "missing selector"},
            })
            _write_json(folder / "interactive-run.json", state)
            with patch("run_interactive_request._ensure_runtime_current"), patch(
                "run_interactive_request.run_intake", side_effect=AssertionError("typed selector must not reopen intake"),
            ), patch.object(
                sys, "argv", ["run_interactive_request.py", "--run-folder", str(folder), "--answers", "第 5.1 节"],
            ), patch("builtins.print"):
                self.assertEqual(main(), 3)
            resumed = json.loads((folder / "interactive-run.json").read_text(encoding="utf-8"))
            self.assertEqual(resumed["status"], "awaiting_confirmation")
            self.assertEqual(resumed["revision_requirement_ids"], ["5.1"])
            self.assertEqual(resumed["revision_scope_manifest"]["authority"], "explicit user answer")

    def test_invalid_confirmed_revision_answer_stays_at_selector_gate_without_agent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "revision-run"
            folder.mkdir()
            (folder / "prd.md").write_text("| 5.1 | 状态提示 |\n### 5.1 状态提示\n", encoding="utf-8")
            turn = {
                "turn": 1, "user_text": "更新状态提示", "summary": "已确认需要修订",
                "scope": {"goal": "更新第 5.1 节", "in_scope": ["5.1 状态提示"]},
                "assumptions": [], "decisions": [], "risks": [], "buckets": {},
            }
            state = create_state("更新现有 PRD", folder)
            state.update({
                "delivery_variant": "in_place_revision",
                "revision_history": [{"request": state["raw_request"], "mode": "in_place_revision"}],
                "status": "needs_input", "termination": "needs_input", "turns": [turn],
                "confirmed_fact_packet": json.loads(json.dumps(turn)),
                "user_confirmation": {"confirmed": True, "source": "test"},
                "required_input": {"field": "revision_selector", "question": "请指定需求 ID", "reason": "missing selector"},
            })
            _write_json(folder / "interactive-run.json", state)
            with patch("run_interactive_request._ensure_runtime_current"), patch(
                "run_interactive_request.run_intake", side_effect=AssertionError("invalid selector must not call intake"),
            ), patch.object(
                sys, "argv", ["run_interactive_request.py", "--run-folder", str(folder), "--answers", "请整体检查一下"],
            ), patch("builtins.print"):
                self.assertEqual(main(), 3)
            resumed = json.loads((folder / "interactive-run.json").read_text(encoding="utf-8"))
            self.assertEqual(resumed["status"], "needs_input")
            self.assertEqual(resumed["required_input"]["field"], "revision_selector")
            self.assertEqual(resumed["agent_calls"], [])

    def test_legacy_confirmed_revision_migrates_only_one_frozen_current_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "revision-run"
            folder.mkdir()
            prd = folder / "prd.md"
            html = folder / "prd.html"
            prd.write_text("| 5.1 | 状态提示 |\n### 5.1 状态提示\n### 5.2 其他需求\n", encoding="utf-8")
            html.write_text("<!doctype html><html></html>\n", encoding="utf-8")
            state = create_state("更新现有 PRD", folder)
            state.update({
                # Older states kept the create-state default even after revision started.
                "delivery_variant": "new",
                "revision_history": [{
                    "mode": "in_place_revision",
                    "prd_before_sha256": hashlib.sha256(prd.read_bytes()).hexdigest(),
                    "html_before_sha256": hashlib.sha256(html.read_bytes()).hexdigest(),
                }],
                "confirmed_fact_packet": {
                    "scope": {"goal": "仅更新第 5.1 节", "in_scope": ["PRD 第 5.1 节"]},
                },
                "required_input": {"field": "revision_selector", "question": "请指定需求 ID", "reason": "legacy"},
            })
            self.assertTrue(_migrate_legacy_confirmed_revision_scope(state))
            self.assertEqual(state["delivery_variant"], "in_place_revision")
            self.assertEqual(state["revision_requirement_ids"], ["5.1"])
            self.assertEqual(state["revision_scope_manifest"]["authority"], "legacy confirmed-fact-packet migration")
            self.assertNotIn("required_input", state)

    def test_legacy_confirmed_revision_does_not_migrate_after_source_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "revision-run"
            folder.mkdir()
            prd = folder / "prd.md"
            html = folder / "prd.html"
            prd.write_text("### 5.1 状态提示\n", encoding="utf-8")
            html.write_text("<!doctype html><html></html>\n", encoding="utf-8")
            state = create_state("更新现有 PRD", folder)
            state.update({
                "revision_history": [{
                    "mode": "in_place_revision",
                    "prd_before_sha256": hashlib.sha256(prd.read_bytes()).hexdigest(),
                    "html_before_sha256": hashlib.sha256(html.read_bytes()).hexdigest(),
                }],
                "confirmed_fact_packet": {"scope": {"goal": "更新第 5.1 节", "in_scope": []}},
            })
            prd.write_text("### 5.1 已被其他人更新\n", encoding="utf-8")
            self.assertFalse(_migrate_legacy_confirmed_revision_scope(state))
            self.assertNotIn("revision_requirement_ids", state)

    def test_clarification_review_uses_attributable_final_json_not_a_temp_artifact(self) -> None:
        state = create_state("做一个 PRD", Path("/tmp/example"))
        prompt = clarification_review_prompt(state, {"status": "complete", "summary": "范围完整"})
        self.assertIn("Return ONLY one JSON object in your final response", prompt)
        self.assertNotIn("Write ONLY one JSON object to", prompt)
        self.assertNotIn("clarification-review.json", prompt)

    def test_failed_resume_keeps_the_frozen_confirmed_fact_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "run"
            folder.mkdir()
            frozen = {"summary": "已确认范围", "scope": {"goal": "原始 5.1", "in_scope": ["5.1"]}}
            state = create_state("更新现有 PRD", folder)
            state.update({
                "status": "failed", "termination": "failed",
                "turns": [{"summary": "错误的新摘要", "scope": {"goal": "错误 5.2"}}],
                "confirmed_fact_packet": json.loads(json.dumps(frozen)),
                "user_confirmation": {"confirmed": True, "source": "prior confirmation"},
            })
            _write_json(folder / "interactive-run.json", state)

            selected_providers = []

            def complete_delivery(replayed_state, provider, *args, **kwargs):
                selected_providers.append(provider)
                replayed_state["status"] = "complete"
                replayed_state["termination"] = "complete"

            with patch("run_interactive_request._ensure_runtime_current"), patch(
                "run_interactive_request._confirmed_delivery", side_effect=complete_delivery,
            ), patch.object(
                sys, "argv", ["run_interactive_request.py", "--run-folder", str(folder), "--confirm"],
            ), patch("builtins.print"):
                self.assertEqual(main(), 0)
            resumed = json.loads((folder / "interactive-run.json").read_text(encoding="utf-8"))
            self.assertEqual(resumed["confirmed_fact_packet"], frozen)
            self.assertEqual(selected_providers, ["auto"])

    def test_trace_normalisation_replaces_stale_version_and_asset_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            assets = folder / "assets"
            assets.mkdir()
            asset = assets / "current.png"
            asset.write_bytes(b"current image")
            trace = folder / "run-log.yaml"
            trace.write_text(
                "pm_copilot_version: 5.0.3\nimplemented_feature_prd:\n"
                "  screenshots_and_placeholders:\n"
                "    - target_ref: 5.1\n"
                "      coverage_decision: real_figure\n"
                "      path: assets/current.png\n"
                "      asset_sha256: stale\n",
                encoding="utf-8",
            )
            self.assertEqual(_normalise_trace_runtime_evidence(trace), 1)
            text = trace.read_text(encoding="utf-8")
            active_version = (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip()
            self.assertIn(f"pm_copilot_version: {active_version}", text)
            self.assertIn(hashlib.sha256(b"current image").hexdigest(), text)

    def test_trace_normalisation_refreshes_nested_additional_asset_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            assets = folder / "assets"
            assets.mkdir()
            asset = assets / "secondary.png"
            asset.write_bytes(b"secondary image")
            trace = folder / "run-log.yaml"
            trace.write_text(
                "implemented_feature_prd:\n  screenshots_and_placeholders:\n"
                "    - target_ref: '5.1'\n      coverage_decision: real_figure\n"
                "      path: assets/primary.png\n      asset_sha256: pending\n"
                "      additional_assets:\n        - path: assets/secondary.png\n"
                "          asset_sha256: pending_controller_hash\n",
                encoding="utf-8",
            )
            _normalise_trace_runtime_evidence(trace)
            self.assertIn(hashlib.sha256(b"secondary image").hexdigest(), trace.read_text(encoding="utf-8"))

    def test_stream_disconnect_retries_prd_agent_and_preserves_the_failure_reason(self) -> None:
        calls = []

        def worker(*args, **kwargs):
            calls.append(args)
            return {"provider": "test", "model": "test", "status": "failed", "output": "", "error": "stream disconnected"}

        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个 PRD", Path(temporary))
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            self.assertFalse(_run_artifact_agent(state, "prd.md", "test", 15, worker=worker))
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0][3], 15)
            self.assertIn("stream disconnected", state["last_error"])

    def test_stage_agent_no_progress_is_retryable(self) -> None:
        calls = []

        def worker(*args, **kwargs):
            calls.append(args)
            return {
                "provider": "codex", "model": "gpt-5.6-terra", "status": "timed_out",
                "output": "", "error": "no first artifact within 30 second(s)",
                "failure_category": "agent_no_progress",
            }

        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个 PRD", Path(temporary))
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            self.assertFalse(_run_artifact_agent(state, "prd.md", "seawork", 15, worker=worker))
            self.assertEqual(len(calls), 2)

    def test_idle_agent_with_an_unchanged_stage_artifact_cannot_promote(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            target = folder / "prd.md"
            target.write_text("old PRD\n", encoding="utf-8")
            state = create_state("做一个 PRD", folder)
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]

            def idle_worker(*args, **kwargs):
                return {"provider": "seawork", "model": "codex/gpt-5.6-terra", "status": "complete", "output": "idle", "error": ""}

            self.assertFalse(_run_artifact_agent(state, "prd.md", "seawork", 5, worker=idle_worker))
            self.assertEqual(target.read_text(encoding="utf-8"), "old PRD\n")
            self.assertEqual(len(state["agent_calls"]), 1)
            self.assertEqual(state["delivery_stages"]["prd.md"]["artifact_status"], "failed")
            self.assertIn("prd.md was not changed in the project staging directory", state["last_error"])

    def test_unattributable_stage_write_cannot_promote_or_be_reused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            target = folder / "prd.md"
            target.write_text("old PRD\n", encoding="utf-8")
            state = create_state("做一个 PRD", folder)
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]

            def unattributable_worker(provider, prompt, cwd, *args):
                staged_target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
                staged_target.write_text("new but unattributable PRD\n", encoding="utf-8")
                return {"status": "complete", "output": "written", "error": ""}

            self.assertFalse(_run_artifact_agent(state, "prd.md", "test", 5, worker=unattributable_worker))
            self.assertEqual(target.read_text(encoding="utf-8"), "old PRD\n")
            self.assertEqual(state["delivery_stages"]["prd.md"]["artifact_status"], "failed")
            self.assertNotIn("prd.md", state["artifacts"])

    def test_controller_trace_is_materialized_without_a_remote_worker_for_new_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prd.md").write_text("# 新需求\n\n### 5.1 新能力\n", encoding="utf-8")
            state = create_state("新增一个能力的 PRD", folder)
            state["turns"] = [{
                "summary": "已澄清", "scope": {"goal": "新增能力", "in_scope": ["核心流程"]},
                "assumptions": [], "risks": [],
            }]
            worker_called = False

            def worker(*args, **kwargs):
                nonlocal worker_called
                worker_called = True
                raise AssertionError("controller-owned run-log must not invoke a remote worker")

            self.assertTrue(_run_artifact_agent(state, "run-log.yaml", "seawork", 1, worker=worker))
            self.assertFalse(worker_called)
            trace = (folder / "run-log.yaml").read_text(encoding="utf-8")
            self.assertIn("pm_copilot_revision: controller-deterministic-trace", trace)
            self.assertEqual(state["delivery_stages"]["run-log.yaml"]["artifact_status"], "promoted")
            self.assertEqual(state["agent_calls"][-1]["execution_mode"], "deterministic_trace_materialization")

    def test_controller_trace_records_extraction_snapshot_hash_and_confirmed_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "extracted-prd"
            folder.mkdir()
            source = root / "legacy-prd.md"
            source.write_text(
                "# 旧 PRD\n\n### 5.7 结算流程\n仅提取该流程。\n",
                encoding="utf-8",
            )
            (folder / "prd.md").write_text("# 独立提取需求\n\n### 5.7 提取后的流程\n", encoding="utf-8")
            state = create_state("从旧 PRD 提取结算流程，形成一份新的独立 PRD", folder)
            register_extraction_source(state, source)
            state["extraction_source"]["selected_scope"] = ["5.7 结算流程"]
            state["turns"] = [{
                "summary": "已确认", "scope": {
                    "goal": "提取结算流程", "in_scope": ["旧 PRD 的结算流程"], "out_of_scope": ["原 PRD 其余内容"],
                },
                "assumptions": [], "risks": [],
            }]
            worker_called = False

            def worker(*args, **kwargs):
                nonlocal worker_called
                worker_called = True
                raise AssertionError("controller-owned run-log must not invoke a remote worker")

            self.assertTrue(_run_artifact_agent(state, "run-log.yaml", "codex", 1, worker=worker))
            self.assertFalse(worker_called)
            trace_text = (folder / "run-log.yaml").read_text(encoding="utf-8")
            trace = yaml.safe_load(trace_text)
            lineage = trace["artifact_lineage"]
            self.assertEqual(lineage["mode"], "extraction_run")
            self.assertEqual(lineage["source_snapshot_path"], "source-material/source-prd.md")
            self.assertEqual(lineage["source_prd_display_name"], "legacy-prd.md")
            self.assertEqual(
                lineage["source_prd_sha256"],
                hashlib.sha256(source.read_bytes()).hexdigest(),
            )
            self.assertEqual(lineage["selected_source_scope"], ["5.7 结算流程"])
            self.assertEqual(lineage["source_scope_resolution"], [{
                "selector": "5.7 结算流程",
                "kind": "requirement_id",
                "matches": ["5.7"],
            }])
            self.assertEqual(
                (folder / "source-material" / "source-prd.md").read_text(encoding="utf-8"),
                source.read_text(encoding="utf-8"),
            )
            self.assertEqual(trace["context"]["source_mode"], "document-backed")
            self.assertIn("source-material/source-prd.md", trace["context"]["product_documents_loaded"])
            self.assertNotIn(str(source.resolve()), trace_text)

    def test_extraction_scope_must_resolve_in_the_snapshot_before_delivery(self) -> None:
        source_text = (
            "# 旧 PRD\n\n"
            "### 5.3 画布性能优化\n提升大画布渲染性能。\n\n"
            "### 5.4 画布渲染优化\n减少重绘。\n\n"
            "### 5.5 画布导出优化\n改善导出队列。\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "legacy-prd.md"
            source.write_text(source_text, encoding="utf-8")
            folder = root / "extracted"
            folder.mkdir()
            state = create_state("从旧 PRD 提取画布优化内容，创建新的独立 PRD", folder)
            register_extraction_source(state, source)
            state["confirmed_fact_packet"] = {
                "summary": "已确认范围", "scope": {"goal": "提取画布优化", "in_scope": ["5.3 至 5.5"]},
                "assumptions": [], "risks": [],
            }
            self.assertIsNone(_delivery_input_problem(state))

            state["confirmed_fact_packet"]["scope"]["in_scope"] = ["不存在的画布功能"]
            state["turns"] = [state["confirmed_fact_packet"]]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            worker_called = False

            def worker(*args, **kwargs):
                nonlocal worker_called
                worker_called = True
                self.fail("an unresolved extraction selector must stop before writers run")

            _confirmed_delivery(state, "codex", 1, worker=worker)

            self.assertFalse(worker_called)
            self.assertEqual(state["status"], "needs_input")
            self.assertEqual(state["termination"], "needs_input")
            self.assertEqual(state["required_input"]["field"], "extraction_scope")
            self.assertIn("无法在旧 PRD 快照中唯一定位", state["last_error"])

    def test_extraction_scope_accepts_a_heading_or_unique_text_but_rejects_repeated_text(self) -> None:
        source_text = (
            "# 旧 PRD\n\n"
            "### 5.1 实时协作\n离线状态下保留本地草稿。\n\n"
            "### 5.2 导出\n共享反馈。\n\n"
            "### 5.3 审核\n共享反馈。\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "legacy-prd.md"
            source.write_text(source_text, encoding="utf-8")
            folder = root / "extracted"
            folder.mkdir()
            state = create_state("从旧 PRD 拆出一份新的独立 PRD", folder)
            register_extraction_source(state, source)
            state["confirmed_fact_packet"] = {
                "summary": "已确认范围", "scope": {"goal": "提取范围", "in_scope": ["实时协作"]},
                "assumptions": [], "risks": [],
            }

            self.assertIsNone(_delivery_input_problem(state))

            state["confirmed_fact_packet"]["scope"]["in_scope"] = ["离线状态下保留本地草稿"]
            self.assertIsNone(_delivery_input_problem(state))

            state["confirmed_fact_packet"]["scope"]["in_scope"] = ["共享反馈"]
            self.assertIn("匹配多个旧 PRD 文本位置", _delivery_input_problem(state) or "")

    def test_implemented_feature_without_evidence_pauses_before_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            state = create_state("把已实现功能还原成 PRD", folder)
            state["task_mode"] = "implemented_feature_prd"
            state["context_source"] = {"mode": "repo-backed", "files_loaded": []}
            state["turns"] = [{
                "summary": "已确认", "scope": {"goal": "还原已实现功能", "in_scope": ["当前功能"]},
                "assumptions": [], "risks": [], "buckets": {},
            }]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            worker_called = False

            def worker(*args, **kwargs):
                nonlocal worker_called
                worker_called = True
                self.fail("missing implementation evidence must stop before any delivery Agent runs")

            _confirmed_delivery(state, "codex", 1, worker=worker)

            self.assertFalse(worker_called)
            self.assertEqual(state["status"], "needs_input")
            self.assertEqual(state["termination"], "needs_input")
            self.assertEqual(state["required_input"]["field"], "implementation_evidence")
            self.assertIn("实施证据包", state["last_error"])
            self.assertEqual(state["agent_calls"], [])
            self.assertFalse((folder / "prd.md").exists())
            self.assertFalse((folder / "run-log.yaml").exists())

    def test_extraction_source_drift_blocks_delivery_and_invalidates_reuse_after_resnapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, canonical, _ = self._eligible_retry_reuse_state(root)
            source = root / "legacy-prd.md"
            source.write_text("# 旧 PRD\n\n### 5.7 结算流程\n第一版。\n", encoding="utf-8")
            state["raw_request"] = "从旧 PRD 提取结算流程，形成独立 PRD"
            register_extraction_source(state, source)
            state["extraction_source"]["selected_scope"] = ["5.7 结算流程"]
            state["confirmed_fact_packet"] = {
                "summary": "已确认提取范围",
                "scope": {"goal": "提取结算流程", "in_scope": ["5.7 结算流程"]},
                "assumptions": [], "risks": [],
            }
            initial_fingerprint = _confirmed_scope_fingerprint(state)
            for stage in state["delivery_stages"].values():
                stage["scope_fingerprint"] = initial_fingerprint
            _snapshot_reusable_delivery_artifacts(state)
            cache = _retry_reuse_cache_folder(state)
            self.assertTrue(cache.is_dir())

            source.write_text("# 旧 PRD\n\n### 5.7 结算流程\n第二版，规则已变化。\n", encoding="utf-8")
            state["turns"] = [{
                "summary": "已确认", "scope": {"goal": "提取结算流程", "in_scope": ["5.7 结算流程"]},
                "assumptions": [], "risks": [], "buckets": {},
            }]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            worker_called = False

            def worker(*args, **kwargs):
                nonlocal worker_called
                worker_called = True
                self.fail("a changed extraction source must stop before cached artifacts or delivery Agents are used")

            _confirmed_delivery(state, "codex", 1, worker=worker)

            self.assertFalse(worker_called)
            self.assertEqual(state["status"], "needs_input")
            self.assertEqual(state["termination"], "needs_input")
            self.assertIn("原始旧 PRD 在确认后已发生变化", state["last_error"])
            self.assertEqual(state["retry_reuse"]["status"], "available")
            self.assertTrue(cache.is_dir())

            register_extraction_source(state, source)
            self.assertNotEqual(_confirmed_scope_fingerprint(state), initial_fingerprint)
            restored = _prepare_delivery_workspace(state)

            self.assertFalse((restored / "confirmed-requirements.md").exists())
            self.assertFalse((restored / "prd.md").exists())
            self.assertEqual(state["retry_reuse"]["status"], "discarded")
            self.assertEqual(state["retry_reuse"]["reason"], "scope_or_runtime_changed")
            self.assertFalse(cache.exists())
            self.assertEqual(canonical, Path(state["folder"]))

    def test_prd_prompt_assigns_html_rendering_to_the_controller(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("更新 5.1", Path(temporary))
            state["turns"] = [{"summary": "已确认", "scope": {"goal": "更新 5.1"}, "assumptions": [], "risks": []}]
            prompt = _artifact_prompt(state, "prd.md")
        self.assertIn("this Agent writes only prd.md", prompt)
        self.assertIn("The controller renders and validates prd.html", prompt)
        self.assertIn("not a conflict", prompt)

    def test_input_asset_snapshot_survives_temporary_source_cleanup_and_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "canonical"
            canonical.mkdir()
            temporary_input = root / "temporary-attachments" / "result.png"
            temporary_input.parent.mkdir()
            temporary_input.write_bytes(b"confirmed screenshot bytes")
            state = create_state("使用用户提供的截图更新 PRD", canonical)
            state["turns"] = [{
                "summary": "已确认截图范围",
                "scope": {"goal": "更新截图说明", "in_scope": ["引用 result.png"]},
                "assumptions": [], "risks": [],
            }]
            state["confirmed_fact_packet"] = dict(state["turns"][-1])
            state["user_confirmation"] = {"confirmed": True, "source": "test"}

            records = register_input_assets(state, [temporary_input])
            self.assertEqual(records[0]["asset_path"], "assets/result.png")
            self.assertEqual(state["input_assets"], [records[0]["snapshot_path"]])
            self.assertNotIn(str(temporary_input.resolve()), json.dumps(state, ensure_ascii=False))
            descriptor = state["input_asset_manifest"]
            manifest = canonical / descriptor["manifest_path"]
            snapshot = canonical / records[0]["snapshot_path"]
            self.assertTrue(manifest.is_file())
            self.assertEqual(_artifact_digest(snapshot), records[0]["sha256"])
            fingerprint = _confirmed_scope_fingerprint(state)

            # The caller's OS-managed attachment path is deliberately removed
            # before both the first stage and a later recovery attempt.
            temporary_input.unlink()
            restored_state = json.loads(json.dumps(state, ensure_ascii=False))
            self.assertIsNone(_delivery_input_problem(restored_state))
            self.assertEqual(_confirmed_scope_fingerprint(restored_state), fingerprint)

            workspace = _prepare_delivery_workspace(restored_state)
            self.assertEqual(
                (workspace / "assets" / "result.png").read_bytes(),
                b"confirmed screenshot bytes",
            )
            prompt = _artifact_prompt(restored_state, "prd.md")
            self.assertIn('Provided user visual assets already copied to this delivery workspace: ["result.png"]', prompt)

            shutil.rmtree(workspace.parent)
            recovered_workspace = _prepare_delivery_workspace(restored_state)
            self.assertEqual(
                (recovered_workspace / "assets" / "result.png").read_bytes(),
                b"confirmed screenshot bytes",
            )

            # A snapshot is not a convenience cache. Any byte change must stop
            # before an Agent can receive the staged artifact path.
            snapshot.write_bytes(b"tampered bytes")
            problem = _delivery_input_problem(restored_state)
            self.assertIn("SHA-256", problem or "")
            with self.assertRaises(ValueError):
                _prepare_delivery_workspace(restored_state)

    def test_explicit_asset_reattachment_repairs_an_invalid_attested_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "canonical"
            canonical.mkdir()
            source = root / "attachments" / "result.png"
            source.parent.mkdir()
            source.write_bytes(b"original confirmed bytes")
            state = create_state("使用附件更新 PRD", canonical)
            record = register_input_assets(state, [source])[0]
            snapshot = canonical / record["snapshot_path"]

            for failure in ("missing", "tampered"):
                with self.subTest(failure=failure):
                    if failure == "missing":
                        snapshot.unlink()
                    else:
                        snapshot.write_bytes(b"corrupt bytes")
                    self.assertIsNotNone(_delivery_input_problem(state))

                    repaired = register_input_assets(state, [source])

                    self.assertEqual(repaired[0]["sha256"], record["sha256"])
                    self.assertEqual(snapshot.read_bytes(), b"original confirmed bytes")
                    self.assertIsNone(_delivery_input_problem(state))

            source.write_bytes(b"different bytes")
            snapshot.write_bytes(b"corrupt again")
            with self.assertRaisesRegex(FileExistsError, "conflicts with another confirmed asset"):
                register_input_assets(state, [source])

    def test_explicit_asset_reattachment_recovers_a_missing_or_tampered_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "canonical"
            canonical.mkdir()
            source = root / "attachments" / "result.png"
            source.parent.mkdir()
            source.write_bytes(b"original confirmed bytes")
            state = create_state("使用附件更新 PRD", canonical)
            register_input_assets(state, [source])
            descriptor = dict(state["input_asset_manifest"])
            manifest = canonical / descriptor["manifest_path"]

            for failure in ("missing", "tampered"):
                with self.subTest(failure=failure):
                    if failure == "missing":
                        manifest.unlink()
                    else:
                        manifest.write_text('{"assets":[]}', encoding="utf-8")
                    self.assertIsNotNone(_delivery_input_problem(state))

                    records = register_input_assets(state, [source])

                    self.assertEqual(len(records), 1)
                    self.assertEqual(_artifact_digest(manifest), descriptor["manifest_sha256"])
                    self.assertIsNone(_delivery_input_problem(state))

    def test_manifest_recovery_requires_every_original_attachment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "canonical"
            canonical.mkdir()
            source_a = root / "attachments" / "result-a.png"
            source_b = root / "attachments" / "result-b.png"
            source_a.parent.mkdir()
            source_a.write_bytes(b"first confirmed bytes")
            source_b.write_bytes(b"second confirmed bytes")
            state = create_state("使用附件更新 PRD", canonical)
            records = register_input_assets(state, [source_a, source_b])
            manifest = canonical / state["input_asset_manifest"]["manifest_path"]
            manifest.unlink()

            with self.assertRaisesRegex(ValueError, "reattach every originally confirmed asset"):
                register_input_assets(state, [source_a])

            self.assertFalse(manifest.exists())
            self.assertEqual(len(records), 2)

    def test_legacy_input_asset_path_is_migrated_before_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "canonical"
            canonical.mkdir()
            temporary_input = root / "temporary-attachments" / "legacy.png"
            temporary_input.parent.mkdir()
            temporary_input.write_bytes(b"legacy screenshot bytes")
            state = create_state("更新 PRD", canonical)
            # This is the path-only state written by older controller versions.
            state["input_assets"] = [str(temporary_input)]

            self.assertIsNone(_delivery_input_problem(state))
            self.assertIsInstance(state["input_asset_manifest"], dict)
            temporary_input.unlink()

            workspace = _prepare_delivery_workspace(state)
            self.assertEqual(
                (workspace / "assets" / "legacy.png").read_bytes(),
                b"legacy screenshot bytes",
            )

    def test_prd_writer_prompt_injects_complete_controller_revision_scope_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "canonical"
            assets = canonical / "assets"
            assets.mkdir(parents=True)
            for name in ("old-result.png", "upload-node.png"):
                (assets / name).write_bytes(name.encode("utf-8"))
            baseline = (
                "## 一、文档说明\n### 版本记录\n"
                "| 版本 | 日期 | 变更摘要 | 负责人 |\n| --- | --- | --- | --- |\n"
                "| v1.0 | 2026-09-01 | 首次创建 | PM |\n\n"
                "## 四、需求清单\n| 5.1 | 节点执行结果 |\n| 5.2 | 上传节点 |\n\n"
                "## 五、需求详情\n### 5.1 节点执行结果\n旧规则。\n"
                "[[prd-detail-media src=\"./assets/old-result.png\" alt=\"old\" copy=\"旧执行结果\"]]\n\n"
                "### 5.2 上传节点\n保留上传规则。\n"
                "[[prd-detail-media src=\"./assets/upload-node.png\" alt=\"upload\" copy=\"上传节点\"]]\n\n"
                "## 六、多语言需求\n| 文案 | 说明 |\n| --- | --- |\n"
                "| 旧执行结果 | 旧说明 |\n| 上传节点 | 保留说明 |\n"
            )
            (canonical / "prd.md").write_text(baseline, encoding="utf-8")
            (canonical / "prd.html").write_text("<html>baseline</html>\n", encoding="utf-8")
            incoming = root / "incoming-assets"
            incoming.mkdir()
            input_assets = []
            for name in ("execution-success.png", "execution-failure.png"):
                path = incoming / name
                path.write_bytes(name.encode("utf-8"))
                input_assets.append(str(path))

            state = create_state("更新 5.1", canonical)
            state.update({
                "delivery_variant": "in_place_revision",
                "revision_requirement_ids": ["5.1"],
                "revision_history": [{
                    "mode": "in_place_revision",
                    "request": (
                        "仅更新 5.1 对应多语言文案；5.1 仅保留两张固定顺序图示："
                        "./assets/execution-success.png、./assets/execution-failure.png；不引用第三张图。"
                    ),
                    "prd_before_sha256": hashlib.sha256(baseline.encode("utf-8")).hexdigest(),
                    "html_before_sha256": hashlib.sha256(b"<html>baseline</html>\n").hexdigest(),
                }],
                "confirmed_fact_packet": {
                    "scope": {"goal": "更新 5.1", "in_scope": ["5.1 对应中文文案和两张固定图示"]},
                    "decisions": [], "assumptions": [], "risks": [],
                },
                "user_confirmation": {"confirmed": True, "source": "test"},
                "input_assets": input_assets,
            })
            _materialize_revision_scope_manifest(state)
            _prepare_delivery_workspace(state)
            prompt = _artifact_prompt(state, "prd.md")

        self.assertIn("Controller-owned in-place revision scope contract (authoritative)", prompt)
        self.assertIn('"selected_requirement_ids":["5.1"]', prompt)
        self.assertIn('"protected_requirement_ids":["5.2"]', prompt)
        self.assertIn('"protected_asset_paths":["assets/old-result.png","assets/upload-node.png"]', prompt)
        self.assertIn('"allowed_new_asset_paths":["assets/execution-failure.png","assets/execution-success.png"]', prompt)
        self.assertIn('"linked_localization_rows_allowed":true', prompt)
        self.assertIn('"append_only_version_history_allowed":true', prompt)
        self.assertIn("use exactly 2 local image marker(s)", prompt)
        self.assertIn("assets/execution-success.png, assets/execution-failure.png", prompt)
        self.assertIn("Keep their marker order exactly", prompt)
        self.assertIn("Leave every unrelated localization row unchanged", prompt)
        self.assertIn("existing version-history heading and every prior record are protected", prompt)
        self.assertIn("material selected-requirement change", prompt)
        self.assertIn("layout/media-only change", prompt)

    def test_stream_disconnected_agent_write_is_not_promoted_without_terminal_completion(self) -> None:
        calls = 0
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            target = folder / "prd.md"
            target.write_text("old PRD\n", encoding="utf-8")
            state = create_state("做一个 PRD", folder)
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]

            def reconnecting_worker(provider, prompt, cwd, *args):
                nonlocal calls
                calls += 1
                staged_target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
                staged_target.write_text("new but unconfirmed PRD\n", encoding="utf-8")
                return {"provider": provider, "model": "codex/gpt-5.6-terra", "status": "failed", "output": "", "error": "stream disconnected"}

            self.assertFalse(_run_artifact_agent(state, "prd.md", "seawork", 5, worker=reconnecting_worker))
            self.assertEqual(calls, 2)
            self.assertEqual(target.read_text(encoding="utf-8"), "old PRD\n")
            self.assertEqual(state["delivery_stages"]["prd.md"]["artifact_status"], "failed")

    def test_agent_write_in_the_wrong_workspace_cannot_promote_or_pollute_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            target = folder / "prd.md"
            target.write_text("old PRD\n", encoding="utf-8")
            state = create_state("做一个 PRD", folder)
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]

            def wrong_workspace_worker(provider, prompt, cwd, *args):
                target.write_text("wrong workspace PRD\n", encoding="utf-8")
                return {"provider": provider, "model": "codex/gpt-5.6-terra", "status": "complete", "output": "idle", "error": ""}

            self.assertFalse(_run_artifact_agent(state, "prd.md", "seawork", 5, worker=wrong_workspace_worker))
            self.assertEqual(target.read_text(encoding="utf-8"), "old PRD\n")
            stage = state["delivery_stages"]["prd.md"]
            self.assertEqual(stage["artifact_status"], "failed")
            self.assertTrue(state["agent_calls"][-1]["artifact_changed_in_workspace"] is False)

    def test_delivery_worker_disables_the_first_artifact_watchdog(self) -> None:
        with patch("run_interactive_request.execute", return_value={"status": "complete"}) as execute:
            _delivery_worker("test", "write", Path.cwd(), 15, None, None, False, 8000)
        self.assertIsNone(execute.call_args.kwargs["first_artifact_seconds"])

    def test_atomic_copy_replaces_the_complete_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = folder / "source.txt"
            destination = folder / "destination.txt"
            source.write_text("new trace", encoding="utf-8")
            destination.write_text("old trace", encoding="utf-8")
            _atomic_copy(source, destination)
            self.assertEqual(destination.read_text(encoding="utf-8"), "new trace")

    def test_recovery_attempt_discards_stale_stage_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个 PRD", Path(temporary))
            state.update({
                "resume_from_status": "recovery_required",
                "delivery_stages": {"run-log.yaml": {"review_status": "passed", "artifact_status": "promoted"}},
                "validation": [{"status": "failed"}],
                "artifacts": ["discussion.md", "prd.md", "run-log.yaml"],
                "recovery": {"status": "retry_required"},
                "revision_stop_reason": "validation budget exhausted",
            })
            _restart_delivery_attempt(state)
            self.assertEqual(state["delivery_stages"], {})
            self.assertEqual(state["validation"], [])
            self.assertEqual(state["artifacts"], ["discussion.md"])
            self.assertNotIn("recovery", state)
            self.assertEqual(state["delivery_attempts"][-1]["prior_status"], "recovery_required")

    def test_nonexistent_run_folder_cannot_create_a_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "would-be-copy"
            with patch.object(sys, "argv", ["run_interactive_request.py", "--run-folder", str(missing), "--dry-run"]):
                with self.assertRaises(SystemExit):
                    main()
            self.assertFalse(missing.exists())
    def test_material_unknown_stops_before_confirmation(self) -> None:
        responses = [
            '{"status":"needs_input","summary":"目标尚不明确","questions":["目标用户是谁？"],"buckets":{"must_answer_before_generation":["target user"]}}',
            '{"status":"complete","summary":"目标用户已明确","questions":[],"buckets":{"must_answer_before_generation":[]},"scope":{"goal":"降低流失","users":["付费用户"],"in_scope":["提醒"],"out_of_scope":["改价"],"platform":"Web"}}',
            '{"status":"complete","summary":"独立复核通过","questions":[],"blockers":[],"coverage":{"goal":"covered","users":"covered","scope":"covered","success_evidence":"covered","constraints_and_risk":"covered"}}',
        ]

        def worker(*args, **kwargs):
            return {"provider": "test", "model": "test", "status": "complete", "output": responses.pop(0), "error": ""}

        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个留存提醒", Path(temporary))
            state = run_intake(state, "test", 1, worker=worker)
            self.assertEqual(state["status"], "needs_input")
            self.assertEqual(state["termination"], "needs_input")
            state = run_intake(state, "test", 1, worker=worker, answers="付费用户，Web，先做提醒")
            self.assertEqual(state["status"], "awaiting_confirmation")
            write_discussion(Path(temporary), state)
            self.assertTrue((Path(temporary) / "discussion.md").is_file())

    def test_intake_passes_an_explicit_model_to_the_runtime(self) -> None:
        observed_models = []

        def worker(*args, **kwargs):
            observed_models.append(args[4])
            return {"provider": "seawork", "model": "codex/gpt-5.6-terra", "status": "complete", "output": '{"status":"needs_input","questions":["目标用户？"],"buckets":{"must_answer_before_generation":["target user"]}}', "error": ""}

        with tempfile.TemporaryDirectory() as temporary:
            state = run_intake(
                create_state("做一个 PRD", Path(temporary)), "seawork", 1,
                worker=worker, model="codex/gpt-5.6-terra",
            )
        self.assertEqual(state["status"], "needs_input")
        self.assertEqual(observed_models, ["codex/gpt-5.6-terra"])

    def test_incomplete_coverage_cannot_pass_clarification_review(self) -> None:
        responses = [
            '{"status":"complete","summary":"初步完成","questions":[],"buckets":{"must_answer_before_generation":[]}}',
            '{"status":"complete","summary":"未提供覆盖证明","questions":[],"blockers":[],"coverage":{"goal":"covered"}}',
        ]

        def worker(*args, **kwargs):
            return {"provider": "test", "model": "test", "status": "complete", "output": responses.pop(0), "error": ""}

        with tempfile.TemporaryDirectory() as temporary:
            state = run_intake(create_state("做一个 PRD", Path(temporary)), "test", 1, worker=worker)
            self.assertEqual(state["status"], "needs_input")
            self.assertIn("未证明", state["turns"][-1]["buckets"]["must_answer_before_generation"][0])

    def test_independent_review_blocks_premature_confirmation(self) -> None:
        responses = [
            '{"status":"complete","summary":"初步完成","questions":[],"buckets":{"must_answer_before_generation":[]},"scope":{"goal":"降低流失"}}',
            '{"status":"needs_input","summary":"缺少验收边界","questions":["留存提升以什么口径验收？"],"blockers":["success metric"]}',
        ]

        def worker(*args, **kwargs):
            return {"provider": "test", "model": "test", "status": "complete", "output": responses.pop(0), "error": ""}

        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个留存提醒", Path(temporary))
            state = run_intake(state, "test", 1, worker=worker)
            self.assertEqual(state["status"], "needs_input")
            self.assertEqual(state["termination"], "needs_input")
            self.assertIn("留存提升", state["turns"][-1]["questions"][0])

    def test_delivery_is_not_allowed_without_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个 PRD", Path(temporary))
            (Path(temporary) / "prd.html").write_text("<!doctype html><html></html>", encoding="utf-8")
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            state["status"] = "awaiting_confirmation"
            _confirmed_delivery(state, "test", 1, worker=lambda *args: self.fail("worker must not run"))
            self.assertEqual(state["status"], "awaiting_confirmation")
            self.assertEqual(state["termination"], "human_checkpoint")
            self.assertIn("Explicit user confirmation", state["last_error"])

    def test_confirmed_delivery_records_each_agent_stage(self) -> None:
        def worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
            if "Clarification Review Agent" in prompt:
                return {"provider": provider, "model": "test", "status": "complete", "output": '{"status":"complete","blockers":[],"questions":[]}', "error": ""}
            if "Stage Quality Review Agent" in prompt:
                review_path = Path(prompt.split("Write ONLY one JSON object to ", 1)[1].split(" (UTF-8):", 1)[0])
                review_path.write_text(
                    '{"status":"pass","blocking_findings":[],"acceptance_evidence":["contract checked"]}',
                    encoding="utf-8",
                )
                return {"provider": provider, "model": "test", "status": "complete", "output": "", "error": ""}
            marker = "Write one complete artifact at "
            target = Path(prompt.split(marker, 1)[1].split(".\n", 1)[0])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# artifact\n", encoding="utf-8")
            if target.name == "prd.md":
                target.with_name("prd.html").write_text("<!doctype html><html></html>", encoding="utf-8")
            return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}

        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个 PRD", Path(temporary))
            (Path(temporary) / "prd.html").write_text("<!doctype html><html></html>", encoding="utf-8")
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            state["agent_calls"] = [
                {"phase": "intake", "provider": "test", "model": "test", "status": "complete"},
                {"phase": "clarification_review", "provider": "test", "model": "test", "status": "complete"},
            ]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            with patch("run_interactive_request._validate_delivery", return_value=[{"status": "passed"}]), patch(
                "run_interactive_request._trace_contract_findings", return_value="",
            ):
                _confirmed_delivery(state, "test", 1, worker=worker)
            self.assertEqual(state["status"], "complete")
            self.assertEqual(len(state["agent_calls"]), 8)
            self.assertTrue((Path(temporary) / "prd.md").is_file())

    def test_confirmed_delivery_converges_after_failed_validation(self) -> None:
        writes = 0

        def worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
            nonlocal writes
            if "Clarification Review Agent" in prompt:
                return {"provider": provider, "model": "test", "status": "complete", "output": '{"status":"complete","blockers":[],"questions":[]}', "error": ""}
            if "Stage Quality Review Agent" in prompt:
                review_path = Path(prompt.split("Write ONLY one JSON object to ", 1)[1].split(" (UTF-8):", 1)[0])
                review_path.write_text(
                    '{"status":"pass","blocking_findings":[],"acceptance_evidence":["contract checked"]}',
                    encoding="utf-8",
                )
                return {"provider": provider, "model": "test", "status": "complete", "output": "", "error": ""}
            target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
            target.parent.mkdir(parents=True, exist_ok=True)
            writes += 1
            target.write_text(f"# artifact {writes}\n", encoding="utf-8")
            if target.name == "prd.md":
                target.with_name("prd.html").write_text("<!doctype html><html></html>", encoding="utf-8")
            return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}

        failed = [{"command": "scripts/validate_outputs.py", "status": "failed", "stdout": "missing section", "stderr": ""}]
        passed = [{"command": "scripts/validate_outputs.py", "status": "passed", "stdout": "", "stderr": ""}]
        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个 PRD", Path(temporary))
            (Path(temporary) / "prd.html").write_text("<!doctype html><html></html>", encoding="utf-8")
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            state["agent_calls"] = [
                {"phase": "intake", "provider": "test", "model": "test", "status": "complete"},
                {"phase": "clarification_review", "provider": "test", "model": "test", "status": "complete"},
            ]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            with patch("run_interactive_request._validate_delivery", side_effect=[failed, passed, passed]), patch(
                "run_interactive_request._trace_contract_findings", return_value="",
            ):
                _confirmed_delivery(state, "test", 1, worker=worker, max_revisions=1)
            self.assertEqual(state["status"], "complete")
            self.assertTrue(any(check["status"] == "failed" for check in state["validation"]))
            self.assertTrue(any(
                call.get("artifact") == "run-log.yaml"
                and call.get("execution_mode") == "deterministic_trace_materialization"
                for call in state["agent_calls"]
            ))

    def test_delivery_exposes_retry_recovery_when_agent_evidence_is_missing(self) -> None:
        def unauthenticated_worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
            marker = "Write one complete artifact at "
            target = Path(prompt.split(marker, 1)[1].split(".\n", 1)[0])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# artifact\n", encoding="utf-8")
            return {"status": "complete", "output": "written", "error": ""}

        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("做一个 PRD", Path(temporary))
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            state["agent_calls"] = [
                {"phase": "intake", "provider": "test", "model": "test", "status": "complete"},
                {"phase": "clarification_review", "provider": "test", "model": "test", "status": "complete"},
            ]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            _confirmed_delivery(state, "test", 1, worker=unauthenticated_worker)
            self.assertEqual(state["status"], "recovery_required")
            self.assertIn("provider/model", state["last_error"])
            self.assertEqual(state["recovery"]["failed_stage"], "confirmed-requirements.md")
            self.assertEqual(state["recovery"]["retry_entry"], "--confirm")
            self.assertTrue(state["recovery"]["retry_action"].endswith(" --confirm"))
            self.assertNotIn("--provider", state["recovery"]["retry_action"])
            self.assertNotIn("--model", state["recovery"]["retry_action"])
            self.assertEqual(
                state["recovery"]["failed_runtime"],
                {"provider": "test", "model": None, "retry_policy": "reselect_from_current_device"},
            )
            self.assertEqual(state["recovery"]["completed_artifacts"], [])
            self.assertFalse((Path(temporary) / "prd.md").exists())

    def test_delivery_agent_uses_project_staging_directory_as_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pm-copilot-outputs" / "example"
            folder.mkdir(parents=True)
            state = create_state("做一个 PRD", folder)
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]

            def worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
                target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
                self.assertEqual(cwd, target.parent)
                self.assertNotEqual(cwd, Path(__file__).resolve().parents[1])
                target.write_text("# confirmed\n", encoding="utf-8")
                return {"provider": "test", "model": "test", "status": "complete", "output": "written", "error": ""}

            self.assertTrue(_run_artifact_agent(state, "confirmed-requirements.md", "test", 1, worker=worker))
            self.assertTrue((folder / "confirmed-requirements.md").is_file())

    def test_controller_trace_promotes_only_controller_materialized_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pm-copilot-outputs" / "example"
            folder.mkdir(parents=True)
            state = create_state("做一个 PRD", folder)
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            (folder / "prd.md").write_text("# 新需求\n\n### 5.1 新能力\n", encoding="utf-8")
            (folder / "run-log.yaml").write_text("legacy: stale\n", encoding="utf-8")
            worker_called = False

            def worker(*args, **kwargs):
                nonlocal worker_called
                worker_called = True
                raise AssertionError("controller-owned run-log must not invoke a remote worker")

            self.assertTrue(_run_artifact_agent(state, "run-log.yaml", "test", 1, worker=worker))
            self.assertFalse(worker_called)
            promoted = (folder / "run-log.yaml").read_text(encoding="utf-8")
            self.assertIn("pm_copilot_revision: controller-deterministic-trace", promoted)
            self.assertNotIn("legacy: stale", promoted)
            self.assertNotIn(".example.stage-", promoted)

    def test_in_place_revision_trace_is_materialized_without_a_remote_writer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            target = folder / "run-log.yaml"
            target.write_text("legacy: stale\n", encoding="utf-8")
            (folder / "prd.md").write_text(
                "# 修订需求\n\n| 5.1 | 状态规则 |\n\n### 5.1 状态规则\n",
                encoding="utf-8",
            )
            state = create_state("修订 5.1", folder)
            state["turns"] = [{
                "summary": "已确认", "scope": {"goal": "修订状态规则", "in_scope": ["5.1"]},
                "assumptions": [], "risks": [],
            }]
            state["revision_requirement_ids"] = ["5.1"]
            state["revision_history"] = [{
                "request": "仅修订 5.1",
                "prd_before_sha256": "old-prd",
                "html_before_sha256": "old-html",
                "at": "2026-09-03T00:00:00+00:00",
            }]
            state["delivery_variant"] = "in_place_revision"
            _materialize_controller_trace(state, target)
            trace = yaml.safe_load(target.read_text(encoding="utf-8"))
            self.assertEqual(trace["artifact_lineage"]["mode"], "in_place_revision")
            self.assertEqual(trace["artifact_lineage"]["revised_requirement_ids"], ["5.1"])
            self.assertEqual(trace["artifact_lineage"]["revision_evidence_path"], "revision-evidence.json")
            self.assertNotIn("legacy", target.read_text(encoding="utf-8"))
            evidence = json.loads((folder / "revision-evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["controller_scope_ids"], ["5.1"])
            target.write_text("legacy: stale\n", encoding="utf-8")

            worker_called = False

            def worker(*args, **kwargs):
                nonlocal worker_called
                worker_called = True
                raise AssertionError("revision trace must not invoke a remote writer")

            self.assertTrue(_run_artifact_agent(state, "run-log.yaml", "seawork", 1, worker=worker))
            self.assertFalse(worker_called)
            self.assertTrue((folder / "revision-evidence.json").is_file())
            self.assertEqual(
                state["agent_calls"][-1]["execution_mode"],
                "deterministic_trace_materialization",
            )

    def test_in_place_revision_trace_migrates_legacy_missing_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            target = folder / "run-log.yaml"
            # This mirrors the pre-ledger traces found in existing canonical runs.
            target.write_text("schema_version: 1\n", encoding="utf-8")
            state = create_state("修订 5.1", folder)
            state["revision_history"] = [{"request": "仅修订 5.1", "at": "2026-09-03T00:00:00+00:00"}]

            _materialize_controller_trace(state, target)
            text = target.read_text(encoding="utf-8")
            self.assertIn("agent_task_ledger:", text)
            self.assertIn("loop_state:", text)
            self.assertIn("readiness:", text)
            self.assertNotIn("schema_version: 1", text)

    def test_controller_trace_finalization_never_marks_failed_checks_as_passed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "prd.md").write_text("# 新需求\n\n### 5.1 新能力\n", encoding="utf-8")
            target = folder / "run-log.yaml"
            state = create_state("新增能力", folder)
            state["turns"] = [{"summary": "已确认", "scope": {"goal": "新增能力"}, "assumptions": [], "risks": []}]
            _materialize_controller_trace(state, target)

            finalized = _finalize_deterministic_trace(folder, [{
                "command": "scripts/validate_outputs.py", "status": "failed",
                "stdout": "required marker missing", "stderr": "",
            }])

            trace = yaml.safe_load(target.read_text(encoding="utf-8"))
            self.assertFalse(finalized)
            self.assertIs(trace["quality_decision"]["passed"], False)
            self.assertNotEqual(trace["termination_condition"]["status"], "complete")
            self.assertTrue(all(item["status"] != "passed" for item in trace["validation_results"]))

    def test_revision_evidence_is_promoted_with_the_validated_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "pm-copilot-outputs" / "example"
            workspace = canonical.parent / ".example.delivery-stage" / canonical.name
            canonical.mkdir(parents=True)
            workspace.mkdir(parents=True)
            (workspace / "confirmed-requirements.md").write_text("# confirmed\n", encoding="utf-8")
            (workspace / "prd.md").write_text("# revised\n", encoding="utf-8")
            (workspace / "prd.html").write_text("<!doctype html><html></html>", encoding="utf-8")
            (workspace / "run-log.yaml").write_text("trace: current\n", encoding="utf-8")
            (workspace / "assets").mkdir()
            (workspace / "revision-evidence.json").write_text(
                '{"mode":"in_place_revision","prd_before_sha256":"old"}\n', encoding="utf-8",
            )
            state = create_state("修订需求", canonical)
            state["delivery_variant"] = "in_place_revision"
            state["delivery_workspace"] = str(workspace)

            _promote_delivery_workspace(state)

            self.assertEqual(
                (canonical / "revision-evidence.json").read_text(encoding="utf-8"),
                '{"mode":"in_place_revision","prd_before_sha256":"old"}\n',
            )
            self.assertEqual((canonical / "confirmed-requirements.md").read_text(encoding="utf-8"), "# confirmed\n")

    def test_promotion_excludes_non_content_metadata_from_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "pm-copilot-outputs" / "example"
            workspace = canonical.parent / ".example.delivery-stage" / canonical.name
            canonical.mkdir(parents=True)
            workspace.mkdir(parents=True)
            for name, content in {
                "confirmed-requirements.md": "# confirmed\n",
                "prd.md": "# current\n",
                "prd.html": "<!doctype html><html></html>\n",
                "run-log.yaml": "trace: current\n",
            }.items():
                (workspace / name).write_text(content, encoding="utf-8")
            canonical_assets = canonical / "assets"
            canonical_assets.mkdir()
            (canonical_assets / ".private.png").write_bytes(b"old metadata")
            workspace_assets = workspace / "assets"
            workspace_assets.mkdir()
            (workspace_assets / "visible.png").write_bytes(b"content")
            (workspace_assets / ".hidden.png").write_bytes(b"metadata")
            (workspace_assets / "desktop.ini").write_bytes(b"metadata")
            state = create_state("更新 PRD", canonical)
            state["delivery_workspace"] = str(workspace)

            _promote_delivery_workspace(state)

            self.assertTrue((canonical / "assets" / "visible.png").is_file())
            self.assertFalse((canonical / "assets" / ".private.png").exists())
            self.assertFalse((canonical / "assets" / ".hidden.png").exists())
            self.assertFalse((canonical / "assets" / "desktop.ini").exists())

    def test_promotion_rejects_a_staged_confirmed_attachment_with_different_bytes(self) -> None:
        """A same-name staged asset cannot diverge from the user-confirmed snapshot."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "pm-copilot-outputs" / "example"
            canonical.mkdir(parents=True)
            source = root / "attachments" / "result.png"
            source.parent.mkdir()
            source.write_bytes(b"confirmed attachment bytes")
            state = create_state("使用截图创建 PRD", canonical)
            register_input_assets(state, [source])
            workspace = _prepare_delivery_workspace(state)
            for name, content in {
                "confirmed-requirements.md": "# confirmed\n",
                "prd.md": "# current\n",
                "prd.html": "<!doctype html><html></html>\n",
                "run-log.yaml": "trace: current\n",
            }.items():
                (workspace / name).write_text(content, encoding="utf-8")
            (workspace / "assets" / "result.png").write_bytes(b"different staged bytes")

            with self.assertRaisesRegex(RuntimeError, "confirmed input asset SHA-256"):
                _promote_delivery_workspace(state)

            self.assertFalse((canonical / "assets" / "result.png").exists())

    def test_promotion_rejects_a_nested_canonical_source_material_symlink(self) -> None:
        """A late nested link cannot be dereferenced while building a candidate."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "pm-copilot-outputs" / "example"
            canonical.mkdir(parents=True)
            source = root / "attachments" / "result.png"
            source.parent.mkdir()
            source.write_bytes(b"confirmed attachment bytes")
            outside = root / "outside.png"
            outside.write_bytes(b"must not be copied")
            state = create_state("使用截图创建 PRD", canonical)
            register_input_assets(state, [source])
            workspace = _prepare_delivery_workspace(state)
            for name, content in {
                "confirmed-requirements.md": "# confirmed\n",
                "prd.md": "# current\n",
                "prd.html": "<!doctype html><html></html>\n",
                "run-log.yaml": "trace: current\n",
            }.items():
                (workspace / name).write_text(content, encoding="utf-8")
            link = canonical / "source-material" / "input-assets" / "late-link.png"
            try:
                link.symlink_to(outside)
            except OSError as error:
                self.skipTest(f"symbolic links are unavailable in this environment: {error}")

            with self.assertRaisesRegex(RuntimeError, "canonical PRD folder before promotion.*symbolic links"):
                _promote_delivery_workspace(state)

            self.assertFalse((canonical / "assets" / "result.png").exists())

    def test_non_revision_promotion_discards_stale_revision_evidence(self) -> None:
        """New and extracted deliveries must not reuse a prior revision's proof."""
        for variant in ("new", "extract_to_new"):
            with self.subTest(delivery_variant=variant), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                canonical = root / "pm-copilot-outputs" / "example"
                workspace = canonical.parent / ".example.delivery-stage" / canonical.name
                canonical.mkdir(parents=True)
                workspace.mkdir(parents=True)
                stale_evidence = '{"scope_validation":{"report_path":"tool-results/missing.json"}}\n'
                (canonical / "revision-evidence.json").write_text(stale_evidence, encoding="utf-8")
                for name, content in {
                    "confirmed-requirements.md": "# confirmed\n",
                    "prd.md": "# current\n",
                    "prd.html": "<!doctype html><html></html>\n",
                    "run-log.yaml": "trace: current\n",
                    "revision-evidence.json": stale_evidence,
                }.items():
                    (workspace / name).write_text(content, encoding="utf-8")
                (workspace / "assets").mkdir()
                state = create_state("新的独立需求", canonical)
                state.update({
                    "delivery_variant": variant,
                    "delivery_workspace": str(workspace),
                })

                _promote_delivery_workspace(state)

                self.assertFalse((canonical / "revision-evidence.json").exists())
                self.assertEqual((canonical / "prd.md").read_text(encoding="utf-8"), "# current\n")

    def test_promotion_retains_scope_report_referenced_by_revision_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "pm-copilot-outputs" / "example"
            workspace = canonical.parent / ".example.delivery-stage" / canonical.name
            canonical.mkdir(parents=True)
            workspace.mkdir(parents=True)
            (workspace / "confirmed-requirements.md").write_text("# confirmed\n", encoding="utf-8")
            (workspace / "prd.md").write_text("### 5.1 Revised requirement\n", encoding="utf-8")
            (workspace / "prd.html").write_text("<!doctype html><html></html>\n", encoding="utf-8")
            (workspace / "assets").mkdir()

            manifest = {
                "schema_version": 1,
                "requirement_ids": ["5.1"],
                "baseline": {"requirement_sections": {"5.1": {"sha256": "baseline"}}},
            }
            manifest_sha256 = hashlib.sha256(
                json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            staged_report = workspace / "tool-results" / "revision-scope-validation.json"
            staged_report.parent.mkdir()
            staged_report.write_text(
                json.dumps({"status": "passed", "manifest_sha256": manifest_sha256}),
                encoding="utf-8",
            )
            (workspace / "revision-evidence.json").write_text(json.dumps({
                "mode": "in_place_revision",
                "controller_scope_ids": ["5.1"],
                "deleted_requirement_ids": [],
                "baseline_requirement_ids": ["5.1"],
                "scope_manifest": manifest,
                "scope_validation": {
                    "status": "passed",
                    "report_path": "tool-results/revision-scope-validation.json",
                    "manifest_sha256": manifest_sha256,
                },
            }), encoding="utf-8")
            (workspace / "run-log.yaml").write_text(yaml.safe_dump({
                "agent_strategy": {"task_mode": "prd_delivery"},
                "resume_checkpoint": {"task_mode": "prd_delivery"},
                "artifact_lineage": {
                    "mode": "in_place_revision",
                    "target_prd_path": "prd.md",
                    "target_html_path": "prd.html",
                    "revision_evidence_path": "revision-evidence.json",
                    "revised_requirement_ids": ["5.1"],
                    "deleted_requirement_ids": [],
                    "historical_artifacts": [{
                        "path": "prd.md",
                        "role": "comparison_only",
                        "excluded_from_current_facts": True,
                    }],
                    "output_folder_reset": False,
                },
            }, allow_unicode=True, sort_keys=False), encoding="utf-8")
            state = create_state("修订 5.1", canonical)
            state["delivery_variant"] = "in_place_revision"
            state["delivery_workspace"] = str(workspace)

            _promote_delivery_workspace(state)

            self.assertEqual(
                (canonical / "tool-results" / "revision-scope-validation.json").read_text(encoding="utf-8"),
                staged_report.read_text(encoding="utf-8"),
            )
            self.assertEqual(validate_artifact_lineage(canonical / "run-log.yaml"), [])

    def test_promotion_rejects_revision_scope_report_path_outside_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "pm-copilot-outputs" / "example"
            workspace = canonical.parent / ".example.delivery-stage" / canonical.name
            canonical.mkdir(parents=True)
            workspace.mkdir(parents=True)
            (workspace / "revision-evidence.json").write_text(json.dumps({
                "scope_validation": {"report_path": "../outside.json"},
            }), encoding="utf-8")
            (workspace / "run-log.yaml").write_text("trace: current\n", encoding="utf-8")
            state = create_state("修订 5.1", canonical)
            state["delivery_variant"] = "in_place_revision"
            state["delivery_workspace"] = str(workspace)

            with self.assertRaisesRegex(RuntimeError, "scope_validation report_path escapes the staged run folder"):
                _promote_delivery_workspace(state)

    def test_promotion_replaces_source_material_from_the_validated_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "pm-copilot-outputs" / "example"
            workspace = canonical.parent / ".example.delivery-stage" / canonical.name
            canonical.mkdir(parents=True)
            workspace.mkdir(parents=True)
            for name, content in {
                "confirmed-requirements.md": "# confirmed\n",
                "prd.md": "# current\n",
                "prd.html": "<!doctype html><html></html>\n",
                "run-log.yaml": "trace: current\n",
            }.items():
                (workspace / name).write_text(content, encoding="utf-8")
            (workspace / "assets").mkdir()
            canonical_packet = canonical / "source-material" / "implemented-feature-evidence.json"
            canonical_packet.parent.mkdir()
            canonical_packet.write_text('{"state":"tampered canonical"}\n', encoding="utf-8")
            staged_packet = workspace / "source-material" / "implemented-feature-evidence.json"
            staged_packet.parent.mkdir()
            staged_packet.write_text('{"state":"validated staging"}\n', encoding="utf-8")
            state = create_state("还原已实现功能 PRD", canonical)
            state["delivery_workspace"] = str(workspace)

            _promote_delivery_workspace(state)

            self.assertEqual(
                canonical_packet.read_text(encoding="utf-8"),
                '{"state":"validated staging"}\n',
            )

    def test_promotion_rejects_a_staged_implemented_evidence_packet_that_no_longer_matches_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "pm-copilot-outputs" / "example"
            workspace = canonical.parent / ".example.delivery-stage" / canonical.name
            canonical.mkdir(parents=True)
            workspace.mkdir(parents=True)
            for name, content in {
                "confirmed-requirements.md": "# confirmed\n",
                "prd.md": "# current\n",
                "prd.html": "<!doctype html><html></html>\n",
            }.items():
                (workspace / name).write_text(content, encoding="utf-8")
            (workspace / "assets").mkdir()
            packet_payload = {"branch_name": "feature/canvas", "changed_files": ["src/canvas.ts"]}
            staged_packet = workspace / "source-material" / "implemented-feature-evidence.json"
            staged_packet.parent.mkdir()
            staged_packet.write_text(json.dumps(packet_payload), encoding="utf-8")
            expected_digest = hashlib.sha256(staged_packet.read_bytes()).hexdigest()
            (workspace / "run-log.yaml").write_text(
                yaml.safe_dump({
                    "agent_strategy": {"task_mode": "implemented_feature_prd"},
                    "resume_checkpoint": {"task_mode": "implemented_feature_prd"},
                    "artifact_lineage": {
                        "mode": "new_run",
                        "output_folder_reset": True,
                        "target_prd_path": "",
                        "target_html_path": "",
                        "revision_evidence_path": "",
                        "revised_requirement_ids": [],
                        "source_snapshot_path": "",
                        "source_prd_display_name": "",
                        "source_prd_sha256": "",
                        "selected_source_scope": [],
                        "source_scope_resolution": [],
                        "historical_artifacts": [],
                    },
                    "implemented_feature_prd": {
                        "active": True,
                        "mode": "implemented_feature_prd",
                        **packet_payload,
                        "evidence_packet": {
                            "path": "source-material/implemented-feature-evidence.json",
                            "sha256": expected_digest,
                            "imported_result_refs": [],
                        },
                    },
                }, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            canonical_packet = canonical / "source-material" / "implemented-feature-evidence.json"
            canonical_packet.parent.mkdir()
            canonical_packet.write_text('{"state":"old canonical"}\n', encoding="utf-8")
            # Simulate a concurrent staged input mutation after final staging
            # validation but before the publish transaction begins.
            staged_packet.write_text('{"state":"tampered staging"}\n', encoding="utf-8")
            state = create_state("还原已实现功能 PRD", canonical)
            state["delivery_workspace"] = str(workspace)

            with self.assertRaisesRegex(RuntimeError, "candidate delivery provenance validation failed"):
                _promote_delivery_workspace(state)

            self.assertEqual(
                canonical_packet.read_text(encoding="utf-8"),
                '{"state":"old canonical"}\n',
            )

    def test_promotion_retains_only_trace_referenced_tool_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "pm-copilot-outputs" / "example"
            workspace = canonical.parent / ".example.delivery-stage" / canonical.name
            canonical.mkdir(parents=True)
            workspace.mkdir(parents=True)
            for name, content in {
                "confirmed-requirements.md": "# confirmed\n",
                "prd.md": "# current\n",
                "prd.html": "<!doctype html><html></html>\n",
                "run-log.yaml": (
                    "implemented_feature_prd:\n"
                    "  visual_capture_recovery:\n"
                    "    - attempt_id: capture-1\n"
                    "      result_ref: tool-results/capture-1.json\n"
                ),
            }.items():
                (workspace / name).write_text(content, encoding="utf-8")
            (workspace / "assets").mkdir()
            results = workspace / "tool-results"
            results.mkdir()
            (results / "capture-1.json").write_text('{"status":"failed"}\n', encoding="utf-8")
            (results / "stale-controller.log").write_text("discard me\n", encoding="utf-8")
            old_results = canonical / "tool-results"
            old_results.mkdir()
            (old_results / "old.json").write_text("obsolete\n", encoding="utf-8")
            state = create_state("还原已实现功能 PRD", canonical)
            state["delivery_workspace"] = str(workspace)

            _promote_delivery_workspace(state)

            self.assertEqual(
                (canonical / "tool-results" / "capture-1.json").read_text(encoding="utf-8"),
                '{"status":"failed"}\n',
            )
            self.assertFalse((canonical / "tool-results" / "stale-controller.log").exists())
            self.assertFalse((canonical / "tool-results" / "old.json").exists())

    def test_promotion_rejects_trace_result_reference_outside_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "pm-copilot-outputs" / "example"
            workspace = canonical.parent / ".example.delivery-stage" / canonical.name
            canonical.mkdir(parents=True)
            workspace.mkdir(parents=True)
            for name, content in {
                "confirmed-requirements.md": "# confirmed\n",
                "prd.md": "# current\n",
                "prd.html": "<!doctype html><html></html>\n",
                "run-log.yaml": "evidence:\n  result_ref: ../outside.json\n",
            }.items():
                (workspace / name).write_text(content, encoding="utf-8")
            (workspace / "assets").mkdir()
            state = create_state("Create a PRD", canonical)
            state["delivery_workspace"] = str(workspace)

            with self.assertRaisesRegex(RuntimeError, "escapes the staged run folder"):
                _promote_delivery_workspace(state)

            self.assertFalse((canonical / "prd.md").exists())

    def test_promotion_rolls_back_every_official_artifact_after_later_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "pm-copilot-outputs" / "example"
            workspace = canonical.parent / ".example.delivery-stage" / canonical.name
            canonical.mkdir(parents=True)
            workspace.mkdir(parents=True)
            for name, content in {
                "confirmed-requirements.md": "old confirmed\n",
                "prd.md": "old prd\n",
                "prd.html": "<html>old</html>\n",
                "run-log.yaml": "old: trace\n",
            }.items():
                (canonical / name).write_text(content, encoding="utf-8")
                (workspace / name).write_text("new " + content, encoding="utf-8")
            (canonical / "assets").mkdir()
            (canonical / "assets" / "old.png").write_bytes(b"old asset")
            (workspace / "assets").mkdir()
            (workspace / "assets" / "new.png").write_bytes(b"new asset")
            old_results = canonical / "tool-results"
            old_results.mkdir()
            (old_results / "old.json").write_text('{"old":true}\n', encoding="utf-8")

            def snapshot(folder: Path) -> dict[str, bytes]:
                return {
                    path.relative_to(folder).as_posix(): path.read_bytes()
                    for path in folder.rglob("*") if path.is_file()
                }

            before = snapshot(canonical)
            state = create_state("更新 PRD", canonical)
            state["delivery_workspace"] = str(workspace)
            backup = _promote_delivery_workspace(state)
            self.assertNotEqual(snapshot(canonical), before)

            _rollback_delivery_promotion(canonical, backup)

            self.assertEqual(snapshot(canonical), before)

    def test_promotion_copy_failure_leaves_canonical_artifacts_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "pm-copilot-outputs" / "example"
            workspace = canonical.parent / ".example.delivery-stage" / canonical.name
            canonical.mkdir(parents=True)
            workspace.mkdir(parents=True)
            for name, content in {
                "confirmed-requirements.md": "old confirmed\n",
                "prd.md": "old prd\n",
                "prd.html": "<html>old</html>\n",
                "run-log.yaml": "old: trace\n",
            }.items():
                (canonical / name).write_text(content, encoding="utf-8")
                (workspace / name).write_text("new " + content, encoding="utf-8")
            (canonical / "assets").mkdir()
            (canonical / "assets" / "old.png").write_bytes(b"old asset")
            (workspace / "assets").mkdir()
            (workspace / "assets" / "new.png").write_bytes(b"new asset")
            before = {
                path.relative_to(canonical).as_posix(): path.read_bytes()
                for path in canonical.rglob("*") if path.is_file()
            }
            state = create_state("更新 PRD", canonical)
            state["delivery_workspace"] = str(workspace)
            original_copy = _atomic_copy
            calls = 0

            def failing_copy(source: Path, destination: Path) -> None:
                nonlocal calls
                calls += 1
                if calls == 3:
                    raise OSError("simulated publish copy failure")
                original_copy(source, destination)

            with patch("run_interactive_request._atomic_copy", side_effect=failing_copy):
                with self.assertRaisesRegex(OSError, "simulated publish copy failure"):
                    _promote_delivery_workspace(state)

            after = {
                path.relative_to(canonical).as_posix(): path.read_bytes()
                for path in canonical.rglob("*") if path.is_file()
            }
            self.assertEqual(after, before)

    def test_stage_review_records_the_delivery_workspace_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "pm-copilot-outputs" / "example"
            delivery = canonical.parent / ".example.delivery-stage" / canonical.name
            canonical.mkdir(parents=True)
            delivery.mkdir(parents=True)
            (canonical / "prd.md").write_text("# stale canonical\n", encoding="utf-8")
            staged_prd = delivery / "prd.md"
            staged_prd.write_text("# reviewed staged PRD\n", encoding="utf-8")
            state = create_state("修订需求", canonical)
            state["delivery_workspace"] = str(delivery)
            state["turns"] = [{"summary": "已确认", "scope": {"goal": "修订需求"}, "assumptions": [], "risks": []}]

            def worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
                review_path = Path(prompt.split("Write ONLY one JSON object to ", 1)[1].split(" (UTF-8):", 1)[0])
                review_path.write_text(
                    '{"status":"pass","summary":"checked","blocking_findings":[],"acceptance_evidence":["staged bytes"]}',
                    encoding="utf-8",
                )
                return {"provider": provider, "model": "test", "status": "complete", "output": "", "error": ""}

            passed, _ = _review_artifact(state, "prd.md", "test", 1, worker=worker)
            self.assertTrue(passed)
            self.assertEqual(
                state["delivery_stages"]["prd.md"]["reviewed_sha256"],
                hashlib.sha256(staged_prd.read_bytes()).hexdigest(),
            )

    def test_retry_reuse_restores_only_fully_reviewed_content_stages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state, canonical, workspace = self._eligible_retry_reuse_state(Path(temporary))
            _snapshot_reusable_delivery_artifacts(state)
            cache = _retry_reuse_cache_folder(state)
            self.assertTrue(cache.is_dir())

            # A malicious or obsolete trace cache entry must never cross the
            # retry boundary; every run creates fresh controller provenance.
            cached_trace = cache / "run-log.yaml"
            cached_trace.write_text("untrusted: old trace\n", encoding="utf-8")
            manifest_path = cache / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifacts"].append({
                "artifact": "run-log.yaml",
                "sha256": hashlib.sha256(cached_trace.read_bytes()).hexdigest(),
            })
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            restored = _prepare_delivery_workspace(state)

            self.assertEqual(
                (restored / "confirmed-requirements.md").read_text(encoding="utf-8"),
                "# Confirmed requirements\n",
            )
            self.assertEqual(
                (restored / "prd.md").read_text(encoding="utf-8"),
                "# Staged PRD\n\n### 5.1 Staged requirement\n",
            )
            self.assertEqual(
                (restored / "prd.html").read_text(encoding="utf-8"),
                "<!doctype html><html><body>staged</body></html>\n",
            )
            self.assertFalse((restored / "run-log.yaml").exists())
            self.assertEqual(state["retry_reuse"]["status"], "consumed")
            self.assertEqual(
                state["retry_reuse"]["artifacts"],
                ["confirmed-requirements.md", "prd.md"],
            )
            self.assertEqual(
                state["delivery_stages"]["prd.md"]["reuse_source"],
                "prior_verified_delivery_workspace",
            )
            self.assertFalse(cache.exists())
            self.assertEqual(canonical, Path(state["folder"]))
            self.assertEqual(restored.resolve(), workspace.resolve())

    def test_in_place_recovery_rebuilds_scope_report_before_trace_materialization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "pm-copilot-outputs" / "example"
            workspace = canonical.parent / ".example.delivery-stage" / canonical.name
            canonical.mkdir(parents=True)
            (canonical / "assets").mkdir()
            baseline_prd = "| 5.1 | Result |\n\n### 5.1 Result\nOld rule.\n"
            revised_prd = baseline_prd.replace("Old rule.", "Revised rule.")
            baseline_html = "<!doctype html><html><body>baseline</body></html>\n"
            revised_html = "<!doctype html><html><body>revised</body></html>\n"
            (canonical / "prd.md").write_text(baseline_prd, encoding="utf-8")
            (canonical / "prd.html").write_text(baseline_html, encoding="utf-8")
            workspace.mkdir(parents=True)
            (workspace / "prd.md").write_text(revised_prd, encoding="utf-8")
            (workspace / "prd.html").write_text(revised_html, encoding="utf-8")
            stale_report = workspace / "tool-results" / "revision-scope-validation.json"
            stale_report.parent.mkdir()
            stale_report.write_text('{"status":"passed","origin":"discarded-workspace"}\n', encoding="utf-8")

            state = create_state("修订 5.1", canonical)
            state.update({
                "delivery_variant": "in_place_revision",
                "revision_requirement_ids": ["5.1"],
                "revision_history": [{
                    "mode": "in_place_revision",
                    "request": "仅修订 5.1",
                    "prd_before_sha256": hashlib.sha256(baseline_prd.encode("utf-8")).hexdigest(),
                    "html_before_sha256": hashlib.sha256(baseline_html.encode("utf-8")).hexdigest(),
                    "baseline_requirement_ids": ["5.1"],
                }],
                "confirmed_fact_packet": {
                    "summary": "已确认修订范围",
                    "scope": {"goal": "修订 5.1", "in_scope": ["5.1"]},
                    "assumptions": [], "decisions": [], "risks": [],
                },
                "user_confirmation": {"confirmed": True, "source": "test"},
                "delivery_workspace": str(workspace),
            })
            manifest = _materialize_revision_scope_manifest(state)
            fingerprint = _confirmed_scope_fingerprint(state)
            digest = hashlib.sha256(revised_prd.encode("utf-8")).hexdigest()
            state["delivery_stages"] = {
                "prd.md": {
                    "artifact_status": "promoted",
                    "review_status": "passed",
                    "artifact_sha256": digest,
                    "reviewed_sha256": digest,
                    "scope_fingerprint": fingerprint,
                    "pm_copilot_version": _active_runtime_version(),
                },
            }
            state["revision_scope_validation"] = {
                "status": "passed",
                "report_path": "tool-results/revision-scope-validation.json",
                "manifest_sha256": "old-workspace-report",
            }

            _restart_delivery_attempt(state)
            restored = _prepare_delivery_workspace(state)

            report = json.loads((restored / "tool-results" / "revision-scope-validation.json").read_text(encoding="utf-8"))
            expected_manifest_sha256 = hashlib.sha256(
                json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["manifest_sha256"], expected_manifest_sha256)
            self.assertNotIn("discarded-workspace", json.dumps(report))
            self.assertEqual(state["delivery_stages"]["prd.md"]["reuse_source"], "prior_verified_delivery_workspace")

            _materialize_controller_trace(state, restored / "run-log.yaml")
            self.assertEqual(validate_artifact_lineage(restored / "run-log.yaml"), [])

    def test_retry_reuse_rejects_fingerprint_version_review_and_hash_mismatches(self) -> None:
        with self.subTest("review mismatch is never snapshotted"):
            with tempfile.TemporaryDirectory() as temporary:
                state, _, _ = self._eligible_retry_reuse_state(Path(temporary))
                for stage in state["delivery_stages"].values():
                    stage["review_status"] = "needs_revision"
                _snapshot_reusable_delivery_artifacts(state)
                self.assertNotIn("retry_reuse", state)
                self.assertFalse(_retry_reuse_cache_folder(state).exists())

        with self.subTest("confirmed scope mismatch is never restored"):
            with tempfile.TemporaryDirectory() as temporary:
                state, _, _ = self._eligible_retry_reuse_state(Path(temporary))
                _snapshot_reusable_delivery_artifacts(state)
                state["raw_request"] = "Changed confirmed request"
                restored = _prepare_delivery_workspace(state)
                self.assertFalse((restored / "confirmed-requirements.md").exists())
                self.assertFalse((restored / "prd.md").exists())
                self.assertEqual(state["retry_reuse"]["status"], "discarded")
                self.assertEqual(state["retry_reuse"]["reason"], "scope_or_runtime_changed")

        with self.subTest("runtime version mismatch is never restored"):
            with tempfile.TemporaryDirectory() as temporary:
                state, _, _ = self._eligible_retry_reuse_state(Path(temporary))
                _snapshot_reusable_delivery_artifacts(state)
                with patch("run_interactive_request._active_runtime_version", return_value="different-runtime"):
                    restored = _prepare_delivery_workspace(state)
                self.assertFalse((restored / "confirmed-requirements.md").exists())
                self.assertFalse((restored / "prd.md").exists())
                self.assertEqual(state["retry_reuse"]["status"], "discarded")
                self.assertEqual(state["retry_reuse"]["reason"], "scope_or_runtime_changed")

        with self.subTest("cached hash mismatch is never restored"):
            with tempfile.TemporaryDirectory() as temporary:
                state, _, _ = self._eligible_retry_reuse_state(Path(temporary))
                _snapshot_reusable_delivery_artifacts(state)
                cache = _retry_reuse_cache_folder(state)
                (cache / "confirmed-requirements.md").write_text("tampered\n", encoding="utf-8")
                (cache / "prd.md").write_text("tampered\n", encoding="utf-8")
                restored = _prepare_delivery_workspace(state)
                self.assertFalse((restored / "confirmed-requirements.md").exists())
                self.assertFalse((restored / "prd.md").exists())
                self.assertEqual(state["retry_reuse"]["status"], "discarded")
                self.assertEqual(state["retry_reuse"]["reason"], "cache_hash_mismatch")

    def test_quality_decision_validation_failure_regenerates_trace_locally(self) -> None:
        failed_quality_check = [{
            "command": "scripts/validate_outputs.py",
            "status": "failed",
            "stdout": "Quality decision must explicitly pass for final generated artifacts",
            "stderr": "",
        }]
        passed_checks = [{
            "command": "scripts/validate_outputs.py", "status": "passed", "stdout": "", "stderr": "",
        }]
        with tempfile.TemporaryDirectory() as temporary:
            canonical = Path(temporary) / "pm-copilot-outputs" / "example"
            canonical.mkdir(parents=True)
            state = create_state("Create a PRD", canonical)
            state["turns"] = [{"summary": "Confirmed", "scope": {"goal": "Create a PRD"}, "assumptions": [], "risks": []}]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            regenerated: list[str] = []
            original_runner = _run_artifact_agent

            def worker(*args, **kwargs):
                self.fail("controller-owned run-log generation and review must not invoke a remote worker")

            def deliver(state_arg, artifact, *args, **kwargs):
                target = Path(state_arg["delivery_workspace"]) / artifact
                if artifact == "run-log.yaml":
                    _materialize_controller_trace(state_arg, target)
                else:
                    target.write_text(f"# {artifact}\n", encoding="utf-8")
                return True

            def record_and_run(*args, **kwargs):
                regenerated.append(args[1])
                return original_runner(*args, **kwargs)

            with patch("run_interactive_request._deliver_artifact_to_quality_gate", side_effect=deliver), patch(
                "run_interactive_request._run_artifact_agent", side_effect=record_and_run,
            ), patch(
                "run_interactive_request._validate_delivery",
                side_effect=[failed_quality_check, failed_quality_check, passed_checks, passed_checks],
            ), patch(
                "run_interactive_request._trace_contract_findings", return_value="",
            ), patch(
                "run_interactive_request._required_production_evidence", return_value=(False, "test stop"),
            ):
                _confirmed_delivery(state, "codex", 1, worker=worker, max_revisions=1)

            self.assertEqual(regenerated, ["run-log.yaml"])
            self.assertTrue(any(
                call.get("artifact") == "run-log.yaml"
                and call.get("execution_mode") == "deterministic_trace_materialization"
                for call in state["agent_calls"]
            ))
            self.assertFalse(any(call.get("artifact") == "prd.md" for call in state["agent_calls"]))

    def test_delivery_checkpoint_survives_interruption_after_artifact_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            state_path = folder / "interactive-run.json"
            state = create_state("做一个 PRD", folder)
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            _write_json(state_path, state)

            def interrupted_worker(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
                if "Stage Quality Review Agent" in prompt:
                    raise KeyboardInterrupt("simulated controller interruption")
                target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("# confirmed\n", encoding="utf-8")
                return {"provider": "test", "model": "test", "status": "complete", "output": "written", "error": ""}

            with self.assertRaises(KeyboardInterrupt):
                _confirmed_delivery(state, "test", 1, worker=interrupted_worker, state_path=state_path)
            persisted = __import__("json").loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "failed")
            self.assertEqual(persisted["termination"], "failed")
            self.assertTrue(persisted["user_confirmation"]["confirmed"])
            self.assertIn("confirmed-requirements.md", persisted["artifacts"])
            self.assertEqual(persisted["delivery_stages"]["confirmed-requirements.md"]["artifact_status"], "promoted")

    def test_delivery_exception_always_converges_from_running(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            state_path = folder / "interactive-run.json"
            state = create_state("做一个 PRD", folder)
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            state["status"] = "confirmed"
            _write_json(state_path, state)

            def exploding_worker(*args, **kwargs):
                raise RuntimeError("transport exploded")

            with self.assertRaises(RuntimeError):
                _confirmed_delivery(state, "test", 1, worker=exploding_worker, state_path=state_path)
            persisted = __import__("json").loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "failed")
            self.assertEqual(persisted["termination"], "failed")
            self.assertIn("transport exploded", persisted["last_error"])

    def test_interactive_budget_exhaustion_recovers_before_next_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            state_path = folder / "interactive-run.json"
            state = create_state("做一个 PRD", folder)
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            state["user_confirmation"] = {"confirmed": True, "source": "test"}
            _write_json(state_path, state)
            with patch("run_interactive_request.time.monotonic", side_effect=[0, 61]):
                _confirmed_delivery(state, "test", 1, worker=lambda *args: self.fail("budget should stop delivery"), state_path=state_path, interactive_timeout=1)
            persisted = __import__("json").loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "recovery_required")
            self.assertEqual(persisted["termination"], "retry_required")
            self.assertNotEqual(persisted["status"], "delivery")

    def test_identical_recovery_attempts_stop_before_another_agent_call(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            state = create_state("做一个 PRD", folder)
            state.update({
                "status": "recovery_required",
                "termination": "retry_required",
                "restart_delivery": True,
                "last_error": "Seawork control plane unavailable",
                "last_failure_category": "control_plane_unavailable",
                "recovery": {"failed_stage": "confirmed-requirements.md"},
                "turns": [{"summary": "已澄清", "scope": {"goal": "稳定目标"}, "assumptions": [], "risks": []}],
                "confirmed_fact_packet": {"summary": "已澄清", "scope": {"goal": "稳定目标"}, "assumptions": [], "risks": []},
                "user_confirmation": {"confirmed": True, "source": "test"},
            })
            decision = _retry_failure_guard_decision(state, "seawork", "codex/gpt-5.6-terra")
            state["delivery_failure_history"] = [
                {"failure_fingerprint": decision["fingerprint"], "outcome": "no_progress"},
                {"failure_fingerprint": decision["fingerprint"], "outcome": "no_progress"},
            ]
            dispatched = False

            def worker(*args, **kwargs):
                nonlocal dispatched
                dispatched = True
                return {"provider": "seawork", "model": "codex/gpt-5.6-terra", "status": "failed"}

            _confirmed_delivery(
                state, "seawork", 1, worker=worker,
                model="codex/gpt-5.6-terra",
            )
            self.assertFalse(dispatched)
            self.assertEqual(state["status"], "failed")
            self.assertEqual(state["termination"], "needs_maintenance")
            self.assertEqual(state["recovery"]["status"], "needs_maintenance")
            self.assertEqual(state["delivery_failure_guard"]["no_progress_attempts"], 2)

    def test_confirmation_freezes_fact_packet_for_downstream_agents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            state = create_state("做一个 PRD", folder)
            state["turns"] = [{
                "turn": 1, "user_text": "完整确认规则", "summary": "完整摘要",
                "scope": {"goal": "稳定目标", "in_scope": ["固定规则"]},
                "assumptions": ["无猜测"], "decisions": ["D1"], "risks": [],
                "buckets": {"can_draft_with_stated_assumption": [], "must_confirm_before_development_or_launch": []},
            }]
            state["user_confirmation"] = {"confirmed": True, "at": "now"}
            from run_interactive_request import _confirmed_fact_source, _confirmation_packet
            state["confirmed_fact_packet"] = json.loads(json.dumps(state["turns"][-1]))
            state["turns"].append({"turn": 2, "summary": "丢失细节的后续摘要", "scope": {}})
            self.assertEqual(_confirmed_fact_source(state)["scope"]["goal"], "稳定目标")
            self.assertEqual(_confirmation_packet(state)["scope"]["goal"], "稳定目标")

    def test_revision_scope_guard_rejects_missing_or_unapproved_heading_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = root / "baseline.md"
            candidate = root / "candidate.md"
            baseline.write_text("### 5.1 A\nold\n## 六、语言\nunchanged\n", encoding="utf-8")
            candidate.write_text("### 5.1 A\nnew\n## 六、语言\nchanged\n", encoding="utf-8")
            self.assertIsNotNone(_revision_scope_violation(candidate, baseline, ["5.1"]))
            self.assertIn(
                "no confirmed requirement selector",
                _revision_scope_violation(candidate, baseline, []) or "",
            )

    def test_controller_scope_contract_allows_selected_images_and_linked_copy_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            canonical = Path(temporary) / "canonical"
            assets = canonical / "assets"
            assets.mkdir(parents=True)
            for name in ("old-result.png", "execution-success.png", "execution-failure.png", "upload-node.png"):
                (assets / name).write_bytes(name.encode("utf-8"))
            baseline = (
                "| 5.1 | 节点执行结果 |\n| 5.2 | 上传节点 |\n\n"
                "### 5.1 节点执行结果\n旧规则。\n"
                "[[prd-detail-media src=\"./assets/old-result.png\" alt=\"old\" copy=\"旧执行结果\"]]\n\n"
                "### 5.2 上传节点\n保留上传规则。\n"
                "[[prd-detail-media src=\"./assets/upload-node.png\" alt=\"upload\" copy=\"上传节点\"]]\n\n"
                "## 六、多语言需求\n| 文案 | 说明 |\n| --- | --- |\n"
                "| 旧执行结果 | 旧说明 |\n| 上传节点 | 保留说明 |\n"
            )
            candidate = baseline.replace(
                "旧规则。\n[[prd-detail-media src=\"./assets/old-result.png\" alt=\"old\" copy=\"旧执行结果\"]]",
                "执行成功和执行失败。\n"
                "[[prd-detail-media src=\"./assets/execution-success.png\" alt=\"success\" copy=\"执行成功\"]]\n"
                "[[prd-detail-media src=\"./assets/execution-failure.png\" alt=\"failure\" copy=\"执行失败\"]]",
            ).replace("| 旧执行结果 | 旧说明 |", "| 执行成功 | 成功标题 |\n| 执行失败 | 失败标题 |")
            (canonical / "prd.md").write_text(baseline, encoding="utf-8")
            (canonical / "prd.html").write_text("<html>baseline</html>\n", encoding="utf-8")
            state = create_state("更新 5.1", canonical)
            state.update({
                "delivery_variant": "in_place_revision",
                "revision_requirement_ids": ["5.1"],
                "revision_history": [{
                    "mode": "in_place_revision", "request": (
                        "仅更新 5.1 对应多语言文案；5.1 仅保留两张固定顺序图示："
                        "./assets/execution-success.png、./assets/execution-failure.png；不引用第三张图。"
                    ),
                    "prd_before_sha256": hashlib.sha256(baseline.encode("utf-8")).hexdigest(),
                    "html_before_sha256": hashlib.sha256(b"<html>baseline</html>\n").hexdigest(),
                }],
                "confirmed_fact_packet": {
                    "scope": {"goal": "更新 5.1", "in_scope": ["5.1 对应中文文案和两张固定图示"]},
                    "decisions": [], "assumptions": [], "risks": [],
                },
                "user_confirmation": {"confirmed": True, "source": "test"},
            })
            manifest = _materialize_revision_scope_manifest(state)
            self.assertEqual(manifest["image_contracts"][0]["requirement_ids"], ["5.1"])
            workspace = _prepare_delivery_workspace(state)

            def worker(provider, prompt, cwd, *args):
                target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
                target.write_text(candidate, encoding="utf-8")
                return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}

            self.assertTrue(_run_artifact_agent(state, "prd.md", "test", 1, worker=worker))
            report = json.loads((workspace / "tool-results" / "revision-scope-validation.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "passed")
            updated = (workspace / "prd.md").read_text(encoding="utf-8")
            self.assertIn("上传节点\n保留上传规则", updated)
            self.assertIn("assets/upload-node.png", updated)

    def test_controller_scope_contract_restores_unselected_section_changes_before_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            canonical = Path(temporary) / "canonical"
            canonical.mkdir()
            baseline = "| 5.1 | A |\n| 5.2 | B |\n\n### 5.1 A\nold\n\n### 5.2 B\nprotected\n"
            (canonical / "prd.md").write_text(baseline, encoding="utf-8")
            (canonical / "prd.html").write_text("<html>baseline</html>\n", encoding="utf-8")
            state = create_state("更新 5.1", canonical)
            state.update({
                "delivery_variant": "in_place_revision", "revision_requirement_ids": ["5.1"],
                "revision_history": [{
                    "mode": "in_place_revision", "request": "仅更新 5.1",
                    "prd_before_sha256": hashlib.sha256(baseline.encode("utf-8")).hexdigest(),
                    "html_before_sha256": hashlib.sha256(b"<html>baseline</html>\n").hexdigest(),
                }],
                "confirmed_fact_packet": {"scope": {"goal": "更新 5.1"}, "decisions": [], "assumptions": [], "risks": []},
            })
            _materialize_revision_scope_manifest(state)
            _prepare_delivery_workspace(state)

            def worker(provider, prompt, cwd, *args):
                target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
                target.write_text(
                    baseline.replace("old", "updated selected rule").replace("protected", "mutated"),
                    encoding="utf-8",
                )
                return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}

            self.assertTrue(_run_artifact_agent(state, "prd.md", "test", 1, worker=worker))
            updated = (Path(str(state["delivery_workspace"])) / "prd.md").read_text(encoding="utf-8")
            self.assertIn("updated selected rule", updated)
            self.assertIn("### 5.2 B\nprotected", updated)
            self.assertNotIn("mutated", updated)
            self.assertEqual(state["revision_scope_validation"]["status"], "passed")
            self.assertEqual(state["status"], "new")

    def test_revision_skips_global_controller_transforms_outside_confirmed_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            canonical = Path(temporary) / "canonical"
            canonical.mkdir()
            original = (
                "| 5.1 | 已选需求 |\n| 5.3 | 未选需求 |\n\n"
                "### 5.1 已选需求\n节点执行失败，请稍后重试。\n\n"
                "### 5.3 未选需求\n节点执行失败，请稍后重试\n"
            )
            (canonical / "prd.md").write_text(original, encoding="utf-8")
            (canonical / "prd.html").write_text("<html>before</html>\n", encoding="utf-8")
            state = create_state("修订需求 5.1", canonical)
            state["delivery_variant"] = "in_place_revision"
            state["revision_requirement_ids"] = ["5.1"]
            state["revision_history"] = [{
                "mode": "in_place_revision",
                "prd_before_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
                "html_before_sha256": hashlib.sha256(b"<html>before</html>\n").hexdigest(),
            }]
            state["turns"] = [{"summary": "已澄清", "scope": {}, "assumptions": [], "risks": []}]
            workspace = _prepare_delivery_workspace(state)

            def worker(provider, prompt, cwd, *args):
                target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
                target.write_text(original.replace("### 5.1 已选需求", "### 5.1 已更新需求"), encoding="utf-8")
                return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}

            self.assertTrue(_run_artifact_agent(state, "prd.md", "test", 1, worker=worker))
            updated = (workspace / "prd.md").read_text(encoding="utf-8")
            self.assertIn("### 5.1 已更新需求", updated)
            self.assertIn("### 5.3 未选需求\n节点执行失败，请稍后重试\n", updated)
            self.assertNotIn("### 5.3 未选需求\n节点执行失败，请稍后重试。\n", updated)

    def test_revision_deletion_preserves_confirmed_scope_and_numbering_holes(self) -> None:
        names = {"5.1": "需求一", "5.2": "需求二", "5.3": "需求三"}
        rules = {"5.1": "规则一", "5.2": "规则二", "5.3": "规则三"}
        original = (
            "| 5.1 | 需求一 |\n| 5.2 | 需求二 |\n| 5.3 | 需求三 |\n\n"
            "### 5.1 需求一\n规则一\n\n"
            "### 5.2 需求二\n规则二\n\n"
            "### 5.3 需求三\n规则三\n"
        )
        for deleted_id, expected_ids in (("5.2", ["5.1", "5.3"]), ("5.3", ["5.1", "5.2"])):
            with self.subTest(deleted_id=deleted_id):
                with tempfile.TemporaryDirectory() as temporary:
                    canonical = Path(temporary) / "canonical"
                    canonical.mkdir()
                    (canonical / "prd.md").write_text(original, encoding="utf-8")
                    (canonical / "prd.html").write_text("<html>before</html>\n", encoding="utf-8")
                    state = create_state(f"删除需求 {deleted_id}", canonical)
                    state["delivery_variant"] = "in_place_revision"
                    state["revision_requirement_ids"] = [deleted_id]
                    state["revision_history"] = [{
                        "mode": "in_place_revision",
                        "prd_before_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
                        "html_before_sha256": hashlib.sha256(b"<html>before</html>\n").hexdigest(),
                        "baseline_requirement_ids": ["5.1", "5.2", "5.3"],
                    }]
                    state["turns"] = [{
                        "summary": "已确认删除范围", "scope": {"goal": f"删除 {deleted_id}"},
                        "assumptions": [], "risks": [],
                    }]
                    manifest = _materialize_revision_scope_manifest(state)
                    self.assertIsInstance(manifest, dict)
                    self.assertEqual(manifest["deleted_requirement_ids"], [deleted_id])
                    workspace = _prepare_delivery_workspace(state)
                    candidate = original.replace(f"| {deleted_id} | {names[deleted_id]} |\n", "")
                    section = f"### {deleted_id} {names[deleted_id]}\n{rules[deleted_id]}\n"
                    if deleted_id != "5.3":
                        section += "\n"
                    candidate = candidate.replace(section, "")

                    def worker(provider, prompt, cwd, *args):
                        target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
                        target.write_text(candidate, encoding="utf-8")
                        return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}

                    self.assertTrue(_run_artifact_agent(state, "prd.md", "test", 1, worker=worker))
                    staged_prd = workspace / "prd.md"
                    staged_text = staged_prd.read_text(encoding="utf-8")
                    observed_ids = [
                        requirement_id for requirement_id in ("5.1", "5.2", "5.3")
                        if f"| {requirement_id} |" in staged_text
                    ]
                    self.assertEqual(observed_ids, expected_ids)
                    lineage = _trace_lineage(state, staged_prd)
                    self.assertEqual(lineage["revised_requirement_ids"], [deleted_id])
                    self.assertEqual(lineage["deleted_requirement_ids"], [deleted_id])
                    _materialize_revision_evidence(state, workspace / "run-log.yaml")
                    evidence = json.loads((workspace / "revision-evidence.json").read_text(encoding="utf-8"))
                    self.assertEqual(evidence["controller_scope_ids"], [deleted_id])
                    self.assertEqual(evidence["deleted_requirement_ids"], [deleted_id])
                    self.assertEqual(evidence["baseline_requirement_ids"], ["5.1", "5.2", "5.3"])

    def test_promotion_time_revision_source_drift_requires_a_fresh_revision(self) -> None:
        for changed_name in ("prd.md", "prd.html", "assets/image.png"):
            with self.subTest(changed_name=changed_name):
                with tempfile.TemporaryDirectory() as temporary:
                    canonical = Path(temporary) / "canonical"
                    canonical.mkdir()
                    original_prd = "| 5.1 | 状态提示 |\n\n### 5.1 状态提示\n原始规则\n"
                    original_html = "<html>before</html>\n"
                    (canonical / "prd.md").write_text(original_prd, encoding="utf-8")
                    (canonical / "prd.html").write_text(original_html, encoding="utf-8")
                    (canonical / "assets").mkdir()
                    (canonical / "assets" / "image.png").write_bytes(b"original image")
                    state = create_state("修改需求 5.1", canonical)
                    state.update({
                        "delivery_variant": "in_place_revision",
                        "revision_requirement_ids": ["5.1"],
                        "revision_history": [{
                            "mode": "in_place_revision",
                            "prd_before_sha256": hashlib.sha256(original_prd.encode("utf-8")).hexdigest(),
                            "html_before_sha256": hashlib.sha256(original_html.encode("utf-8")).hexdigest(),
                            "baseline_requirement_ids": ["5.1"],
                        }],
                        "turns": [{"summary": "已确认", "scope": {"goal": "修改状态提示"}, "assumptions": [], "risks": []}],
                        "user_confirmation": {"confirmed": True, "source": "test"},
                    })

                    def deliver(state_arg, artifact, *args, **kwargs):
                        target = Path(state_arg["delivery_workspace"]) / artifact
                        if artifact == "confirmed-requirements.md":
                            target.write_text("# confirmed\n", encoding="utf-8")
                        elif artifact == "prd.md":
                            target.write_text("| 5.1 | 状态提示 |\n\n### 5.1 状态提示\n更新规则\n", encoding="utf-8")
                            target.with_name("prd.html").write_text("<html>staged</html>\n", encoding="utf-8")
                        else:
                            target.write_text("trace: staged\n", encoding="utf-8")
                        return True

                    actual_promote = _promote_delivery_workspace

                    def mutate_source_then_promote(state_arg):
                        changed_path = canonical / changed_name
                        if changed_path.suffix == ".png":
                            changed_path.write_bytes(b"external concurrent image update")
                        else:
                            changed_path.write_text(
                                f"external concurrent update to {changed_name}\n", encoding="utf-8",
                            )
                        return actual_promote(state_arg)

                    passed = [{"command": "test validation", "status": "passed", "stdout": "", "stderr": ""}]
                    with patch(
                        "run_interactive_request._deliver_artifact_to_quality_gate", side_effect=deliver,
                    ), patch(
                        "run_interactive_request._validate_delivery", return_value=passed,
                    ), patch(
                        "run_interactive_request._required_production_evidence", return_value=(True, ""),
                    ), patch(
                        "run_interactive_request._promote_delivery_workspace", side_effect=mutate_source_then_promote,
                    ):
                        _confirmed_delivery(state, "test", 1)

                    self.assertEqual(state["status"], "needs_input")
                    self.assertEqual(state["termination"], "needs_input")
                    self.assertEqual(state["required_input"]["field"], "revision_source_drift")
                    self.assertIn("重新发起原地修订", state["required_input"]["question"])
                    changed_path = canonical / changed_name
                    if changed_path.suffix == ".png":
                        self.assertEqual(changed_path.read_bytes(), b"external concurrent image update")
                    else:
                        self.assertIn("external concurrent update", changed_path.read_text(encoding="utf-8"))
                    self.assertFalse(state.get("delivery_promoted_at"))

    def test_legacy_interrupted_delivery_is_not_reported_as_awaiting_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "run"
            folder.mkdir()
            state = create_state("做一个 PRD", folder)
            state["status"] = "awaiting_confirmation"
            state["termination"] = "human_checkpoint"
            (folder / "confirmed-requirements.md").write_text("# partial\n", encoding="utf-8")
            (folder.parent / ".run.stage-abandoned").mkdir()
            self.assertTrue(_recover_interrupted_delivery(state, folder))
            self.assertEqual(state["status"], "recovery_required")
            self.assertEqual(state["termination"], "interrupted")
            self.assertIn("confirmed-requirements.md", state["recovery"]["promoted_artifacts"])

    def test_dead_controller_lease_recovers_running_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "run"
            folder.mkdir()
            state = create_state("做一个 PRD", folder)
            state.update({"status": "delivery", "termination": "running", "controller_pid": 99999999})
            (folder / "confirmed-requirements.md").write_text("# confirmed\n", encoding="utf-8")
            self.assertTrue(_recover_interrupted_delivery(state, folder))
            self.assertEqual(state["status"], "recovery_required")
            self.assertEqual(state["termination"], "interrupted")
            self.assertEqual(state["recovery"]["controller_pid"], 99999999)

    def test_stage_review_uses_full_confirmed_evidence_and_keeps_later_gates_nonblocking(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = create_state("创建独立 PRD", Path(temporary))
            state["turns"] = [{
                "user_text": "确认来源：/tmp/source/prd.md；端口 ID 由开发前确认。",
                "summary": "已确认迁移来源，端口契约后置。",
                "scope": {"goal": "迁移需求"}, "assumptions": [], "risks": [],
            }]
            prompt = _artifact_review_prompt(state, "confirmed-requirements.md", Path(temporary) / "review.json")
            self.assertIn("/tmp/source/prd.md", prompt)
            self.assertIn("not PRD\ngeneration blockers", prompt)

    def test_in_place_review_prompt_uses_controller_asset_attestation_and_typed_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state, _, workspace = self._in_place_review_state(Path(temporary))

            prompt = _artifact_review_prompt(state, "prd.md", workspace / ".stage-review.json")

            self.assertEqual(state["revision_asset_attestation"]["status"], "passed")
            self.assertIn("Controller-owned staged asset attestation", prompt)
            self.assertIn("\"status\":\"passed\"", prompt)
            self.assertIn("controller attestation is conclusive", prompt)
            self.assertIn("\"blocking_findings\":[]", prompt)
            self.assertIn("\"revision_findings\"", prompt)
            self.assertIn("\"owner\":\"prd_writer\"", prompt)

    def test_in_place_review_uses_isolated_workspace_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state, _, workspace = self._in_place_review_state(Path(temporary))
            observed: dict[str, Path | str] = {}

            def worker(provider, prompt, cwd, *args):
                review_path = Path(prompt.split("Write ONLY one JSON object to ", 1)[1].split(" (UTF-8):", 1)[0])
                observed["cwd"] = cwd
                observed["prompt"] = prompt
                observed["review_path"] = review_path
                review_path.write_text(
                    '{"status":"pass","summary":"checked","blocking_findings":[],"revision_findings":[],"acceptance_evidence":["selected section checked"]}',
                    encoding="utf-8",
                )
                return {"provider": provider, "model": "test", "status": "complete", "output": "", "error": ""}

            passed, _ = _review_artifact(state, "prd.md", "test", 1, worker=worker)

            self.assertTrue(passed)
            self.assertNotEqual(observed["cwd"], workspace)
            self.assertEqual(observed["review_path"], Path(observed["cwd"]) / ".stage-review.json")
            self.assertIn(f"Read only {Path(observed['cwd']) / 'prd.md'}", str(observed["prompt"]))
            self.assertNotIn(f"Read only {workspace / 'prd.md'}", str(observed["prompt"]))

    def test_in_place_review_rejects_controller_owned_asset_provenance_repair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state, _, workspace = self._in_place_review_state(Path(temporary))

            def writer(provider, prompt, cwd, *args):
                target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
                target.write_text(
                    (workspace / "prd.md").read_text(encoding="utf-8").replace(
                        "Selected exact copy remains visible.", "Selected exact copy was refreshed.",
                    ), encoding="utf-8",
                )
                return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}

            self.assertTrue(_run_artifact_agent(state, "prd.md", "test", 1, worker=writer))
            self.assertEqual(state["revision_asset_attestation"]["status"], "passed")

            def worker(provider, prompt, cwd, *args):
                review_path = Path(prompt.split("Write ONLY one JSON object to ", 1)[1].split(" (UTF-8):", 1)[0])
                review_path.write_text(
                    json.dumps({
                        "status": "needs_revision",
                        "summary": "asset review",
                        "blocking_findings": [],
                        "revision_findings": [{
                            "kind": "selected_media_semantics_gap",
                            "owner": "prd_writer",
                            "requirement_ids": ["5.1"],
                            "evidence": '5.1: "Selected exact copy was refreshed."',
                            "repair": "Verify the selected image source and SHA-256 before accepting it.",
                        }],
                        "acceptance_evidence": [],
                    }, ensure_ascii=False),
                    encoding="utf-8",
                )
                return {"provider": provider, "model": "test", "status": "complete", "output": "", "error": ""}

            passed, findings = _review_artifact(state, "prd.md", "test", 1, worker=worker)

            self.assertFalse(passed)
            self.assertIn("controller-owned asset existence or provenance", findings)
            self.assertEqual(state["review_contract_rejection"]["artifact"], "prd.md")
            self.assertEqual(state["delivery_stages"]["prd.md"]["review_findings"], [])
            self.assertNotIn("SHA-256 before accepting", state["agent_calls"][-1]["output"])

    def test_in_place_review_rejects_findings_outside_selected_requirement_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state, _, _ = self._in_place_review_state(Path(temporary))

            def worker(provider, prompt, cwd, *args):
                review_path = Path(prompt.split("Write ONLY one JSON object to ", 1)[1].split(" (UTF-8):", 1)[0])
                review_path.write_text(
                    json.dumps({
                        "status": "needs_revision",
                        "summary": "wrong scope",
                        "blocking_findings": [],
                        "revision_findings": [{
                            "kind": "selected_copy_gap",
                            "owner": "prd_writer",
                            "requirement_ids": ["5.2"],
                            "evidence": '5.2: "Protected exact copy remains visible."',
                            "repair": "Rewrite protected copy.",
                        }],
                        "acceptance_evidence": [],
                    }, ensure_ascii=False),
                    encoding="utf-8",
                )
                return {"provider": provider, "model": "test", "status": "complete", "output": "", "error": ""}

            passed, findings = _review_artifact(state, "prd.md", "test", 1, worker=worker)

            self.assertFalse(passed)
            self.assertIn("target only selected requirement IDs", findings)
            self.assertEqual(state["review_contract_rejection"]["artifact"], "prd.md")

    def test_in_place_quality_gate_retries_invalid_reviewer_without_calling_writer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state, _, _ = self._in_place_review_state(Path(temporary))
            calls: list[str] = []

            def worker(provider, prompt, cwd, *args):
                if "Stage Quality Review Agent" not in prompt:
                    self.fail("invalid reviewer output must not be sent to the PRD writer")
                calls.append(prompt)
                review_path = Path(prompt.split("Write ONLY one JSON object to ", 1)[1].split(" (UTF-8):", 1)[0])
                review_path.write_text(
                    '{"status":"needs_revision","summary":"legacy","blocking_findings":["rewrite 5.2"],"acceptance_evidence":[]}',
                    encoding="utf-8",
                )
                return {"provider": provider, "model": "test", "status": "complete", "output": "", "error": ""}

            passed = _deliver_artifact_to_quality_gate(state, "prd.md", "test", 1, worker=worker, max_revisions=0)

            self.assertFalse(passed)
            self.assertEqual(len(calls), 2)
            self.assertIn("prior response violated this output contract", calls[1].lower())
            self.assertEqual(state["revision_stop_reason"], "prd.md stage review contract rejected twice")

    def test_in_place_quality_gate_sends_valid_typed_finding_to_writer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state, _, workspace = self._in_place_review_state(Path(temporary))
            calls: list[str] = []

            def worker(provider, prompt, cwd, *args):
                if "Stage Quality Review Agent" in prompt:
                    calls.append("review")
                    review_path = Path(prompt.split("Write ONLY one JSON object to ", 1)[1].split(" (UTF-8):", 1)[0])
                    if calls.count("review") == 1:
                        review_path.write_text(
                            json.dumps({
                                "status": "needs_revision", "summary": "copy gap", "blocking_findings": [],
                                "revision_findings": [{
                                    "kind": "selected_copy_gap", "owner": "prd_writer", "requirement_ids": ["5.1"],
                                    "evidence": '5.1: "Selected exact copy remains visible."',
                                    "repair": "Change the selected copy to the confirmed wording.",
                                }],
                                "acceptance_evidence": [],
                            }), encoding="utf-8",
                        )
                    else:
                        review_path.write_text(
                            '{"status":"pass","summary":"checked","blocking_findings":[],"revision_findings":[],"acceptance_evidence":["selected repair verified"]}',
                            encoding="utf-8",
                        )
                    return {"provider": provider, "model": "test", "status": "complete", "output": "", "error": ""}
                calls.append(prompt)
                target = Path(prompt.split("Write one complete artifact at ", 1)[1].split(".\n", 1)[0])
                self.assertEqual(target, cwd / "prd.md")
                self.assertIn("[selected_copy_gap] 5.1", prompt)
                self.assertIn("Selected evidence:", prompt)
                target.write_text(
                    (cwd / "prd.md").read_text(encoding="utf-8").replace(
                        "Selected exact copy remains visible.", "Confirmed selected copy is visible.",
                    ), encoding="utf-8",
                )
                return {"provider": provider, "model": "test", "status": "complete", "output": "written", "error": ""}

            passed = _deliver_artifact_to_quality_gate(state, "prd.md", "test", 1, worker=worker, max_revisions=1)

            self.assertTrue(passed)
            self.assertEqual(calls.count("review"), 2)
            self.assertTrue(any("Write one complete artifact at" in call for call in calls if call != "review"))
            self.assertEqual(state["delivery_stages"]["prd.md"]["revision_findings"], [])

    def test_non_revision_stage_review_accepts_legacy_blocking_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            target = folder / "confirmed-requirements.md"
            target.write_text("# Confirmed\n", encoding="utf-8")
            state = create_state("新建 PRD", folder)
            state["confirmed_fact_packet"] = {
                "summary": "已确认", "scope": {"goal": "新建 PRD"},
                "assumptions": [], "decisions": [], "risks": [],
            }

            def worker(provider, prompt, cwd, *args):
                review_path = Path(prompt.split("Write ONLY one JSON object to ", 1)[1].split(" (UTF-8):", 1)[0])
                review_path.write_text(
                    '{"status":"needs_revision","summary":"legacy","blocking_findings":["add acceptance evidence"],"acceptance_evidence":[]}',
                    encoding="utf-8",
                )
                return {"provider": provider, "model": "test", "status": "complete", "output": "", "error": ""}

            passed, findings = _review_artifact(state, "confirmed-requirements.md", "test", 1, worker=worker)

            self.assertFalse(passed)
            self.assertEqual(findings, "add acceptance evidence")
            self.assertNotIn("review_contract_rejection", state)

    def test_confirmation_packet_uses_only_final_confirmed_turn(self) -> None:
        state = create_state("旧请求", Path("/tmp/example"))
        state["turns"] = [
            {"user_text": "旧范围", "summary": "旧结论", "scope": {"goal": "旧"}, "assumptions": [], "decisions": [], "risks": [], "buckets": {}},
            {"user_text": "最终范围", "summary": "最终结论", "scope": {"goal": "新"}, "assumptions": [], "decisions": ["最终决定"], "risks": [], "buckets": {}},
        ]
        packet = _confirmation_packet(state)
        self.assertEqual(packet["final_user_message"], "最终范围")
        self.assertEqual(packet["scope"], {"goal": "新"})


if __name__ == "__main__":
    unittest.main()
