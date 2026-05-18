# Context Loading Rules

## Principle

Load only the context needed for the current workflow state. Too much context can lower output quality by mixing unrelated product facts, stale decisions, and conflicting examples.

## Loading Order

1. Task brief
2. Product context summary
3. Relevant personas and user segments
4. Relevant business model and metrics
5. Relevant PRD style and artifact preferences
6. Relevant tracking taxonomy
7. Relevant competitors or research notes
8. Historical examples only when the requested artifact style depends on them

## Conflict Resolution

| Conflict | Priority |
|---|---|
| User instruction vs repository default | User instruction wins if it does not violate guardrails |
| Product context vs template | Product context wins |
| Artifact contract vs template example | Artifact contract wins |
| Source-backed research vs generic model knowledge | Source-backed research wins |
| Current user answer vs old memory | Current user answer wins |

## Context Hygiene

- Do not load all examples by default.
- Do not use old example assumptions as current task facts.
- Mark stale, unknown, or inferred context explicitly.
- Use anonymized data unless the environment is approved for sensitive data.
