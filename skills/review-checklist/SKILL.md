---
name: review-checklist
description: Use when reviewing generated PM artifacts for completeness, ambiguity, missing metrics, edge cases, dependencies, risks, and stakeholder readiness.
---

# Delivery Review

## Goal

Decide whether the PRD and prototype delivery is ready for stakeholder review, engineering handoff, or launch.

## Workflow

1. Check `prd.md`, prototype HTML, and optional exports against their contracts.
2. Identify gaps by severity: Critical, High, Medium, Low.
3. Record artifact, evidence, owner, required-before phase, and status for each finding.
4. Verify source IDs, requirement links, acceptance links, tracking links, prototype references, and local file references resolve.
5. Verify validation evidence is concrete and not a stale placeholder.
6. Route each finding to the responsible agent or artifact.
7. Separate required fixes from optional improvements.
8. State PRD, engineering handoff, and launch readiness separately.
9. For HTML prototypes, verify numbered callouts are grouped by page or screen in the annotation panel. A single generic annotation list is a finding unless the prototype has only one screen.
10. For operational workflows such as feedback, moderation, support, release checks, or admin review, verify the state machine, owner role, SLA or timing assumption, user-visible status, internal-only status, reply/content review, reopen/cancel path, and notification behavior.
11. For comparison, ranking, scoring, or recommendation-adjacent experiences, verify neutral default ordering, no unexplained winner/highlight, source/fee/risk definitions, disclaimer visibility, and whether any wording implies advice or guaranteed superiority.
12. For launch-sensitive packages, verify required human approvals are present before any ready-to-launch wording is allowed.

## Output

- Summary recommendation
- Findings by severity
- Artifact checklist
- Open decisions
- Human confirmation required
- Content source and launch review status, when relevant
- Validation results
- Next actions

## Quality Bar

- Findings are actionable.
- Severity is justified.
- Each finding includes enough evidence for the owner to reproduce or inspect it.
- Critical issues block the relevant readiness phase.
- No-Critical-or-High reviews still record what was checked and any residual risk.
- Prototype review confirms page-scoped annotations, platform chrome, eligible/ineligible states, and placeholder-content labels when relevant.
- Operational workflows identify who acts next and what status the user sees while waiting, after closure, and after failure.
- Comparison and ranking reviews flag hidden recommendations, biased defaults, and missing methodology as readiness blockers.
