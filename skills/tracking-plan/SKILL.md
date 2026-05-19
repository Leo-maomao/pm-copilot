---
name: tracking-plan
description: Use when designing analytics events, event properties, trigger timing, validation notes, and privacy notes for a product feature.
---

# Tracking Plan

## Goal

Create an analytics plan that engineering and analytics can implement and QA can verify.

## Workflow

1. Load tracking taxonomy from product context.
2. If no taxonomy is found after targeted context loading, mark generated events as a proposed taxonomy that requires analytics or engineering approval.
3. Map core user actions and system events.
4. Define event names, triggers, actor, platform, required properties, and optional properties.
5. Define property type, allowed values or enum source, required/optional status, sensitivity, and retention or redaction note.
6. Mark optional-scope events as conditional instead of required MVP instrumentation.
7. Create a Markdown event table with complete columns.
8. Create a property dictionary table for every field used by any event.
9. Add validation notes for QA and analytics, including where to inspect the event and what test data or state is required.
10. Add privacy notes for sensitive fields.
11. State analytics approval status when the plan is proposed or deviates from the existing taxonomy.
12. For sensitive domains, explicitly state which raw properties are excluded, such as health status, pregnancy details, hospital, payment details, government IDs, document titles, expiry dates tied to identity, notification body text, raw contact data, holdings amount, cost basis, trade detail, investment preference, and exact alert threshold.
13. For reminder or notification features, track delivery state, trigger type, and permission-safe category only. Do not track raw reminder content, exact sensitive dates, document names, addresses, or recipient contact details unless the user has supplied an approved analytics policy.
14. For financial reminders, alerts, and portfolio tools, prefer coarse buckets such as threshold_type, delivery_state, and auth_state over raw percentages, prices, amounts, personal target allocations, or watchlist intent.
15. Put the reviewable tables in `prd.md` by default.
16. Export CSV only when analytics or engineering needs a machine-readable companion.

## Output

- Tracking plan section for `prd.md` with event table and property dictionary
- Taxonomy source status
- Optional `tracking-plan.md` split handoff file only when requested
- Optional `tracking-plan.csv` export
- Validation checklist
- Privacy notes

## Quality Bar

- Events use the configured naming convention, or are explicitly labeled as proposed when no configured convention was found.
- Each event has a precise trigger.
- Each event row has complete actor, platform, properties, validation notes, and privacy notes.
- Every property is defined once in the property dictionary.
- Property names, event names, data types, and enum values are implementable without interpretation.
- Sensitive properties are minimized or excluded.
- Reminder analytics use coarse, permission-safe properties and state exactly which notification payload fields are excluded.
- Financial analytics excludes raw holdings, cost basis, exact alert thresholds, and investment preference unless an approved analytics policy explicitly allows them.
- If no existing taxonomy is found, no event or property should be described as already standardized.
