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
4. Add validation notes for QA and analytics.
5. Add privacy notes for sensitive fields.

## Output

- Tracking plan table or CSV
- Event property definitions
- Validation checklist
- Privacy notes

## Quality Bar

- Events use the configured naming convention.
- Each event has a precise trigger.
- Sensitive properties are minimized or excluded.
