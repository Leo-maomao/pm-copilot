"""Stage capability policy shared by Agent controllers.

Model IDs below are compatibility fallbacks only. Normal routing must use the
user/provider model catalog and may not assume these IDs exist.
"""

from __future__ import annotations

MODEL_ROUTING_POLICY = "adaptive-stage-v1"
# Kept for backwards-compatible traces and explicit operator fallback only.
STANDARD_MODEL = "gpt-5.6-terra"
HIGH_JUDGMENT_MODEL = "gpt-5.6-sol"
DEFAULT_SEAWORK_MODEL = f"codex/{HIGH_JUDGMENT_MODEL}"

__all__ = [
    "DEFAULT_SEAWORK_MODEL",
    "HIGH_JUDGMENT_MODEL",
    "MODEL_ROUTING_POLICY",
    "STANDARD_MODEL",
]
