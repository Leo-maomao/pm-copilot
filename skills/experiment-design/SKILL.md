---
name: experiment-design
description: Use when planning A/B tests, fake-door tests, beta rollouts, product experiments, metric decision rules, or interpreting experiment outcomes.
---

# Experiment Design

## Goal

Design product experiments that produce decision-ready evidence without confusing statistical movement, business impact, and launch approval.

## Workflow

1. Write the hypothesis in a testable format: audience, intervention, expected metric movement, mechanism, and minimum useful effect.
2. Choose exactly one primary decision metric. Add guardrails for quality, retention, revenue, support, privacy, reliability, or compliance risk.
3. Define population, eligibility, exclusions, randomization unit, exposure event, analysis window, and timezone.
4. Estimate feasibility from baseline rate, traffic, minimum detectable effect, expected duration, and instrumentation readiness.
5. Select the experiment type: A/B, multivariate, holdout, sequential rollout, fake-door, prototype test, concierge test, or beta cohort.
6. Define stopping rules before launch. Avoid declaring success from early spikes or unplanned segment fishing.
7. Add data-quality checks: sample-ratio mismatch, missing exposure events, bot/internal traffic, delayed ingestion, release overlap, and instrumentation drift.
8. State decision rules: ship, iterate, stop, extend, or investigate.
9. Keep launch-sensitive approvals separate from experiment success.

## Boundary

Use this skill for experiment design, rollout tests, fake-door tests, beta cohorts, and experiment decision rules. Use `skills/product-ops-analysis/SKILL.md` for exploratory data analysis, `skills/metrics-tree/SKILL.md` for general KPI hierarchy, and `skills/tracking-plan/SKILL.md` for event/property implementation details. Do not create separate A/B-test, beta-rollout, or experiment-analysis skills; extend this one.

## Output

- Experiment hypothesis
- Metric and guardrail table
- Population and exposure definition
- Sample/traffic feasibility note
- Instrumentation and QA checklist
- Decision rule and risk log

## Quality Bar

- The experiment has one primary decision metric.
- Guardrails protect against harmful local optimization.
- The analysis window, randomization unit, and exposure event are explicit.
- Weak traffic, weak instrumentation, or small samples downgrade confidence.
- Experiment success does not imply legal, privacy, payment, or launch approval.
