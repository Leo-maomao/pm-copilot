# Artifact Contracts

Every generated artifact must follow the relevant contract. If a section cannot be completed, keep the section and mark it as `Unknown`, `Assumed`, or `Not applicable`.

Use the user's language for all human-facing artifact content, including headings, table column labels, status labels, notes, prototype annotations, and review labels. For analytics tables, localize reviewer-facing labels and keep machine field names such as `event_name` or `required_properties` visible in code formatting when implementation needs them. Keep file names, event names, property names, Mermaid node IDs, and other machine-readable identifiers in ASCII.

Repository templates are structure guides, not literal English copy. Translate template headings and labels when the requested output language is not English.

## Default Delivery

The default product-manager delivery contains only:

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/prototype-<platform>.html` when a user-facing prototype is relevant

`outputs/<run-id>/run-log.yaml` is an internal trace artifact for debugging, regression, and auditability. It is not a PM-facing deliverable.

Do not create separate `task-brief.md`, `clarifying-questions.md`, `assumptions.md`, `pm-package.md`, `metrics-tree.md`, `tracking-plan.md`, `user-flow.md`, `review-checklist.md`, or `final-package-summary.md` by default. Create split files only when the user asks, an external workflow needs them, or a machine-readable export is useful.

The original request, clarified answers, low-risk assumptions, scope decisions, metrics, tracking plan, flow diagrams, risks, and validation results belong in `prd.md`.

## Clarification Gate

Clarification output must not contradict itself. Do not mark one question as both blocking and assumed. Use distinct buckets:

- `must answer before generation`
- `can draft with stated assumption`
- `must confirm before development or launch`

If must-answer questions are unresolved, ask the user and stop before generating `prd.md` or prototype HTML. User silence is not approval.

Default readiness is `Ready for engineering` for the confirmed engineering scope. If engineering-blocking confirmations are missing, the agent must stop and ask. It may generate a draft only when the user explicitly requests a draft or accepts the risk, and the PRD status must reflect that downgrade. Launch readiness is a separate field; a PRD may be ready for engineering while launch remains blocked by content, legal, compliance, operational, or analytics approval.

## PRD

Required sections:

- Title
- Version history
- Requirement input and confirmation record
- Readiness summary
- Background
- Research and reference findings
- Project goals and metrics
- Requirement scope
- Surface and permission states, when relevant
- Content source and review status, when relevant
- Requirement list
- Requirement details
- Flow diagrams, when useful
- Tracking plan
- Prototype reference
- Risks and open confirmations
- Acceptance criteria
- Delivery review findings
- Validation results

Required formatting:

- Use tables for version history, confirmations, goals, scope, requirement list, requirement details, tracking, risks, and acceptance criteria when there are multiple items.
- Use stable IDs such as `R1`, `F1`, `AC1`, and `E1`.
- Use short paragraphs for background, research conclusions, and rationale.
- Avoid long undifferentiated unordered lists.
- Keep confirmed MVP scope separate from optional, conditional, future, and non-goal scope.
- Acceptance criteria cover confirmed MVP requirements only.
- PRD status, engineering handoff status, and launch status are separate and non-contradictory.
- Existing-product entry points, navigation visibility, permission or eligibility states, and fallback states are explicit when the feature adds or changes a surface.

Requirement details must be implementation-grade. For each functional item, include the relevant subset of:

- Function ID and function name
- User scenario
- Entry point or trigger
- Page or content requirements
- Business logic
- Interaction rules
- Data rules
- Permission or eligibility rules
- Edge and fallback states
- Tracking event links
- Acceptance criteria links

Minimum quality bar:

- A PM, designer, engineer, QA, and analytics reviewer can understand the requirement from `prd.md` plus the prototype.
- Goals are measurable or tied to a measurement plan.
- Research and reference findings explain why the solution is shaped this way. This section may include user research, competitor research, historical PRDs, screenshots, current implementation findings, or technical solution references.
- Requirements are testable.
- Edge cases include error, empty, permission, payment, rollback, content-review, and launch-blocking cases where relevant.
- Open questions and launch blockers are visible, not hidden inside prose.
- Validation results list the exact command, pass/fail/skipped status, and limitation. The PRD must not conflict with `run-log.yaml` about what was validated.
- Content source, review owner, review status, and disclaimer status are visible when the requirement includes reference, policy, medical, legal, financial, safety, or operational content. Unreviewed content is labeled as placeholder or draft and blocks launch.
- Delivery review findings include artifact, evidence, owner, required-before phase, and status, or explicitly state that no Critical or High findings were found after review.

## Tracking Plan

The tracking plan is a PRD section by default.

Required event table semantic columns. CSV exports must use the exact machine column names below; Markdown review tables may localize the visible label and include the machine name in code formatting.

- event_name
- description
- trigger
- platform
- actor
- required_properties
- optional_properties
- success_criteria
- validation_notes
- privacy_notes

Required property table semantic columns. CSV exports must use the exact machine column names below; Markdown review tables may localize the visible label and include the machine name in code formatting.

- property_name
- type
- required
- example
- description
- allowed_values
- privacy_level
- source

Minimum quality bar:

- Event names follow the configured taxonomy.
- If no configured taxonomy was found, the tracking plan is labeled as a proposed taxonomy and records the context source or absence of source.
- Each core user action has coverage or an explicit omission reason.
- Every property used by any event is defined once in the property dictionary.
- Sensitive properties are flagged and minimized.

## Flow Diagrams

Flow diagrams are PRD sections by default. Create `user-flow.mmd` only when a Mermaid source export is useful or requested.

Useful diagram types:

- Functional flow: system or feature-level logic, branches, and states.
- Operation flow: user-facing action path across pages or controls.

Minimum quality bar:

- Diagrams are standard Mermaid flowcharts when Markdown rendering is expected.
- Branch labels are meaningful.
- The flow matches the confirmed PRD scope.
- Notes explain only assumptions or edge cases that cannot fit cleanly in the diagram.

## HTML Prototype

Required elements:

- Runs locally without build tooling.
- Simulates the selected platform container.
- Matches existing product style when current screenshots, demos, routes, components, or design-system references are available.
- Includes key screens and states.
- Includes interaction for the main path.
- States its fidelity level: `low`, `mid`, or `high`.
- Uses left-side prototype and right-side numbered annotation panel by default.
- Places compact numbered callouts such as `①`, `②`, and `③` beside the concrete UI element, state, or transition being explained.
- Uses matching numbered notes in the side panel.

Prototype annotations must cover the relevant subset of:

- Product design intent
- Logic rule
- Interaction behavior such as tap, hover, long-press, disabled, loading, error, and success
- Text length limit, truncation, and ellipsis behavior
- Content source and placeholder status
- Data source and refresh behavior
- Permission or eligibility behavior
- Tracking hook
- Engineering handoff note

Minimum quality bar:

- No external assets are required.
- Text fits in the layout.
- Callouts do not cover critical copy or controls.
- The prototype does not claim to be production code.
- The prototype shows real screens, state changes, validation, empty states, errors, permissions, and success feedback where relevant.
- When existing product UI exists, the prototype adapts the existing surface and highlights the new requirement delta instead of inventing an unrelated product surface.

## Optional Exports

Split PRD, split tracking Markdown, split user-flow Markdown, review checklist files, `pm-package.md`, and `final-package-summary.md` must not be generated by default. Create a separate file only when the user explicitly asks for it or an external tool requires a machine-readable export such as CSV or Mermaid source.
