---
name: prd-writing
description: Use when generating or improving the primary PRD handoff artifact, including version history, research, goals, scope, requirement list, requirement details, flows, tracking, risks, acceptance criteria, and prototype reference.
---

# PRD Writing

## Goal

Create `outputs/<run-id>/prd.md`, the primary product-manager handoff artifact that product, design, engineering, QA, and analytics can review directly.

## Workflow

1. Load the PRD contract from `artifacts/prd-contract.md`.
2. Use discovery output, user answers, current product context, and research findings as the source of truth.
3. Add version history and requirement input / confirmation record.
4. Write concise background and research/reference findings. Include competitor research, user/business research, existing implementation findings, historical PRD findings, screenshots, and technical solution references when available.
5. Define project goals and metrics.
6. Separate confirmed MVP scope, optional or conditional scope, future scope, and non-goals.
7. Create a requirement list with stable IDs.
8. Write requirement details for each functional item, including function, scenario, entry/trigger, content requirements, business logic, interaction rules, data rules, permission rules, edge states, tracking links, and acceptance links where relevant.
9. Add functional and operation flow diagrams when they improve reviewability.
10. Add tracking plan event and property tables inside the PRD by default.
11. Add a prototype reference section that links the HTML prototype and avoids duplicating page-level annotations.
12. Add risks, open confirmations, acceptance criteria, and validation results.

## Output

- `outputs/<run-id>/prd.md`
- Optional machine-readable exports only when useful or requested

## Quality Bar

- The PRD is detailed enough for design, engineering, QA, and analytics to proceed without guessing core intent.
- Requirement details contain concrete logic, content, rules, interactions, data behavior, permission behavior, edge states, tracking links, and acceptance links where relevant.
- Research and reference findings sit before requirements because they explain the solution direction.
- Prototype details are not duplicated in the PRD; the PRD links the prototype and summarizes covered screens/states.
- No unresolved decision is hidden inside prose.
