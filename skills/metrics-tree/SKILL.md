---
name: metrics-tree
description: Use when translating product goals into KPI trees, primary metrics, secondary metrics, guardrails, diagnostics, and measurement assumptions.
---

# Metrics Tree

## Goal

Define how success will be measured inside the PRD before or alongside the tracking plan.

## Workflow

1. Start from the product goal.
2. Assign metric IDs such as `M1`, `M2`, and trace each metric to a goal or requirement.
3. Choose one primary metric and state why it is the best proxy for success.
4. Add secondary metrics that explain user behavior.
5. Add guardrail metrics for possible harm.
6. Add diagnostic metrics to explain movement.
7. Define metric formulas, data source, aggregation grain, measurement window, owner, and refresh cadence.
8. State baseline, target, or directional expectation when available; otherwise mark it as unknown rather than inventing a number.
9. Record measurement limitations, especially when no analytics taxonomy exists or when privacy rules intentionally exclude user-level or sensitive properties.
10. For dashboards, workload summaries, activity summaries, recency indicators, or other aggregate views, define the aggregation grain, permission filter, small-sample privacy risk, excluded detail fields, and whether users without detail access can see the aggregate.
11. For activity or recency summaries, prefer coarse states such as active/inactive buckets over exact timestamps or specific object names unless an approved privacy rule allows more detail.
12. For attribution, contribution, performance decomposition, or funnel breakdowns, define the attribution window, denominator, residual/unattributed bucket, missing-data behavior, and whether the calculation is directional or exact.
13. Do not define a metric that requires collecting raw sensitive data unless an approved analytics or privacy policy allows it.

## Output

- KPI tree or compact metric hierarchy for the PRD
- Metric definitions with ID, owner, source, formula, grain, window, baseline or target status
- Measurement assumptions
- Guardrail metrics
- Diagnostic metrics
- Optional split metric export only when explicitly requested

## Quality Bar

- The primary metric maps to the stated goal.
- Guardrails capture negative side effects.
- Metrics can be instrumented or calculated.
- Every metric states whether it is leading, lagging, diagnostic, or guardrail.
- Sensitive-data minimization can be measured as a guardrail when the feature touches health, finance, payment, identity, or private family context.
- Aggregate metrics avoid leaking private records through counts, rankings, or member-level comparisons unless that visibility is explicitly approved.
- Recency and activity signals do not expose exact private behavior, specific records, or sensitive object names by default.
- Attribution metrics expose residual and missing-data limitations instead of forcing all movement into misleading buckets.
- Default delivery keeps metric content in `prd.md`; do not create `metrics-tree.md` unless the user explicitly asks for a split file.
