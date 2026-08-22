import unittest

from runtime_limits import (
    DEFAULT_EVALUATION_MAX_REVISIONS, DEFAULT_EXECUTION_TIMEOUT_MINUTES,
    DEFAULT_INTERACTIVE_MAX_REVISIONS, DEFAULT_LOOP_MAX_ITERATIONS,
    DEFAULT_LOOP_TIMEOUT_MINUTES, DEFAULT_PORTFOLIO_MAX_REVISIONS,
    DEFAULT_PORTFOLIO_WORKERS, MAX_CODEX_CASE_WORKERS,
    SEAWORK_RESTART_TIMEOUT_SECONDS,
)


class RuntimeLimitsTests(unittest.TestCase):
    def test_defaults_preserve_existing_workflow_contracts(self) -> None:
        self.assertEqual(DEFAULT_EXECUTION_TIMEOUT_MINUTES, 15)
        self.assertEqual(DEFAULT_INTERACTIVE_MAX_REVISIONS, 3)
        self.assertEqual(DEFAULT_EVALUATION_MAX_REVISIONS, 2)
        self.assertEqual(DEFAULT_PORTFOLIO_MAX_REVISIONS, 1)
        self.assertEqual(DEFAULT_PORTFOLIO_WORKERS, 1)
        self.assertEqual(MAX_CODEX_CASE_WORKERS, 3)
        self.assertEqual(DEFAULT_LOOP_TIMEOUT_MINUTES, 30)
        self.assertEqual(DEFAULT_LOOP_MAX_ITERATIONS, 2)
        self.assertEqual(SEAWORK_RESTART_TIMEOUT_SECONDS, 90)

    def test_revision_budgets_are_explicitly_ordered(self) -> None:
        self.assertGreater(DEFAULT_INTERACTIVE_MAX_REVISIONS, DEFAULT_EVALUATION_MAX_REVISIONS)
        self.assertGreater(DEFAULT_EVALUATION_MAX_REVISIONS, DEFAULT_PORTFOLIO_MAX_REVISIONS)


if __name__ == "__main__":
    unittest.main()
