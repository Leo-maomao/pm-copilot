---
name: opportunity-discovery
description: Use when validating product opportunities, mapping assumptions, planning discovery work, or deciding whether a problem is worth PRD/prototype investment.
---

# Opportunity Discovery

## Goal

Turn an ambiguous idea into an evidence-backed opportunity brief before PM Copilot commits to solution scope, PRD details, or prototype fidelity.

## Workflow

1. Define the decision this discovery must unblock: proceed, narrow, pivot, stop, or run another test.
2. State the desired business or user outcome and the baseline metric when available.
3. Split the opportunity from the solution. Capture user pain, current workaround, frequency, severity, willingness to change, and affected segment.
4. Build an opportunity tree: outcome, user opportunities, candidate solutions, fastest learning tests.
5. Map assumptions across desirability, viability, feasibility, usability, risk, compliance, and operational readiness.
6. Rank assumptions by impact if wrong and current evidence strength.
7. Pick the fastest validation method for top assumptions: interview, support-ticket synthesis, analytics pull, fake-door test, prototype task test, concierge test, or limited beta.
8. Define decision rules before gathering evidence, including what evidence would stop the idea.
9. Feed confirmed opportunities into PRD scope and keep unvalidated ideas as optional or future scope.

## Boundary

Use this skill for deciding whether a problem or opportunity is worth product investment. Use `skills/feedback-synthesis/SKILL.md` when the input is raw interviews, tickets, reviews, surveys, or sales notes. Do not create separate assumption-mapping or product-discovery skills; extend this one.

## Output

- Opportunity statement
- Evidence inventory and source status
- Assumption map with risk and confidence
- Opportunity tree
- Validation plan and decision rules
- PRD implication: confirmed MVP, optional, future, or stop

## Quality Bar

- The opportunity is expressed as a user/business problem, not a preselected feature.
- Every high-risk assumption has a proposed validation method.
- Stated-preference evidence is not treated as behavior evidence.
- Missing evidence downgrades readiness instead of being hidden.
- PRD scope includes only opportunities that are confirmed or explicitly accepted as assumption risk.
