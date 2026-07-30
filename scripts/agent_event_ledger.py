#!/usr/bin/env python3
"""Validate portable JSONL event ledgers for observable multi-agent runs."""

from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


EVENT_TYPES = {"task_started", "agent_started", "tool_called", "evidence_recorded", "review_completed", "task_completed", "task_failed"}
REQUIRED = {"event_id", "timestamp", "run_id", "workspace", "type", "data"}


def event_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def append_event(path: Path, run_id: str, workspace: str, event_type: str, data: dict[str, object]) -> dict[str, object]:
    """Append one durable, vendor-neutral event and return the recorded payload."""
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unsupported agent event type: {event_type}")
    payload: dict[str, object] = {
        "event_id": str(uuid.uuid4()),
        "timestamp": event_timestamp(),
        "run_id": run_id,
        "workspace": workspace,
        "type": event_type,
        "data": data,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
    try:
        os.write(descriptor, encoded.encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return payload


def validate_event(event: object) -> str | None:
    if not isinstance(event, dict) or not REQUIRED.issubset(event):
        return "missing_required_fields"
    if event["type"] not in EVENT_TYPES:
        return "unsupported_type"
    if not isinstance(event["data"], dict):
        return "data_must_be_object"
    try:
        datetime.fromisoformat(str(event["timestamp"]).replace("Z", "+00:00"))
    except ValueError:
        return "invalid_timestamp"
    return None


def validate_file(path: Path) -> list[str]:
    failures: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            failures.append(f"{line_number}:invalid_json")
            continue
        if error := validate_event(event):
            failures.append(f"{line_number}:{error}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate PM Copilot agent-events.jsonl.")
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args()
    failures = validate_file(args.ledger)
    if failures:
        print("\n".join(failures))
        raise SystemExit(1)
    print(f"Valid agent event ledger: {args.ledger}")


if __name__ == "__main__":
    main()
