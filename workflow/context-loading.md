# Context Loading Rules

## Principle

Load only the context needed for the current workflow state. Too much context can lower output quality by mixing unrelated product facts, stale decisions, and conflicting examples.

## Loading Order

1. Current user request and explicit user answers
2. Product context sources provided by the user
3. Host project context, when PM Copilot is embedded in another repository
4. Local memory files in `context/*.local.yaml`, when present
5. Product context summary
6. Relevant personas and user segments
7. Relevant business model and metrics
8. Relevant PRD style and artifact preferences
9. Relevant tracking taxonomy
10. Relevant competitors or research notes

Local memory should reduce repeated questions, not override current evidence. Load only relevant memory sections for the current task.

## Memory Context

PM Copilot supports local file-based memory:

- `context/product-memory.local.yaml`
- `context/user-preferences.local.yaml`
- `context/decision-log.local.yaml`

Use `context/*-memory.example.yaml` and `context/decision-log.example.yaml` only as schemas, not product facts.

Memory can provide stable product facts, user preferences, and prior decisions. Current user instructions, current host implementation, current user-provided documents, and guardrails override memory.

When memory conflicts with current context, follow the conflict table below and record or mention the conflict when it affects scope, readiness, data, privacy, payment, legal, compliance, security, analytics, or launch risk.

At the end of a run, suggest memory updates only for reusable facts, preferences, or durable decisions. One-off task details stay in `run-log.yaml`.

## Context Source Modes

PM Copilot must work for PMs with or without code repositories. Classify the run into one of these modes:

- `repo-backed`: PM Copilot is embedded in a host software repository or the user provides a project path. Use relevant product docs and code-adjacent files as current product context.
- `document-backed`: No software repository is available, but the user provides PRDs, specs, research notes, screenshots, meeting notes, support tickets, analytics exports, roadmap docs, or other product documents. Use those documents as the current product context.
- `brief-only`: The user provides only a short request. Ask the minimum must-answer questions before downstream generation, then proceed only with explicit assumptions for low-risk unknowns.

## Repo-Backed Context

In repo-backed mode, the host project is one source of product reality. Load enough current-state context to avoid proposing a requirement that ignores existing implementation or product constraints.

Use relevant files only. Typical sources include:

- Host README and product docs.
- Existing PRDs, specs, issues, or roadmap notes.
- Route definitions, pages, screens, navigation, and UI components near the affected area.
- Existing demos, screenshots, Storybook stories, preview pages, design-system examples, and component states.
- API contracts, service modules, data models, permission rules, and feature flags.
- Tenant, workspace, organization, family, account, or project identity sources such as `current_family_id`, active workspace state, cache keys, request filters, and server-side isolation checks.
- Notification, message, announcement, reminder, or inbox sources when the feature changes user communication, including read state, priority, frequency limits, delivery channel, and public/private source boundaries.
- Browser extension, embedded widget, iframe, or companion-app manifests and runtime constraints when the feature runs outside the main Web shell, including permissions, storage, auth/session handoff, popup size, and cache policy.
- Analytics conventions, event naming, existing tracking plans, and metric definitions.
- Navigation visibility, authorization gates, eligibility states, empty or ineligible states, and route fallback behavior.
- Content sources, editorial ownership, disclaimer patterns, review cadence, or compliance notes when the feature serves reference or regulated content.
- Package metadata or framework config when it reveals platform and app structure.

Do not load the whole host repository by default. Start with file discovery, then read the smallest set of files that can answer product-fit questions.

If analytics files or conventions are not found after a reasonable targeted search, record `analytics_taxonomy_source.status: not found` in the run log. Tracking output can still be useful, but it must be labeled as a proposed taxonomy that needs analytics or engineering approval.

For multi-tenant, multi-family, workspace-switching, or account-switching products, capture the active-entity source, query filter boundary, local cache invalidation expectation, and cross-entity fallback behavior before proposing requirements. If those facts are unavailable and the feature can expose data across entities, treat the gap as a must-answer or security-sensitive confirmation.

## Document-Backed Context

When no engineering repository is available, use the user's documents as the product reality. Historical PRDs, requirement docs, prototypes, screenshots, release notes, research summaries, customer feedback, analytics exports, and meeting notes can all be valid context.

Extract only decision-relevant information:

- Current product behavior and known constraints.
- Existing UI screens, demos, screenshots, or prototype references.
- Existing navigation, permission, eligibility, and fallback behavior.
- Content sources, editorial ownership, review status, disclaimer patterns, and approval requirements.
- Target users, scenarios, and pain points.
- Prior decisions, rejected directions, and open questions.
- Existing metrics, tracking taxonomy, and baseline data.
- Platform, rollout, compliance, privacy, payment, security, and operational constraints.
- Terminology and language style used by the product team.

Mark document facts separately from inferred assumptions. If documents conflict, prefer newer, user-confirmed, or source-owned documents, and record the conflict.

If the provided documents do not include an analytics taxonomy, record that gap instead of implying that proposed event names are already standardized.

## Brief-Only Context

When the user has no repository and no product documents, do not block forever. Ask only the minimum must-answer questions needed to avoid a misleading PRD/prototype delivery. Common must-answer fields are product goal, target user, platform, scope boundary, success metric, and major risk area.

After the user answers or explicitly asks for a draft with assumption or confirmation risk, generate a useful first PRD/prototype delivery with visible assumptions, open questions, and non-ready status.

If current behavior, affected module, platform, data ownership, rollout constraints, or historical product decisions remain unclear and materially affect the solution, classify the missing information as `must answer before generation` and stop at the clarification gate.

## Conflict Resolution

| Conflict | Priority |
|---|---|
| User instruction vs repository default | User instruction wins if it does not violate guardrails |
| Current host implementation vs greenfield assumption | Current host implementation wins |
| User-provided product documents vs generic model knowledge | User-provided product documents win |
| Product context vs template | Product context wins |
| Artifact contract vs template example | Artifact contract wins |
| Source-backed research vs generic model knowledge | Source-backed research wins |
| Current user answer vs old memory | Current user answer wins |
| Current host implementation vs old memory | Current host implementation wins |
| Current user-provided document vs old memory | Current user-provided document wins |
| Guardrail vs memory | Guardrail wins |

## Context Hygiene

- Do not load all examples by default.
- Do not use old example assumptions as current task facts.
- Do not treat PM Copilot sample outputs as host product facts.
- Do not treat memory schema examples as host product facts.
- Do not require a software repository when product documents can provide enough current context.
- Mark stale, unknown, or inferred context explicitly.
- Use anonymized data unless the environment is approved for sensitive data.
- In default-option or evaluation mode, recommended defaults must be derived from current user instructions and current product context. Do not use templates, example scenarios, or prior generated outputs as the source of a default product decision.
