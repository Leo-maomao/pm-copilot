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
4. In repo-backed frontend products, run a style reuse pass before writing HTML: inspect the host app shell/root layout, global stylesheet or theme config, design-system components, affected route/page/component files, and relevant screenshots or demos; extract navigation, tab bar, colors, spacing, typography, icons, card density, radius, shadows, copy tone, and component states; prefer reusing host component hierarchy, tokens, and class patterns; record `style_evidence` in the run log.
5. Capture or record an existing UI visual baseline when possible: running host app screenshot, preview route, Storybook/demo screenshot, or user-provided image. Record `existing_ui_visual_baseline` with status, source, target, screenshot paths, comparison method, and limitation.
6. Explain whether the prototype extends an existing surface or creates a new surface, and why.
7. Run a design calibration pass after the host style is understood: choose layout variance, motion intensity, and visual density from the product surface, not from generic AI taste; operational tools should stay dense and scannable, while marketing/editorial pages may use more asymmetry and motion.
8. Choose fidelity: high when enough visual context exists, mid by default, low only for exploratory work.
9. Create a single self-contained HTML file with no CDN, remote font, remote script, or network image dependency.
10. Include a hidden `style-source-summary` comment or `data-style-source` attribute that names the host style evidence used.
11. Include main path interaction and make every visible primary control produce a visible state change.
12. Include relevant non-happy states.
13. Show eligible and ineligible user states when access depends on account, role, setup, plan, consent, location, or permission.
14. Label placeholder or unreviewed reference content as draft and avoid presenting it as approved final content.
15. Build an annotation map before writing HTML: number, page/screen, UI element, logic note, interaction note, data or permission note, and tracking note when relevant.
16. Add numbered callout markers on the prototype surface and matching numbered notes in a right-side panel. Default markers are small red circular badges with `annotation-marker`, `data-annotation-id`, and `data-annotation-placement="top-right"` placed at the annotated component's top-right corner. If that covers key text or controls, offset the badge just outside the same corner. The right panel uses matching circled numbers such as `①`, `②`, and `③`.
17. Label the artifact as prototype-only, not production code.
18. For personalization, ordering, layout, or preference features, show the edit mode, save/apply behavior, reset/default behavior, unavailable items, and sync or persistence failure state when relevant.
19. For Web prototypes, run a shell/responsive checklist before delivery: desktop navigation visible, page header visible, content density matches the host app, mobile breakpoint or responsive notes are present, touch target and mis-tap risks are considered for mobile Web, desktop regression risk is named, and visitor/signed-in/permission states are represented when relevant.
20. For public Web or SEO surfaces, annotate indexable content, metadata/structured-data expectations, noindex/private-page boundary, and cache/fallback behavior when relevant.
21. For Mini Program prototypes, run a chrome/page-level checklist before delivery: status or capsule area visible, primary tab pages use the existing tab bar style, secondary pages show page-header/back behavior, and ineligible/setup states are represented when relevant.
22. When validation scripts are available, run prototype visual validation or the delivery checks and record the evidence.

## Output

- HTML prototype
- Platform rationale
- Fidelity rationale
- Annotation notes
- Existing-surface mapping and change summary
- Style-source summary
- Style evidence: source files, reused host components, reused tokens or class patterns, prototype delta, limitations
- Existing UI visual baseline: status, source, target, screenshots, comparison method, limitation
- Design calibration summary: layout variance, motion intensity, visual density, and any deliberate anti-generic choices
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
- If host frontend source exists, the prototype reuses the current app shell, component density, design tokens, and class patterns; it must not use a generic new shell or unrelated palette unless the user requested a redesign.
- If an existing UI screenshot or rendered host app is available, the prototype uses it as a visual baseline for unchanged regions. If not available, the run log records the limitation and does not claim pixel parity.
- Design calibration improves the existing surface without overriding it. Do not import React, Next.js, Tailwind, Framer Motion, icon libraries, fonts, or external assets into the HTML prototype unless the artifact is intentionally production-code-oriented and dependencies are verified.
- Avoid generic AI UI signatures: unrelated hero layouts, equal 3-card feature rows, decorative gradient blobs, invented palettes, default avatars/names, fake round numbers, dead controls, and static success-only screens.
- Use complete interaction states: loading skeletons shaped like the final layout, empty states, inline form errors, disabled/loading/success feedback, and tactile active states where they match the host style.
- Prefer CSS Grid for stable multi-column layouts. Keep fixed-format elements dimensionally stable, collapse complex desktop layouts to one column on mobile, and avoid full-screen height assumptions that cause mobile viewport jumps.
- Use motion sparingly for prototypes. If motion is shown, animate only transform and opacity, avoid scroll listeners and layout-changing animations, and keep it secondary to reviewability.
- Annotations are tied to specific pages, components, or interactions, not mixed into one generic notes list.
- Annotation notes are concrete enough for engineering. Examples: text length limit and ellipsis rule, tap result, hover tooltip, long-press behavior, disabled/loading/error behavior, data source, permission rule, and tracking event.
- Mini Program prototypes preserve the current mini-program chrome, tab bar, visual density, and component style when any current UI evidence is available.
- Mini Program prototypes make page hierarchy explicit: primary-tab screens and secondary-page screens should use different chrome that matches the host route model.
- Preference and layout prototypes make reversible actions, unavailable modules, and persistence/sync failures visible instead of only showing the final customized state.
- Web prototypes preserve the app shell and include responsive behavior or explicit breakpoint notes, especially when the host product has both desktop and mobile usage.
- Responsive Web requirements specify breakpoint behavior, priority of information on small screens, touch target expectations, and desktop parity or intentional differences.
