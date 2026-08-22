"""Canonical deterministic contracts shared by evaluation portfolio tools."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def plan_digest(cases: list[dict[str, Any]]) -> str:
    """Return the stable identity of an evaluation plan snapshot."""
    payload = json.dumps(cases, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = ["plan_digest"]
