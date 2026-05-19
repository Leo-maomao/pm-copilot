---
name: acceptance-criteria
description: Use when writing testable acceptance criteria, QA-ready conditions, and completion rules for product requirements.
---

# Acceptance Criteria

## Goal

Make requirements objectively reviewable and testable.

## Workflow

1. Assign stable acceptance IDs such as `AC-F1-01` and trace each item to a requirement or function ID.
2. Convert each requirement into observable behavior.
3. Include only confirmed MVP requirements, not optional or future capabilities.
4. Include normal, boundary, error, permission, eligibility, fallback, rollback, and cancellation cases when relevant.
5. Use Given/When/Then for multi-step flows, approvals, async states, or cross-role workflows.
6. Link acceptance criteria to tracking or metrics when behavior must be measured.
7. State the verification method: UI check, API response, data record, log/audit entry, analytics event, or manual approval evidence.
8. For unreviewed content payloads, verify placeholder or draft handling without treating the content as launch-approved.
9. For user-facing repo-backed features, include enough criteria to cover entry, primary path, ineligible or permission state, content/source state, and analytics/privacy behavior.
10. For generated or repeated records, include at least one criterion for duplicate prevention, edit/delete propagation, skipped instance handling, and boundary dates when those behaviors are in MVP scope.
11. For destructive, irreversible, membership-changing, or permission-reducing actions, include criteria for impact summary, explicit confirmation, blocking conditions, recovery or cooling-off behavior when available, audit/log expectation, and the state after cancellation.
12. For financial calculation or portfolio-analysis features, include criteria for calculation source, stale/missing data behavior, disclaimer visibility, and proof that the UI does not instruct the user to buy, sell, or rebalance unless that advice workflow has explicit approval.
13. Keep launch approvals, content approvals, legal reviews, and operational readiness as readiness gates unless the PRD explicitly makes them product behavior.

## Output

- Acceptance criteria table with ID, source requirement, condition, expected result, priority or phase, and verification method
- Given/When/Then scenarios
- QA notes
- Measurement verification notes
- Launch-readiness exclusions for content, compliance, or operational approvals

## Quality Bar

- A tester can verify pass/fail.
- Every criterion has a source requirement ID and a stable acceptance ID.
- Criteria do not depend on hidden assumptions.
- Critical edge cases are covered.
- Recurrence, scheduled reminders, retry queues, and other generated-state features have objective pass/fail checks for instance creation and cleanup.
- Dangerous actions are testable for both completed and canceled paths, including who is blocked from acting.
- Financial outputs are testable as calculations or explanations, not hidden investment recommendations.
- Optional or launch-only decisions do not become must-build MVP criteria.
- Acceptance criteria cover confirmed MVP behavior only, but they still test launch-blocking labels and safeguards when placeholder or regulated content is visible.
