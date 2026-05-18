# Artifact Contracts

Every generated artifact must follow the relevant contract. If a section cannot be completed, keep the section and mark it as `Unknown`, `Assumed`, or `Not applicable`.

Use the user's language for artifact prose. Keep file names, event names, property names, Mermaid node IDs, and other machine-readable identifiers in ASCII.

Write generated run artifacts under the active `outputs/<run-id>/` folder, including `task-brief.md`. Do not overwrite a previous requirement run unless the user explicitly asks to revise it. Use `examples/` only for curated scenario-library inputs, not ordinary generated runs.

If must-answer questions are unresolved, generate only the task brief, clarifying questions, assumptions, and run log. Downstream artifacts must wait for user answers or explicit assumption approval.

The primary reviewer-facing artifact is `pm-package.md`. Separate files may still be generated as source files, exports, or focused handoff artifacts, but the user should be able to review the whole requirement from the package.

Clarification output must not contradict itself. Do not mark one question as both blocking and assumed. Use distinct buckets: `must answer before generation`, `can draft with stated assumption`, and `must confirm before development or launch`.

## PM Package

Required sections:

- Executive summary
- Context and current-state fit
- Clarification status
- PRD
- Metrics tree
- Tracking plan table
- User flow diagram
- Prototype link, annotations, and implementation notes
- Review checklist
- Assumptions and confirmations
- Open risks and next actions

Minimum quality bar:

- A reviewer can understand the whole requirement without opening every source file.
- Source files and exports are linked from the package.
- Status is explicit: `Blocked`, `Draft with assumptions`, `Ready for review`, or `Ready for engineering`.
- Items that must be confirmed before development or launch are separate from assumptions used for draft generation.

## PRD

Required sections:

- Title
- Status and owners
- Background
- Problem statement
- Goals
- Non-goals
- Target users
- User scenarios
- Scope
- Requirements
- Edge cases
- Metrics
- Dependencies
- Risks
- Open questions
- Acceptance criteria

Minimum quality bar:

- Goals are measurable or tied to a measurement plan.
- Scope and non-goals are explicit.
- Requirements are testable.
- Edge cases include error, empty, permission, payment, and rollback where relevant.
- Open questions are visible, not hidden inside prose.

## Metrics Tree

Required sections:

- Product goal
- Primary metric
- Secondary metrics
- Guardrail metrics
- Diagnostic metrics
- Metric definitions
- Measurement assumptions

Minimum quality bar:

- The primary metric maps directly to the product goal.
- Guardrails capture possible harm.
- Diagnostic metrics explain why the primary metric moved.

## Tracking Plan

Primary output:

- `tracking-plan.md` with Markdown tables.
- `tracking-plan.csv` as a machine-readable export when analytics or engineering needs importable data.

Required event table columns:

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

Required property table columns:

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
- Each core user action has coverage or an explicit omission reason.
- Each event lists complete required and optional properties.
- Property definitions are centralized so engineering and analytics do not infer field meaning.
- Sensitive properties are flagged and minimized.

## User Flow Diagram

Primary output:

- `user-flow.md` containing a renderable Mermaid diagram block plus legend and notes.
- `user-flow.mmd` as the Mermaid source export.

Required diagram elements:

- Entry point
- Main success path
- Decision points
- Error or cancellation branches
- Completion state

Minimum quality bar:

- The artifact is a standard flowchart, not a prose list.
- The diagram renders as Mermaid in GitHub-compatible Markdown or another stated renderer.
- Branch labels are meaningful.
- The flow matches the PRD scope.
- Notes explain only assumptions or edge cases that cannot fit cleanly in the diagram.

## HTML Prototype

Required elements:

- Runs locally without build tooling.
- Simulates the selected platform container.
- Includes key screens and states.
- Includes interaction for the main path.
- States its fidelity level: `low`, `mid`, or `high`.
- Includes clickable annotations or an annotation panel for UI, interaction, data, edge case, and implementation notes.
- Includes enough spacing, hierarchy, copy, states, and component behavior for UI and engineering reference.

Minimum quality bar:

- No external assets are required.
- Text fits in the layout.
- The prototype does not claim to be production code.
- The prototype is implementation-oriented: it shows real screens, state changes, validation, errors, empty states, permissions, and success feedback where relevant.
- Use high-fidelity direction when the request provides enough brand, visual, and interaction context; otherwise use a polished mid-fidelity prototype rather than a bare wireframe.

## Review Checklist

Required sections:

- Summary recommendation
- Critical issues
- High issues
- Medium issues
- Low issues
- Artifact-by-artifact checklist
- Open decisions
- Human confirmation required

Minimum quality bar:

- Findings are actionable.
- Severity is explicit.
- The checklist can route work back to the responsible agent.
