---
name: requirement-intake
description: Use when turning an ambiguous product request into clarified goals, users, scenarios, constraints, assumptions, and open questions before PRD generation.
---

# Requirement Intake

## Goal

Convert a vague product request into a usable brief without inventing business-critical facts.

## Workflow

1. Restate the request in one sentence.
2. Load relevant current-state product context from the best available source: host repository, historical PRDs, specs, product docs, screenshots, analytics exports, support tickets, meeting notes, or direct user answers.
3. Identify the target user, problem, desired outcome, platform, affected product area, and business goal.
4. Ask only high-impact clarification questions.
5. Split unknowns into `must answer before generation`, `can draft with stated assumption`, and `must confirm before development or launch`.
6. Stop before PRD generation if any `must answer before generation` question is unanswered.
7. Write explicit assumptions only after the user says to proceed with assumptions or the unknown is low-impact.
8. Do not put the same unknown in more than one bucket.

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
- Draft assumptions and pre-development confirmations are clearly separated.
- Output fits the current product context instead of assuming a greenfield product.
- The workflow remains usable when the PM has documents but no software repository.
- The PRD writer can proceed without guessing the core intent.
