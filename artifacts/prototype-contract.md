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
| Web | Desktop products, SaaS, dashboards, content management, user account tools, financial tools | Desktop viewport, sidebar or top navigation, responsive behavior, tables/forms/cards, authenticated and unauthenticated states when relevant |
| H5 | Mobile browser, landing pages, lightweight checkout, campaigns | Mobile browser frame, URL/header hint, single-column layout |
| App | Native mobile product flows | App frame, top bar, bottom tabs or native navigation |
| Mini Program | Mini-program style flows | Status bar, capsule area, current mini-program navigation, existing tab bar style, page stack feel, authorization and lightweight forms |
| Browser extension | Extension popup, content script, toolbar action, side panel | Extension frame or popup dimensions, permission boundary, logged-in/logged-out state, cache/offline state |

For Mini Program prototypes, page level must be visible and consistent with the host product. Primary tab pages should show the current tab bar and avoid secondary `page-header` chrome; secondary pages should show `page-header` or back behavior and should not show the primary tab bar unless the host product does. The top status/capsule region should be represented so reviewers can judge Mini Program fit rather than a generic mobile web frame.

For Web prototypes, the product shell must be visible and consistent with the host product. Show the relevant desktop navigation model, page header, content density, responsive/mobile breakpoint behavior, and access states such as visitor, signed-in, permission-denied, or account-required when those states affect the feature. Do not present a Web feature as an isolated card floating outside the existing app shell unless the host product actually uses that pattern.

Responsive Web prototypes should make small-screen priorities explicit: which metrics or actions stay visible, which content collapses, minimum touch-target expectations, and what must remain unchanged on desktop.

For browser extension prototypes, show the extension container instead of a full Web app shell when the requested surface is the popup or side panel. Annotate extension permissions, account/session handoff, storage/cache behavior, and degraded state when the main site session expires.

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

Prototype files must not depend on external scripts, fonts, CDNs, network images, or remote CSS. If a visual asset is necessary, embed it, use an existing local asset reference only when the host project path is stable, or explain the limitation in the PRD and run log.

## Browser Visual Validation

Validate generated prototypes with:

```bash
python3 scripts/validate_prototype_visual.py outputs/<run-id>
```

The check should capture at least desktop/default and constrained/mobile screenshots when relevant, confirm the view is not blank, and compare against visual baselines when the run is part of a regression suite. When multiple platform prototypes exist, the command validates all supported prototype files unless `--prototype <file>` is supplied. Store screenshots and `visual-report.json` under `outputs/<run-id>/visual-review/`. If Playwright or browser tooling is unavailable, run or guide `python3 scripts/setup_visual_validation.py` first; if a system browser launch fails, use the bundled/default Chromium fallback before recording a limitation. Record a skipped check only when setup fails, browser launch is forbidden, or the user declines installation.

For final delivery, prefer the delivery orchestrator so HTML parsing and output validation are recorded with the visual evidence:

```bash
python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>
```
