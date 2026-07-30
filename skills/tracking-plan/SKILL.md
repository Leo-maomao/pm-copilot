---
name: tracking-plan
description: Use when designing analytics events, event properties, trigger timing, validation notes, and privacy notes for a product feature.
---

# Tracking Plan

## Goal

Create an analytics plan that engineering and analytics can implement and QA can verify.

## Workflow

1. Load tracking taxonomy from product context when it exists.
2. Map measurable entry, meaningful operation, important result, and value behavior from the confirmed user journey.
3. Name each event as a unique lowercase semantic `feature_action` identifier.
4. In a PRD, create only `事件`、`事件名称`、`上报时机`、`附加参数`、`备注`; use `/` for empty parameters or notes.
5. Keep `上报时机` to one observable sentence and include only event-external properties in `附加参数`.
6. Omit unsupported events instead of marking them as proposed, inferred, or pending in the PRD.
7. Create a detailed event table, property dictionary, validation notes, and privacy notes only when the user explicitly requests `tracking-plan.md`, CSV, or analytics/engineering handoff.
8. For sensitive domains, explicitly state which raw properties are excluded in the requested detailed handoff, such as health status, pregnancy details, hospital, payment details, government IDs, document titles, expiry dates tied to identity, notification body text, raw contact data, holdings amount, cost basis, trade detail, investment preference, and exact alert threshold.
9. For reminder or notification features, track delivery state, trigger type, and permission-safe category only. Do not track raw reminder content, exact sensitive dates, document names, addresses, or recipient contact details unless the user has supplied an approved analytics policy.
10. For financial reminders, alerts, and portfolio tools, prefer coarse buckets such as threshold_type, delivery_state, and auth_state over raw percentages, prices, amounts, personal target allocations, or watchlist intent.
11. Keep the concise PRD table in `prd.md`; keep detailed analytics material in the requested companion handoff only.
12. Export CSV only when analytics or engineering needs a machine-readable companion.

## Boundary

Use this skill only for event instrumentation, event properties, trigger timing, validation notes, and privacy-safe tracking implementation. Use `skills/metrics-tree/SKILL.md` for KPI strategy and `skills/product-ops-analysis/SKILL.md` for interpreting collected data. Do not create separate analytics-event or telemetry-plan skills; extend this one.

## Output

- Concise tracking section for `prd.md` with the five canonical columns
- Optional detailed taxonomy/property handoff only when requested
- Optional `tracking-plan.md` split handoff file only when requested
- Optional `tracking-plan.csv` export
- Validation and privacy material only in an explicitly requested detailed handoff

## Quality Bar

- PRD events use the configured naming convention when available, otherwise semantic `feature_action` identifiers without proposal labels.
- Each PRD event has a precise observable trigger, only necessary additional parameters, and no unsupported rows.
- Detailed handoff events include actor, platform, properties, validation notes, and privacy notes only when that handoff is requested.
- Every property in a detailed handoff is defined once in that handoff's property dictionary.
- Detailed-handoff property names, event names, data types, and enum values are implementable without interpretation.
- Sensitive properties are minimized or excluded.
- Reminder analytics use coarse, permission-safe properties and state exactly which notification payload fields are excluded.
- Financial analytics excludes raw holdings, cost basis, exact alert thresholds, and investment preference unless an approved analytics policy explicitly allows them.
- If no existing taxonomy is found, no event or property should be described as already standardized.
