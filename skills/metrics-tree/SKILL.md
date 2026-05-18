---
name: metrics-tree
description: Use when translating product goals into KPI trees, primary metrics, secondary metrics, guardrails, diagnostics, and measurement assumptions.
---

# Metrics Tree

## Goal

Define how success will be measured inside the PRD before or alongside the tracking plan.

## Workflow

1. Start from the product goal.
2. Choose one primary metric.
3. Add secondary metrics that explain user behavior.
4. Add guardrail metrics for possible harm.
5. Add diagnostic metrics to explain movement.
6. Define metric formulas and measurement windows.

## Output

- KPI tree or compact metric hierarchy for the PRD
- Metric definitions
- Measurement assumptions
- Guardrail metrics
- Diagnostic metrics
- Optional split metric export only when explicitly requested

## Quality Bar

- The primary metric maps to the stated goal.
- Guardrails capture negative side effects.
- Metrics can be instrumented or calculated.
- Default delivery keeps metric content in `prd.md`; do not create `metrics-tree.md` unless the user asks for a split legacy file.
