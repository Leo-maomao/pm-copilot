---
name: prd-writing
description: Use when generating or improving the primary PRD handoff artifact, including version history, research, goals, scope, requirement list, requirement details, flows, tracking, risks, acceptance criteria, and UI delivery reference.
---

# PRD Writing

## Goal

Create `outputs/<run-id>/prd.md`, the primary product-manager handoff artifact that product, design, engineering, QA, and analytics can review directly.

## Workflow

1. Load the PRD contract from `artifacts/prd-contract.md`.
2. Use discovery output, user answers, current product context, and research findings as the source of truth.
3. For implemented-feature PRD delivery, inspect branch/diff evidence before drafting. Record changed files, UI surfaces, business logic, data operations, permissions, screenshots/assets, tests, and unverified intent; then reconstruct the requirement from observed behavior instead of inventing product scope.
4. Localize human-facing headings and prose to the user's language, while keeping machine-readable IDs, event names, property names, and file names ASCII.
5. Add version history and requirement input / confirmation record.
6. Add separate PRD status, engineering handoff status, and launch status.
7. Write concise background and research/reference findings. Include competitor research, user/business research, existing implementation findings, historical PRD findings, screenshots, and technical solution references when available.
8. Mark source date, confidence, and limitation for external or time-sensitive facts.
9. Define project goals and metrics.
10. Separate confirmed MVP scope, optional or conditional scope, future scope, and non-goals.
11. For implemented-feature PRD delivery, add an implementation evidence and coverage map that links branch evidence to requirement IDs and exposes partial/unverified/conflicting behavior.
12. Create a requirement list with stable IDs.
13. Write requirement details for each functional item, including function, scenario, entry/trigger, content requirements, business logic, interaction rules, data rules, permission rules, edge states, tracking links, and acceptance links where relevant.
14. Place screenshots or image placeholders inline in the related requirement, flow, or evidence position. Do not create a separate image list by default.
15. Add a repo-backed engineering map when repository or implementation context is available.
16. Add functional and operation flow diagrams when they improve reviewability.
17. Add tracking plan event and property tables inside the PRD by default.
18. Add a UI delivery reference section that links the source-backed preview/delta, compatibility HTML artifact, and `prd.html` document when requested, while avoiding duplicated page-level annotations.
19. Add structured risks, open confirmations, acceptance criteria, delivery review findings, and validation results.

## Output

- `outputs/<run-id>/prd.md`
- Optional machine-readable exports only when useful or requested

## Quality Bar

- The PRD is detailed enough for design, engineering, QA, and analytics to proceed without guessing core intent.
- Requirement, function, acceptance, metric, and tracking IDs are stable and cross-linked.
- Requirement details contain concrete logic, content, rules, interactions, data behavior, permission behavior, edge states, tracking links, and acceptance links where relevant.
- Implemented-feature PRDs cover every meaningful behavior visible in the implementation or mark the missing product intent as a gap with owner and impact.
- Research and reference findings sit before requirements because they explain the solution direction.
- UI delivery details are not duplicated in the PRD; the PRD links the UI deliverable and summarizes covered screens/states.
- Images and image placeholders appear inline where they support the requirement; reviewers should not need to cross-reference a detached screenshot list.
- No unresolved decision is hidden inside prose.
- Time-sensitive or external claims are sourced, dated, or explicitly marked unverified.
- Readiness status does not imply engineering or launch approval without evidence.
