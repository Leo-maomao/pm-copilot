# Main Workflow

## Default Flow

```text
S0 Intake
-> S1 Context loading
-> S2 Discovery and clarification
-> S3 Clarification gate
-> S4 Optional research
-> S5 PRD drafting
-> S6 Metrics and tracking
-> S7 Flow and prototype
-> S8 Review
-> S9 Revision loop
-> S10 Delivery check
```

## State Definitions

| State | Owner | Entry Criteria | Exit Criteria |
|---|---|---|---|
| S0 Intake | PM Orchestrator | Task brief received | Request goal and artifact needs are identified |
| S1 Context loading | PM Orchestrator | Product context source is known or needs discovery | Relevant PM Copilot context and available product context are loaded |
| S2 Discovery and clarification | Discovery Agent | Request is ambiguous, incomplete, or needs current-product-fit validation | Critical questions, assumptions, and open decisions are captured |
| S3 Clarification gate | PM Orchestrator | Clarification questions exist or blocking assumptions are detected | User answers are applied, or the user explicitly asks for a draft with assumption or confirmation risk |
| S4 Optional research | Research Agent | External context is needed and tools are available | Source-backed research brief is produced or limitation is stated |
| S5 PRD drafting | Requirements Agent | Discovery output is usable | `prd.md` contract is satisfied |
| S6 Metrics and tracking | Analytics Agent | PRD includes goals and user actions | Metrics and tracking sections are complete inside `prd.md` |
| S7 Flow and prototype | Prototype Agent | Core flow and platform are known | Flow sections are complete inside `prd.md`; HTML prototype contract is satisfied |
| S8 Review | Review Agent | Draft PRD and prototype exist | Risks, blockers, and required fixes are reflected in PRD status and validation sections |
| S9 Revision loop | PM Orchestrator | Review finds critical gaps | Artifacts are updated or gaps are accepted as open risks |
| S10 Delivery check | PM Orchestrator | Critical gaps are closed or accepted | `prd.md`, prototype, and optional exports are internally consistent |

## Human-in-the-Loop Checkpoints

Human confirmation is required before drafting downstream artifacts when:

- The product goal or target user is unclear.
- The current product state is unknown and could change the proposed solution.
- Scope materially affects engineering effort, payment, privacy, legal, or compliance.
- The agent must choose between materially different product directions.
- Platform, affected module, primary user journey, or rollout surface is unclear.
- The tracking plan includes sensitive properties.
- Research sources are unavailable but competitor claims would affect the solution.
- The PRD/prototype delivery contains high-severity open risks.
- An item is marked `must confirm before development or launch` and the requested output is expected to claim the readiness that item blocks.

If any must-answer question exists, ask the user and stop before creating `prd.md` or prototype HTML. Create or update only `outputs/<run-id>/run-log.yaml` when a persistent trace is useful.

Do not create PRD, metrics, tracking, flow, prototype, review, or delivery artifacts until the user answers or explicitly says to proceed with assumptions. User silence is not approval.

## Clarification Semantics

Avoid contradictory clarification output. A single unknown must belong to exactly one bucket:

- `Must answer before generation`: blocks PRD, metrics, tracking, flow, prototype, review, and delivery check.
- `Can draft with stated assumption`: can be assumed for a draft PRD/prototype, but the assumption must be visible and reviewable.
- `Must confirm before development or launch`: blocks the readiness phase it applies to. Each item must state whether it blocks engineering handoff, launch, or both.

If the user asks to proceed with assumptions while must-answer or engineering-blocking confirmation questions remain, downgrade PRD status to `Draft with assumption risk` or `Draft with confirmation risk`. Do not call it development-ready. If only launch-blocking confirmations remain, the PRD may be engineering-ready only when launch status is explicitly blocked and the engineering acceptance criteria exclude the unconfirmed launch item.

Conditional risks should follow the chosen scope. If the generated scope explicitly excludes the behavior that creates a risk, record the risk as a non-goal, future-scope blocker, or guardrail instead of leaving it as an unresolved current-launch confirmation. If the scope includes the behavior or is ambiguous, keep the confirmation open.

## Readiness Model

Every final PRD must carry three related but separate readiness fields:

- PRD status: whether the delivery is blocked, a draft, ready for review, or ready for engineering.
- Engineering handoff status: whether engineering can build the confirmed scope now, and which decisions block implementation.
- Launch status: whether the shipped behavior, content, copy, compliance, analytics, and operational process are approved for release.

Do not use one `Ready` label to hide a blocked phase. A framework can be ready for engineering while content, legal copy, or operational approval blocks launch; the PRD must say both facts.

## Scope Integrity

After user answers are applied, separate product decisions into:

- Confirmed MVP scope: requirements and acceptance criteria may be written here.
- Optional or conditional scope: describe as a decision still needed; do not include it in MVP acceptance criteria.
- Future scope: useful direction that is not part of the current delivery.
- Explicit non-goals: behaviors that should not be built without a new requirement pass.

If the user says a capability is possible, desirable, or "if needed" but does not confirm it for MVP, treat it as optional or future scope. Do not turn it into a must-build requirement.

For content-heavy features, separate the product framework from the content payload. Requirements may cover the content container, states, permissions, and maintenance flow while launch remains blocked on source, review owner, review status, or disclaimer confirmation.

## Current Product Fit

The new requirement must fit the current product instead of assuming a greenfield product, unless the user explicitly asks for a greenfield exploration.

Current product context can come from a host software repository, historical PRDs, specs, product docs, screenshots, analytics exports, support tickets, meeting notes, or direct user answers. A software repository is useful but not required.

Before S2 exits, capture:

- Existing product area or module likely affected.
- Relevant current behavior, user journeys, UI patterns, API contracts, data models, permission rules, analytics conventions, or documented historical decisions.
- Entry points, navigation visibility, permission or eligibility states, and fallback behavior for users who cannot access the new surface.
- Gaps between the user's requested change and the current product context.
- Project constraints that should shape scope, rollout, migration, and acceptance criteria.

If no analytics convention or event taxonomy is found, record that as a current-state fact. S6 may still produce a tracking proposal, but it must be labeled as proposed and must not claim to follow an existing taxonomy.

If the agent cannot determine the current product state from available repositories, documents, or user answers, ask for the missing context as must-answer questions.

## Run Folder Rules

Use `outputs/<run-id>/` as the single generated-artifact folder for each real requirement run. The run id is the scenario slug unless that output folder already exists. For repeat or similar requirements, append a local timestamp such as `team-permissions-20260518-1430`.

Only update an existing run folder when the user explicitly names that folder or asks to revise the existing requirement.

The repository does not ship example output folders. `outputs/` is generated at runtime by real user runs and should not be treated as product context.

## Delivery Rules

Default delivery should optimize for reviewability, not file count.

- Create `outputs/<run-id>/prd.md` as the primary product-manager handoff artifact.
- Create `outputs/<run-id>/prototype-<platform>.html` when a user-facing prototype is relevant.
- Create `outputs/<run-id>/run-log.yaml` as an internal trace when useful.
- Keep source or export files only when they are useful for analytics import, Mermaid rendering, external review workflow, or user-requested iteration.
- `prd.md` must include version history, requirement input and confirmation record, background, research/reference findings, goals/metrics, scope, requirement list, requirement details, flow diagrams when useful, tracking plan, prototype reference, risks/open confirmations, acceptance criteria, and validation results.
- Do not create separate `task-brief.md`, `clarifying-questions.md`, `assumptions.md`, `pm-package.md`, `metrics-tree.md`, `tracking-plan.md`, `user-flow.md`, `review-checklist.md`, or `final-package-summary.md` by default.
- Avoid making the user open many small Markdown files to understand one requirement.

## Language Rules

Use the user's language for conversation and generated artifacts. Chinese requests should produce Chinese headings, table labels, statuses, narrative text, prototype notes, and review labels; English requests should produce English equivalents. For analytics tables, localize reviewer-facing labels and keep machine field names such as `event_name` or `required_properties` visible in code formatting when implementation needs them. Keep file names, event names, property names, Mermaid node IDs, and other machine-readable identifiers in ASCII.

Repository templates are structural examples, not literal copy. Translate headings and labels before writing user-facing artifacts.

## Skippable Steps

- Research can be skipped when the task does not need external evidence.
- Prototype can be omitted when the request is purely backend, infra, or analytics.
- Tracking can be reduced when the task is a non-user-facing operational change, but the omission must be explained in the PRD.

## Revision Rules

- Review findings with severity `Critical` or `High` must route back to the owning agent.
- Medium findings may be listed as review-time discussion points.
- Low findings may remain as optional improvements.
- Review findings must include artifact, evidence, owner, required-before phase, and status. A review that reports no Critical or High issues must still record the checks performed and any Medium or Low residual risks.

## Trace Format

Use `templates/agent-run-log-template.yaml` as the canonical trace shape.

Minimum trace requirements:

- Record `context.source_mode` as `repo-backed`, `document-backed`, or `brief-only`.
- In repo-backed mode, record host files inspected and current-state facts used for product-fit decisions.
- Record `workflow.clarification_gate.required`, `status`, `stopped_before_generation`, and `assumption_risk_accepted`.
- Classify every unresolved question as exactly one of `must answer before generation`, `can draft with stated assumption`, or `must confirm before development or launch`.
- Record numeric review scores when a quality rubric exists.
- If S5-S10 artifacts are generated while unresolved must-answer or pre-development confirmation questions remain, record the user's explicit draft-risk acceptance as evidence and downgrade PRD readiness.
- Record validation commands actually run, their results, and any skipped validation with the reason. The PRD and run log must use the same validation status.
- Record PRD, engineering handoff, and launch readiness separately, including blockers for each phase.
- Record content source and review status when the feature includes reference, policy, medical, legal, financial, safety, or operational content.
- Record structured review findings or an explicit no-finding review summary with evidence of the checks performed.
