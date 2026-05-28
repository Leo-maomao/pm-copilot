# Evaluation Case: Model Integration Catalog Handoff

## Metadata

| Field | Value |
|---|---|
| Case ID | model-integration-catalog-handoff |
| Scenario | new-model-parameter-matrix-for-engineering |
| Platform | Cross-platform |
| Product Area | AI model integration, engineering reference documentation |
| Fixture Scope | None |
| PM User Type | AI product manager / Senior PM |
| Risk Profile | Data quality / Operations / Compliance |
| Created | 2026-05-27 |
| Last Updated | 2026-05-27 |

## Raw Request

```text
We are integrating a batch of new AI models. Please list every model's provider, model id, supported input/output modalities, context window, required parameters, optional parameters, rate limits, pricing source, deprecation status, SDK/API notes, and engineering integration caveats. Deliver it as Markdown, and also provide HTML if useful for engineering review.
```

## Expected Workflow

- Classify this as a structured reference/catalog handoff, not a PRD/UI task.
- Use `knowledge-ops` and `artifacts/structured-catalog-contract.md`.
- If HTML is generated for document review, use document prototype semantics and do not require ordinary product UI annotation markers.
- Ask for source documents or use current official sources before filling fast-changing model facts.
- Mark unknown parameters, limits, pricing, availability, regions, or deprecation status per row instead of inventing values.
- Generate `catalog.md` by default and `catalog.html` only when requested or useful.
- Preserve source facts separately from product decisions when user calibration changes model parameters or defaults.
- Run delivery checks.

## Required Artifacts

- `outputs/<run-id>/catalog.md`
- `outputs/<run-id>/run-log.yaml`
- `outputs/<run-id>/catalog.html` when HTML is requested or useful for review

## Artifact Expectation Matrix

| Artifact | Required When | Validation |
|---|---|---|
| `catalog.md` | Always required because the request is a model parameter matrix handoff. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |
| `catalog.html` | Required only when the user asks for HTML or a browser-readable table. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |
| `run-log.yaml` | Required to record source status, review status, row count, blocked rows, and validation evidence. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` |
| `prd.md` | Not required unless the user also asks for a product requirement or rollout plan. | Explicit not-applicable evidence in `run-log.yaml`. |

## Pass Criteria

- `catalog.md` starts with `artifact_type: structured_catalog` frontmatter.
- Catalog includes field dictionary, source/review status, model integration table, engineering handoff notes, and validation results.
- Every row includes `item_id`, `provider`, `model_id`, `display_name`, `version_or_release`, `input_modalities`, `output_modalities`, `context_window`, `required_parameters`, `optional_parameters`, `rate_limits`, `pricing_source`, `deprecation_status`, `source_status`, `review_status`, `owner`, `access_date`, and `implementation_notes`.
- Fast-changing values are source-backed or explicitly marked draft/blocked with owner confirmation.
- HTML, when generated, is self-contained and includes the structured catalog meta marker.
- Document prototype HTML, when generated instead of a flat catalog HTML, is self-contained, includes `pm-copilot-artifact=document_prototype`, and uses typed attention points for source gaps, overrides, conflicts, engineering must-read notes, blockers, and changes.
- `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` passes.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Structured catalog fit | 5 / 5 |
| Source and review status | 5 / 5 |
| Model parameter completeness | 5 / 5 |
| Unknown-value handling | 4 / 5 |
| Engineering handoff usability | 5 / 5 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-27 | table-handoff-forced-into-prd | Medium | Table-first engineering reference requests can be forced into PRD/UI workflow and lose row-level source, review, and parameter completeness. | Add structured catalog contract, template, validation, and model integration eval. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Pending execution with source-backed or user-supplied model data. |
