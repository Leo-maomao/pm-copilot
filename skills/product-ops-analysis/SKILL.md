---
name: product-ops-analysis
description: Use when analyzing operating metrics, funnels, retention, conversion, support signals, experiment results, dashboards, CSV exports, notebooks, BI tools, or product analytics sources.
---

# Product Ops Analysis

## Goal

Turn product and operations data into reviewable product decisions without overclaiming data quality, exposing sensitive data, or treating exploratory analysis as an approved metric standard.

## Workflow

1. Define the decision the analysis must support, not just the chart to produce.
2. Identify the data source type: CSV or spreadsheet export, analytics tool, BI dashboard, warehouse, database, notebook, support tickets, CRM, ads platform, or manually supplied summary.
3. Load existing metric definitions and tracking taxonomy when available. If none is found, label metrics and events as proposed.
4. Classify data sensitivity and choose the safest access path: local exported files before live systems, read-only database or warehouse credentials before write-capable credentials, aggregated or sampled data before row-level customer data, and synthetic data for demos and public examples.
5. Use `skills/tool-vetting/SKILL.md` before connecting to analytics, warehouse, CRM, support, ads, or automation tools.
6. Record query or transformation assumptions, date ranges, filters, exclusions, timezone, identity grain, and cohort definitions.
7. Separate observed data from interpretation and recommendation.
8. Include uncertainty: missing events, sampling, bot/internal traffic, attribution gaps, delayed ingestion, experiment imbalance, small sample size, or changed instrumentation.
9. Produce decision-ready outputs: metric summary, segment/cohort differences, funnel or retention interpretation, risks, recommended product action, and validation follow-up.
10. Do not recommend launch approval, budget change, CRM action, or customer messaging solely from exploratory analysis unless the required owner has approved the decision.

## Boundary

Use this skill for analyzing existing product or operations data. Use `skills/metrics-tree/SKILL.md` to define success metrics before analysis, `skills/tracking-plan/SKILL.md` to specify event instrumentation, and `skills/experiment-design/SKILL.md` to design or interpret controlled product experiments. Do not create a separate funnel, retention, or dashboard-analysis skill; extend this one.

## Output

- Analysis question and decision owner
- Data source inventory and access status
- Metric definitions and taxonomy source status
- Query/filter/cohort assumptions
- Findings table with evidence, implication, confidence, and limitation
- Recommended product action or follow-up experiment
- Privacy and data-quality notes

## Quality Bar

- The analysis names its data source, time window, grain, and filters.
- Sensitive raw identifiers and payloads are excluded unless explicitly approved.
- Findings distinguish data facts from product interpretation.
- Recommendations state whether they are ready for product review, engineering planning, experiment design, or launch decision.
- Missing or untrusted instrumentation downgrades confidence instead of being hidden.
