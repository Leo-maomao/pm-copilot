# Artifact Contracts

Every generated artifact must follow the relevant contract. If a section cannot be completed, keep the section and mark it as `Unknown`, `Assumed`, or `Not applicable`.

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

Required columns:

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

Minimum quality bar:

- Event names follow the configured taxonomy.
- Each core user action has coverage or an explicit omission reason.
- Sensitive properties are flagged and minimized.

## Mermaid User Flow

Required elements:

- Entry point
- Main success path
- Decision points
- Error or cancellation branches
- Completion state

Minimum quality bar:

- The diagram renders as Mermaid.
- Branch labels are meaningful.
- The flow matches the PRD scope.

## HTML Prototype

Required elements:

- Runs locally without build tooling.
- Simulates the selected platform container.
- Includes key screens and states.
- Includes interaction for the main path.
- Labels itself as low-fidelity.

Minimum quality bar:

- No external assets are required.
- Text fits in the layout.
- The prototype does not claim to be production code.

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
