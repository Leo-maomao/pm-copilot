# PM Package: Team Permissions

## Executive Summary

Improve team permission management for Web admins by making role changes searchable, reviewable, safer, and auditable.

## Context And Current-State Fit

This is a Web admin/SaaS scenario. The package assumes an existing team settings area, role table, permission checks, and audit log surface.

## Clarification Status

### Must Answer Before Generation

| Question | Why It Blocks | Owner |
|---|---|---|
| None for this curated example | The example proceeds with explicit assumptions | PM |

### Can Draft With Stated Assumption

| Assumption | Why Reasonable | Risk |
|---|---|---|
| Workspace roles are owner, admin, member, and viewer | Common SaaS permission model | Actual role taxonomy may differ |

### Must Confirm Before Development Or Launch

| Item | Why It Matters | Owner |
|---|---|---|
| Role taxonomy and permission matrix | Drives UI, API, and acceptance criteria | Product and engineering |
| Audit log retention and visibility | Security and compliance dependency | Security |

## PRD

See `prd.md`.

## Metrics Tree

See `metrics-tree.md`.

## Tracking Plan

See `tracking-plan.md` for the reviewable event and property tables, and `tracking-plan.csv` for the importable export.

## User Flow

See `user-flow.md` for the rendered-friendly diagram and `user-flow.mmd` for source.

## Prototype

- File: `prototype-web.html`
- Fidelity: mid
- Main interactions: search/filter members, select role, review change, confirm, handle success and failure.
- Key annotations: permission constraints, unsafe changes, audit log link, event hooks.
- Implementation notes: API must preserve previous role on failure and block unsafe self-demotion or last-owner changes.

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
| Prototype | `prototype-web.html` | Clickable Web reference |
| Review | `review-checklist.md` | Readiness and risk review |

## Risks And Next Actions

- Confirm exact role taxonomy and directory-sync rules.
- Confirm audit log retention, access, and tracking policy.
