# PM Package: Mini Program Booking

## Executive Summary

Create a Mini Program booking flow that handles authorization, service selection, slot selection, form validation, and booking confirmation.

## Context And Current-State Fit

This scenario assumes an existing mini-program container, booking service, authorization flow, slot inventory, and confirmation page.

## Clarification Status

### Must Answer Before Generation

| Question | Why It Blocks | Owner |
|---|---|---|
| None for this curated example | The example proceeds with explicit assumptions | PM |

### Can Draft With Stated Assumption

| Assumption | Why Reasonable | Risk |
|---|---|---|
| Slot availability is checked again on submit | Prevents stale-slot booking | API behavior may differ |

### Must Confirm Before Development Or Launch

| Item | Why It Matters | Owner |
|---|---|---|
| Required contact fields and authorization scope | Privacy and conversion dependency | Product and legal |
| Slot hold and conflict behavior | Determines error and retry UX | Engineering |

## PRD

See `prd.md`.

## Metrics Tree

See `metrics-tree.md`.

## Tracking Plan

See `tracking-plan.md` for the reviewable event and property tables, and `tracking-plan.csv` for the importable export.

## User Flow

See `user-flow.md` for the rendered-friendly diagram and `user-flow.mmd` for source.

## Prototype

- File: `prototype-mini-program.html`
- Fidelity: mid
- Main interactions: authorize, select service, choose slot, submit form, handle slot conflict.
- Key annotations: auth scope, slot availability, validation, privacy notes.
- Implementation notes: do not log raw contact details or free-text notes.

## Review Checklist

See `review-checklist.md`.

## Artifact Index

| Artifact | File | Purpose |
|---|---|---|
| PRD | `prd.md` | Product requirements and acceptance criteria |
| Metrics | `metrics-tree.md` | Success and guardrail metrics |
| Tracking plan | `tracking-plan.md` | Human-readable analytics requirement |
| Tracking export | `tracking-plan.csv` | Machine-readable analytics export |
| Flow diagram | `user-flow.md` | Rendered-friendly user flow |
| Flow source | `user-flow.mmd` | Mermaid source |
| Prototype | `prototype-mini-program.html` | Clickable Mini Program reference |
| Review | `review-checklist.md` | Readiness and risk review |

## Risks And Next Actions

- Confirm authorization scope and required contact fields.
- Confirm slot hold, timeout, and conflict handling.
