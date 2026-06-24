# Evaluation Case: Commerce PRD HTML Stability

## Metadata

| Field | Value |
|---|---|
| Case ID | eval-034 |
| Scenario | commerce-prd-html-stability |
| Platform | Web |
| Product Area | Commerce / Monetization |
| Fixture Scope | None |
| PM User Type | Monetization PM |
| Risk Profile | Payment / Subscription / Documentation quality |
| Created | 2026-06-24 |
| Last Updated | 2026-06-24 |

## Raw Request

```text
Please review and iterate a browser-readable PRD for a monetization feature. The PRD should cover checkout or order flow, account or entitlement management, transaction records, exception handling, screenshots/placeholders, external payment documentation links, FAQ, agreement copy, and i18n copy. The HTML style should be stable, especially the table of contents.
```

## Expected Workflow

- Classify the work as PRD/document delivery, not a UI prototype request.
- Review the generated PRD as a full artifact, including Markdown structure and HTML rendering.
- Keep the requirement list as a rough summary and put full behavior in requirement details.
- Keep requirement screenshots or placeholders inline with the related requirement detail.
- Preserve normal external document links, such as payment SDK documentation links, while avoiding remote runtime resources.
- Generate `prd.html` with `scripts/render_prd_html.py`.
- Validate final artifacts with `scripts/run_delivery_checks.py`.

## Required Artifacts

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/prd.html`
- `outputs/<run-id>/run-log.yaml`
- `outputs/<run-id>/tool-results/delivery-check-report.json`

## Known Risks

- Commerce PRDs often become over-broad and mix prototype-only or exception-handling behavior into production scope.
- Requirement details can collapse into a rough table that repeats the requirement list.
- Figures can drift into a detached screenshot list, making the PRD hard to review.
- Copy/i18n sections can mix `key = copy` lines in the pure-text extraction block.
- HTML rendering can inherit unstable Pandoc heading IDs, mixed table alignment, or an inconsistent TOC style.
- Delivery checks can mistakenly reject normal external documentation links as remote runtime dependencies.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Delivery | 23 / 32 |
| PRD | 31 / 40 |
| Metrics and tracking | 21 / 28 |
| UI delivery | Not applicable |
| Delivery review inside PRD | 15 / 20 |

## Pass Criteria

- `prd.md` contains exactly one H1 and uses consistent left-aligned Markdown table separators.
- `需求列表` is a scan-level summary; `需求详情` contains complete per-function behavior or a complete detail table.
- Requirement screenshots or `占位图` blocks appear inline with the related detail row or subsection.
- Copy/i18n pure-text blocks contain only visible copy lines; key mapping is separate.
- `prd.html` uses the fixed PM Copilot document shell, excludes the H1 from the TOC, uses stable ASCII anchors, and keeps the TOC synced to `h2`/`h3`.
- `prd.html` keeps tables readable, left-aligned, and width-aware.
- External document hyperlinks are allowed, but remote scripts, stylesheets, images, and CDN runtimes are blocked.
- Mermaid diagrams render through local `assets/mermaid.min.js`.
- `python3 scripts/run_delivery_checks.py outputs/<run-id> --language zh` passes for final artifacts.

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-06-24 | prd-structure-drift | High | Requirement details became unstable and sometimes duplicated the requirement list instead of providing full functional behavior. | Added requirement-detail structure checks and guidance for list/detail separation. |
| 2026-06-24 | prd-html-toc-drift | High | Browser-readable PRD inherited unstable localized heading IDs and inconsistent TOC styling. | Fixed `render_prd_html.py` to use a fixed document shell, H1-free TOC, and stable ASCII anchors. |
| 2026-06-24 | copy-key-leak | Medium | Pure-text i18n block contained `key = copy` lines instead of copy-only text. | Added pure-text copy validation and template guidance to separate copy extraction from key mapping. |

## Latest Result

| Field | Value |
|---|---|
| Run ID | commerce-prd-html-stability-2026-06-24 |
| Status | Passed |
| Notes | Regression criteria were codified in renderer, output validator, workflow docs, PRD contract, and template guidance. |
