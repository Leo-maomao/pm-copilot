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
4. Summarize source quality: confirmed context, inferred context, stale or missing context.
5. Ask only high-impact clarification questions that materially change scope, metrics, solution direction, compliance, or release risk.
6. Split unknowns into `must answer before generation`, `can draft with stated assumption`, and `must confirm before development or launch`.
7. Stop before PRD generation if any `must answer before generation` question is unanswered.
8. Stop before a `Ready for engineering` PRD/UI delivery if any engineering-blocking `must confirm before development or launch` item is unanswered.
9. If the user explicitly asks for iterative evaluation or says to choose recommended options automatically, select conservative defaults instead of stopping, record each default and rationale, and keep unresolved risk visible in readiness.
10. Write explicit assumptions only after the user says to proceed with a draft or the unknown is low-impact.
11. Do not put the same unknown in more than one bucket.
12. If enough evidence exists to draft safely, proceed with assumptions instead of asking low-value questions.

## Output

- Problem statement
- Target users
- User scenarios
- Success criteria candidates
- Clarifying questions
- Current-state fit summary
- Source quality summary
- Assumption log
- Open decisions
- Recommended next agent

## Quality Bar

- Questions materially change scope, metrics, or solution direction.
- Assumptions are labeled and reasonable.
- Must-answer questions are resolved before downstream artifacts are generated.
- Draft assumptions and development/launch confirmations are clearly separated.
- Engineering-blocking confirmations are resolved before the PRD is marked ready for engineering.
- Question count stays small and each question has a clear reason.
- Output fits the current product context instead of assuming a greenfield product.
- The workflow remains usable when the PM has documents but no software repository.
- The PRD writer can proceed without guessing the core intent.
