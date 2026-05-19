# Launch Decision Contract

Use this contract when PM Copilot evaluates whether a generated requirement package is ready for release, staging, or further review.

`launch-decision.yaml` is a decision-support artifact, not an approval system. It can be generated unattended only as a gate result or recommendation. It must not claim that a human-owned approval was granted unless the approval is present in the provided context or user answer.

## Required Fields

```yaml
run_id: ""
source_prd: "prd.md"
source_run_log: "run-log.yaml"
decision: "" # launch_blocked | ready_for_engineering | ready_for_staging | ready_for_release_review | ready_to_launch | not_applicable
decision_mode: "" # unattended_candidate | human_confirmed
decision_owner_required: true
summary: ""
gates:
  prd_complete:
    status: "" # passed | failed | skipped
    evidence: ""
  engineering_handoff:
    status: ""
    evidence: ""
  validation:
    status: ""
    evidence: ""
  visual_validation:
    status: ""
    evidence: ""
  content_approval:
    status: ""
    evidence: ""
  analytics_approval:
    status: ""
    evidence: ""
  privacy_security_legal:
    status: ""
    evidence: ""
  rollout_and_rollback:
    status: ""
    evidence: ""
blockers: []
required_human_approvals: []
allowed_next_actions: []
disallowed_actions: []
rollback_plan:
  owner: ""
  trigger: ""
  steps: []
residual_risks: []
```

## Decision Rules

- Use `launch_blocked` when any launch blocker remains open, any required approval is missing, or validation failed.
- Treat missing `scripts/run_delivery_checks.py` evidence as a launch-readiness gap unless equivalent individual validation results are recorded.
- Use `ready_for_engineering` when the confirmed engineering scope is buildable but launch approvals or release checks remain open.
- Use `ready_for_staging` only when engineering blockers are closed, validation has passed or is explicitly scoped, and remaining approvals can occur before production.
- Use `ready_for_release_review` when the package is ready for final human approval but PM Copilot cannot approve the release itself.
- Use `ready_to_launch` only when the user or provided context explicitly confirms all required product, engineering, QA, analytics, privacy, security, legal, compliance, content, and rollback approvals. In unattended mode this should normally remain unavailable.
- Never use a recommended default to approve privacy, security, legal, compliance, payment, financial, regulated content, customer communication, or production launch decisions.

## Quality Bar

- Every gate has status and evidence.
- Blockers name the owner and required action.
- Allowed and disallowed next actions are explicit.
- Rollback is present for production-facing changes.
- The artifact supports go/no-go review without pretending to be the go/no-go authority.
