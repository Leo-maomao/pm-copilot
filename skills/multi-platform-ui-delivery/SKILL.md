---
name: multi-platform-ui-delivery
description: Use when creating reviewable UI flows, annotated prototypes, visual evidence, or platform-specific specifications without modifying host product code.
---

# Multi-Platform UI Delivery

## Goal

Turn product intent and available UI evidence into a review artifact that design and engineering can implement. Preserve the boundary in `policies/role-boundary.md`: this skill does not create or alter host product implementation.

## Workflow

1. Classify the requested platform, scenario, review purpose, and required decisions.
2. Gather the smallest relevant evidence set: user-provided references first, then read-only source, screenshots, components, or existing rendered screens when available.
3. Separate observed behavior from proposed behavior, assumptions, and open questions.
4. Describe the main flow, loading, empty, error, permission, and success states that matter for the request.
5. Produce an annotated portable prototype, flow, or specification under `outputs/<run-id>/`; do not add preview routes, delta files, or product code to the host repository.
6. Validate the review artifact and record evidence, limitations, and receiving owners in `run-log.yaml`.

## Output

- Platform and scenario scope.
- Evidence inventory and fidelity statement.
- Annotated UI artifact or structured UI specification.
- Interaction, state, accessibility, and edge-case notes.
- Acceptance criteria, open questions, and engineering/design handoff items.

## Quality Bar

- The artifact remains a PM review deliverable, never a claim of implementation.
- Existing UI evidence informs the artifact without being silently copied or rewritten in host source.
- Every proposed behavior has a visible status: proposed, inferred, confirmed, or unknown.
- The artifact supports review on the selected platform and does not rely on remote assets when delivered as portable HTML.
