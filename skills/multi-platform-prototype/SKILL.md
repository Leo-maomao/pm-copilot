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
3. Extract style facts from the current surface: navigation, tab bar, colors, spacing, typography, icons, card density, radius, shadows, and copy tone.
4. Explain whether the prototype extends an existing surface or creates a new surface, and why.
5. Choose fidelity: high when enough visual context exists, mid by default, low only for exploratory work.
6. Create a single self-contained HTML file.
7. Include main path interaction.
8. Include relevant non-happy states.
9. Build an annotation map before writing HTML: number, page/screen, UI element, logic note, interaction note, data or permission note, and tracking note when relevant.
10. Add numbered callout markers on the prototype surface and matching numbered notes in a right-side panel. Use compact markers such as `①`, `②`, and `③`.
11. Label the artifact as prototype-only, not production code.

## Output

- HTML prototype
- Platform rationale
- Fidelity rationale
- Annotation notes
- Existing-surface mapping and change summary
- Style-source summary
- Numbered annotation map
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
- Annotation notes are concrete enough for engineering. Examples: text length limit and ellipsis rule, tap result, hover tooltip, long-press behavior, disabled/loading/error behavior, data source, permission rule, and tracking event.
- Mini Program prototypes preserve the current mini-program chrome, tab bar, visual density, and component style when any current UI evidence is available.
