#!/usr/bin/env python3
"""Regression tests for resumable portfolio orchestration."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from run_evaluation_portfolio import acquire_portfolio_lock, run_portfolio


class EvaluationPortfolioRunnerTest(unittest.TestCase):
    def test_dry_run_records_selected_cases_without_claiming_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = run_portfolio(Path(temporary), timeout_minutes=1, dry_run=True, case_ids={"decision-first-prd", "document-class-reference-prototype"})
        self.assertEqual(state["status"], "planned")
        self.assertEqual(state["summary"]["selected_cases"], 2)
        self.assertEqual(state["summary"]["complete"], 0)
        self.assertEqual(state["cases"]["decision-first-prd"]["controlled_confirmation"], "evaluation-only; not human approval")

    def test_resume_skips_a_verified_complete_case(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = run_portfolio(root, timeout_minutes=1, dry_run=True, case_ids={"decision-first-prd"})
            self.assertEqual(first["status"], "planned")
            # A dry run is deliberately not treated as complete on resume.
            second = run_portfolio(root, timeout_minutes=1, resume=True, dry_run=True, case_ids={"decision-first-prd"})
            self.assertEqual(second["status"], "planned")

    def test_resume_uses_current_runtime_and_records_prior_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_portfolio(root, timeout_minutes=1, provider="seawork", dry_run=True, case_ids={"decision-first-prd"})
            resumed = run_portfolio(root, timeout_minutes=2, provider="codex", resume=True, dry_run=True, case_ids={"decision-first-prd"})
        self.assertEqual(resumed["provider_requested"], "codex")
        self.assertEqual(resumed["timeout_minutes"], 2)
        self.assertEqual(resumed["runtime_overrides"][-1]["from_provider"], "seawork")

    def test_portfolio_manifest_does_not_nest_case_output_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            manifest_root = parent / "evaluation-portfolio-2026-08-18"
            state = run_portfolio(manifest_root, timeout_minutes=1, dry_run=True, case_ids={"decision-first-prd"})
            case_folder = Path(state["cases"]["decision-first-prd"]["folder"])
            self.assertEqual(case_folder.parent, parent)
            self.assertNotEqual(case_folder.parent, manifest_root)

    def test_arbitrary_manifest_directory_keeps_case_directly_under_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            outputs = Path(temporary) / "outputs"
            manifest_root = outputs / "single-case-control-plane"
            state = run_portfolio(
                manifest_root, timeout_minutes=1, dry_run=True, case_ids={"decision-first-prd"},
            )
            self.assertEqual(Path(state["cases"]["decision-first-prd"]["folder"]).parent, outputs)

    def test_same_case_reuses_its_canonical_folder_across_portfolios(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
            prior = parent / f"decision-first-prd-{today}"
            prior.mkdir()
            (prior / "scenario-run.json").write_text("{}\n", encoding="utf-8")
            state = run_portfolio(
                parent / "evaluation-portfolio-new",
                timeout_minutes=1,
                dry_run=True,
                case_ids={"decision-first-prd"},
            )
            self.assertEqual(Path(state["cases"]["decision-first-prd"]["folder"]), prior)

    def test_runtime_exception_isolated_to_case_and_manifest_remains_resumable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "evaluation-portfolio-new"
            with patch("run_evaluation_portfolio.execute_case", side_effect=RuntimeError("runtime status timeout")):
                state = run_portfolio(root, timeout_minutes=1, case_ids={"decision-first-prd"})
            self.assertEqual(state["status"], "failed")
            self.assertEqual(state["cases"]["decision-first-prd"]["status"], "failed")
            self.assertIn("runtime status timeout", state["cases"]["decision-first-prd"]["error"])

    def test_operator_interrupt_stops_portfolio_before_next_case(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch(
                "run_evaluation_portfolio.execute_case",
                side_effect=KeyboardInterrupt,
            ) as execute:
                state = run_portfolio(
                    root,
                    timeout_minutes=1,
                    case_ids={"decision-first-prd", "document-class-reference-prototype"},
                )
        self.assertEqual(state["status"], "interrupted")
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(state["summary"]["recorded_cases"], 1)
        self.assertEqual(state["summary"]["pending"], 1)
        self.assertEqual(state["cases"]["decision-first-prd"]["status"], "interrupted")
        self.assertNotIn("document-class-reference-prototype", state["cases"])

    def test_operator_interrupt_preserves_case_checkpoint_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def write_checkpoint_then_interrupt(*args, **kwargs):
                folder = kwargs["run_folder_path"]
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "scenario-run.json").write_text(json.dumps({
                    "status": "running",
                    "phases": [{"name": "intake", "status": "complete"}],
                    "agent_calls": [{"phase": "discussion", "artifact": "discussion.md", "status": "complete"}],
                    "artifacts": {"discussion.md": {"exists": True}},
                    "validation": [],
                }), encoding="utf-8")
                raise KeyboardInterrupt

            with patch("run_evaluation_portfolio.execute_case", side_effect=write_checkpoint_then_interrupt):
                state = run_portfolio(root, timeout_minutes=1, case_ids={"decision-first-prd"})
        case = state["cases"]["decision-first-prd"]
        self.assertEqual(case["status"], "interrupted")
        self.assertEqual(case["phase_status"], {"intake": "complete"})
        self.assertEqual(case["agent_calls"][0]["artifact"], "discussion.md")

    def test_first_case_checkpoint_is_persisted_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def inspect_checkpoint(*args, **kwargs):
                checkpoint = json.loads((root / "portfolio-run.json").read_text(encoding="utf-8"))
                self.assertEqual(checkpoint["current_case_id"], "decision-first-prd")
                self.assertEqual(checkpoint["cases"]["decision-first-prd"]["status"], "running")
                return {"status": "failed", "phases": [], "agent_calls": [], "artifacts": {}, "validation": []}

            with patch("run_evaluation_portfolio.execute_case", side_effect=inspect_checkpoint):
                run_portfolio(root, timeout_minutes=1, case_ids={"decision-first-prd"})

    def test_seawork_state_failure_retries_same_case_with_codex(self) -> None:
        failed = {
            "status": "failed", "phases": [], "artifacts": {}, "validation": [],
            "agent_calls": [{"error": "failed to initialize sqlite state runtime"}],
        }
        completed = {"status": "complete", "phases": [], "artifacts": {}, "validation": [], "agent_calls": []}
        with tempfile.TemporaryDirectory() as temporary:
            with patch("run_evaluation_portfolio.execute_case", side_effect=[failed, completed]) as execute:
                state = run_portfolio(Path(temporary), timeout_minutes=1, provider="seawork", case_ids={"decision-first-prd"})
        self.assertEqual(state["cases"]["decision-first-prd"]["status"], "complete")
        self.assertEqual(execute.call_args_list[1].kwargs["provider"], "codex")
        self.assertEqual(state["cases"]["decision-first-prd"]["runtime_fallbacks"][0]["from_provider"], "seawork")

    def test_unreachable_seawork_daemon_restarts_then_retries_same_case(self) -> None:
        completed = {"status": "complete", "phases": [], "artifacts": {}, "validation": [], "agent_calls": []}
        with tempfile.TemporaryDirectory() as temporary:
            restart = subprocess.CompletedProcess(["seawork", "restart"], 0, "restarted", "")
            with patch(
                "run_evaluation_portfolio.execute_case",
                side_effect=[RuntimeError("runtime 'seawork-claude' is not ready: Local Daemon unresponsive"), completed],
            ) as execute, patch("run_evaluation_portfolio.shutil.which", return_value="seawork"), patch(
                "run_evaluation_portfolio.subprocess.run", return_value=restart,
            ) as restart_call:
                state = run_portfolio(
                    Path(temporary), timeout_minutes=1, provider="seawork-claude", case_ids={"decision-first-prd"},
                )
        self.assertEqual(state["cases"]["decision-first-prd"]["status"], "complete")
        self.assertEqual(execute.call_count, 2)
        restart_call.assert_called_once_with(
            ["seawork", "restart"], text=True, capture_output=True, timeout=90, check=False,
        )
        self.assertEqual(len(state["cases"]["decision-first-prd"].get("runtime_recoveries", [])), 1)

    def test_daemon_failure_returned_by_case_restarts_once_then_circuits_breaker(self) -> None:
        unavailable = {
            "status": "failed", "last_error": "Local Daemon unresponsive", "phases": [],
            "artifacts": {}, "validation": [], "agent_calls": [],
        }
        with tempfile.TemporaryDirectory() as temporary:
            restart = subprocess.CompletedProcess(["seawork", "restart"], 0, "restarted", "")
            with patch("run_evaluation_portfolio.execute_case", side_effect=[unavailable, unavailable]) as execute, patch(
                "run_evaluation_portfolio.shutil.which", return_value="seawork"
            ), patch("run_evaluation_portfolio.subprocess.run", return_value=restart):
                state = run_portfolio(
                    Path(temporary), timeout_minutes=1, provider="seawork-claude",
                    case_ids={"decision-first-prd", "document-class-reference-prototype"},
                )
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(state["status"], "halted_infrastructure")
        self.assertEqual(state["circuit_breaker"]["category"], "seawork_daemon_unavailable")
        self.assertEqual(state["summary"]["recorded_cases"], 1)
        self.assertEqual(state["cases"]["decision-first-prd"]["runtime_recoveries"][0]["retry_policy"], "one_recovery_retry")

    def test_content_failure_does_not_restart_or_retry(self) -> None:
        content_failure = {
            "status": "failed", "last_error": "stage quality review requires a concrete repair", "phases": [],
            "artifacts": {}, "validation": [], "agent_calls": [],
        }
        with tempfile.TemporaryDirectory() as temporary:
            with patch("run_evaluation_portfolio.execute_case", return_value=content_failure) as execute, patch(
                "run_evaluation_portfolio.subprocess.run"
            ) as restart:
                state = run_portfolio(Path(temporary), timeout_minutes=1, provider="seawork-claude", case_ids={"decision-first-prd"})
        self.assertEqual(execute.call_count, 1)
        restart.assert_not_called()
        self.assertEqual(state["status"], "failed")

    def test_empty_agent_timeout_circuits_before_later_cases(self) -> None:
        timeout = {
            "status": "failed", "phases": [], "validation": [],
            "artifacts": {"discussion.md": {"exists": False}},
            "agent_calls": [{"status": "timed_out", "error": "Agent exceeded 2 minute(s)"}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            with patch("run_evaluation_portfolio.execute_case", return_value=timeout) as execute:
                state = run_portfolio(
                    Path(temporary), timeout_minutes=1, provider="seawork-claude",
                    case_ids={"decision-first-prd", "document-class-reference-prototype"},
                )
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(state["status"], "halted_infrastructure")
        self.assertEqual(state["circuit_breaker"]["category"], "agent_runtime_no_progress")
        self.assertEqual(state["summary"]["recorded_cases"], 1)

    def test_timeout_with_promoted_artifact_does_not_circuit(self) -> None:
        timeout = {
            "status": "failed", "phases": [], "validation": [],
            "artifacts": {"discussion.md": {"exists": True}},
            "agent_calls": [{"status": "timed_out", "error": "Agent exceeded 2 minute(s)"}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            with patch("run_evaluation_portfolio.execute_case", return_value=timeout) as execute:
                state = run_portfolio(Path(temporary), timeout_minutes=1, case_ids={"decision-first-prd"})
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(state["status"], "failed")
        self.assertNotIn("circuit_breaker", state)

    def test_case_summary_retains_call_error_and_failure_fingerprint(self) -> None:
        report = {
            "status": "failed", "phases": [], "artifacts": {}, "validation": [],
            "agent_calls": [{"status": "failed", "error": "Local Daemon unresponsive", "phase": "discussion"}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            with patch("run_evaluation_portfolio.execute_case", return_value=report):
                state = run_portfolio(Path(temporary), timeout_minutes=1, provider="seawork-claude", case_ids={"decision-first-prd"})
        call = state["cases"]["decision-first-prd"]["agent_calls"][0]
        self.assertEqual(call["error"], "Local Daemon unresponsive")
        self.assertEqual(state["cases"]["decision-first-prd"]["failure_fingerprint"]["category"], "seawork_daemon_unavailable")

    def test_completed_case_does_not_treat_agent_output_as_an_error(self) -> None:
        report = {
            "status": "complete", "phases": [], "artifacts": {}, "validation": [],
            "agent_calls": [{"status": "complete", "output": "successful Agent output"}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            with patch("run_evaluation_portfolio.execute_case", return_value=report):
                state = run_portfolio(Path(temporary), timeout_minutes=1, case_ids={"decision-first-prd"})
        summary = state["cases"]["decision-first-prd"]
        self.assertEqual(summary["error"], "")
        self.assertEqual(summary["failure_fingerprint"]["category"], "none")

    def test_portfolio_lock_rejects_a_second_control_plane(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with acquire_portfolio_lock(root):
                with self.assertRaises(RuntimeError):
                    acquire_portfolio_lock(root)

    def test_codex_case_parallelism_is_enabled_and_capped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            completed = {"status": "complete", "phases": [], "artifacts": {}, "validation": [], "agent_calls": []}
            with patch("run_evaluation_portfolio.execute_case", return_value=completed):
                state = run_portfolio(
                    Path(temporary), timeout_minutes=1, provider="codex", workers=8,
                    dry_run=False, case_ids={"decision-first-prd"},
                )
        self.assertEqual(state["runtime_policy"]["requested_workers"], 8)
        self.assertEqual(state["runtime_policy"]["effective_workers"], 3)
        self.assertEqual(state["runtime_policy"]["mode"], "case_parallelism")

    def test_codex_parallel_cases_run_in_the_same_bounded_batch(self) -> None:
        barrier = threading.Barrier(2, timeout=1)
        completed = {"status": "complete", "phases": [], "artifacts": {}, "validation": [], "agent_calls": []}

        def concurrent_case(*args, **kwargs):
            barrier.wait()
            return completed

        with tempfile.TemporaryDirectory() as temporary:
            with patch("run_evaluation_portfolio.execute_case", side_effect=concurrent_case):
                state = run_portfolio(
                    Path(temporary), timeout_minutes=1, provider="codex", workers=2,
                    dry_run=False, case_ids={"decision-first-prd", "document-class-reference-prototype"},
                )
        self.assertEqual(state["status"], "complete")
        self.assertEqual(state["runtime_policy"]["effective_workers"], 2)

    def test_seawork_case_parallelism_remains_serial(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            completed = {"status": "complete", "phases": [], "artifacts": {}, "validation": [], "agent_calls": []}
            with patch("run_evaluation_portfolio.execute_case", return_value=completed):
                state = run_portfolio(
                    Path(temporary), timeout_minutes=1, provider="seawork", workers=2,
                    dry_run=False, case_ids={"decision-first-prd"},
                )
        self.assertEqual(state["runtime_policy"]["requested_workers"], 2)
        self.assertEqual(state["runtime_policy"]["effective_workers"], 1)
        self.assertEqual(state["runtime_policy"]["mode"], "serial")


if __name__ == "__main__":
    unittest.main()
