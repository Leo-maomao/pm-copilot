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
3. For implemented-feature PRD delivery, verify branch evidence was inspected and every visible feature behavior is represented in `prd.md` or marked as an explicit gap/risk. Reviewers should not need to manually inspect the branch to find missing requirement content.
4. Verify PRD and UI deliverable agree on scope, screens, states, logic, interactions, tracking, and blockers.
5. Verify the PRD contains version history, confirmation record, background, research/reference findings, goals/metrics, scope, implementation evidence when applicable, requirement list, requirement details, tracking plan, UI delivery reference, risks/open confirmations, acceptance criteria, and validation results.
6. When `prd.html` exists, verify it is a readable document rendering of `prd.md`, not a UI prototype: normal document content area, optional left TOC, neutral styling, no decorative card/module layout, complete tables, rendered Mermaid diagrams, and no nested content-only scrolling.
7. Verify images or image placeholders appear inline at the relevant PRD position, including table cells when applicable, and are not duplicated as a detached image list. Real images must use local relative paths and support click-to-fullscreen or equivalent lightbox viewing.
8. Verify `run-log.yaml` or equivalent trace evidence records assumptions, tools, validation, skills used, readiness, review findings, and implemented-feature evidence when applicable.
9. For document-class deliveries, verify source facts, product decisions, attention points, object-level change log, completeness check, and source/review status are present and consistent across Markdown, HTML, and run log.
10. Verify optional exports are useful or explicitly requested.
11. Verify local links are relative, readable, and point to files that exist in the output folder.
12. Mark readiness separately: PRD status, engineering handoff status, and launch status.
13. Do not create `pm-package.md` or `final-package-summary.md` unless the user explicitly asks for a separate consolidated summary.
14. When `scripts/run_delivery_checks.py` is available, run it before final delivery and record the result.
15. When `scripts/validate_outputs.py` is available, run it against the output folder and fix any unexpected split files, stale validation placeholders, broken PRD HTML rendering, or trace gaps before final delivery.
16. For host-repository benchmark runs, clean generated output folders after the learning has been moved back into PM Copilot.

## Output

- Delivery check summary
- Missing or inconsistent item list
- Readiness status
- Validation evidence
- Next actions

## Quality Bar

- Reviewers can use `prd.md` and the UI deliverable without assembling the story from many files.
- Reviewers can use `prd.html` directly when browser-readable PRD delivery is requested.
- Reviewers can use the structured reference or document prototype directly when PRD is not in scope.
- Implemented-feature PRDs are complete against the inspected branch evidence, with any unproven product intent called out explicitly.
- Risks and open confirmations are visible.
- Delivery status matches Review Agent findings and validation results.
- The output folder contains only allowed default artifacts plus explicitly justified exports.
- Local references resolve and no output relies on remote assets unless explicitly requested.
- No artifact claims approval, launch readiness, or implementation completion without evidence.
- Document attention points are useful, typed, and target concrete objects, fields, rules, or decisions.
