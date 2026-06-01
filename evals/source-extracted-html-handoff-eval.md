# Evaluation Case: Source-Extracted HTML Handoff

## Metadata

| Field | Value |
|---|---|
| Case ID | source-extracted-html-handoff |
| Scenario | existing-ui-region-extraction |
| Platform | Web / H5 |
| Product Area | Existing product page region |
| Fixture Scope | Public generic |
| PM User Type | Product manager handing UI reference to engineering |
| Risk Profile | Normal |
| Created | 2026-06-01 |
| Last Updated | 2026-06-01 |

## Raw Request

```text
I already generated the desired feature UI in the original project. Extract just this area into an independent HTML file, add numbered annotations and explanation notes, and hand it to engineering.
```

## Context Files

- Host frontend manifest or render command
- Existing route/page/component source
- Isolated preview route/story/demo containing the requested UI
- Screenshot or running preview URL for the target region

## Expected Workflow

- Classify the run as `repo-backed`.
- Inspect host frontend inventory and style evidence before extraction.
- Treat the running host preview as the visual truth source.
- Use `source_extract_html`, not hand-recreated standalone HTML.
- Run or record `python3 scripts/extract_ui_region.py --target <preview-url-or-file> --selector '<css-selector>' --output outputs/<run-id>/prototype-<platform>.html --run-folder outputs/<run-id>`.
- Record source preview command, preview route, changed isolated source files, extraction selector, source-region screenshot, extracted-region screenshot, region diff result, interaction replay scope and results, style capture method, asset handling, annotation layer, extracted HTML path, validation report, and limitations.
- Validate both the source preview and extracted HTML when browser tooling is available.

## Pass Criteria

- `isolated_ui_prototype.mode` is `source_extract_html`.
- `isolated_ui_prototype.preview_files_changed`, `baseline_import`, `delta_patch`, and `source_to_demo_mapping` are populated.
- `isolated_ui_prototype.source_extract` includes `source_target`, `selector`, `extraction_command`, `extracted_html_path`, `source_region_screenshot`, `extracted_region_screenshot`, `region_diff`, `interaction_scope`, `interaction_checks`, `style_capture_method`, `asset_handling`, `annotation_layer`, `validation_report`, and `limitations`.
- The extracted `prototype-<platform>.html` includes `data-source-extract="true"` or a `source-extract-summary` comment.
- The product surface does not show visible "demo", "prototype", or "not production" labels.
- Annotation markers are numbered, red/white, local to the extracted region, and backed by marker dialogs plus the right-side annotation panel.
- `visual_validation` records source preview evidence and standalone extracted HTML evidence, or a concrete setup limitation.
- The PRD or handoff notes explain that the extracted HTML is a portable reference derived from a captured source preview state, not a replacement for production implementation.

## Artifact Expectation Matrix

| Artifact | Required When | Validation |
|---|---|---|
| `outputs/<run-id>/prd.md` | Required unless the user explicitly asks for UI handoff only. | `python3 scripts/validate_outputs.py outputs/<run-id> --language <en|zh>` |
| Source-backed preview/delta files | Required before extraction when host frontend source exists. | `python3 scripts/validate_ui_preview.py <preview-url-or-file> --run-folder outputs/<run-id>` |
| `outputs/<run-id>/prototype-<platform>.html` | Required when `source_extract_html` is selected. | `python3 scripts/validate_prototype_visual.py outputs/<run-id>` |
| `outputs/<run-id>/run-log.yaml` | Required to preserve extraction traceability. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language <en|zh> --source-preview <preview-url-or-file>` |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-06-01 | extraction-mode-missing | High | The workflow could only choose source preview or standalone fallback, so PMs could not package a source-derived region into an independent annotated HTML handoff. | Add `source_extract_html` as a first-class artifact mode. |
| 2026-06-01 | untraceable-html | High | Standalone HTML had no selector, source screenshot, or preview evidence, so engineering could not audit where it came from. | Require `source_extract` metadata and extraction report. |
| 2026-06-01 | no-equivalence-gate | High | Extracted HTML could be generated without proving it still looked like the rendered demo region. | Require source-region vs extracted-region screenshot diff before claiming visual equivalence. |
| 2026-06-01 | dynamic-behavior-gap | High | Screenshot-matched extracted HTML could still fail core interactions from the source demo. | Add interaction replay and post-action screenshot diff requirements before claiming behavioral equivalence. |

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Source preview evidence | 5 / 5 |
| Extraction traceability | 5 / 5 |
| Standalone HTML annotation contract | 5 / 5 |
| Style and asset limitation honesty | 4 / 5 |
| Validation evidence | 4 / 5 |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Regression case for PM handoff workflows that derive standalone HTML from an already-rendered host-source UI region. |
