---
name: test-first-maintenance
description: Use only for PM Copilot self-improvement when changing this repository's executable validation or automation logic test-first.
---

# Test-First Maintenance

## Goal

Make a behavior-changing maintenance change to PM Copilot's own scripts or validators through a small red-green-refactor loop, without touching an embedded host product.

## Scope

- Applies only when `task_mode` is `self_improvement` and the target is this repository.
- Does not authorize changes to host product code, configuration, data, infrastructure, tickets, or deployment state.
- Use existing deterministic validators as the public seams whenever possible.

## Workflow

1. State the maintenance behavior and the existing validation seam before editing code.
2. Add or adjust the smallest deterministic check that fails for the missing or incorrect behavior.
3. Run the targeted check and record the failure evidence.
4. Make the smallest change that makes the check pass.
5. Refactor only after the behavior is green; keep unrelated cleanup out of scope.
6. Run the targeted check, then the repository validation required by `AGENTS.md`.
7. Record the changed rule owner, validation command, and residual risk in the self-improvement trace.

## Output

- Targeted behavior and confirmed validation seam.
- Failing-check evidence before the implementation change.
- Minimal fix summary and passing validation evidence.
- Residual risk and any human review still required.

## Quality Bar

- Tests and validators observe documented behavior, not incidental implementation details.
- Each change has one explicit, independently checkable expected result.
- A passing broad check never substitutes for a missing targeted regression check.
- No implementation work occurs in a host product under the name of PM Copilot maintenance.
