---
name: artifact-packaging
description: Use when checking final PM delivery consistency across PRD, prototype, optional exports, readiness status, assumptions, risks, and validation results.
---

# Delivery Check

## Goal

Make the final PM delivery easy to review, share, and continue without creating extra default Markdown packages.

## Workflow

1. Verify `prd.md` exists and follows the PRD contract.
2. Verify `prototype-<platform>.html` exists when UI is in scope.
3. Verify PRD and prototype agree on scope, screens, states, logic, interactions, tracking, and blockers.
4. Verify the PRD contains version history, confirmation record, background, research/reference findings, goals/metrics, scope, requirement list, requirement details, tracking plan, prototype reference, risks/open confirmations, acceptance criteria, and validation results.
5. Verify optional exports are useful or explicitly requested.
6. Mark readiness separately: PRD status, engineering handoff status, and launch status.
7. Do not create `pm-package.md` or `final-package-summary.md` unless the user explicitly asks for a separate consolidated summary.

## Output

- Delivery check summary
- Missing or inconsistent item list
- Readiness status
- Next actions

## Quality Bar

- Reviewers can use `prd.md` and the prototype without assembling the story from many files.
- Risks and open confirmations are visible.
- Delivery status matches Review Agent findings and validation results.
