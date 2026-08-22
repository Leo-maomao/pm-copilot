#!/usr/bin/env python3
"""Regression tests for the canonical Agent runtime policy constants."""

import unittest

from agent_runtime import DEFAULT_SEAWORK_MODEL
from run_evaluation_scenario import MODEL_ROUTING_POLICY, SOL_MODEL, TERRA_MODEL
from runtime_policy import (
    DEFAULT_SEAWORK_MODEL as CANONICAL_SEAWORK_MODEL,
    HIGH_JUDGMENT_MODEL,
    MODEL_ROUTING_POLICY as CANONICAL_ROUTING_POLICY,
    STANDARD_MODEL,
)


class RuntimePolicyTest(unittest.TestCase):
    def test_controllers_share_one_model_policy_source(self) -> None:
        self.assertEqual(TERRA_MODEL, STANDARD_MODEL)
        self.assertEqual(SOL_MODEL, HIGH_JUDGMENT_MODEL)
        self.assertEqual(MODEL_ROUTING_POLICY, CANONICAL_ROUTING_POLICY)
        self.assertEqual(DEFAULT_SEAWORK_MODEL, CANONICAL_SEAWORK_MODEL)


if __name__ == "__main__":
    unittest.main()
