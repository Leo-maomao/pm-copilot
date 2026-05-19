---
name: user-stories
description: Use when converting product requirements into user stories, jobs-to-be-done, scenarios, and role-goal-benefit statements.
---

# User Stories

## Goal

Express requirements from the user's point of view so design, engineering, and QA understand intent.

## Workflow

1. Identify actor, goal, context, trigger, constraint, and expected value.
2. Assign stable story IDs such as `US-01` and trace them to requirement or function IDs when available.
3. Write stories using `As a <user>, I want <capability>, so that <outcome>`.
4. Add jobs-to-be-done only when they clarify motivation better than a role-goal-benefit story.
5. Add scenario notes for entry point, trigger, completion, and important blocked or exception states.
6. Connect each story to measurable product outcomes where possible.
7. Separate user stories from implementation tasks, UI component requests, and optional future ideas.

## Output

- User story list with ID, actor, capability, outcome, priority, and source requirement
- Scenario table
- Priority signal
- Linked requirement or metric

## Quality Bar

- Each story has a clear actor and outcome.
- Stories are not implementation tasks.
- Stories connect to PRD scope.
- Stories do not create new MVP scope that was not confirmed elsewhere.
- Priority reflects user or business impact, not writing order.
