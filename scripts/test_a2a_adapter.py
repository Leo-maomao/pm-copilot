#!/usr/bin/env python3
"""Regression coverage for the A2A-compatible PM Copilot task boundary."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from a2a_adapter import AGENT_CARD, normalize


class A2AAdapterTest(unittest.TestCase):
    def test_agent_card_declares_product_capabilities(self) -> None:
        self.assertIn("prd_delivery", AGENT_CARD["capabilities"])
        self.assertEqual(AGENT_CARD["interoperability"], "local-task-envelope-only")

    def test_normalizes_task_into_project_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            task = normalize({"id": "task-1", "message": "生成项目创建 PRD"}, Path(temporary))
            self.assertEqual(task["task_id"], "task-1")
            self.assertEqual(task["status"], "accepted")
            self.assertEqual(task["workspace"]["mode"], "global")

    def test_rejects_task_without_actionable_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                normalize({}, Path(temporary))


if __name__ == "__main__":
    unittest.main()
