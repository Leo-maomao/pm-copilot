# Prototype Contract

Prototypes are local HTML artifacts used for product review, UI reference, and engineering handoff. They are not production implementation, but they should be concrete enough to guide implementation.

If a current demo, screenshot, route, component, or design system is available, the prototype must extend that existing surface. It should show what changes, what stays the same, and where the new requirement fits. Do not create a new product shell unless the user explicitly asks for a redesign or no current surface exists.

Visual style fit is part of the contract, not a polish step. When current UI evidence exists, match the existing navigation structure, platform chrome, tab bar, typography scale, spacing rhythm, color tokens, icon style, card density, border radius, shadows, and copy tone before adding the new requirement. Record the style sources used and the intended delta. If no style source is available and the user expects a product-specific prototype, ask for a screenshot, demo, route, or design reference before creating a mid- or high-fidelity prototype.

## Fidelity

Choose the highest useful fidelity the available context supports:

- `high`: use when brand, layout, component, content, and interaction direction are known.
- `mid`: default for most requirements; polished layout, realistic copy, clear components, and complete states.
- `low`: use only when the problem is still exploratory or visual direction is intentionally unknown.

Even low-fidelity prototypes must be clean, clickable, and implementation-oriented. Avoid bare placeholder wireframes when UI or interaction direction is available.

## Platform Selection

| Platform | Use When | Required Simulation |
|---|---|---|
| Web | Desktop admin, SaaS, dashboards, content management | Desktop viewport, sidebar or top navigation, tables/forms |
| H5 | Mobile browser, landing pages, lightweight checkout, campaigns | Mobile browser frame, URL/header hint, single-column layout |
| App | Native mobile product flows | App frame, top bar, bottom tabs or native navigation |
| Mini Program | Mini-program style flows | Status bar, capsule area, current mini-program navigation, existing tab bar style, page stack feel, authorization and lightweight forms |

## Required Interaction

- Main path must be clickable.
- At least one non-happy state must be represented when relevant.
- Buttons and links must have visible outcomes.
- Copy must fit on mobile-sized frames.
- The prototype must include realistic screen states: loading, empty, error, permission, confirmation, success, or rollback where relevant.
- If access depends on account, role, eligibility, plan, location, consent, or setup state, show the eligible and ineligible states or state why one is not relevant.
- If the feature contains unreviewed reference or regulated content, label it as placeholder or draft in the prototype and do not present it as approved final content.
- Important controls should expose annotations through clickable hotspots, side panels, tooltips, or inline markers.
- Annotation state should update by page or screen, so reviewers can tell which note belongs to which UI element.
- Numbered callouts should not cover critical copy or controls. Use compact markers such as `①`, `②`, and `③` beside or above the element being explained.

## Required Annotations

Include annotations for:

- UI intent and component behavior.
- Data fields, validation, and empty/error states.
- Tracking hooks when relevant.
- Permission, privacy, payment, compliance, or operational notes.
- Engineering handoff notes and known assumptions.

Annotation rules:

- The default annotation layout is left-side prototype, right-side annotation panel.
- Each page or screen has its own annotation group in the right-side panel.
- Each annotation references a concrete UI element, state, or transition and uses the same visible number as the callout marker in the prototype, for example `①`.
- Annotation text must be implementation-grade and specific. Include details such as text length limits and ellipsis behavior, tap/hover/long-press behavior, empty/error state handling, permission rules, data source, and tracking hook when relevant.
- Long annotation content should be summarized in the panel and expanded by click, hover, or disclosure. Do not dump every page's notes into one long generic paragraph.
- Cross-page notes belong in a separate `Global notes` group.
- Annotations must be reachable from the prototype UI, not only listed beside it.
- A generic implementation-note card without numbered markers is not sufficient.

## Output Rule

Generate a single self-contained `.html` file unless the task explicitly asks for multiple platform prototypes.

The HTML must clearly state that it is a prototype and not production code, but it should be structured and styled to a standard that UI and engineering can use directly as reference.
