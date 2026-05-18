---
name: acceptance-criteria
description: Use when writing testable acceptance criteria, QA-ready conditions, and completion rules for product requirements.
---

# Acceptance Criteria

## Goal

Make requirements objectively reviewable and testable.

## Workflow

1. Convert each requirement into observable behavior.
2. Include only confirmed MVP requirements, not optional or future capabilities.
3. Include normal, boundary, error, permission, eligibility, fallback, and rollback cases when relevant.
4. Use Given/When/Then for complex flows.
5. Link acceptance criteria to tracking or metrics when behavior must be measured.
6. For unreviewed content payloads, verify placeholder or draft handling without treating the content as launch-approved.

## Output

- Acceptance criteria table
- Given/When/Then scenarios
- QA notes
- Measurement verification notes
- Launch-readiness exclusions for content, compliance, or operational approvals

## Quality Bar

- A tester can verify pass/fail.
- Criteria do not depend on hidden assumptions.
- Critical edge cases are covered.
- Optional or launch-only decisions do not become must-build MVP criteria.
