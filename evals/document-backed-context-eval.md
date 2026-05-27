# Evaluation Case: Document-Backed Product Context

## Metadata

| Field | Value |
|---|---|
| Case ID | eval-003 |
| Scenario | document-backed-checkout |
| Platform | Unknown |
| Product Area | Existing product documented outside code |
| Fixture Scope | None |
| PM User Type | Novice PM |
| Risk Profile | Operations / Data quality |
| Created | 2026-05-18 |
| Last Updated | 2026-05-26 |

## Raw Request

```text
We do not have a project repository here. I uploaded last quarter's checkout PRD, a support-ticket export, and a KPI summary. Please help plan the next checkout improvement.
```

## Context Files

- Historical PRD
- Support ticket export
- KPI summary

## Expected First Pass

- Classify the run as `document-backed`.
- Treat the uploaded product documents as current product context.
- Extract current behavior, pain points, existing metrics, and known constraints from the documents.
- Ask must-answer questions only for gaps that materially affect scope, platform, metrics, privacy, payment, legal, compliance, security, or UI delivery direction.
- Do not ask for a software repository as a prerequisite.

## Pass Criteria

- The agent does not require a host repository.
- The agent cites or references the provided document set as context loaded.
- The agent separates document-backed facts from assumptions.
- The agent asks blocking questions before downstream generation when document context is insufficient.
- The agent can proceed to review-ready PRD/UI delivery after answers or explicit assumption approval.
- Generated prose follows the user's language, while file names and identifiers remain ASCII.
- `python3 scripts/validate_outputs.py outputs/<run-id> --language zh` or `--language en` passes according to the user's output language.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Context mode classification | 5 / 5 |
| Document evidence separation | 5 / 5 |
| Clarification control | 4 / 5 |
| PRD and UI readiness | 4 / 5 |
| Validation evidence | 4 / 5 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-18 | repo-assumption | High | Workflow implied current project context must come from a software repository. | Added repo-backed, document-backed, and brief-only context modes. |

## Latest Result

| Field | Value |
|---|---|
| Run ID | document-backed-checkout-20260526-1852 |
| Status | Passed |
| Notes | Non-fixture document-backed run generated PRD and run-log from uploaded-document context without requiring a repository. `python3 scripts/run_delivery_checks.py outputs/document-backed-checkout-20260526-1852 --language en` passed. Platform, service contracts, privacy review, and launch approvals remain explicit blockers. |
