# Launch Tooling

Launch tooling supports go/no-go reasoning. It does not approve production release without human approval evidence.

## Launch Decision Export

Create `outputs/<run-id>/launch-decision.yaml` when the user asks for:

- release readiness
- launch decision support
- go/no-go review
- unattended launch candidate review

The file must follow `artifacts/launch-decision-contract.md`.

## Gate Evidence

Evaluate at minimum:

- PRD completeness
- engineering handoff status
- validation and visual validation
- analytics readiness
- content/source approval
- privacy, security, legal, compliance, financial, and payment gates when relevant
- rollout and rollback plan

## Decision Rules

- Use `decision_mode: unattended_candidate` unless a human explicitly approves the final launch decision in this run.
- Do not use `ready_to_launch` without explicit approval evidence for every required gate.
- Prefer `ready_for_release_review` when work is implementation-ready but launch approval is missing.
- List allowed and disallowed next actions.
