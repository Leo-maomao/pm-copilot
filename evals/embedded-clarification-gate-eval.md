# Evaluation Case: Embedded Clarification Gate

## Metadata

| Field | Value |
|---|---|
| Case ID | eval-002 |
| Scenario | embedded-simple-request |
| Platform | Unknown |
| Product Area | Host project feature |
| Created | 2026-05-18 |
| Last Updated | 2026-05-18 |

## Raw Request

```text
Add a better approval flow for team changes.
```

## Context Files

- `pm-copilot/PM_COPILOT.md`
- Host project README and relevant app files

## Expected First Pass

- Detect embedded mode.
- Inspect relevant host project context before proposing a solution.
- Infer a unique run id.
- Ask blocking questions in the conversation and create only `run-log.yaml` if a persistent trace is useful when must-answer questions remain open.
- Stop before `prd.md`, metrics/tracking sections, flow sections, prototype, delivery review, and separate summary files.

## Must-Answer Questions

- Which current module or screen owns team changes?
- Who can request, approve, reject, and audit a team change today?
- Which team changes need approval?
- What is the desired business outcome or risk reduction?
- Which platform should be covered first?
- Are there compliance, security, audit, or permission constraints?

## Pass Criteria

- The agent does not assume a greenfield team-management product.
- The agent references host project context that was actually inspected.
- The agent asks must-answer questions before downstream generation.
- The agent does not generate downstream artifacts until the user answers or explicitly asks for a draft with assumption or confirmation risk.
- Generated prose follows the user's language, while file names and identifiers remain ASCII.
- Output paths use `outputs/<run-id>/`, not a shared fixed folder.

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-18 | clarification-gate-bypass | High | Agent generated full PRD/prototype delivery before asking blocking questions. | Added embedded project context loading and clarification gate rules. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Regression case for embedded project usage and simple ambiguous requests. |
