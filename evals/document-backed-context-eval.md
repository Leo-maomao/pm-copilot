# Evaluation Case: Document-Backed Product Context

## Metadata

| Field | Value |
|---|---|
| Case ID | eval-003 |
| Scenario | document-backed-checkout |
| Platform | Unknown |
| Product Area | Existing product documented outside code |
| Created | 2026-05-18 |
| Last Updated | 2026-05-18 |

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

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-18 | repo-assumption | High | Workflow implied current project context must come from a software repository. | Added repo-backed, document-backed, and brief-only context modes. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Regression case for PMs who have product documents but no code repository. |
