# Failover Rules

## Missing User Input

If the user does not answer clarification questions:

1. Continue only if no `must answer before generation` question is open and no unresolved `must confirm before development or launch` item is required for the requested readiness level.
2. Mark assumptions visibly.
3. Add open questions to `prd.md`.
4. Require review before engineering starts.

If any `must answer before generation` question is open, stop before downstream generation. Continue only after the user answers or explicitly says to proceed with assumptions. If the user accepts assumption risk, mark the PRD/UI delivery as `Draft with assumption risk`, not development-ready.

If any engineering-blocking `must confirm before development or launch` item is open, stop before producing a `Ready for engineering` PRD/UI delivery. Continue only if the user answers or explicitly asks for a draft with confirmation risk.

If only launch-blocking items remain open, the PRD/UI delivery may still be engineering-ready only when those blockers are excluded from engineering acceptance criteria and launch status is explicitly blocked.

In explicit evaluation or recommended-default mode, continue with conservative defaults only for the purpose of generating review artifacts. Do not convert open launch, legal, privacy, payment, security, financial, or regulated-content confirmations into approvals.

## Research Unavailable

If search or source access is unavailable:

- Do not fabricate competitor claims.
- Use generic product heuristics only when labeled as non-source-backed.
- Recommend research follow-up in `prd.md`.

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

## Content Review Pending

If source, review, or disclaimer approval is missing for reference or regulated content:

- Use placeholder or draft content only.
- Mark the content payload as not launch-ready.
- Keep framework requirements, container behavior, permissions, and states reviewable for engineering when they are otherwise clear.
- Add the content approval item to launch blockers with owner and required confirmation.

## Conflicting Context

If context conflicts:

1. Current user instruction
2. Current task brief
3. Current product context from repository or user-provided documents
4. Product context config
5. Artifact contract
6. Repository default

Use the highest-priority source and record the conflict.
