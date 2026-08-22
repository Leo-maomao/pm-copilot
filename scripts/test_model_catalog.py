import json
import os
import unittest
from unittest.mock import patch

from model_catalog import ModelOption, discover_model_catalog, select_model


class ModelCatalogTests(unittest.TestCase):
    def test_selects_declared_capability_without_vendor_model_names(self) -> None:
        options = [
            ModelOption("local-fast", "codex", frozenset({"standard"}), "test", 1),
            ModelOption("local-judge", "codex", frozenset({"judgment"}), "test", 2),
        ]
        self.assertEqual(select_model("standard", "codex", options).option.model, "local-fast")
        self.assertEqual(select_model("judgment", "codex", options).option.model, "local-judge")

    def test_missing_judgment_is_explicitly_degraded(self) -> None:
        result = select_model("judgment", "codex", [ModelOption("only", "codex", frozenset({"standard"}), "test")])
        self.assertEqual(result.status, "degraded")
        self.assertIn("no declared judgment", result.reason)

    def test_no_model_is_blocked(self) -> None:
        result = select_model("standard", "codex", [])
        self.assertEqual(result.status, "blocked")
        self.assertIsNone(result.option)

    def test_catalog_reads_user_manifest(self) -> None:
        manifest = json.dumps({"models": [{"model": "user-model", "provider": "codex", "capabilities": ["judgment"]}]})
        with patch.dict(os.environ, {"PM_COPILOT_MODEL_CATALOG": manifest}, clear=False), patch(
            "model_catalog._configured_model", return_value=None,
        ):
            options, warnings = discover_model_catalog("codex")
        self.assertEqual(warnings, [])
        self.assertEqual(options[0].model, "user-model")


if __name__ == "__main__":
    unittest.main()
