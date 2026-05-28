# Evaluation Case: Document-Class Reference Prototype

## Metadata

| Field | Value |
|---|---|
| Case ID | document-class-reference-prototype |
| Scenario | payment-and-risk-rule-reference-with-html-review |
| Platform | Cross-platform |
| Product Area | Documentation, engineering reference, product operations |
| Fixture Scope | None |
| PM User Type | Senior PM / Platform PM |
| Risk Profile | Data quality / Operations / Compliance |
| Created | 2026-05-28 |
| Last Updated | 2026-05-28 |

## Raw Request

```text
We do not need a PRD. Please consolidate these payment gateway rules, refund limits, risk review triggers, and implementation notes into a structured reference document. Include a browser-readable HTML review page if useful. Preserve source facts separately from our final product decisions because we will calibrate rules one group at a time.
```

## Expected Workflow

- Classify this as `structured_reference` plus optional `document_prototype`, not as a normal PRD or product-page UI task.
- Use Knowledge Ops, `artifacts/structured-catalog-contract.md`, `templates/structured-catalog-template.md`, and `templates/document-prototype-template.html`.
- Do not generate `prd.md` because the raw request explicitly says no PRD.
- Build one structured source of truth with entities, fields/rules, source facts, product decisions, attention points, change log, and completeness check.
- Use document attention points for source gaps, PM overrides, conflicts, engineering must-read notes, launch blockers, cost/quota risks, security/compliance risks, and changes.
- Do not require product UI `annotation-marker` controls in the document prototype.

## Required Artifacts

- `outputs/<run-id>/catalog.md` or `outputs/<run-id>/reference.md`
- `outputs/<run-id>/prototype-web.html` or `outputs/<run-id>/reference.html` when HTML is generated
- `outputs/<run-id>/run-log.yaml`

## Artifact Expectation Matrix

| Artifact | Required When | Validation |
|---|---|---|
| Structured reference Markdown | Always required because the request is a document-class reference handoff. | `python3 scripts/validate_outputs.py outputs/<run-id> --language en` |
| Document prototype HTML | Required when the agent chooses browser-readable review as useful or the user asks for HTML. | Must declare `pm-copilot-artifact=document_prototype` and pass `validate_outputs.py`. |
| `run-log.yaml` | Required to record delivery class, source facts, decisions, calibration state, attention points, and validation evidence. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` |
| `prd.md` | Not required and should be omitted. | Explicit not-applicable evidence in `run-log.yaml`. |

## Pass Criteria

- The run log records `structured_reference.delivery_class` and includes entities, fields or rules, decisions, attention points, calibration, change log, and completeness check.
- Markdown distinguishes extracted `source_facts` from final `product_decisions`.
- HTML document prototype, when generated, is self-contained, navigable, table-based, and uses document-native attention points.
- Product UI annotation markers are not required for the document prototype.
- Multi-turn calibration rules require object-level patching and presentation-only mode when requested.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Document delivery fit | 5 / 5 |
| Structured source of truth | 5 / 5 |
| Calibration and change tracking | 5 / 5 |
| Attention point usefulness | 5 / 5 |
| HTML document review usability | 4 / 5 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-28 | document-forced-into-prd | High | Document reference requests can be forced into PRD and ordinary UI prototype delivery. | Add document-class delivery classification, structured reference schema, document prototype template, and attention-point validation. |
| 2026-05-28 | generic-document-annotations | Medium | Document HTML can include useless UI-style annotations instead of source/risk/decision attention points. | Require typed `attention_points` with concrete `target_ref`. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Pending execution with user-supplied payment/risk source data. |
