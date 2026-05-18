---
name: requirement-intake
description: Use when turning an ambiguous product request into clarified goals, users, scenarios, constraints, assumptions, and open questions before PRD generation.
---

# Requirement Intake

## Goal

Convert a vague product request into a usable brief without inventing business-critical facts.

## Workflow

1. Restate the request in one sentence.
2. Load relevant current-state product context, especially host project context in embedded mode.
3. Identify the target user, problem, desired outcome, platform, affected product area, and business goal.
4. Ask only high-impact clarification questions.
5. Split unknowns into `must answer now`, `can assume`, and `can decide later`.
6. Stop before PRD generation if any `must answer now` question is unanswered.
7. Write explicit assumptions only after the user says to proceed with assumptions or the unknown is low-impact.

## Output

- Problem statement
- Target users
- User scenarios
- Success criteria candidates
- Clarifying questions
- Current-state fit summary
- Assumption log
- Open decisions
- Recommended next agent

## Quality Bar

- Questions materially change scope, metrics, or solution direction.
- Assumptions are labeled and reasonable.
- Must-answer questions are resolved before downstream artifacts are generated.
- Embedded-mode output fits the current product instead of assuming a greenfield product.
- The PRD writer can proceed without guessing the core intent.
