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
- Mark fidelity as `evidence_based`, `reference_limited`, or `conceptual`.
- Do not claim 1:1 parity for a proposed feature that has not been implemented by the responsible team.
- Do not write host source, add preview files, or alter an existing route to validate a PM artifact.

## Validation

- Portable HTML must open locally, keep assets local, expose meaningful text and controls, and label itself `portable_html_review_artifact`.
- Review artifacts must identify their evidence, proposed behavior, limitations, and receiving owner.
- A visual check may inspect an existing running surface or the portable artifact, but it is not implementation acceptance.

## Handoff

The final delivery names the artifact path, scope, acceptance criteria, dependencies, unresolved questions, and the human owner responsible for implementation and approval.
