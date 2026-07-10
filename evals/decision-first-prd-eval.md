# Evaluation Case: Decision-First PRD

## Metadata

| Field | Value |
|---|---|
| Case ID | decision-first-prd |
| Scenario | A Chinese PRD must surface product judgment before document administration |
| Platform | Cross-platform |
| Product Area | PRD quality and PM decision support |
| Created | 2026-07-10 |
| Last Updated | 2026-07-10 |
| Fixture Scope | Public generic |
| PM User Type | Senior PM |
| Risk Profile | Security / Operations |

## Fixture Isolation Terms

- `<none>`

## Raw Request

```text
Create a Chinese PRD for a team permission change. Make the recommendation, confidence, scope, blockers, readiness, and next checkpoint clear before the detailed requirements.
```

## Context Files

- `artifacts/prd-contract.md`
- `templates/prd-template.md`
- `scripts/test_prd_contract.py`

## Objective

Verify that a PRD helps a PM make and execute a product decision before it satisfies document-administration conventions.

## Scenario

Create a Chinese PRD for a team permission change that affects role assignment, high-risk confirmation, audit retention, access states, engineering handoff, and launch approval.

## Required Behavior

- Use the canonical eight-section planned PRD structure.
- Put recommendation, evidence-based confidence, separate PRD/engineering/launch states, key blocker, and next checkpoint on the first rendered screen.
- Separate MVP, optional, future, and non-goal scope.
- Use `需求详情` as the single behavioral source of truth; do not add a duplicate top-level requirement list.
- Make the strongest rejected alternative, risk owner, required-before phase, and acceptance evidence visible.
- Include tracking, copy/i18n, UI handoff, or test subsections only when they apply.
- Require applicable UI loading, empty, error, recovery, and access states without imposing those markers on non-UI PRDs.

## Deterministic Validation

```bash
python3 scripts/test_prd_contract.py
```

For a generated delivery, also run:

```bash
python3 scripts/validate_outputs.py outputs/<run-id> --language zh
python3 scripts/run_delivery_checks.py outputs/<run-id> --language zh
```

The regression suite must accept the decision-first fixture and reject:

- a PRD with no confidence judgment
- a PRD with no next checkpoint
- a PRD that replaces requirement details with a duplicate requirement-list chapter
- a PRD with no traceable acceptance criterion

## Pass Criteria

- `scripts/test_prd_contract.py` accepts the decision-first positive fixture.
- Missing confidence, missing next checkpoint, missing requirement details, and missing traceable acceptance criteria are rejected.
- `templates/prd-template.md` and `templates/implemented-feature-prd-template.md` render successfully with `scripts/render_prd_html.py`.
- `scripts/validate_repo.py` confirms that active prompts, contracts, skills, docs, and evals reference the decision-first structure.

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-07-10 | prd-decision-latency | High | Document metadata and fixed tables appeared before the recommendation, scope, blockers, and readiness judgment. | Replaced the 11/14-section templates with a decision-first 8/10-section contract. |
| 2026-07-10 | prd-conditional-bloat | Medium | Tracking, i18n, tests, and UI states were mandatory even when they did not apply. | Moved cross-functional material into optional delivery-design subsections and made UI-state validation applicability-aware. |

## Latest Result

| Field | Value |
|---|---|
| Run ID | deterministic-prd-contract-2026-07-10 |
| Status | Passed |
| Notes | Positive and four negative contract branches pass through `scripts/test_prd_contract.py`. |
