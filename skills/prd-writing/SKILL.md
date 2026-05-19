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
3. Localize human-facing headings and prose to the user's language, while keeping machine-readable IDs, event names, property names, and file names ASCII.
4. Add version history and requirement input / confirmation record.
5. Add separate PRD status, engineering handoff status, and launch status.
6. Write concise background and research/reference findings. Include competitor research, user/business research, existing implementation findings, historical PRD findings, screenshots, and technical solution references when available.
7. Mark source date, confidence, and limitation for external or time-sensitive facts.
8. Define project goals and metrics.
9. Separate confirmed MVP scope, optional or conditional scope, future scope, and non-goals.
10. Create a requirement list with stable IDs.
11. Write requirement details for each functional item, including function, scenario, entry/trigger, content requirements, business logic, interaction rules, data rules, permission rules, edge states, tracking links, and acceptance links where relevant.
12. Add a repo-backed engineering map when repository or implementation context is available.
13. Add functional and operation flow diagrams when they improve reviewability.
14. Add tracking plan event and property tables inside the PRD by default.
15. Add a prototype reference section that links the HTML prototype and avoids duplicating page-level annotations.
16. Add structured risks, open confirmations, acceptance criteria, delivery review findings, and validation results.

## Output

- `outputs/<run-id>/prd.md`
- Optional machine-readable exports only when useful or requested

## Quality Bar

- The PRD is detailed enough for design, engineering, QA, and analytics to proceed without guessing core intent.
- Requirement, function, acceptance, metric, and tracking IDs are stable and cross-linked.
- Requirement details contain concrete logic, content, rules, interactions, data behavior, permission behavior, edge states, tracking links, and acceptance links where relevant.
- Research and reference findings sit before requirements because they explain the solution direction.
- Prototype details are not duplicated in the PRD; the PRD links the prototype and summarizes covered screens/states.
- No unresolved decision is hidden inside prose.
- Time-sensitive or external claims are sourced, dated, or explicitly marked unverified.
- Readiness status does not imply engineering or launch approval without evidence.
