import sys
import unittest
from unittest.mock import patch

import prd_request_controller
from prd_request_controller import is_prd_request


class PrdRequestControllerTests(unittest.TestCase):
    def test_natural_prd_requests_route_to_production_controller(self) -> None:
        self.assertTrue(is_prd_request("调用 pm-copilot 生成PRD"))
        self.assertTrue(is_prd_request("帮我写一份产品需求文档"))

    def test_non_prd_request_is_not_routed_to_prd_controller(self) -> None:
        self.assertFalse(is_prd_request("检查一下当前测试结果"))

    def test_revision_flags_are_supported(self) -> None:
        # Argument forwarding is exercised by the production entry point; the
        # parser must expose the explicit in-place revision contract.
        self.assertIn("--run-folder", prd_request_controller.main.__code__.co_consts)

    def test_extraction_input_is_forwarded_as_a_new_requirement(self) -> None:
        with patch.object(sys, "argv", [
            "prd_request_controller.py", "--request", "从旧 PRD 提取结算流程生成新 PRD",
            "--extract-from", "/tmp/legacy-prd.md",
        ]), patch("prd_request_controller.interactive_main", return_value=0):
            self.assertEqual(prd_request_controller.main(), 0)
            self.assertIn("--new-requirement", sys.argv)
            self.assertEqual(sys.argv[sys.argv.index("--extract-from") + 1], "/tmp/legacy-prd.md")

    def test_existing_run_forwards_revision_selector_without_becoming_new_requirement(self) -> None:
        with patch.object(sys, "argv", [
            "prd_request_controller.py", "--request", "更新 PRD 的 5.1 和 5.2",
            "--run-folder", "/tmp/canonical-run", "--revise", "--revision-requirement-id", "5.1",
            "--revision-requirement-id", "5.2",
        ]), patch("prd_request_controller.interactive_main", return_value=0):
            self.assertEqual(prd_request_controller.main(), 0)
            self.assertNotIn("--new-requirement", sys.argv)
            self.assertEqual(sys.argv[sys.argv.index("--run-folder") + 1], "/tmp/canonical-run")
            selectors = [
                sys.argv[index + 1]
                for index, value in enumerate(sys.argv)
                if value == "--revision-requirement-id"
            ]
            self.assertEqual(selectors, ["5.1", "5.2"])

    def test_existing_run_without_explicit_revision_is_rejected(self) -> None:
        with patch.object(sys, "argv", [
            "prd_request_controller.py", "--request", "更新已有 PRD",
            "--run-folder", "/tmp/canonical-run",
        ]), patch("prd_request_controller.interactive_main") as interactive_main:
            with self.assertRaises(SystemExit):
                prd_request_controller.main()
            interactive_main.assert_not_called()

    def test_implemented_evidence_input_is_forwarded_as_a_new_requirement(self) -> None:
        with patch.object(sys, "argv", [
            "prd_request_controller.py", "--request", "为已实现功能生成 PRD",
            "--implemented-evidence", "/tmp/implemented-evidence.json",
        ]), patch("prd_request_controller.interactive_main", return_value=0):
            self.assertEqual(prd_request_controller.main(), 0)
            self.assertIn("--new-requirement", sys.argv)
            self.assertEqual(
                sys.argv[sys.argv.index("--implemented-evidence") + 1],
                "/tmp/implemented-evidence.json",
            )


if __name__ == "__main__":
    unittest.main()
