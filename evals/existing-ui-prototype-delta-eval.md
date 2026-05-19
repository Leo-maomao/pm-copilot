# Evaluation Case: Existing UI Prototype Delta

## Metadata

| Field | Value |
|---|---|
| Case ID | existing-ui-prototype-delta |
| Scenario | existing-settings-enhancement |
| Platform | Web |
| Product Area | Existing settings page |
| Created | 2026-05-18 |
| Last Updated | 2026-05-18 |

## Raw Request

```text
Add an approval reminder setting to the existing workspace settings page. There is already a demo page and component library in the repository.
```

## Context Files

- Host repository README
- Existing settings route or demo page
- Existing component or design-system files

## Expected Workflow

- Classify the run as `repo-backed`.
- Inspect the existing settings page or demo before prototyping.
- Treat the prototype as a change to the existing surface, not as a new product.

## Pass Criteria

- Prototype preserves the current page structure, navigation, layout density, and component style.
- Prototype clearly shows the new requirement as a delta on the existing page.
- Each page or screen has its own annotation group.
- Each annotation is reachable from a marker or hotspot tied to a specific UI element, with details in a marker-triggered dialog and the current-state annotation list.
- Cross-page notes are separated from page-specific notes.
- The PRD records which existing files or screenshots informed the prototype.

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-18 | prototype-greenfield | High | Prototype looked like a new product instead of extending an existing demo. | Require existing-surface mapping and page-scoped annotations. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Regression case for prototype quality in repo-backed products with existing UI. |
