#!/usr/bin/env python3
"""Regression coverage for the sole v2 MCP-to-controller path."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pm_copilot_mcp", ROOT / "plugins/pm-copilot/scripts/pm_copilot_mcp.py")
assert SPEC and SPEC.loader
MCP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MCP)


class PmCopilotMcpTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = patch.object(MCP, "RUNTIME_HOME", ROOT)
        self.controller = patch.object(MCP, "CONTROLLER", ROOT / "scripts/prd_request_controller.py")
        self.runtime.start()
        self.controller.start()

    def tearDown(self) -> None:
        self.controller.stop()
        self.runtime.stop()

    def test_bridge_uses_the_v2_controller_and_state_name(self) -> None:
        self.assertEqual(MCP.CONTROLLER.name, "prd_request_controller.py")
        wrapper = (ROOT / "plugins/pm-copilot/scripts/pm_copilot_mcp.py").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "run"
            started = MCP.start_request("为审批人增加审批提醒功能", temporary, str(folder))
            self.assertTrue(started["ok"], started)
            state = json.loads((folder / "delivery-run.json").read_text(encoding="utf-8"))
            self.assertEqual(state["protocol_version"], 2)

    def test_plugin_configuration_has_no_runtime_override(self) -> None:
        config = json.loads((ROOT / "plugins/pm-copilot/.mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(config["mcpServers"]["pm-copilot"]["args"], ["./scripts/pm_copilot_mcp.py"])
        wrapper = (ROOT / "plugins/pm-copilot/scripts/pm_copilot_mcp.py").read_text(encoding="utf-8")
        self.assertNotIn("PM_COPILOT_REPOSITORY", wrapper)


if __name__ == "__main__":
    unittest.main()
