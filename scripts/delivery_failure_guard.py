"""Pure helpers for preventing repeated, identical failed delivery attempts.

The controller owns persistence and decides which failures are worth recording.
This module only creates a stable fingerprint and evaluates a caller-supplied
history.  A history item has this minimal shape::

    {"failure_fingerprint": "...", "outcome": "no_progress"}

Only an exact fingerprint and the ``no_progress`` outcome consume the retry
budget.  Changing any fingerprint input therefore starts a separate budget.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


FINGERPRINT_SCHEMA_VERSION = 1
NO_PROGRESS_OUTCOME = "no_progress"


@dataclass(frozen=True)
class DeliveryFailureGuardDecision:
    """The pure decision a controller can persist or expose to an operator."""

    fingerprint: str
    no_progress_attempts: int
    no_progress_limit: int
    blocked: bool
    reason: str

    @property
    def allowed(self) -> bool:
        """Whether a new attempt may be launched."""
        return not self.blocked

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation for controller state."""
        return {
            "fingerprint": self.fingerprint,
            "no_progress_attempts": self.no_progress_attempts,
            "no_progress_limit": self.no_progress_limit,
            "blocked": self.blocked,
            "allowed": self.allowed,
            "reason": self.reason,
        }


def _canonical_text(value: object) -> str | None:
    """Preserve meaningful values while removing accidental boundary whitespace."""
    if value is None:
        return None
    return str(value).strip()


def delivery_failure_fingerprint_payload(
    *,
    scope_fingerprint: object,
    baseline_digest: object,
    runtime_version: object,
    controller_version: object,
    requested_provider: object,
    requested_model: object,
    failed_artifact: object,
    failure_category: object,
    precondition_digest: object,
) -> dict[str, str | int | None]:
    """Return the canonical, versioned payload used for a failure fingerprint.

    Digest values are intentionally opaque.  ``None`` remains distinct from
    an empty string so a newly discovered value can re-key a retry budget.
    """
    return {
        "schema_version": FINGERPRINT_SCHEMA_VERSION,
        "scope_fingerprint": _canonical_text(scope_fingerprint),
        "baseline_digest": _canonical_text(baseline_digest),
        "runtime_version": _canonical_text(runtime_version),
        "controller_version": _canonical_text(controller_version),
        "requested_provider": _canonical_text(requested_provider),
        "requested_model": _canonical_text(requested_model),
        "failed_artifact": _canonical_text(failed_artifact),
        "failure_category": _canonical_text(failure_category),
        "precondition_digest": _canonical_text(precondition_digest),
    }


def build_delivery_failure_fingerprint(
    *,
    scope_fingerprint: object,
    baseline_digest: object,
    runtime_version: object,
    controller_version: object,
    requested_provider: object,
    requested_model: object,
    failed_artifact: object,
    failure_category: object,
    precondition_digest: object,
) -> str:
    """Create a stable SHA-256 fingerprint for one no-progress failure state."""
    payload = delivery_failure_fingerprint_payload(
        scope_fingerprint=scope_fingerprint,
        baseline_digest=baseline_digest,
        runtime_version=runtime_version,
        controller_version=controller_version,
        requested_provider=requested_provider,
        requested_model=requested_model,
        failed_artifact=failed_artifact,
        failure_category=failure_category,
        precondition_digest=precondition_digest,
    )
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def failure_attempt_record(fingerprint: str, *, made_progress: bool = False) -> dict[str, str]:
    """Create the minimal history record understood by the retry guard."""
    return {
        "failure_fingerprint": str(fingerprint),
        "outcome": "progress" if made_progress else NO_PROGRESS_OUTCOME,
    }


def count_matching_no_progress_attempts(attempts: Iterable[object], fingerprint: str) -> int:
    """Count recorded no-progress attempts for this exact fingerprint only."""
    return sum(
        1
        for attempt in attempts
        if isinstance(attempt, Mapping)
        and attempt.get("failure_fingerprint") == fingerprint
        and attempt.get("outcome") == NO_PROGRESS_OUTCOME
    )


def decide_delivery_failure_attempt(
    attempts: Iterable[object],
    *,
    fingerprint: str,
    no_progress_limit: int,
) -> DeliveryFailureGuardDecision:
    """Decide whether another attempt would repeat exhausted no-progress work.

    ``no_progress_limit`` is the number of previously recorded identical
    no-progress attempts tolerated before launching another attempt is blocked.
    It must be at least one, so a first attempt is always possible.
    """
    is_valid_limit = (
        isinstance(no_progress_limit, int)
        and not isinstance(no_progress_limit, bool)
        and no_progress_limit >= 1
    )
    if not is_valid_limit:
        raise ValueError("no_progress_limit must be an integer greater than zero")

    count = count_matching_no_progress_attempts(attempts, fingerprint)
    blocked = count >= no_progress_limit
    return DeliveryFailureGuardDecision(
        fingerprint=fingerprint,
        no_progress_attempts=count,
        no_progress_limit=no_progress_limit,
        blocked=blocked,
        reason=(
            "identical_failure_fingerprint_no_progress_limit_reached"
            if blocked
            else "failure_fingerprint_is_new_or_within_no_progress_budget"
        ),
    )


__all__ = [
    "DeliveryFailureGuardDecision",
    "FINGERPRINT_SCHEMA_VERSION",
    "NO_PROGRESS_OUTCOME",
    "build_delivery_failure_fingerprint",
    "count_matching_no_progress_attempts",
    "decide_delivery_failure_attempt",
    "delivery_failure_fingerprint_payload",
    "failure_attempt_record",
]
