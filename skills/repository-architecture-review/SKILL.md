---
name: repository-architecture-review
description: Use only for PM Copilot self-improvement to assess this repository's routing, document ownership, validation seams, and prompt-budget structure before proposing a scoped refactor.
---

# Repository Architecture Review

## Goal

Identify a small number of evidence-backed improvements to PM Copilot's own architecture without turning a review into an unbounded refactor or an instruction to modify a host product.

## Scope

- Applies only to `task_mode: self_improvement` and this repository.
- Reviews routing, canonical ownership, document locality, validation seams, prompt budget, and maintainability.
- Produces recommendations first. It changes files only after the user selects a recommendation or explicitly asks for implementation.

## Workflow

1. Define the review target from the user request; otherwise use recent commits and validation failures to select one high-churn area.
2. Read the active canonical documents, nearby validators, and only the evidence necessary to understand the target.
3. Look for duplicated authority, shallow documents that force excessive cross-file reading, unclear handoffs, unvalidated routing, or rules that cannot be loaded on demand.
4. For each candidate, climb a minimality ladder before proposing a change: remove the need, reuse an existing rule or validator, use the repository's existing mechanism, then add the smallest new surface that closes the gap. Do not treat a smaller diff as success if it removes validation, security, privacy, accessibility, evidence, or approval gates.
5. Produce up to three candidates. For each, state evidence, expected benefit, affected canonical owner, risk, validation approach, and why it is preferable to doing nothing.
6. Ask the user to select a candidate before proposing an interface, folder move, or file change.
7. If selected, apply the narrowest change, preserve one canonical owner per capability, and add a deterministic regression check when practical.

## Boundary

Do not create production features, change an embedded host repository, or automatically write durable decision records. Architecture review recommendations remain proposals until a human selects them.

## Output

- Review target and evidence inspected.
- Up to three ranked improvement candidates.
- For each candidate: canonical owner, expected benefit, risk, validation plan, and explicit decision required.
- Selected change status or a clear `needs_input` outcome.

## Quality Bar

- Recommendations name a concrete friction and supporting repository evidence.
- No recommendation repeats an existing active rule under a new name.
- Every proposed change states the first minimality rung that holds and names the quality gates that remain non-negotiable.
- The chosen change reduces lookup cost, ambiguity, or validation risk measurably.
- Completion includes repository validation and any remaining human decision.
