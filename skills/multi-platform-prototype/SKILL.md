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
2. Load `artifacts/prototype-contract.md` when available.
3. Inspect existing demos, screenshots, routes, components, or design-system files when available.
4. Extract style facts from the current surface: navigation, tab bar, colors, spacing, typography, icons, card density, radius, shadows, and copy tone.
5. Explain whether the prototype extends an existing surface or creates a new surface, and why.
6. Choose fidelity: high when enough visual context exists, mid by default, low only for exploratory work.
7. Create a single self-contained HTML file with no CDN, remote font, remote script, or network image dependency.
8. Include main path interaction and make every visible primary control produce a visible state change.
9. Include relevant non-happy states.
10. Show eligible and ineligible user states when access depends on account, role, setup, plan, consent, location, or permission.
11. Label placeholder or unreviewed reference content as draft and avoid presenting it as approved final content.
12. Build an annotation map before writing HTML: number, page/screen, UI element, logic note, interaction note, data or permission note, and tracking note when relevant.
13. Add numbered callout markers on the prototype surface and matching numbered notes in a right-side panel. Use compact markers such as `①`, `②`, and `③`.
14. Label the artifact as prototype-only, not production code.
15. For personalization, ordering, layout, or preference features, show the edit mode, save/apply behavior, reset/default behavior, unavailable items, and sync or persistence failure state when relevant.
16. For Web prototypes, run a shell/responsive checklist before delivery: desktop navigation visible, page header visible, content density matches the host app, mobile breakpoint or responsive notes are present, touch target and mis-tap risks are considered for mobile Web, desktop regression risk is named, and visitor/signed-in/permission states are represented when relevant.
17. For public Web or SEO surfaces, annotate indexable content, metadata/structured-data expectations, noindex/private-page boundary, and cache/fallback behavior when relevant.
18. For Mini Program prototypes, run a chrome/page-level checklist before delivery: status or capsule area visible, primary tab pages use the existing tab bar style, secondary pages show page-header/back behavior, and ineligible/setup states are represented when relevant.
19. When validation scripts are available, run prototype visual validation or the delivery checks and record the evidence.

## Output

- HTML prototype
- Platform rationale
- Fidelity rationale
- Annotation notes
- Existing-surface mapping and change summary
- Style-source summary
- Numbered annotation map
- Permission and fallback state notes
- Interaction notes
- Cross-platform differences if multiple prototypes are needed
- Visual validation result or skipped reason

## Quality Bar

- Opens locally without build tooling.
- No external assets are required.
- The platform container is obvious.
- Text fits inside the frame.
- The UI is polished enough to guide UI and engineering; avoid bare placeholders when product context exists.
- Main states, validation, errors, empty states, permission states, and success feedback are represented when relevant.
- Primary controls are not dead ends; every click either changes state or is clearly disabled.
- Text, callouts, and controls do not overlap at desktop or mobile-sized widths.
- Access-gated surfaces include eligible and ineligible states or an explicit not-applicable note.
- Placeholder or unreviewed content is visibly labeled and does not look launch-approved.
- If current product UI exists, the prototype preserves the existing structure and shows the new requirement as a delta.
- Annotations are tied to specific pages, components, or interactions, not mixed into one generic notes list.
- Annotation notes are concrete enough for engineering. Examples: text length limit and ellipsis rule, tap result, hover tooltip, long-press behavior, disabled/loading/error behavior, data source, permission rule, and tracking event.
- Mini Program prototypes preserve the current mini-program chrome, tab bar, visual density, and component style when any current UI evidence is available.
- Mini Program prototypes make page hierarchy explicit: primary-tab screens and secondary-page screens should use different chrome that matches the host route model.
- Preference and layout prototypes make reversible actions, unavailable modules, and persistence/sync failures visible instead of only showing the final customized state.
- Web prototypes preserve the app shell and include responsive behavior or explicit breakpoint notes, especially when the host product has both desktop and mobile usage.
- Responsive Web requirements specify breakpoint behavior, priority of information on small screens, touch target expectations, and desktop parity or intentional differences.
