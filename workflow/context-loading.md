# Context Loading Rules

## Principle

Load only the context needed for the current workflow state. Too much context can lower output quality by mixing unrelated product facts, stale decisions, and conflicting examples.

## Loading Order

1. Task brief
2. Host project context, when PM Copilot is embedded in another repository
3. Product context summary
4. Relevant personas and user segments
5. Relevant business model and metrics
6. Relevant PRD style and artifact preferences
7. Relevant tracking taxonomy
8. Relevant competitors or research notes
9. Historical examples only when the requested artifact style depends on them

## Host Project Context

In embedded mode, the host project is the product reality. Load enough current-state context to avoid proposing a requirement that ignores existing implementation or product constraints.

Use relevant files only. Typical sources include:

- Host README and product docs.
- Existing PRDs, specs, issues, or roadmap notes.
- Route definitions, pages, screens, navigation, and UI components near the affected area.
- API contracts, service modules, data models, permission rules, and feature flags.
- Analytics conventions, event naming, existing tracking plans, and metric definitions.
- Package metadata or framework config when it reveals platform and app structure.

Do not load the whole host repository by default. Start with file discovery, then read the smallest set of files that can answer product-fit questions.

If current behavior, affected module, platform, data ownership, or rollout constraints remain unclear, classify the missing information as `must answer now` and stop at the clarification gate.

## Conflict Resolution

| Conflict | Priority |
|---|---|
| User instruction vs repository default | User instruction wins if it does not violate guardrails |
| Current host implementation vs greenfield assumption | Current host implementation wins |
| Product context vs template | Product context wins |
| Artifact contract vs template example | Artifact contract wins |
| Source-backed research vs generic model knowledge | Source-backed research wins |
| Current user answer vs old memory | Current user answer wins |

## Context Hygiene

- Do not load all examples by default.
- Do not use old example assumptions as current task facts.
- Do not treat PM Copilot sample outputs as host product facts.
- Mark stale, unknown, or inferred context explicitly.
- Use anonymized data unless the environment is approved for sensitive data.
