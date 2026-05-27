# Qiki Multi-Scenario Iteration Eval

## Metadata

| Field | Value |
|---|---|
| Case ID | qiki-multi-scenario-iteration |
| Scenario | family-workspace-mini-program-iteration-portfolio |
| Platform | Mini Program |
| Product Area | Family workspace operations |
| Fixture Scope | Fixture-scoped |
| PM User Type | Founder-operator / Ops PM |
| Risk Profile | Privacy / Security / Operations |
| Created | 2026-05-21 |
| Last Updated | 2026-05-26 |

## Fixture Isolation Terms

- `Qiki`
- `qiki`

Use this eval when PM Copilot is embedded in Qiki or a similar family/workspace product and the user asks for broad self-iteration instead of a single scenario.

## Context

- Host project: Qiki WeChat Mini Program family hub.
- Required artifacts per round: `prd.md`, a Mini Program UI deliverable (`prototype-mini-program.html` only for compatibility HTML mode), and `run-log.yaml`.
- Validation: `python3 scripts/validate_repo.py`, `python3 scripts/validate_outputs.py outputs/<run-id> --language zh`, HTML parser fallback when system `tidy` reports old HTML5 warnings.
- Default-option mode: choose conservative recommended defaults, record them in `run-log.yaml`, and keep security, privacy, content, launch, and analytics approvals open.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Scenario diversity | 5 / 5 |
| Privacy and security handling | 5 / 5 |
| Mini Program state fidelity | 4 / 5 |
| Default-option traceability | 4 / 5 |
| Validation evidence | 5 / 5 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-21 | iteration-narrowness | High | Broad self-iteration could overfit one family/workspace path and miss security, privacy, and operations variants. | Add multi-scenario portfolio with repeated validation and blocker separation. |

## Scenario Set

| Round | Scenario | Primary Regression Risk | Expected PM Copilot Coverage |
|---|---|---|---|
| R41 | Monthly budget alerts | Legal content/status fields misread as stale validation | Validation distinguishes real stale placeholders from legitimate review states |
| R42 | Recurring family items | Repetition rules underspecified | Instance generation, skip, backfill, boundary dates, and idempotency are explicit |
| R43 | Document expiry reminders | Notification analytics leaks private document data | Reminder events exclude raw titles, exact sensitive dates, message bodies, and contact data |
| R44 | Permission templates | Convenience templates over-grant permissions | Permission matrix, least privilege defaults, server enforcement, and audit expectation are visible |
| R45 | Invite approval | Pending membership states omitted | Requester, approver, rejected, expired, retry, and security invalidation paths are shown |
| R46 | Family switcher | Cross-family data leakage | Active family source, query filter, cache invalidation, and fallback behavior are captured |
| R47 | Feedback triage | Operational workflow lacks owner/status model | State machine, owner, reply review, notification, closure, and reopen paths are covered |
| R48 | Privacy mode | UI hiding treated as access control | UI deliverable and PRD state that masking is display-layer only and permissions are unchanged |
| R49 | Assignee load summary | Aggregates leak private records | Aggregation grain, permission filter, and detail suppression are specified |
| R50 | Cross-module search | Search results ignore per-source permissions | Source-by-source permissions, redaction, partial failure, and performance limits are required |
| R51 | Note tag management | Metadata changes ignore existing records | Rename, merge, delete/archive, duplicate names, and migration effects are covered |
| R52 | Family audit log | Audit requirements lack traceability | Run log can record security/audit boundary, visibility, redaction, retention, and approval owner |
| R53 | Role display names | Long or duplicate labels break handoff | UI delivery notes cover length, truncation, duplicate disambiguation, and edit permissions |
| R54 | Fast input review | Parsed input writes shared data without confirmation | Explicit review/confirm, edit, cancel, low-confidence, retry, and failure states are required |
| R55 | Offline retry | Retry creates duplicates or crosses family boundary | Queue ownership, idempotency, conflict handling, cancellation, and cleanup are specified |
| R56 | Leave family safeguards | Dangerous action lacks impact confirmation | Impact summary, blocking conditions, confirmation, recovery/cooling-off, and audit are tested |
| R57 | Member activity summary | Recency signal exposes private behavior | Coarse active/inactive buckets and suppression of exact object/timestamp data are expected |
| R58 | Home module customization | Personalization misses persistence and unavailable states | Edit mode, reset, unavailable modules, and sync/persistence failure are visible |
| R59 | Private note sharing | Temporary access implemented as front-end link | Explicit grant scope, recipient, expiry, revocation, one-time use, forwarding limits, and audit are required |
| R60 | Release readiness check | Validator pass mistaken for business approval | Release notes keep human approval, rollback, limitations, and regression coverage separate |

## Pass Criteria

- Every round generates the full artifact set and passes output validation.
- Improvements are applied across validators, workflow, contracts, guardrails, agents, skills, templates, docs, and evals as appropriate.
- Generated Qiki `outputs/` folders are removed after evidence is scored and PM Copilot fixes are captured.
- Remaining blockers are product decisions, security/privacy approvals, content approval, analytics approval, or launch approval rather than PM Copilot artifact defects.
