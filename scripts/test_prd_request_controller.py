import unittest

from prd_request_controller import is_prd_request


class PrdRequestControllerTests(unittest.TestCase):
    def test_natural_prd_requests_route_to_production_controller(self) -> None:
        self.assertTrue(is_prd_request("调用 pm-copilot 生成PRD"))
        self.assertTrue(is_prd_request("帮我写一份产品需求文档"))

    def test_non_prd_request_is_not_routed_to_prd_controller(self) -> None:
        self.assertFalse(is_prd_request("检查一下当前测试结果"))


if __name__ == "__main__":
    unittest.main()
