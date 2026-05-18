# Team Permission Management PRD

## Status and Owners

| Field | Value |
|---|---|
| Status | Draft for review |
| Product owner | TBD |
| Design owner | TBD |
| Engineering owner | TBD |
| Analytics owner | TBD |

## Background

Workspace admins need to assign roles safely and understand the impact of permission changes. Current workflows create confusion and support tickets when users receive too much or too little access.

## Problem Statement

Admins lack a clear, auditable permission management flow that explains role impact before changes are applied.

## Goals

| Goal | Metric | Target | Notes |
|---|---|---|---|
| Reduce accidental permission changes | Permission rollback rate | TBD | Primary |
| Improve admin confidence | Permission review completion rate | TBD | Secondary |
| Reduce support tickets | Access-related support ticket rate | No increase after launch | Guardrail |

## Non-goals

- Redesign authentication.
- Build custom roles in v1.
- Change billing seat logic.
- Replace audit log infrastructure.

## Target Users

- Workspace owner
- Workspace admin
- Support operator reviewing access issues

## User Scenarios

| Scenario | Entry Point | User Need | Expected Outcome |
|---|---|---|---|
| Change member role | Team settings | Understand role impact before applying | Role updates after confirmation |
| Review pending changes | Confirmation drawer | Check affected permissions | Admin confirms or cancels |
| Investigate history | Audit log link | See who changed access and when | Admin can trace change |

## Scope

| Area | In Scope | Out of Scope |
|---|---|---|
| Role table | View members and current roles | Custom role creation |
| Change confirmation | Compare current and new permissions | Approval workflow |
| Audit note | Capture actor, target, old role, new role | Full audit log redesign |
| Search and filter | Find member by name or email | Advanced directory sync |

## Requirements

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| R1 | Admins can view members, roles, and status in a table. | Must | Web desktop layout |
| R2 | Admins can search and filter by role. | Must | Supports large teams |
| R3 | Role changes show a confirmation panel before saving. | Must | Explain permission impact |
| R4 | Confirmation includes old role, new role, affected permissions, and target user. | Must | Reduces accidental access |
| R5 | Successful changes show a status message and audit log hint. | Must | Reinforces accountability |
| R6 | Failed changes show recoverable errors. | Must | No silent failures |
| R7 | Events track views, role selection, confirmation, success, failure, and audit link clicks. | Must | See tracking plan |

## Edge Cases

| Case | Expected Behavior | Owner |
|---|---|---|
| Admin tries to demote self | Block and explain why | Product, Engineering |
| Last owner is removed | Block action | Engineering |
| Directory sync locks role | Disable role selector and show reason | Engineering |
| Permission update fails | Keep old role and show retry | Engineering |
| User lacks admin rights | Show read-only state | Product |

## Metrics

- Primary: permission rollback rate.
- Secondary: role change confirmation completion rate, search usage rate.
- Guardrails: access-related support ticket rate, failed permission update rate.

## Dependencies

- Role and permission service.
- Audit log service.
- Admin authorization checks.
- Analytics pipeline.

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Admin accidentally grants high access | High | Confirmation panel and affected permission summary |
| Self-demotion locks workspace | High | Block last-owner and self-demotion cases |
| Directory sync conflicts with manual edits | Medium | Show locked state and source of truth |

## Open Questions

1. Which roles exist in v1?
2. Are custom roles planned soon?
3. Does directory sync control any workspace roles?
4. What audit log details are available today?

## Acceptance Criteria

| Requirement ID | Criteria | Verification |
|---|---|---|
| R1 | Admin can view role table with member status. | QA with seeded workspace |
| R3 | Role change cannot be saved without confirmation. | QA interaction test |
| R4 | Confirmation lists old and new role impact. | Product and design review |
| R6 | Failed update preserves old role. | Engineering failure simulation |
| R7 | Analytics events fire with required properties. | Analytics QA |
