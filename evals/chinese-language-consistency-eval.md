# Evaluation Case: Chinese Language Consistency

## Metadata

| Field | Value |
|---|---|
| Case ID | chinese-language-consistency |
| Scenario | chinese-checkout-improvement |
| Platform | H5 |
| Product Area | Checkout optimization |
| Created | 2026-05-18 |
| Last Updated | 2026-05-18 |

## Raw Request

```text
我们想优化结算页优惠券使用体验，请先看现有结算相关文档，如果关键信息不够先问我。
```

## Expected Workflow

- Classify context mode.
- Load relevant product context.
- Ask blocking questions before downstream generation when needed.
- Generate Chinese artifacts after the clarification gate passes.

## Pass Criteria

- Human-facing headings in `prd.md` are Chinese, not copied from English templates.
- Table labels, status labels, prototype annotations, review labels, and next actions are Chinese.
- File names, event names, property names, requirement IDs, and Mermaid node IDs remain ASCII.
- Any English terms that remain are product names, technical identifiers, or intentionally preserved terms.

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-18 | localization-template-leak | Medium | Markdown headings stayed English while body text was Chinese. | Require localization of headings, table labels, statuses, and prototype annotations. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Regression case for mixed English headings and Chinese body text. |
