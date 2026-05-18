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
2. Explain the platform choice.
3. Choose fidelity: high when enough visual context exists, mid by default, low only for exploratory work.
4. Create a single self-contained HTML file.
5. Include main path interaction.
6. Include relevant non-happy states.
7. Add clickable annotations or an annotation panel for UI, data, tracking, edge cases, and implementation notes.
8. Label the artifact as prototype-only, not production code.

## Output

- HTML prototype
- Platform rationale
- Fidelity rationale
- Annotation notes
- Interaction notes
- Cross-platform differences if multiple prototypes are needed

## Quality Bar

- Opens locally without build tooling.
- No external assets are required.
- The platform container is obvious.
- Text fits inside the frame.
- The UI is polished enough to guide UI and engineering; avoid bare placeholders when product context exists.
- Main states, validation, errors, empty states, permission states, and success feedback are represented when relevant.
