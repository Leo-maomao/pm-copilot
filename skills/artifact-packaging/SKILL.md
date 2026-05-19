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
5. Verify `run-log.yaml` or equivalent trace evidence records assumptions, tools, validation, skills used, readiness, and review findings.
6. Verify optional exports are useful or explicitly requested.
7. Verify local links are relative, readable, and point to files that exist in the output folder.
8. Mark readiness separately: PRD status, engineering handoff status, and launch status.
9. Do not create `pm-package.md` or `final-package-summary.md` unless the user explicitly asks for a separate consolidated summary.
10. When `scripts/run_delivery_checks.py` is available, run it before final delivery and record the result.
11. When `scripts/validate_outputs.py` is available, run it against the output folder and fix any unexpected split files, stale validation placeholders, or trace gaps before final delivery.
12. For host-repository benchmark runs, clean generated output folders after the learning has been moved back into PM Copilot.

## Output

- Delivery check summary
- Missing or inconsistent item list
- Readiness status
- Validation evidence
- Next actions

## Quality Bar

- Reviewers can use `prd.md` and the prototype without assembling the story from many files.
- Risks and open confirmations are visible.
- Delivery status matches Review Agent findings and validation results.
- The output folder contains only allowed default artifacts plus explicitly justified exports.
- Local references resolve and no output relies on remote assets unless explicitly requested.
- No artifact claims approval, launch readiness, or implementation completion without evidence.
