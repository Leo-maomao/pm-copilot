---
name: user-flow
description: Use when creating Mermaid user flows for product requirements, including entry points, main paths, decisions, errors, and completion states.
---

# User Flow

## Goal

Produce a standard rendered-friendly flowchart that makes the product path and key branches reviewable.

## Workflow

1. Identify entry points and actors.
2. Map the main success path.
3. Add decision points and failure branches.
4. Add completion, cancellation, and retry states.
5. Keep node labels short and clear.
6. Add the Mermaid code block to the flow section of `prd.md` so GitHub-compatible tools render it as a diagram.
7. Generate `user-flow.md` or `user-flow.mmd` only when a separate export is useful or requested.

## Output

- Rendered-friendly Mermaid diagram block for `prd.md`
- Optional `user-flow.md` or `user-flow.mmd` export
- Flow notes
- Branch assumptions

## Quality Bar

- The output is a standard flowchart, not a prose list.
- The flow renders in Mermaid.
- The diagram matches PRD scope.
- Error and cancellation paths are represented when relevant.
