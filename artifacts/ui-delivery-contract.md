# UI Delivery Contract

## Purpose

UI delivery is a product-review artifact that communicates intended behavior and visual direction. It does not authorize implementation, host-source modification, deployment, or release approval.

## Required Content

Every UI delivery includes:

- Target platform, user role, entry point, and scenario.
- Evidence inventory with observed, user-confirmed, inferred, proposed, and unknown items separated.
- Main flow plus relevant loading, empty, error, permission, and success states.
- Interaction notes, validation rules, and acceptance criteria.
- Accessibility, responsive, content, data, and dependency notes when applicable.
- Named receiving owner and unresolved decisions.

## Artifact Modes

| Mode | Use | Boundary |
|---|---|---|
| `portable_html` | Interactive annotated review artifact | Stored only under `outputs/<run-id>/`; not production code |
| `ui_specification` | PRD section, flow, or annotated reference | Captures behavior and decisions without executable product changes |
| `existing_ui_extract` | Read-only extract of an already rendered screen | Documents existing evidence; does not represent a requested feature as implemented |
| `document_prototype` | Browser-readable reference or catalog | Not a user-facing product surface |

## Evidence and Fidelity

- State the source of every visual baseline: user reference, existing rendered screen, design system, source inspection, or generic proposal.
- Classify concrete displayed data. Queue counts, rates, case IDs, timestamps, reviewer identities, performance values, and SLA durations must be either source-backed with their evidence classification or visibly labeled illustrative prototype data. Proposed targets must be labeled as proposed rather than observed facts.
- Keep approval scopes executable: distinguish an individual workflow decision from a global engineering or launch gate. A control named as a decision prerequisite must be modeled in that decision's validation; otherwise state its separate scope, accountable owner, blocking phase, and closure evidence.
- Mark fidelity as `evidence_based`, `reference_limited`, or `conceptual`.
- Do not claim 1:1 parity for a proposed feature that has not been implemented by the responsible team.
- Do not write host source, add preview files, or alter an existing route to validate a PM artifact.

## Validation

- Portable HTML must open locally, keep assets local, expose meaningful text and controls, and label itself `portable_html_review_artifact`.
- Review artifacts must identify their evidence, proposed behavior, limitations, and receiving owner.
- A visual check may inspect an existing running surface or the portable artifact, but it is not implementation acceptance.

## Handoff

The final delivery names the artifact path, scope, acceptance criteria, dependencies, unresolved questions, and the human owner responsible for implementation and approval.
