import unittest

from delivery_failure_guard import (
    NO_PROGRESS_OUTCOME,
    build_delivery_failure_fingerprint,
    decide_delivery_failure_attempt,
    delivery_failure_fingerprint_payload,
    failure_attempt_record,
)


BASE_CONTEXT = {
    "scope_fingerprint": "scope-v1",
    "baseline_digest": "baseline-v1",
    "runtime_version": "6.2.103",
    "controller_version": "controller-v1",
    "requested_provider": "seawork",
    "requested_model": "codex/gpt-5.6-terra",
    "failed_artifact": "run-log.yaml",
    "failure_category": "control_plane_unavailable",
    "precondition_digest": "stage-v1",
}


class DeliveryFailureGuardTests(unittest.TestCase):
    def test_fingerprint_is_stable_for_equivalent_context(self) -> None:
        first = build_delivery_failure_fingerprint(**BASE_CONTEXT)
        equivalent = {key: f"  {value}  " for key, value in BASE_CONTEXT.items()}
        second = build_delivery_failure_fingerprint(**equivalent)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertEqual(
            delivery_failure_fingerprint_payload(**BASE_CONTEXT)["schema_version"],
            1,
        )

    def test_every_context_input_rekeys_the_fingerprint(self) -> None:
        original = build_delivery_failure_fingerprint(**BASE_CONTEXT)
        for field, value in BASE_CONTEXT.items():
            with self.subTest(field=field):
                changed = dict(BASE_CONTEXT)
                changed[field] = f"changed-{value}"
                self.assertNotEqual(original, build_delivery_failure_fingerprint(**changed))

    def test_identical_no_progress_attempts_are_blocked_at_limit(self) -> None:
        fingerprint = build_delivery_failure_fingerprint(**BASE_CONTEXT)
        history = [
            failure_attempt_record(fingerprint),
            {"failure_fingerprint": fingerprint, "outcome": NO_PROGRESS_OUTCOME},
            failure_attempt_record(fingerprint, made_progress=True),
            {"failure_fingerprint": "different", "outcome": NO_PROGRESS_OUTCOME},
            object(),
        ]

        decision = decide_delivery_failure_attempt(history, fingerprint=fingerprint, no_progress_limit=2)

        self.assertTrue(decision.blocked)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.no_progress_attempts, 2)
        self.assertEqual(
            decision.reason,
            "identical_failure_fingerprint_no_progress_limit_reached",
        )
        self.assertTrue(decision.as_dict()["blocked"])

    def test_attempt_is_allowed_below_identical_no_progress_limit(self) -> None:
        fingerprint = build_delivery_failure_fingerprint(**BASE_CONTEXT)
        decision = decide_delivery_failure_attempt(
            [failure_attempt_record(fingerprint)],
            fingerprint=fingerprint,
            no_progress_limit=2,
        )

        self.assertTrue(decision.allowed)
        self.assertFalse(decision.blocked)
        self.assertEqual(decision.no_progress_attempts, 1)

    def test_changed_context_uses_a_fresh_budget(self) -> None:
        original = build_delivery_failure_fingerprint(**BASE_CONTEXT)
        exhausted_history = [failure_attempt_record(original)]

        for field, value in BASE_CONTEXT.items():
            with self.subTest(field=field):
                changed = dict(BASE_CONTEXT)
                changed[field] = f"changed-{value}"
                fingerprint = build_delivery_failure_fingerprint(**changed)
                decision = decide_delivery_failure_attempt(
                    exhausted_history,
                    fingerprint=fingerprint,
                    no_progress_limit=1,
                )
                self.assertTrue(decision.allowed)
                self.assertEqual(decision.no_progress_attempts, 0)

    def test_invalid_no_progress_limit_is_rejected(self) -> None:
        fingerprint = build_delivery_failure_fingerprint(**BASE_CONTEXT)
        for limit in (0, -1, True, "2"):
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError):
                    decide_delivery_failure_attempt([], fingerprint=fingerprint, no_progress_limit=limit)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
