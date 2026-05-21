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
- Record host frontend inventory, including entry files, route/page files, component-library files, style files, icon/asset sources, render command, and preview surface.
- Treat the prototype as a change to the existing surface, not as a new product.
- Import/render the existing baseline from host source and add the new requirement only through isolated delta patch files.
- Record concrete style evidence and source-to-demo mappings before claiming the prototype is complete.

## Pass Criteria

- Prototype preserves the current page structure, navigation, layout density, and component style.
- Run log `host_frontend_inventory`, `style_evidence.source_files`, `style_evidence.reused_components`, `style_evidence.icon_asset_sources`, and `source_to_demo_mapping` name real host files/components/assets and explain how they are represented in the prototype.
- Run log `isolated_ui_prototype.baseline_import` lists imported baseline sources and `delta_patch` lists only preview/delta files, strategy, and next multi-turn anchor.
- Prototype clearly shows the new requirement as a delta on the existing page.
- Each page or screen has its own annotation group.
- Each annotation is reachable from a marker or hotspot tied to a specific UI element, with details in a local marker popover beside that UI element and the current-state annotation list.
- Marker visual style does not change after click, and clicking the same marker again closes the local popover.
- Markers and matching annotation number badges are red fill, white text, borderless, and use plain digits instead of circled numeral glyphs or nested badge content.
- The annotation floating control shows only `注释` or `Notes`, hides while a right-edge full-height annotation panel is open, and reappears when the panel closes.
- Any page/state switching control is fixed outside the product layout.
- Marker-triggered notes do not open a full-screen/global modal or backdrop.
- If host frontend source exists, the run uses a source-rendered delta patch, preview route, Storybook/demo, Mini Program preview page, or App preview screen as appropriate; otherwise the standalone HTML limitation is explicit.
- Cross-page notes are separated from page-specific notes.
- The PRD records which existing files or screenshots informed the prototype.

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-18 | prototype-greenfield | High | Prototype looked like a new product instead of extending an existing demo. | Require existing-surface mapping and page-scoped annotations. |
| 2026-05-21 | global-marker-modal | Medium | Marker click opened a centered global annotation modal instead of a small popover beside the marked component. | Require local marker popovers and add validation for marker-dialog geometry. |
| 2026-05-21 | shallow-style-evidence | High | Prototype claimed host style reuse but did not faithfully mirror the real component library and online surface. | Require concrete source files, reused components, and source-to-demo mappings. |
| 2026-05-21 | source-parity-gap | High | Standalone HTML could not exactly reproduce real icons, component internals, or native platform chrome. | Add source-rendered preview modes for Web/H5, Mini Program, and App fidelity expectations. |
| 2026-05-21 | prototype-only-misread | High | Agent interpreted "only generate a prototype" as consent for standalone HTML and skipped a renderable host source preview. | Require raw-request portable/standalone/HTML wording or concrete source-rendering blocker before standalone fallback. |
| 2026-05-21 | source-first-missing | High | Agent treated source rendering as optional unless exact fidelity was requested. | Require source-rendered preview/delta whenever frontend source exists, except explicit standalone, explicit redesign/greenfield, or concrete blocker cases. |
| 2026-05-21 | annotation-ui-inconsistency | Medium | Marker badges, note badges, annotation panel, and state switcher controls did not follow the required fixed interaction model. | Enforce red/white borderless badges, short annotation floating control, right-side full-height panel, and fixed state switchers. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Regression case for prototype quality in repo-backed products with existing UI. |
