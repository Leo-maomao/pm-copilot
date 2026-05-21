# Evaluation Case: Existing UI Prototype Delta

## Metadata

| Field | Value |
|---|---|
| Case ID | existing-ui-prototype-delta |
| Scenario | existing-settings-enhancement |
| Platform | Web |
| Product Area | Existing settings page |
| Created | 2026-05-18 |
| Last Updated | 2026-05-21 |

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
- Inspect the existing component library, style tokens, route/page source, and any available screenshot before prototyping.
- Treat the prototype as a change to the existing surface, not as a new product.
- Record concrete style evidence and source-to-demo mappings before claiming the prototype is complete.

## Pass Criteria

- Prototype preserves the current page structure, navigation, layout density, and component style.
- Run log `style_evidence.source_files`, `style_evidence.reused_components`, and `source_to_demo_mapping` name real host files/components and explain how they are represented in the prototype.
- Prototype clearly shows the new requirement as a delta on the existing page.
- Each page or screen has its own annotation group.
- Each annotation is reachable from a marker or hotspot tied to a specific UI element, with details in a local marker popover beside that UI element and the current-state annotation list.
- Marker visual style does not change after click, and clicking the same marker again closes the local popover.
- Marker-triggered notes do not open a full-screen/global modal or backdrop.
- If exact online fidelity is requested, the run uses a host-rendered preview route or Storybook/demo mode when source changes are allowed; otherwise the standalone HTML limitation is explicit.
- Cross-page notes are separated from page-specific notes.
- The PRD records which existing files or screenshots informed the prototype.

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-18 | prototype-greenfield | High | Prototype looked like a new product instead of extending an existing demo. | Require existing-surface mapping and page-scoped annotations. |
| 2026-05-21 | global-marker-modal | Medium | Marker click opened a centered global annotation modal instead of a small popover beside the marked component. | Require local marker popovers and add validation for marker-dialog geometry. |
| 2026-05-21 | shallow-style-evidence | High | Prototype claimed host style reuse but did not faithfully mirror the real component library and online surface. | Require concrete source files, reused components, and source-to-demo mappings. |
| 2026-05-21 | source-parity-gap | High | Standalone HTML could not exactly reproduce real icons and component internals. | Add host-rendered preview route/story mode for source-level fidelity expectations. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Regression case for prototype quality in repo-backed products with existing UI. |
