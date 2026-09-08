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

    def test_bridge_collects_explicit_and_request_image_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = [root / f"字幕擦除-状态-{index}.png" for index in range(1, 4)]
            for asset in assets:
                asset.write_bytes(bytes.fromhex(
                    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                    "0000000d49444154789c6360f8cfc000000401010018dd8db00000000049454e44ae426082"
                ))
            folder = root / "run"
            started = MCP.start_request(
                "生成字幕擦除 PRD，图示为 " + " ".join(str(asset) for asset in assets),
                temporary, str(folder), asset_paths=[str(asset) for asset in assets],
            )
            self.assertTrue(started["ok"], started)
            state = json.loads((folder / "delivery-run.json").read_text(encoding="utf-8"))
            self.assertEqual(state["input_assets"], [str(asset.resolve()) for asset in assets])
            markdown = (folder / "prd.md").read_text(encoding="utf-8")
            for asset in assets:
                self.assertIn(f'[[prd-detail-media src="./assets/{asset.name}"', markdown)

    def test_plugin_configuration_has_no_runtime_override(self) -> None:
        config = json.loads((ROOT / "plugins/pm-copilot/.mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(config["mcpServers"]["pm-copilot"]["args"], ["./scripts/pm_copilot_mcp.py"])
        wrapper = (ROOT / "plugins/pm-copilot/scripts/pm_copilot_mcp.py").read_text(encoding="utf-8")
        self.assertNotIn("PM_COPILOT_REPOSITORY", wrapper)


if __name__ == "__main__":
    unittest.main()
