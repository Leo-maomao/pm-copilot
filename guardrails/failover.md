# Failover Rules

## Missing User Input

If the user does not answer clarification questions:

1. Continue only if no `must answer before generation` question is open and no unresolved `must confirm before development or launch` item is required for the requested readiness level.
2. Mark assumptions visibly.
3. Add open questions to the final package.
4. Require review before engineering starts.

If any `must answer before generation` question is open, stop before downstream generation. Continue only after the user answers or explicitly says to proceed with assumptions. If the user accepts assumption risk, mark the package as `Draft with assumption risk`, not development-ready.

If any `must confirm before development or launch` item is open, stop before producing a `Ready for engineering` package. Continue only if the user answers or explicitly asks for a draft with confirmation risk.

## Research Unavailable

If search or source access is unavailable:

- Do not fabricate competitor claims.
- Use generic product heuristics only when labeled as non-source-backed.
- Recommend research follow-up in the final package.

## Tool Unavailable

If a generation or preview tool is unavailable:

- Produce the raw artifact when possible.
- State what was not verified.
- Add a review checklist item for manual verification.

## Artifact Incomplete

If an artifact cannot meet its contract:

- Keep the artifact with an `Incomplete` status.
- List missing sections and blockers.
- Route back to the owning agent if the missing item is critical.

## Conflicting Context

If context conflicts:

1. Current user instruction
2. Current task brief
3. Current product context from repository or user-provided documents
4. Product context config
5. Artifact contract
6. Repository default

Use the highest-priority source and record the conflict.
