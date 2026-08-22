#!/usr/bin/env python3
"""Regression tests for the canonical evaluation portfolio contract."""

import unittest

from portfolio_contract import plan_digest


class PortfolioContractTest(unittest.TestCase):
    def test_plan_digest_is_order_stable_for_mapping_keys(self) -> None:
        self.assertEqual(
            plan_digest([{"case_id": "case-a", "request": "x"}]),
            plan_digest([{"request": "x", "case_id": "case-a"}]),
        )


if __name__ == "__main__":
    unittest.main()
