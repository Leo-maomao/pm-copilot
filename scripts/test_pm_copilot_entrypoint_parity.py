#!/usr/bin/env python3
"""Keep explicit plugin and natural-language PM Copilot PRD entrypoints aligned."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SKILL = ROOT / "plugins" / "pm-copilot" / "skills" / "pm-copilot" / "SKILL.md"
GLOBAL_SKILL = ROOT / "distribution" / "seawork-skill" / "SKILL.md"


class PmCopilotEntrypointParityTest(unittest.TestCase):
    def test_explicit_and_natural_prd_entrypoints_use_the_canonical_controller(self) -> None:
        plugin = PLUGIN_SKILL.read_text(encoding="utf-8")
        global_skill = GLOBAL_SKILL.read_text(encoding="utf-8")
        for text in (plugin, global_skill):
            self.assertIn("prd_request_controller.py", text)
            self.assertIn("awaiting_confirmation", text)
            self.assertIn("delivery_calls", text)
        self.assertIn("prd_run_status", plugin)
        self.assertIn("pm_copilot_mcp.py", global_skill)

    def test_global_skill_declares_natural_requests_equivalent_to_explicit_activation(self) -> None:
        text = GLOBAL_SKILL.read_text(encoding="utf-8")
        self.assertIn("equivalent activation signals", text)


if __name__ == "__main__":
    unittest.main()
