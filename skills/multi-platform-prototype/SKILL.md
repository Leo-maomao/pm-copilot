---
name: multi-platform-prototype
description: Use when generating clickable local HTML prototypes for Web, H5, App, or Mini Program product scenarios, including UI and engineering annotations.
---

# Multi-Platform Prototype

## Goal

Generate a local clickable HTML prototype that matches the selected product platform and is useful for product review, UI reference, and engineering handoff.

## Platform Selection

- Web: desktop admin, SaaS, dashboards, tables, complex forms.
- H5: mobile browser, landing page, lightweight campaign or payment flow.
- App: native mobile flows, persistent app navigation, account or content scenarios.
- Mini Program: mini-program container, authorization, booking, ordering, lightweight forms.

## Workflow

1. Choose the platform based on PRD scenario.
2. Inspect existing demos, screenshots, routes, components, or design-system files when available.
3. Explain whether the prototype extends an existing surface or creates a new surface, and why.
4. Choose fidelity: high when enough visual context exists, mid by default, low only for exploratory work.
5. Create a single self-contained HTML file.
6. Include main path interaction.
7. Include relevant non-happy states.
8. Add page-scoped clickable annotations or annotation panels for UI, data, tracking, edge cases, and implementation notes.
9. Label the artifact as prototype-only, not production code.

## Output

- HTML prototype
- Platform rationale
- Fidelity rationale
- Annotation notes
- Existing-surface mapping and change summary
- Interaction notes
- Cross-platform differences if multiple prototypes are needed

## Quality Bar

- Opens locally without build tooling.
- No external assets are required.
- The platform container is obvious.
- Text fits inside the frame.
- The UI is polished enough to guide UI and engineering; avoid bare placeholders when product context exists.
- Main states, validation, errors, empty states, permission states, and success feedback are represented when relevant.
- If current product UI exists, the prototype preserves the existing structure and shows the new requirement as a delta.
- Annotations are tied to specific pages, components, or interactions, not mixed into one generic notes list.
