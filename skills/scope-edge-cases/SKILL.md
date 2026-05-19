---
name: scope-edge-cases
description: Use when defining product scope, non-goals, boundary conditions, dependencies, and edge cases for a PRD.
---

# Scope and Edge Cases

## Goal

Prevent scope drift and missed review issues.

## Workflow

1. Assign stable edge-case IDs such as `E-F1-01` when the output will feed acceptance criteria or QA.
2. Separate in-scope, out-of-scope, and future-scope work.
3. Identify dependencies across design, engineering, data, legal, operations, security, analytics, and support.
4. Cover edge cases for empty states, errors, permissions, eligibility/setup state, content-review state, cancellation, payment, retries, rollback, and notifications.
5. Mark assumptions and unresolved decisions.
6. For reference or regulated content, separate framework scope from content payload approval and launch blockers.
7. For rule-generated behavior such as recurring tasks, scheduled reminders, budget thresholds, or retry queues, define the rule lifecycle: creation, edit, pause, skip, catch-up/backfill, deletion, duplicate prevention, timezone/date boundary, and migration behavior.
8. For metadata management such as tags, categories, labels, statuses, templates, or dictionaries, define create, rename, merge, delete/archive, duplicate name, localization, historical record impact, permission boundary, and migration behavior.
9. For offline, retry, sync, or failed-save behavior, define queue ownership, idempotency key, retry trigger, duplicate prevention, conflict handling, user cancellation, success cleanup, error visibility, and behavior after account/workspace/family switching.
10. For import, upload, bulk edit, or migration flows, define file/source validation, field mapping, preview, duplicate detection, partial failure handling, rollback, confirmation-before-write, retention of uploaded content, and privacy exclusions for logs/analytics.
11. For notification, inbox, announcement, or message-center features, define source separation, read/unread sync, priority, frequency cap, delivery failure, dismissal, retention, and sensitive-content redaction.
12. For public links, read-only shares, or external-facing snapshots, define grant scope, snapshot/live behavior, expiry, revocation, noindex/cache behavior, redaction, access logging, and unavailable/expired states.
13. For market-hours, trading-calendar, availability-window, or schedule banners, define timezone, holiday schedule, exceptional closure, stale or delayed data behavior, fallback copy, and the boundary between informational status and transactional capability.
14. Mark not-applicable categories explicitly when reviewers might otherwise expect them.

## Output

- Scope table
- Non-goals
- Edge case matrix with ID, source requirement, condition, expected behavior, owner, and required-before phase
- Dependency list
- Risk notes

## Quality Bar

- Boundaries are explicit.
- Cross-functional dependencies are visible.
- Edge cases are specific enough for QA review.
- Edge cases map back to requirements and forward to acceptance criteria where relevant.
- Generated instances, retries, schedules, and thresholds include boundary behavior instead of only naming the feature.
- Metadata lifecycle changes explain what happens to existing records, filters, analytics, and user-visible labels.
- Offline and retry flows include idempotency and queue ownership, not just a generic retry button.
- Import and bulk flows separate parsing from writing and show what happens to failed, duplicate, and canceled rows.
- Notification flows distinguish public announcements from private user alerts and avoid exposing sensitive payloads in lists or analytics.
- Share links and snapshots include both access-control and public-Web indexing safeguards.
- Calendar and availability messages avoid implying real-time execution or system capability that the product does not provide.
- Non-goals prevent optional features from leaking into MVP acceptance criteria.
