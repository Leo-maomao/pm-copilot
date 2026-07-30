#!/usr/bin/env python3
"""Regression coverage for vendor-neutral agent event ledgers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_event_ledger import append_event, validate_file


class AgentEventLedgerTest(unittest.TestCase):
    def test_accepts_valid_event(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "agent-events.jsonl"
            path.write_text(json.dumps({"event_id": "evt-1", "timestamp": "2026-07-30T12:00:00Z", "run_id": "run-1", "workspace": "/tmp/project", "type": "task_started", "data": {}}) + "\n", encoding="utf-8")
            self.assertEqual(validate_file(path), [])

    def test_rejects_missing_event_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "agent-events.jsonl"
            path.write_text('{"event_id":"evt-1"}\n', encoding="utf-8")
            self.assertEqual(validate_file(path), ["1:missing_required_fields"])

    def test_appends_a_valid_event(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "agent-events.jsonl"
            append_event(path, "run-1", "/tmp/project", "tool_called", {"tool": "agent_runtime"})
            self.assertEqual(validate_file(path), [])


if __name__ == "__main__":
    unittest.main()
