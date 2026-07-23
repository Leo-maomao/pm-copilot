---
name: review-checklist
description: Use when reviewing PM artifacts for completeness, ambiguity, missing metrics, edge cases, dependencies, risks, and readiness.
---

# Delivery Review

## Goal

Decide whether the PRD and UI delivery is ready for stakeholder review, engineering handoff, or launch.

## Workflow

1. Check `prd.md`, UI deliverable references, portable HTML when present, and optional exports against their contracts.
2. Identify gaps by severity: Critical, High, Medium, Low.
3. Record artifact, evidence, owner, required-before phase, and status for each finding.
4. Verify source IDs, requirement links, acceptance links, tracking links, UI delivery references, and local file references resolve.
5. Verify validation evidence is concrete and not a stale placeholder.
6. Route each finding to the responsible agent or artifact.
7. Separate required fixes from optional improvements.
8. State PRD, engineering handoff, and launch readiness separately.
9. For repo-backed UI deliveries, verify `host_frontend_inventory` records the evidence inspected and `ui_delivery_trace` records `host_read_only`, target surface, artifact mode, non-empty source-to-demo mapping, fidelity, proposed behavior, limitations, and the human implementation owner. Source presence improves evidence quality but never authorizes preview, delta, or implementation files. Existing UI extracts must identify source target, selector, command, capture, generated path, and limitations.
10. For portable HTML UI deliverables, verify JavaScript parses, primary controls change realistic product state, numbered callouts open marker dialogs, callouts are red/white borderless and not clipped or folding compact labels, the annotation floating control uses only `注释` or `Notes`, opens a right-edge full-height current-state panel, hides while the panel is open, and reappears when closed. A visible row of state/storyboard tabs is a finding; reviewer-only state switchers must be fixed, collapsed, marked `data-reviewer-only="true"`, and secondary to real interactions. A single generic all-screen annotation list is a finding unless the UI deliverable has only one screen.
11. Verify the product surface does not contain visible `示例`, `演示`, `Demo`, `Sample`, `Prototype`, `Not production code`, or `不是生产代码` labels unless the product requirement explicitly needs visible draft status. Delivery boundaries should be in metadata, run logs, PRD notes, comments, or annotations.
12. For access-gated UI deliverables, verify logged-out, guest, no-permission, and eligible states do not reveal signed-in-only data or actions from the wrong state.
13. For operational workflows such as feedback, moderation, support, release checks, or admin review, verify the state machine, owner role, SLA or timing assumption, user-visible status, internal-only status, reply/content review, reopen/cancel path, and notification behavior.
14. For comparison, ranking, scoring, or recommendation-adjacent experiences, verify neutral default ordering, no unexplained winner/highlight, source/fee/risk definitions, disclaimer visibility, and whether any wording implies advice or guaranteed superiority.
15. For launch-sensitive packages, verify required human approvals are present before any ready-to-launch wording is allowed.

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
- UI delivery review confirms page-scoped annotations, platform chrome, eligible/ineligible states, access-state coherence, and placeholder-content labels when relevant.
- Operational workflows identify who acts next and what status the user sees while waiting, after closure, and after failure.
- Comparison and ranking reviews flag hidden recommendations, biased defaults, and missing methodology as readiness blockers.
