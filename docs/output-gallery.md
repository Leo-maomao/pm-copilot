# Output Gallery

This gallery describes what useful PM Copilot outputs should do.
It intentionally avoids committing large example output folders.

## PRD Markdown

`prd.md` is the primary product-decision artifact for feature work.
Its first screen should let a reviewer understand the recommendation, confidence, MVP and non-goals, key blocker, separate readiness states, and next checkpoint before reading implementation detail.

Useful signs:

- The recommendation and strongest rejected alternative are visible.
- Confidence is tied to evidence rather than tone.
- PRD status, engineering handoff status, and launch status are separate.
- MVP, optional scope, future scope, and non-goals are explicit.
- Assumptions and confirmations are visible.
- External research is separated from current repository evidence.
- Requirement details are the single behavioral source of truth rather than a duplicate requirement list.
- Tracking, copy/i18n, UI handoff, and tests appear only when applicable.
- Risks, owners, required-before phases, acceptance evidence, and next checkpoints make the PRD actionable.

## PRD HTML

`prd.html` is a browser-readable rendering of `prd.md`, not a marketing page and not a UI prototype.
It should preserve tables, Mermaid diagrams, local images, inline screenshot placeholders, and readable navigation.

Useful signs:

- Reviewers can read the whole PRD without opening Markdown.
- Wide tables remain complete and legible.
- Real screenshots are local and can be inspected.
- Missing screenshots use inline `占位图` markers at the exact requirement position.

## UI Delivery

UI delivery should help PM, design, and engineering align on real screens and interaction states.
When frontend source exists, source-backed preview or delta is preferred.
Standalone portable HTML is useful when there is no source, the user explicitly needs portable HTML, or source rendering is blocked.

Useful signs:

- The selected artifact mode is stated.
- Current component, token, layout, and style evidence are recorded.
- Access states, empty states, loading states, errors, permission states, and responsive behavior are covered.
- Visual validation uses `validate_prototype_visual.py` or `validate_ui_preview.py` when possible.

## Development Tasks

`dev-tasks.yaml` turns confirmed scope into issue-ready work.
It should not hide open product decisions.

Useful signs:

- Each task has source requirements and acceptance criteria.
- Dependencies and blockers are explicit.
- Testing suggestions are attached to relevant work.
- `ready_for_issue` is false when critical decisions remain open.

## Launch Decision

`launch-decision.yaml` supports go/no-go decisions.
It is useful when the launch depends on approvals, legal/payment/support readiness, analytics, rollout, rollback, or operational preparation.

Useful signs:

- Launch blockers have owners and required confirmations.
- Rollout and rollback are concrete.
- Engineering readiness is separated from launch readiness.
- Decision owner is required when human approval is missing.

## Structured Reference

Structured references are for document-class work: parameter tables, API/model/vendor matrices, data dictionaries, rule references, SOPs, runbooks, and migration inventories.
The value is not prose volume; the value is source-backed, reviewable structure.

Useful signs:

- Source facts and product decisions are separate.
- `source_status` and `review_status` are visible.
- Fields, entities, rules, or steps have stable IDs.
- `attention_points` call out gaps, PM overrides, launch blockers, cost/quota risks, and engineering must-read items.

## Run Log

`run-log.yaml` is internal trace evidence.
It should explain why the Agent chose a route and how it verified the result.

Useful signs:

- `agent_strategy`, `task_mode`, `autonomy_level`, success criteria, tool plan, decisions, replan triggers, review loop, next actions, and memory candidates are present.
- `loop_policy`, `iteration_trace`, evidence deltas, progress scores, stop reason, and termination-condition alignment are present.
- Tool results are concrete, not stale placeholders.
- Skips and degradations have reasons.
