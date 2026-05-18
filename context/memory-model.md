# Memory Model

PM Copilot uses local file-based memory. It does not require a database, account system, cloud storage, or telemetry. Memory is designed to make repeated use smoother without making the agent stubborn or unsafe.

## Memory Files

| File | Committed | Purpose |
|---|---|---|
| `context/product-memory.example.yaml` | Yes | Example schema for stable product facts |
| `context/user-preferences.example.yaml` | Yes | Example schema for user working style and delivery preferences |
| `context/decision-log.example.yaml` | Yes | Example schema for durable product decisions and rejected options |
| `context/product-memory.local.yaml` | No | User's private product memory |
| `context/user-preferences.local.yaml` | No | User's private preference memory |
| `context/decision-log.local.yaml` | No | User's private decision history |
| `outputs/<run-id>/run-log.yaml` | No by default | Single-run trace and task memory |

`.local.yaml` and `.private.yaml` files are ignored by Git. They are for the user's real product context and should not be committed to public repositories.

## Memory Layers

### Product Memory

Stores stable product facts that should help future requirements fit the current product:

- Product name, category, business model, and platforms
- User roles and segments
- Product surfaces, entry points, navigation rules, permissions, and fallback states
- Business rules and constraints
- Analytics taxonomy and forbidden properties
- Design-system and interaction preferences
- Compliance, content-source, and review requirements

### User Preference Memory

Stores how the user likes PM Copilot to work:

- Artifact language preferences
- PRD structure and writing style
- Prototype fidelity and annotation style
- Default delivery preferences
- Clarification style and risk tolerance
- Memory write preferences

### Decision Log

Stores durable product decisions:

- Confirmed product decisions
- Rejected options and reasons
- Superseded decisions
- Open strategic questions
- Source, confidence, owner, and last-updated metadata

### Run Memory

Stored in `outputs/<run-id>/run-log.yaml` when a persistent trace is useful:

- Raw request
- Context files inspected
- Clarification questions and answers
- Assumptions and risk acceptance
- Agent, skill, and tool use
- Generated artifact paths
- Validation commands and results
- Candidate memory updates

## Read Order

For each run, load memory after repository defaults and before generating task-specific artifacts:

1. `PM_COPILOT.md`
2. Workflow, guardrails, artifact contracts, and prompt system
3. Local memory files in `context/*.local.yaml`, when present
4. Current user request and answers
5. Current host repository context or user-provided documents
6. Tool observations from the current run

Memory is never stronger than current user instruction or current product evidence.

## Priority Rules

| Conflict | Winner |
|---|---|
| Current user instruction vs memory | Current user instruction |
| Current host implementation vs memory | Current host implementation |
| Current user-provided document vs memory | Current user-provided document |
| Product memory vs user preference memory | Depends on topic; product facts beat style preferences for product behavior |
| Decision log vs newer confirmed answer | Newer confirmed answer |
| Memory vs guardrail | Guardrail |

When conflict affects scope, readiness, data, privacy, payment, legal, compliance, security, or launch risk, mention the conflict and ask or record the chosen source.

## Write Rules

PM Copilot may suggest memory updates at the end of a run. It should not silently write sensitive long-term memory.

Write candidates only when they are reusable:

- Stable product fact -> `product-memory.local.yaml`
- User working preference -> `user-preferences.local.yaml`
- Confirmed durable decision -> `decision-log.local.yaml`
- One-off task detail -> keep in `run-log.yaml`

Each durable memory record should include:

- `id`
- `fact` or `decision`
- `source`
- `confidence`
- `last_updated`
- optional `owner`
- optional `supersedes`

## Sensitive Data Rules

Do not store these in memory unless the user's environment is explicitly approved and the user confirms:

- Raw personal data
- Credentials
- Full payment details
- Government IDs
- Confidential partner/customer terms
- Unreleased financials
- Private legal or compliance advice

Prefer aggregated, anonymized, sampled, or placeholder values.

## Memory Update Prompt

At the end of a run, if reusable memory was discovered, summarize it like this:

```text
Suggested memory updates:
- product-memory.local.yaml: <stable product fact and source>
- user-preferences.local.yaml: <working preference and evidence>
- decision-log.local.yaml: <confirmed decision and rationale>
```

Ask before writing when the update is sensitive, strategic, or could affect future product direction.

## Failover

- If memory files are missing, continue without them.
- If memory files are malformed, ignore the malformed section, record the issue in `run-log.yaml` when available, and continue.
- If memory appears stale, prefer current context and mark the memory as stale in suggested updates.
- If memory creates uncertainty, ask the user instead of generating with hidden assumptions.
