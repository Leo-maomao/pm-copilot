"""Shared acceptance terms for implemented-feature evidence recovery.

The delivery prompt, trace validator, and output validator must describe the
same recovery path. Keep these values here instead of maintaining independent
lists in each layer.
"""

VISUAL_RUNTIME_CAPABILITIES = (
    "existing_preview_discovery",
    "project_runtime_activation",
    "test_state_recovery",
)
VISUAL_RUNTIME_STATUSES = ("passed", "failed", "blocked", "not_available", "not_required")
VISUAL_CAPTURE_METHODS = ("playwright", "chrome_devtools", "computer_use")
VISUAL_CAPTURE_STATUSES = ("passed", "failed", "blocked", "not_available")


def required_placeholder_trace_instruction() -> str:
    """Return the prompt projection of the validator-owned placeholder contract."""
    capabilities = ", ".join(VISUAL_RUNTIME_CAPABILITIES)
    methods = ", ".join(VISUAL_CAPTURE_METHODS)
    capture_statuses = ", ".join(VISUAL_CAPTURE_STATUSES)
    return f"""
Implemented-feature placeholder contract: when `screenshots_and_placeholders`
uses `required_placeholder`, record exactly these runtime-discovery capabilities:
`{capabilities}`. Record exactly these capture recovery methods: `{methods}`.
Each capture record's status must be one of `{capture_statuses}` and include an
action, evidence, and a non-empty run-folder-relative `result_ref` to existing
evidence. Do not claim that a browser or capture method ran when it was
unavailable; use `not_available` or `blocked` with the concrete evidence
instead. The matching PRD requirement
detail must contain `占位图`, and the PRD document-status row must say
`visual figures require manual completion` (or `图示待人工补全`). Set
`readiness.prd_status` to `ready for review`; the placeholder keeps engineering
and launch readiness blocked, not the PRD review state."""
