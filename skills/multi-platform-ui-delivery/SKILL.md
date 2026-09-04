---
name: multi-platform-ui-delivery
description: Use when a PRD requirement needs frontend evidence or an isolated reconstructed figure.
---

# Frontend Evidence

## Goal

Attach verifiable frontend evidence to the PRD. Preserve the boundary in
`policies/role-boundary.md`: this skill never changes host product code and
does not produce a standalone UI delivery.

## Workflow

1. Inspect the smallest relevant read-only evidence set: runnable pages first, then routes, components, screenshots, and assets.
2. Capture a real runnable frontend state when it proves the PRD behavior.
3. When no runnable state exists, reconstruct only the confirmed state below the run folder and label the resulting image as `还原图示`.
4. When capture and reconstruction both fail, retain the controlled PRD placeholder and record why a future figure is required.
5. Record the figure path, source type, matching requirement ID, and limitation in `run-log.yaml`.

## Output

- A figure beside every PRD requirement that needs frontend presentation.
- Read-only source provenance or reconstruction provenance.
- A concise evidence limitation when no verified capture is available.

## Quality Bar

- A real screenshot is preferred over reconstruction; reconstruction is preferred over a placeholder.
- Figures are evidence for requirement logic, not an independently deliverable prototype.
- Every figure maps to one concrete requirement state and makes its source type clear.
