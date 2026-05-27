---
name: knowledge-ops
description: Use when auditing, improving, or creating product docs, structured catalogs, parameter tables, model/API matrices, SOPs, runbooks, decision records, onboarding docs, wiki spaces, or PM knowledge bases.
---

# Knowledge Ops

## Goal

Keep product and operations knowledge findable, owned, current, structured, and safe enough for PM Copilot to use as context or hand off to engineering.

## Workflow

1. Inventory the knowledge source: Notion, Confluence, Google Drive, Obsidian, Markdown, repo docs, support macros, or exported files.
2. Identify canonical owners, last-reviewed dates, audience, lifecycle state, and source-of-truth boundaries.
3. Check each document for 5W2H completeness: who, what, when, where, why, how, and cost/effort.
4. For runbooks and SOPs, verify trigger, owner, prerequisites, step owner, expected duration, success signal, failure signal, rollback, escalation, and audit trail.
5. Detect knowledge-base hygiene issues: stale docs, orphan pages, duplicate docs, conflicting definitions, missing owners, missing links, unreviewed policy content, and outdated screenshots.
6. Prioritize cleanup by usage, risk, staleness, compliance impact, and dependency count.
7. Produce rewrite/archive/merge/keep recommendations with owners and due dates.
8. For structured catalogs, define the field dictionary, stable row IDs, source status, review status, owner, access date, unknown-value handling, and engineering handoff notes.
9. For model/API/vendor parameter tables, distinguish source-backed facts from implementation recommendations; mark fast-changing values as draft or blocked unless current official or user-supplied sources are available.
10. Record limitations when live workspace access is unavailable and only exports were reviewed.

## Boundary

Use this skill for knowledge artifacts: docs, structured catalogs, parameter tables, model/API matrices, SOPs, runbooks, decision records, wiki spaces, and KB hygiene. Use `skills/process-mapping/SKILL.md` for the actual business workflow, handoffs, queues, approvals, and cycle time. Do not create separate SOP, runbook, model-catalog, or KB-cleanup skills; extend this one.

## Output

- Knowledge-source inventory
- `catalog.md` or `catalog.html` structured catalog handoff when requested
- Field dictionary and row-level source/review status
- SOP/runbook completeness checklist
- KB hygiene findings
- Prioritized cleanup backlog
- Canonical-source recommendations
- Owner, review, and approval gaps

## Quality Bar

- Every cleanup recommendation names an owner or owner gap.
- Stale or conflicting documents are not silently used as authoritative context.
- Operational or regulated content has review status and launch impact.
- Structured catalog rows have stable IDs, source status, review status, owner, access date, and unknown-value handling.
- Fast-changing model/API facts are current-source-backed or explicitly marked draft/blocked.
- The output distinguishes documentation hygiene from product requirements.
- The agent does not require live workspace access when exported docs are sufficient.
