---
name: user-flow
description: Use when creating Mermaid user flows for product requirements, including entry points, main paths, decisions, errors, and completion states.
---

# User Flow

## Goal

Produce a Mermaid flow that makes the product path and key branches reviewable.

## Workflow

1. Identify entry points and actors.
2. Map the main success path.
3. Add decision points and failure branches.
4. Add completion, cancellation, and retry states.
5. Keep node labels short and clear.

## Output

- Mermaid `flowchart` source
- Flow notes
- Branch assumptions

## Quality Bar

- The flow renders in Mermaid.
- The diagram matches PRD scope.
- Error and cancellation paths are represented when relevant.
