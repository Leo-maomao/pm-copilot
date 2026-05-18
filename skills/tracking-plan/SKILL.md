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
5. Mark optional-scope events as conditional instead of required MVP instrumentation.
6. Create a Markdown event table with complete columns.
7. Create a property dictionary table for every field used by any event.
8. Add validation notes for QA and analytics.
9. Add privacy notes for sensitive fields.
10. Put the reviewable tables in `prd.md` by default.
11. Export CSV only when analytics or engineering needs a machine-readable companion.

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
- Sensitive properties are minimized or excluded.
