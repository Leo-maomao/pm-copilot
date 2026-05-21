---
name: multi-platform-prototype
description: Use when generating clickable local HTML prototypes for Web, H5, App, or Mini Program product scenarios, including UI and engineering annotations.
---

# Multi-Platform Prototype

## Goal

Generate a local clickable HTML prototype that matches the selected product platform and is useful for product review, UI reference, and engineering handoff. In repo-backed UI work, the prototype should be an isolated mirror of the real product surface: read real frontend code and assets, keep host production files unchanged by default, and show only the requested feature as the new delta.

## Platform Selection

- Web: desktop admin, SaaS, dashboards, tables, complex forms.
- H5: mobile browser, landing page, lightweight campaign or payment flow.
- App: native mobile flows, persistent app navigation, account or content scenarios.
- Mini Program: mini-program container, authorization, booking, ordering, lightweight forms.

## Workflow

1. Choose the platform based on PRD scenario.
2. Load `artifacts/prototype-contract.md` when available.
3. Inspect existing demos, screenshots, routes, components, or design-system files when available.
4. In repo-backed frontend products, run a style reuse pass before writing HTML: inspect the host app shell/root layout, global stylesheet or theme config, design-system/component-library files, affected route/page/component files, local assets/icons, and relevant screenshots or demos; extract navigation, tab bar, colors, spacing, typography, icons, card density, radius, shadows, copy tone, and component states; prefer reusing host component hierarchy, tokens, and class patterns; record `style_evidence` in the run log.
5. For repo-backed prototype-only work, define the isolation boundary and artifact mode before writing UI: host production source is read-only unless the user explicitly asks for implementation or approves a prototype branch/source-preview change. Use `self_contained_html_from_host_code` for portable PM review; use `code_preview_route` or `storybook_or_demo` when near-online fidelity, exact iconography, or real component-library behavior is required. The HTML demo may emulate inspected components, tokens, assets, interactions, and mock data, but it must state fidelity limitations when exact host rendering is expected.
6. Build a source-to-demo map for repo-backed UI before drafting: target route or screen, page/component source files, reusable component-library components, token and class sources, local assets or icon sources, data shape or mock source, permission/state gates, and backend behavior represented by mock data plus annotations. Each mapped source needs a visible `prototype_representation`. Record this under `isolated_ui_prototype` and `style_evidence`.
7. Split the repo-backed UI prototype into two layers: `baseline_layer` reconstructs unchanged product UI from the host repository and visual baseline; `delta_layer` contains only new or changed feature UI, marked with numbered callouts and explanation dialogs.
8. Keep annotation markers and prototype controls from degrading the baseline layer: they must not resize, crop, recolor, or cover critical unchanged UI. If a marker is attached to an unchanged component, the note must distinguish the baseline component from the new delta behavior.
9. Capture or record an existing UI visual baseline when possible: running host app screenshot, preview route, Storybook/demo screenshot, or user-provided image. Record `existing_ui_visual_baseline` with status, source, target, screenshot paths, comparison method, and limitation.
10. Explain whether the prototype extends an existing surface or creates a new surface, and why.
11. Run a design calibration pass after the host style is understood: choose layout variance, motion intensity, and visual density from the product surface, not from generic AI taste; operational tools should stay dense and scannable, while marketing/editorial pages may use more asymmetry and motion.
12. Choose fidelity: high when enough visual context exists, mid by default, low only for exploratory work. Repo-backed work cannot claim high or pixel-level parity without required style evidence and baseline evidence.
13. Create a single self-contained HTML file with no CDN, remote font, remote script, or network image dependency.
14. Include a hidden `style-source-summary` comment or `data-style-source` attribute that names the host style evidence used.
15. Include main path interaction and make every visible primary control produce a visible state change.
16. Include relevant non-happy states.
17. Show eligible and ineligible user states when access depends on account, role, setup, plan, consent, location, or permission.
18. Check access-state coherence before delivery: logged-out, guest, and no-permission controls must not reveal signed-in-only profile data, user IDs, account-management actions, sync actions, logout actions, or privileged navigation.
19. Label placeholder or unreviewed reference content as draft and avoid presenting it as approved final content.
20. Build an annotation map before writing HTML: number, page/screen, UI element, logic note, interaction note, data or permission note, and tracking note when relevant.
21. Add numbered callout markers on the prototype surface and matching notes in marker-triggered dialogs. Default markers are small red circular badges with `annotation-marker`, `data-annotation-id`, and `data-annotation-placement="top-right"` placed at a safe top-right spot on the annotated component. Do not use negative offsets inside clipping containers, do not let markers force labels to wrap, and do not cover key controls. Marker visual style must not change when opened. Clicking a marker opens a small local `annotation-dialog` popover beside that marker; clicking the same marker again closes it. It must not open a full-screen/global modal or backdrop. A draggable top-right `annotation-toggle` with `data-draggable="true"` opens an `annotation-list` overlay for all markers in the current page/state.
22. Label the artifact as prototype-only, not production code.
23. For personalization, ordering, layout, or preference features, show the edit mode, save/apply behavior, reset/default behavior, unavailable items, and sync or persistence failure state when relevant.
24. For Web prototypes, run a shell/responsive checklist before delivery: desktop navigation visible, page header visible, content density matches the host app, mobile breakpoint or responsive notes are present, touch target and mis-tap risks are considered for mobile Web, desktop regression risk is named, and visitor/signed-in/permission states are represented when relevant.
25. For public Web or SEO surfaces, annotate indexable content, metadata/structured-data expectations, noindex/private-page boundary, and cache/fallback behavior when relevant.
26. For Mini Program prototypes, run a chrome/page-level checklist before delivery: status or capsule area visible, primary tab pages use the existing tab bar style, secondary pages show page-header/back behavior, and ineligible/setup states are represented when relevant.
27. When validation scripts are available, run prototype visual validation or the delivery checks and record the evidence.

## Output

- HTML prototype
- Platform rationale
- Fidelity rationale
- Annotation notes
- Existing-surface mapping and change summary
- Isolation boundary and source-to-demo map
- Baseline layer and delta layer summary
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
- Access-gated controls do not leak authenticated account data or actions from logged-out, guest, or no-permission states.
- Placeholder or unreviewed content is visibly labeled and does not look launch-approved.
- If current product UI exists, the prototype preserves the existing structure and shows the new requirement as a delta.
- If host frontend source exists, the prototype reuses the current app shell, component density, design tokens, and class patterns; it must not use a generic new shell or unrelated palette unless the user requested a redesign.
- Repo-backed style evidence must name real host files/assets and explain how inspected components are represented in the prototype. Empty `source_files`, generic component names, or a style-source summary without a source-to-demo map are not complete.
- When exact online fidelity is the user goal, prefer a host-rendered preview route/story/demo using the real component library instead of hand-recreating icons and components in standalone HTML. If source mutation is not allowed, clearly mark the self-contained HTML parity claim as limited.
- Repo-backed prototype-only work leaves host production files unchanged unless the user explicitly requested production-oriented implementation.
- Backend-dependent behavior is represented with coherent mock data, loading/empty/error/permission states, and annotations that name the expected API or data contract when known.
- If an existing UI screenshot or rendered host app is available, the prototype uses it as a visual baseline for unchanged regions. If not available, the run log records the limitation and does not claim pixel parity.
- Keep the product surface full width. Do not reserve a persistent annotation board or shrink the layout for notes; marker notes live in local popovers beside the marker, can be toggled closed by clicking the marker again, and the top-right list overlay is only for the current page/state note list.
- For many pages, many states, or content beyond one screen, preserve the host product's real scroll behavior and state structure. Do not place the product inside an artificial fixed-height frame that clips dialogs or long content.
- Prototype controls must be live. Before delivery, check that JavaScript parses, primary buttons visibly change state, annotation markers open dialogs, the annotation toggle opens the current-state list, the toggle can be dragged away from top-right controls, and compact tabs or segmented controls do not fold text because of annotations.
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
