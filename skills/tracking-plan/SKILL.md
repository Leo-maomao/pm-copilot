---
name: tracking-plan
description: Use when designing analytics events, event properties, trigger timing, validation notes, and privacy notes for a product feature.
---

# Tracking Plan

## Goal

Create an analytics plan that engineering and analytics can implement and QA can verify.

## Workflow

1. Load tracking taxonomy from product context.
2. Map core user actions and system events.
3. Define event names, triggers, actor, platform, required properties, and optional properties.
4. Create a Markdown event table with complete columns.
5. Create a property dictionary table for every field used by any event.
6. Add validation notes for QA and analytics.
7. Add privacy notes for sensitive fields.
8. Put the reviewable tables in `pm-package.md` by default.
9. Export CSV only when analytics or engineering needs a machine-readable companion.

## Output

- Tracking plan section for `pm-package.md` with event table and property dictionary
- Optional `tracking-plan.md` split handoff file
- Optional `tracking-plan.csv` export
- Validation checklist
- Privacy notes

## Quality Bar

- Events use the configured naming convention.
- Each event has a precise trigger.
- Each event row has complete actor, platform, properties, validation notes, and privacy notes.
- Every property is defined once in the property dictionary.
- Sensitive properties are minimized or excluded.
