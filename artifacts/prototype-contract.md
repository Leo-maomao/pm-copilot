# Prototype Contract

Prototypes are local HTML artifacts used for product review, UI reference, and engineering handoff. They are not production implementation, but they should be concrete enough to guide implementation.

If a current demo, screenshot, route, component, or design system is available, the prototype must extend that existing surface. It should show what changes, what stays the same, and where the new requirement fits. Do not create a new product shell unless the user explicitly asks for a redesign or no current surface exists.

Visual style fit is part of the contract, not a polish step. When current UI evidence exists, match the existing navigation structure, platform chrome, tab bar, typography scale, spacing rhythm, color tokens, icon style, card density, border radius, shadows, and copy tone before adding the new requirement. Record the style sources used and the intended delta. If no style source is available and the user expects a product-specific prototype, ask for a screenshot, demo, route, or design reference before creating a mid- or high-fidelity prototype.

## Repo-Backed Isolation Policy

When PM Copilot is embedded in a real product repository, prototype-only UI work should be isolated from production implementation by default. The agent may read host frontend code, styles, assets, screenshots, stories, routes, and mock/API shapes. It must not modify production flows unless the user explicitly asks for production-oriented implementation, but an exact online/source-code parity request authorizes an isolated preview route, story, demo entry, or preview-only screen that renders real host components.

The expected repo-backed artifact mode depends on the fidelity target. For exact UI parity, exact icons, exact component-library behavior, or "as if added in source code" rendering, use `source_delta_patch`: import/render the real frontend components, styles, assets, and platform chrome as the baseline, then add the new requirement only in isolated preview delta files. Platform-specific source-rendered modes are `code_preview_route`, `storybook_or_demo`, `mini_program_preview`, and `app_preview_screen`. Use standalone HTML fallback only when the user explicitly asks for portable PM review or when source rendering was attempted and blocked by concrete command, browser, simulator, dependency, or preview-surface evidence; mark source-rendered fidelity as limited. Backend-dependent behavior should be represented with coherent mock data, loading/empty/error/permission states, and annotations that name the expected data contract or API behavior when known.

## Two-Layer UI Prototype Model

Repo-backed UI prototypes have two distinct layers:

- `baseline_import`: the original product surface imported or rendered from host repository code, assets, tokens, screenshots, and component behavior. This layer should be source-owned, not rewritten, and should not introduce new visual language, explanatory copy, or prototype-only UI inside unchanged product regions.
- `delta_patch`: the requested new or changed feature behavior, implemented in preview-only wrapper/story/demo/page/screen files or mock state. This layer must be visibly identifiable through numbered markers, marker-triggered explanation dialogs, and the current-state annotation panel. Delta annotations should explain UI intent, interaction, data/API assumptions, backend simulation, permission/state behavior, tracking, and edge cases.

Multi-turn prototype work should preserve the same preview surface and append each new user request to `delta_patch.multi_turn_change_log`. The agent should continue from `delta_patch.next_delta_anchor` rather than re-creating or hand-drawing the baseline.

The prototype should preserve baseline geometry and add the delta in place. Annotation controls must not resize, crop, recolor, or otherwise degrade the baseline layer. If a marker is needed near an unchanged component only to explain how the new feature attaches to it, the annotation must state that the underlying component is baseline UI and identify the new delta separately.

Before writing repo-backed UI, record `host_frontend_inventory`: platform source kind, frontend entry files, route/page/screen files, component-library files, style token/global style files, icon/asset sources, data/mock sources, render command, and preview surface. Use the requirement or target surface as an inventory query when available so the relevant route/component is ranked ahead of unrelated repository files. For Web/H5 inspect routes/pages/components/styles/assets; for Mini Program/Taro/uni-app inspect app/page config, page files, custom components, WXSS/ACSS/TTSS or equivalent styles, and assets; for App inspect React Native/Flutter/native screen, widget/component, theme/style, and asset sources. If these sources are unavailable and the user expects real-product UI, stop for the missing host path or preview instead of fabricating a shell.

Before writing repo-backed HTML or source-rendered preview code, record a source-to-demo map: target route or screen, source page files, reused component files, token/class/style sources, asset/icon sources, data or mock sources, permission/state gates, backend simulation method, and limitations. Record the host mutation policy, artifact mode, preview files changed, `baseline_import`, `delta_patch`, and parity claim under `isolated_ui_prototype` in the run log. If these sources are unavailable, the prototype must be marked `degraded` or `mid` at most, and it must not claim exact, 1:1, source-level, or pixel-level parity.

For repo-backed frontend products, style evidence is required. Inspect the host app shell or root layout, global stylesheet or theme config, design-system/component-library files, affected route/page/component files, local assets/icons, and relevant screenshots or demos. When exact fidelity matters, render those host components directly in an isolated preview. A self-contained HTML file may emulate inspected components and tokens only when the user explicitly requested portability or source rendering was attempted and blocked by a concrete command, browser, simulator, dependency, or preview-surface failure; production read-only policy is not a blocker because isolated preview files are allowed. Record concrete source files/assets, reused components, reused tokens or class patterns, icon/asset sources, intended delta, and limitations in `run-log.yaml` under `style_evidence`. Record `source_to_demo_mapping` entries with non-empty source and prototype representation values so the visual source can be audited. Add a hidden `style-source-summary` comment or `data-style-source` attribute in the HTML when HTML is generated.

Repo-backed prototypes should use an existing UI visual baseline whenever possible. Valid sources include a screenshot from the running host app, a preview route, Storybook/demo, existing screenshot asset, or user-provided image. Record `existing_ui_visual_baseline` with status, source, target page or component, screenshot paths when captured, comparison method, and limitation. If the host frontend is renderable and a standalone HTML fallback is used, a missing baseline must cite an explicit portable-artifact request or concrete attempted-render/browser/setup failure. If no baseline can be captured, say so and do not claim pixel parity.

Design calibration is a secondary pass after style evidence, not permission to redesign the host product. Choose visual density, layout variance, and motion intensity from the product surface and scenario. Operational tools should remain dense, predictable, and scannable; editorial or marketing surfaces may use more asymmetry and motion. Avoid generic AI UI signatures such as unrelated hero sections, equal 3-card feature rows, decorative gradient blobs, invented palettes, default avatars or names, fake round numbers, dead controls, and success-only screens.

## Fidelity

Choose the highest useful fidelity the available context supports:

- `high`: use when brand, layout, component, content, and interaction direction are known.
- `mid`: default for most requirements; polished layout, realistic copy, clear components, and complete states.
- `low`: use only when the problem is still exploratory or visual direction is intentionally unknown.

For repo-backed UI work, `high` requires enough inspected source evidence to mirror the host app shell, affected page, core components, tokens, assets, and state model. A prototype may not claim 1:1 or pixel-level parity unless an existing UI visual baseline exists and unchanged regions were compared or explicitly reviewed against it.

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
- Loading states should match the final layout shape where possible instead of using generic spinners; form errors should be inline and close to the field.
- Multi-page or multi-state prototypes should let reviewers switch state without shrinking the product surface. Use a lightweight overlay control outside the product layout when needed.
- Long pages and modal dialogs must preserve real scrolling behavior. Use viewport-based max heights and internal scroll only when the host product does; do not clip important fields, buttons, or bottom content.
- If access depends on account, role, eligibility, plan, location, consent, or setup state, show the eligible and ineligible states or state why one is not relevant.
- Access-state behavior must be internally coherent. A logged-out, guest, or no-permission entry point must not reveal authenticated profile data, user IDs, account-management links, sync actions, logout actions, or privileged navigation when interacted with.
- If the feature contains unreviewed reference or regulated content, label it as placeholder or draft in the prototype and do not present it as approved final content.
- Important controls should expose annotations through clickable markers or hotspots tied to the concrete UI element being explained.
- Annotation state should update by page or screen, so reviewers can tell which note belongs to which UI element.
- Numbered callouts should not cover critical copy or controls. Place compact markers at the annotated component's top-right corner by default; offset them just outside that same corner when needed to avoid covering key content.
- The default callout shape is a small red circular badge using `annotation-marker`, `data-annotation-id`, and `data-annotation-placement="top-right"` on the prototype surface. Place badges in a safe top-right spot that is visible, not clipped by `overflow: hidden`, and not causing labels or controls to wrap. Marker badges and matching number badges inside marker dialogs and the right-side page annotation panel must use the same red background, white text, and no border line. Visual badges must contain plain digits such as `1`, `2`, and `3`, not circled numeral glyphs or nested badge content. Marker visual style must not change after click. Clicking a marker opens a small local `annotation-dialog` popover beside that marker with the matching number; clicking the same marker again closes it. Marker clicks must not open a full-screen/global modal, backdrop, or centered note dialog.
- A draggable annotation floating control with `data-draggable="true"` should show only `注释` in Chinese outputs or `Notes` in English outputs. Clicking it hides the floating control and opens an `annotation-list` panel from the right edge. The panel must fill viewport height, show annotations for the current page/state, and restore the floating control when closed.
- If page or state switching controls are needed, keep them in a stable fixed position outside the product layout so they do not look like abrupt product UI.

## Required Annotations

Include annotations for:

- UI intent and component behavior.
- Data fields, validation, and empty/error states.
- Tracking hooks when relevant.
- Permission, privacy, payment, compliance, or operational notes.
- Engineering handoff notes and known assumptions.

Annotation rules:

- The default annotation layout keeps the prototype full-width and uses marker-triggered local popovers beside the relevant marker. Do not add a full-screen/global marker modal unless the user explicitly asks for that annotation style.
- Each page or screen has its own annotation group in the right-side full-height `annotation-list` panel.
- Each annotation references a concrete UI element, state, or transition and uses the same visible plain digit as the callout marker in the prototype, for example `2`.
- Each prototype marker and dialog/list note must share a stable annotation ID, for example `data-annotation-id="2"` on the UI badge and the matching `2` note in the marker dialog or current-state annotation panel. UI badges should also declare `data-annotation-placement="top-right"` unless a documented exception is needed.
- Annotation text must be implementation-grade and specific. Include details such as text length limits and ellipsis behavior, tap/hover/long-press behavior, empty/error state handling, permission rules, data source, and tracking hook when relevant.
- Long annotation content should be summarized in marker dialogs and expanded through the `annotation-list` overlay. Do not dump every page's notes into one long generic paragraph.
- Cross-page notes belong in a separate `Global notes` group.
- Annotations must be reachable from the prototype UI, not only listed beside it.
- A generic implementation-note card without numbered markers is not sufficient.
- Prototype JavaScript must parse without browser page errors. If script syntax breaks, buttons and annotation interactions are considered failed even when the HTML structure looks complete.

## Output Rule

Generate a single self-contained `.html` file unless the task explicitly asks for multiple platform prototypes or the repo-backed fidelity target requires a source-rendered preview route/story/demo/page/screen.

The HTML must clearly state that it is a prototype and not production code, but it should be structured and styled to a standard that UI and engineering can use directly as reference.

For repo-backed prototype-only work, self-contained HTML is acceptable when portability matters. It may emulate inspected host components, token values, and local assets, but it cannot guarantee exact parity for icons, fonts, rendered component internals, browser-specific CSS, platform chrome, or runtime state. If the user requests exact online/source-level fidelity, or the task would visibly suffer from hand-recreated icons/components, use a source-rendered preview mode after recording the mutation boundary and changed preview files. Production flows remain untouched unless production implementation is explicitly requested.

Prototype files must not depend on external scripts, fonts, CDNs, network images, or remote CSS. If a visual asset is necessary, embed it, use an existing local asset reference only when the host project path is stable, or explain the limitation in the PRD and run log.

Do not import React, Next.js, Tailwind, Framer Motion, icon libraries, fonts, or remote assets into a prototype artifact unless the user explicitly asks for production-oriented code and the dependency is verified in the host project. For local HTML prototypes, express any motion with lightweight CSS using `transform` and `opacity`; avoid scroll listeners, layout-changing animation, and anything that makes screenshot validation unstable.

## Browser Visual Validation

Validate generated prototypes with:

```bash
python3 scripts/validate_prototype_visual.py outputs/<run-id>
```

The check should capture at least desktop/default and constrained/mobile screenshots when relevant, confirm the view is not blank, run DOM smoke checks for visible text, interactive controls, horizontal overflow, console errors, page errors, and access-state leakage, and compare against visual baselines when the run is part of a regression suite. When multiple platform prototypes exist, the command validates all supported prototype files unless `--prototype <file>` is supplied. Store screenshots and `visual-report.json` under `outputs/<run-id>/visual-review/`. If Playwright or browser tooling is unavailable, run or guide `python3 scripts/setup_visual_validation.py` first; if a system browser launch fails, use the bundled/default Chromium fallback before recording a limitation. Record a skipped check only when setup fails, browser launch is forbidden, or the user declines installation.

For final delivery, prefer the delivery orchestrator so HTML parsing and output validation are recorded with the visual evidence:

```bash
python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>
```
