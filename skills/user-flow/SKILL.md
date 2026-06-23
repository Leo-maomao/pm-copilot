---
name: user-flow
description: Use when creating Mermaid user flows for product requirements, including entry points, main paths, decisions, errors, and completion states.
---

# User Flow

## Goal

Produce a standard rendered-friendly flowchart that makes the product path and key branches reviewable.

## Workflow

1. Identify entry points and actors.
2. Decide whether one flow is enough or whether separate actor, admin, system, or exception flows are clearer.
3. Map the main success path.
4. Add decision points and failure branches.
5. Add completion, cancellation, and retry states.
6. Add eligibility, permission, setup, and content-review branches when they affect access or launch readiness.
7. For approval, invite, membership, verification, or review workflows, model both sides of the handoff: requester state, approver state, timeout/expiry, rejection, retry, cancellation, and security invalidation.
8. For reminder, schedule, trading-calendar, or market-hours workflows, model due date, non-business day adjustment, missed reminder, quiet/suppressed notification, user dismissal, retry, and the boundary between reminder and automatic execution.
9. Keep node labels short and clear.
10. Use simple Mermaid `flowchart` syntax with ASCII node IDs and localized labels.
11. Prefer unquoted node labels and plain branch labels. Avoid `classDef`, HTML labels, icon syntax, and complex styling unless the local renderer has already been verified.
12. Add the Mermaid code block to the flow section of `prd.md` so GitHub-compatible tools and `scripts/render_prd_html.py` render it as a diagram.
13. Generate `user-flow.md` or `user-flow.mmd` only when a separate export is useful or requested.

## Output

- Rendered-friendly Mermaid diagram block for `prd.md`
- Optional `user-flow.md` or `user-flow.mmd` export
- Flow notes
- Branch assumptions

## Quality Bar

- The output is a standard flowchart, not a prose list.
- The output is not a Markdown table or PNG screenshot.
- The flow renders in Mermaid.
- The diagram matches PRD scope.
- Main, exception, and blocked paths are visually distinguishable without long labels.
- Error and cancellation paths are represented when relevant.
- Access-gated and launch-blocked content states are visible when they change product behavior.
- Approval and membership flows show pending, approved, rejected, expired, and retry states when those states exist in the product model.
- Reminder and trading-calendar flows do not imply automatic execution unless the approved scope explicitly includes it.
