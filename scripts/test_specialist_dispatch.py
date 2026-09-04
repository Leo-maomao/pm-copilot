from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from specialist_dispatch import dispatch, select_tasks


class SpecialistDispatchTests(unittest.TestCase):
    def _composition_state(self, source_count: int) -> dict[str, object]:
        return {
            "task_mode": "prd_composition",
            "raw_request": "从多个 PRD 生成新的界面需求 PRD",
            "confirmed_fact_packet": {
                "scope": {"goal": "compose", "in_scope": ["账户", "权限"]},
                "risks": ["同名规则冲突"],
            },
            "extraction_sources": [
                {"source_id": f"source-{index}", "snapshot_path": f"source-{index}.md", "selected_scope": ["5.1"]}
                for index in range(source_count)
            ],
        }

    def test_source_tasks_are_not_capped(self) -> None:
        tasks = select_tasks(self._composition_state(12))
        source_tasks = [task for task in tasks if task["role"] == "source_resolution"]
        self.assertEqual(len(source_tasks), 12)

    def test_dispatch_persists_each_specialist_result(self) -> None:
        calls: list[str] = []

        def runner(provider, prompt, cwd, timeout, model, schema, dry_run, output_limit):
            del provider, cwd, timeout, model, schema, dry_run, output_limit
            calls.append(prompt)
            time.sleep(0.01)
            return {"status": "complete", "provider": "codex", "model": "test", "output": "evidence"}

        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "run"
            workspace.mkdir()
            records = dispatch(self._composition_state(4), workspace, "codex", 1, None, runner)
            self.assertEqual(len(records), len(calls))
            self.assertGreaterEqual(len(records), 6)
            for record in records:
                path = workspace / str(record["path"])
                self.assertTrue(path.is_file())
                self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["status"], "passed")

    def test_specialist_exception_is_recorded_not_raised(self) -> None:
        def runner(*_args):
            raise RuntimeError("offline")

        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "run"
            workspace.mkdir()
            records = dispatch(self._composition_state(1), workspace, "codex", 1, None, runner)
        self.assertTrue(records)
        self.assertTrue(all(record["status"] == "failed" for record in records))


if __name__ == "__main__":
    unittest.main()
