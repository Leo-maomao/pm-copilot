---
name: artifact-packaging
description: Use when checking final PM delivery consistency across PRD, UI deliverable, optional exports, readiness status, assumptions, risks, and validation results.
---

# Delivery Check

## Goal

Make the final PM delivery easy to review, share, and continue without creating extra default Markdown packages.

## Workflow

1. Verify `prd.md` exists and follows the PRD contract when PRD is in scope. If the user explicitly requested no PRD, verify the structured reference or document prototype is the primary delivery instead.
2. Verify a UI deliverable exists or is recorded when UI is in scope: source-backed preview/delta by default when frontend source exists, source-extracted HTML when the UI was first rendered or implemented in the host project, or `prototype-<platform>.html` for compatibility standalone/fallback mode.
3. Verify PRD and UI deliverable agree on scope, screens, states, logic, interactions, tracking, and blockers.
4. Verify the PRD contains version history, confirmation record, background, research/reference findings, goals/metrics, scope, requirement list, requirement details, tracking plan, UI delivery reference, risks/open confirmations, acceptance criteria, and validation results.
5. Verify `run-log.yaml` or equivalent trace evidence records assumptions, tools, validation, skills used, readiness, and review findings.
6. For document-class deliveries, verify source facts, product decisions, attention points, object-level change log, completeness check, and source/review status are present and consistent across Markdown, HTML, and run log.
7. Verify optional exports are useful or explicitly requested.
8. Verify local links are relative, readable, and point to files that exist in the output folder.
9. Mark readiness separately: PRD status, engineering handoff status, and launch status.
10. Do not create `pm-package.md` or `final-package-summary.md` unless the user explicitly asks for a separate consolidated summary.
11. When `scripts/run_delivery_checks.py` is available, run it before final delivery and record the result.
12. When `scripts/validate_outputs.py` is available, run it against the output folder and fix any unexpected split files, stale validation placeholders, or trace gaps before final delivery.
13. For host-repository benchmark runs, clean generated output folders after the learning has been moved back into PM Copilot.

## Output

- Delivery check summary
- Missing or inconsistent item list
- Readiness status
- Validation evidence
- Next actions

## Quality Bar

- Reviewers can use `prd.md` and the UI deliverable without assembling the story from many files.
- Reviewers can use the structured reference or document prototype directly when PRD is not in scope.
- Risks and open confirmations are visible.
- Delivery status matches Review Agent findings and validation results.
- The output folder contains only allowed default artifacts plus explicitly justified exports.
- Local references resolve and no output relies on remote assets unless explicitly requested.
- No artifact claims approval, launch readiness, or implementation completion without evidence.
- Document attention points are useful, typed, and target concrete objects, fields, rules, or decisions.
