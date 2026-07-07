# Evaluation Case: Implemented Feature PRD Inline Figure Table

## Metadata

| Field | Value |
|---|---|
| Case ID | eval-039 |
| Scenario | implemented-feature-prd-inline-figure-table |
| Platform | Web |
| Product Area | Generic asset/content management |
| Created | 2026-07-07 |
| Last Updated | 2026-07-07 |
| Fixture Scope | Fixture-scoped |
| PM User Type | AI product manager |
| Risk Profile | Documentation quality |

## Fixture Isolation Terms

- inline-figure-table-fixture

This eval may use a host product with media assets, dialogs, side panels, or file folders as pressure context. Host product names, local paths, API fields, routes, and domain vocabulary must stay inside fixture evidence or output folders and must not enter generic PM Copilot prompts, templates, skills, workflows, tools, or docs.

## Raw Request

```text
The feature is already implemented. Reconstruct the current branch into a Chinese implemented-feature PRD and browser-readable prd.html. Several UI states need screenshots, but final images are not ready yet; put placeholders where reviewers will replace them later.
```

## Expected Workflow

- Classify the run as `implemented-feature-prd`.
- Inspect current branch evidence before drafting.
- Use `templates/implemented-feature-prd-template.md`.
- Generate both `prd.md` and `prd.html`.
- Keep every screenshot or missing-image marker inline with the exact requirement detail it explains.
- If a requirement detail is written as a two-column field/value table, put the real image or missing-image marker in the same `图示` or `截图` row value cell.
- Render `prd.html` with `scripts/render_prd_html.py`.
- Validate final artifacts with `scripts/run_delivery_checks.py`.

## Required Artifacts

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/prd.html`
- `outputs/<run-id>/run-log.yaml`
- `outputs/<run-id>/tool-results/delivery-check-report.json`

## Known Risks

- The agent may leave a `图示` row blank and place the placeholder below the table.
- The agent may turn screenshots into a detached image list.
- The renderer may include the H1 title in the TOC.
- Replacing placeholders with real images may move the image outside the original requirement row.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Delivery | 23 / 32 |
| PRD | 31 / 40 |
| Metrics and tracking | 21 / 28 |
| UI delivery | Not applicable |
| Delivery review inside PRD | 15 / 20 |

## Pass Criteria

- `prd.md` has exactly one H1 and follows the fixed numbered implemented-feature structure.
- Every missing screenshot marker uses either the blockquote form in prose or the single-cell form inside a table: `占位图：<file>.png<br>用途：...`.
- Requirement-detail field/value tables do not have blank `图示`/`截图` rows when an image or placeholder exists for that requirement.
- Images and placeholders do not appear as paragraphs or blockquotes immediately after a field/value requirement table.
- `prd.html` keeps table images inside table cells and supports click-to-fullscreen for real images.
- `prd.html` TOC starts from numbered sections and excludes the H1 title.
- `python3 scripts/run_delivery_checks.py outputs/<run-id> --language zh` passes.

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-07-07 | inline-figure-table-drift | High | A Chinese implemented-feature PRD placed missing screenshot placeholders outside the requirement detail table, forcing manual repair before review. | Added table-cell placeholder guidance, stricter Markdown validation, and a more robust H1-free PRD HTML TOC renderer. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Added as a regression case for practice-driven self-iteration after a real user correction. |
