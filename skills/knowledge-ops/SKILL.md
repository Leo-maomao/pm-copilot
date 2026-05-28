---
name: knowledge-ops
description: Use when auditing, improving, or creating product docs, structured catalogs, parameter tables, model/API matrices, SOPs, runbooks, decision records, onboarding docs, wiki spaces, or PM knowledge bases.
---

# Knowledge Ops

## Goal

Keep product and operations knowledge findable, owned, current, structured, and safe enough for PM Copilot to use as context, structured reference, document prototype, or engineering handoff.

## Workflow

1. Inventory the knowledge source: Notion, Confluence, Google Drive, Obsidian, Markdown, repo docs, support macros, or exported files.
2. Identify canonical owners, last-reviewed dates, audience, lifecycle state, and source-of-truth boundaries.
3. Check each document for 5W2H completeness: who, what, when, where, why, how, and cost/effort.
4. For runbooks and SOPs, verify trigger, owner, prerequisites, step owner, expected duration, success signal, failure signal, rollback, escalation, and audit trail.
5. Detect knowledge-base hygiene issues: stale docs, orphan pages, duplicate docs, conflicting definitions, missing owners, missing links, unreviewed policy content, and outdated screenshots.
6. Prioritize cleanup by usage, risk, staleness, compliance impact, and dependency count.
7. Produce rewrite/archive/merge/keep recommendations with owners and due dates.
8. For structured references, define the field dictionary, stable IDs, source status, review status, owner, access date, unknown-value handling, and engineering handoff notes.
9. For hierarchical or rules-heavy references, structure entities, fields, rules, decisions, children, conditions, defaults, enums, limits, source facts, and product decisions before rendering Markdown or HTML.
10. For model/API/vendor/rule parameter tables, distinguish source-backed facts from implementation recommendations; mark fast-changing values as draft or blocked unless current official or user-supplied sources are available.
11. For multi-turn calibration, use object-level patching. Updating one model, API, rule, data object, or SOP step must not rewrite unrelated objects. If the user asks only for layout or presentation changes, record presentation-only mode and keep structured content unchanged.
12. Add useful `attention_points` for source gaps, PM overrides, conflicts, engineering must-read notes, launch blockers, cost/quota risks, security/compliance risks, and current-turn changes. Do not add generic annotations that do not change reviewer behavior.
13. Record limitations when live workspace access is unavailable and only exports were reviewed.

## Boundary

Use this skill for knowledge artifacts: docs, structured references, structured catalogs, parameter tables, model/API matrices, payment/risk rule references, SOPs, runbooks, decision records, wiki spaces, document prototypes, and KB hygiene. Use `skills/process-mapping/SKILL.md` for the actual business workflow, handoffs, queues, approvals, and cycle time. Do not create separate SOP, runbook, model-catalog, API-doc, or KB-cleanup skills; extend this one.

## Output

- Knowledge-source inventory
- `catalog.md`, `reference.md`, `catalog.html`, `reference.html`, or document prototype handoff when requested
- Field dictionary and row-level source/review status
- Structured entities, fields, rules, decisions, source facts, product decisions, attention points, change log, and completeness check
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
- The output distinguishes extracted source facts from final product decisions.
- Document attention points are typed, target concrete objects/fields/rules/decisions, and are useful enough for review or engineering.
- Multi-turn edits preserve unrelated objects and record changes.
- The agent does not require live workspace access when exported docs are sufficient.
