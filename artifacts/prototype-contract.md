# UI Delivery Contract (Legacy Prototype Contract)

UI deliverables are annotated artifacts used for product review, UI reference, and engineering handoff. In repo-backed products, the default deliverable is source-backed: import or render the original frontend code as the baseline, then add only the requested change through an isolated preview/delta layer. Standalone HTML is a compatibility mode for no-source work, explicit portable HTML requests, explicit redesign/greenfield requests, or concrete source-rendering blockers.

Legacy file and script names still use "prototype" for compatibility (`prototype-<platform>.html`, `validate_prototype_visual.py`, `isolated_ui_prototype`). Treat that word as a legacy container name, not permission to hand-write a fake UI.

If a current demo, screenshot, route, component, design system, or frontend source exists, the UI deliverable must extend that existing surface. It should show what changes, what stays the same, and where the new requirement fits. Do not create a new product shell unless the raw request explicitly asks to redesign/rebuild/from-scratch/stop reusing the original UI or no current surface exists.

Visual style fit is part of the contract, not a polish step. When current UI evidence exists, match the existing navigation structure, platform chrome, tab bar, typography scale, spacing rhythm, color tokens, icon style, card density, border radius, shadows, and copy tone before adding the new requirement. Record the style sources used and the intended delta. If no style source is available and the user expects a product-specific UI deliverable, ask for a screenshot, demo, route, or design reference before creating a mid- or high-fidelity artifact.

When the user supplies a screenshot, generated concept image, mockup, or cropped UI image as the target, the UI deliverable must run Image Reference Reconstruction Mode from `skills/multi-platform-prototype/SKILL.md`. Record the reference source, exact dimensions, intended viewport, role of the image, visual inventory, asset decisions, screenshot comparison method, mismatches fixed, and remaining fidelity limits. The latest supplied reference image is the visual source of truth for the requested surface or delta, while repo-backed source-first baseline rules still apply when host frontend source exists.

## Repo-Backed Isolation Policy

When PM Copilot is embedded in a real product repository, UI-delivery-only work should be isolated from production implementation by default. The agent may read host frontend code, styles, assets, screenshots, stories, routes, and mock/API shapes. It must not modify production flows unless the user explicitly asks for production-oriented implementation, but frontend source availability authorizes an isolated preview route, story, demo entry, or preview-only screen that renders real host components.

The expected repo-backed artifact mode depends first on source availability. If host frontend source and a preview surface exist, use `source_delta_patch` by default: import/render the real frontend components, styles, assets, and platform chrome as the baseline, then add the new requirement only in isolated preview delta files. This does not require the user to say exact UI parity. Platform-specific source-rendered modes are `code_preview_route`, `storybook_or_demo`, `mini_program_preview`, and `app_preview_screen`. Use standalone HTML fallback only when the user's raw request explicitly asks for portable/standalone/HTML review, explicitly asks to redesign/rebuild/from-scratch/stop reusing the original UI, or when source rendering was attempted and blocked by concrete command, browser, simulator, dependency, or preview-surface evidence; "only generate a prototype" means review scope only and is not a standalone HTML or greenfield request. Mark standalone fallback fidelity as limited. Backend-dependent behavior should be represented with coherent mock data, loading/empty/error/permission states, and annotations that name the expected data contract or API behavior when known.

A source-backed preview may be opened through a local dev URL, but the deliverable is not just that URL. Record the command, route/story/screen, changed preview/delta files, validation evidence, and any setup limits. If the user asks for direct HTML and exact source parity is not required, generate standalone compatibility HTML; if exact parity depends on host components, explain that HTML would be fidelity-limited.

## Two-Layer UI Delivery Model

Repo-backed UI deliverables have two distinct layers:

- `baseline_import`: the original product surface imported or rendered from host repository code, assets, tokens, screenshots, and component behavior. This layer should be source-owned, not rewritten, and should not introduce new visual language, explanatory copy, or UI-delivery-only chrome inside unchanged product regions.
- `delta_patch`: the requested new or changed feature behavior, implemented in preview-only wrapper/story/demo/page/screen files or mock state. This layer must be visibly identifiable through numbered markers, marker-triggered explanation dialogs, and the current-state annotation panel. Delta annotations should explain UI intent, interaction, data/API assumptions, backend simulation, permission/state behavior, tracking, and edge cases.

Multi-turn UI-delivery work should preserve the same preview surface and append each new user request to `delta_patch.multi_turn_change_log`. The agent should continue from `delta_patch.next_delta_anchor` rather than re-creating or hand-drawing the baseline.

The UI deliverable should preserve baseline geometry and add the delta in place. Annotation controls must not resize, crop, recolor, or otherwise degrade the baseline layer. If a marker is needed near an unchanged component only to explain how the new feature attaches to it, the annotation must state that the underlying component is baseline UI and identify the new delta separately.

Before writing repo-backed UI, record `host_frontend_inventory`: platform source kind, frontend entry files, route/page/screen files, component-library files, style token/global style files, icon/asset sources, data/mock sources, render command, and preview surface. Use the requirement or target surface as an inventory query when available so the relevant route/component is ranked ahead of unrelated repository files. For Web/H5 inspect routes/pages/components/styles/assets; for Mini Program/Taro/uni-app inspect app/page config, page files, custom components, WXSS/ACSS/TTSS or equivalent styles, and assets; for App inspect React Native/Flutter/native screen, widget/component, theme/style, and asset sources. If these sources are unavailable and the user expects real-product UI, stop for the missing host path or preview instead of fabricating a shell.

Before writing repo-backed HTML or source-rendered preview code, record a source-to-demo map: target route or screen, source page files, reused component files, token/class/style sources, asset/icon sources, data or mock sources, permission/state gates, backend simulation method, and limitations. Record the host mutation policy, artifact mode, preview files changed, `baseline_import`, `delta_patch`, and parity claim under `isolated_ui_prototype` in the run log. If these sources are unavailable, the UI deliverable must be marked `degraded` or `mid` at most, and it must not claim exact, 1:1, source-level, or pixel-level parity.

For repo-backed frontend products, style evidence is required. Inspect the host app shell or root layout, global stylesheet or theme config, design-system/component-library files, affected route/page/component files, local assets/icons, and relevant screenshots or demos. When host frontend source exists, render those host components directly in an isolated preview by default. A self-contained HTML file may emulate inspected components and tokens only when the user's raw request explicitly requested portable/standalone/HTML output, explicitly requested redesign/rebuild/from-scratch/no original UI reuse, or source rendering was attempted and blocked by a concrete command, browser, simulator, dependency, or preview-surface failure; production read-only policy is not a blocker because isolated preview files are allowed. Record concrete source files/assets, reused components, reused tokens or class patterns, icon/asset sources, intended delta, and limitations in `run-log.yaml` under `style_evidence`. Record `source_to_demo_mapping` entries with non-empty source and `prototype_representation` values so the visual source can be audited. Add a hidden `style-source-summary` comment or `data-style-source` attribute in compatibility HTML when HTML is generated.

Repo-backed UI deliverables should use an existing UI visual baseline whenever possible. Valid sources include a screenshot from the running host app, a preview route, Storybook/demo, existing screenshot asset, or user-provided image. Record `existing_ui_visual_baseline` with status, source, target page or component, screenshot paths when captured, comparison method, and limitation. If the host frontend is renderable and a standalone HTML fallback is used, a missing baseline must cite a raw-request portable/standalone/HTML request or concrete attempted-render/browser/setup failure. If no baseline can be captured, say so and do not claim pixel parity.

For screenshot-to-UI or target-mockup work, the first validation pass must use the primary reference viewport in CSS pixels. Browser screenshots should be captured at the same viewport whenever tooling is available. Do not use CSS `zoom`, root transforms, screenshot backgrounds, or inflated canvases to make a superficial match. Claims such as high fidelity, exact, 1:1, pixel-level, or "matches the image" require screenshot comparison evidence; otherwise mark the parity claim as `style_evidence_only_fidelity_limited` or `degraded` and state why.

Design calibration is a secondary pass after style evidence, not permission to redesign the host product. Choose visual density, layout variance, and motion intensity from the product surface and scenario. Operational tools should remain dense, predictable, and scannable; editorial or marketing surfaces may use more asymmetry and motion. Avoid generic AI UI signatures such as unrelated hero sections, equal 3-card feature rows, decorative gradient blobs, invented palettes, default avatars or names, fake round numbers, dead controls, and success-only screens.

## Fidelity

Choose the highest useful fidelity the available context supports:

- `high`: use when brand, layout, component, content, and interaction direction are known.
- `mid`: default for most requirements; polished layout, realistic copy, clear components, and complete states.
- `low`: use only when the problem is still exploratory or visual direction is intentionally unknown.

For repo-backed UI work, `high` requires enough inspected source evidence to mirror the host app shell, affected page, core components, tokens, assets, and state model. A UI deliverable may not claim 1:1 or pixel-level parity unless an existing UI visual baseline exists and unchanged regions were compared or explicitly reviewed against it.

Even low-fidelity UI deliverables must be clean, clickable, and implementation-oriented. Avoid bare placeholder wireframes when UI or interaction direction is available.

## Platform Selection

| Platform | Use When | Required Simulation |
|---|---|---|
| Web | Desktop products, SaaS, dashboards, content management, user account tools, financial tools | Desktop viewport, sidebar or top navigation, responsive behavior, tables/forms/cards, authenticated and unauthenticated states when relevant |
| H5 | Mobile browser, landing pages, lightweight checkout, campaigns | Mobile browser frame, URL/header hint, single-column layout |
| App | Native mobile product flows | App frame, top bar, bottom tabs or native navigation |
| Mini Program | Mini-program style flows | Status bar, capsule area, current mini-program navigation, existing tab bar style, page stack feel, authorization and lightweight forms |
| Browser extension | Extension popup, content script, toolbar action, side panel | Extension frame or popup dimensions, permission boundary, logged-in/logged-out state, cache/offline state |

For Mini Program UI deliverables, page level must be visible and consistent with the host product. Primary tab pages should show the current tab bar and avoid secondary `page-header` chrome; secondary pages should show `page-header` or back behavior and should not show the primary tab bar unless the host product does. The top status/capsule region should be represented so reviewers can judge Mini Program fit rather than a generic mobile web frame.

For Web UI deliverables, the product shell must be visible and consistent with the host product. Show the relevant desktop navigation model, page header, content density, responsive/mobile breakpoint behavior, and access states such as visitor, signed-in, permission-denied, or account-required when those states affect the feature. Do not present a Web feature as an isolated card floating outside the existing app shell unless the host product actually uses that pattern.

Responsive Web UI deliverables should make small-screen priorities explicit: which metrics or actions stay visible, which content collapses, minimum touch-target expectations, and what must remain unchanged on desktop.

For browser extension UI deliverables, show the extension container instead of a full Web app shell when the requested surface is the popup or side panel. Annotate extension permissions, account/session handoff, storage/cache behavior, and degraded state when the main site session expires.

## Required Interaction

- Main path must be clickable.
- At least one non-happy state must be represented when relevant.
- Buttons and links must have visible outcomes.
- Copy must fit on mobile-sized frames.
- Conversion or speed pressure must not remove accessible names, visible labels, focus order, consent clarity, total cost visibility, or error recovery. If an accessible or consent-preserving state is not visually shown, record the implementation requirement and owner before delivery.
- The UI deliverable must include realistic screen states: loading, empty, error, permission, confirmation, success, or rollback where relevant.
- Loading states should match the final layout shape where possible instead of using generic spinners; form errors should be inline and close to the field.
- State coverage must be reachable through realistic product interactions, permission gates, retry actions, form submissions, or mocked data/API transitions. A reviewer-only switcher can speed inspection, but it cannot be the only way a state exists.
- Multi-page or multi-state UI deliverables should let reviewers switch state without shrinking the product surface. Use a lightweight overlay control outside the product layout when needed.
- Long pages and modal dialogs must preserve real scrolling behavior. Use viewport-based max heights and internal scroll only when the host product does; do not clip important fields, buttons, or bottom content.
- If access depends on account, role, eligibility, plan, location, consent, or setup state, show the eligible and ineligible states or state why one is not relevant.
- Access-state behavior must be internally coherent. A logged-out, guest, or no-permission entry point must not reveal authenticated profile data, user IDs, account-management links, sync actions, logout actions, or privileged navigation when interacted with.
- If the feature contains unreviewed reference or regulated content, label it as placeholder or draft in the UI deliverable and do not present it as approved final content.
- Important controls should expose annotations through clickable markers or hotspots tied to the concrete UI element being explained.
- For image-reference reconstruction, all visible controls, small icons, carets, logos, badges, status dots, data visualizations, and asset crops from the reference must be represented or explicitly called out as missing or placeholder material with a replacement path.
- Annotation state should update by page or screen, so reviewers can tell which note belongs to which UI element.
- Numbered callouts should not cover critical copy or controls. Place compact markers at the annotated component's top-right corner by default; offset them just outside that same corner when needed to avoid covering key content.
- The default callout shape is a small red circular badge using `annotation-marker`, `data-annotation-id`, and `data-annotation-placement="top-right"` on the UI surface. Place badges in a safe top-right spot that is visible, not clipped by `overflow: hidden`, and not causing labels or controls to wrap. Marker badges and matching number badges inside marker dialogs and the right-side page annotation panel must use the same red background, white text, no border line, rendered diameter, font size, font weight, line height, and centered digit alignment. Reuse one shared badge style or CSS variables so dialog and panel numbers do not inherit heading or list typography. Visual badges must contain plain digits such as `1`, `2`, and `3`, not circled numeral glyphs or nested badge content. Marker visual style must not change after click. Clicking a marker opens a small local `annotation-dialog` popover beside that marker with the matching number; clicking the same marker again closes it. Marker clicks must not open a full-screen/global modal, backdrop, or centered note dialog.
- A draggable annotation floating control with `data-draggable="true"` should show only `注释` in Chinese outputs or `Notes` in English outputs. Clicking it hides the floating control and opens an `annotation-list` panel from the right edge. The panel must fill viewport height, show annotations for the current page/state, and restore the floating control when closed.
- If page or state switching controls are needed, keep them in a stable fixed/collapsed reviewer-only control outside the product layout, marked with `data-reviewer-only="true"`, so they do not look like abrupt product UI.

## Required Annotations

Include annotations for:

- UI intent and component behavior.
- Data fields, validation, and empty/error states.
- Tracking hooks when relevant.
- Permission, privacy, payment, compliance, or operational notes.
- Engineering handoff notes and known assumptions.

Annotation rules:

- The default annotation layout keeps the product UI full-width and uses marker-triggered local popovers beside the relevant marker. Do not add a full-screen/global marker modal unless the user explicitly asks for that annotation style.
- Each page or screen has its own annotation group in the right-side full-height `annotation-list` panel.
- Each annotation references a concrete UI element, state, or transition and uses the same visible plain digit as the callout marker in the UI deliverable, for example `2`.
- Each UI marker and dialog/list note must share a stable annotation ID, for example `data-annotation-id="2"` on the UI badge and the matching `2` note in the marker dialog or current-state annotation panel. UI badges should also declare `data-annotation-placement="top-right"` unless a documented exception is needed. The matching dialog/list note number must render with the same badge dimensions, digit font sizing, and centered alignment as the UI badge.
- Annotation text must be implementation-grade and specific. Include details such as text length limits and ellipsis behavior, tap/hover/long-press behavior, empty/error state handling, permission rules, data source, and tracking hook when relevant.
- Long annotation content should be summarized in marker dialogs and expanded through the `annotation-list` overlay. Do not dump every page's notes into one long generic paragraph.
- Cross-page notes belong in a separate `Global notes` group.
- Annotations must be reachable from the UI surface, not only listed beside it.
- A generic implementation-note card without numbered markers is not sufficient.
- Standalone HTML JavaScript must parse without browser page errors when HTML is generated. If script syntax breaks, buttons and annotation interactions are considered failed even when the HTML structure looks complete.

## Output Rule

Generate a single self-contained `.html` file only when standalone HTML is the selected artifact mode. When repo-backed fidelity requires source rendering, generate the isolated preview route/story/demo/page/screen delta files instead and record them in `isolated_ui_prototype.preview_files_changed`.

Standalone HTML must record that it is a compatibility review artifact through metadata, comments, run-log fields, or PRD notes, but it should not add visible "example/demo/not production" copy to the product surface. It should be structured and styled to a standard that UI and engineering can use directly as reference.

For repo-backed UI-delivery-only work, self-contained HTML is acceptable only when the raw request asks for portable/standalone/HTML review, explicitly asks to redesign/rebuild/from-scratch/stop reusing the original UI, or source rendering is concretely blocked. It may emulate inspected host components, token values, and local assets, but it cannot guarantee exact parity for icons, fonts, rendered component internals, browser-specific CSS, platform chrome, or runtime state. If frontend source exists, use a source-rendered preview mode after recording the mutation boundary and changed preview files. Production flows remain untouched unless production implementation is explicitly requested.

Standalone HTML files must not depend on external scripts, fonts, CDNs, network images, or remote CSS. If a visual asset is necessary, embed it, use an existing local asset reference only when the host project path is stable, or explain the limitation in the PRD and run log. Source-rendered previews should use verified host-project dependencies and assets through the host build path.

Do not import React, Next.js, Tailwind, Framer Motion, icon libraries, fonts, or remote assets into standalone HTML. For source-rendered previews, import only verified dependencies already used by the host project. For local HTML compatibility artifacts, express any motion with lightweight CSS using `transform` and `opacity`; avoid scroll listeners, layout-changing animation, and anything that makes screenshot validation unstable.

## Browser Visual Validation

Validate generated compatibility HTML deliverables with:

```bash
python3 scripts/validate_prototype_visual.py outputs/<run-id>
```

The check should capture at least desktop/default and constrained/mobile screenshots when relevant, confirm the view is not blank, run DOM smoke checks for visible text, interactive controls, horizontal overflow, console errors, page errors, and access-state leakage, and compare against visual baselines when the run is part of a regression suite. When multiple compatibility HTML files exist, the command validates all supported prototype files unless `--prototype <file>` is supplied. For source-backed previews, run the host dev/preview/Storybook/simulator path, then run `python3 scripts/validate_ui_preview.py <preview-url-or-file> --run-folder outputs/<run-id>` when a browser URL or local preview file is available; otherwise record equivalent browser or simulator evidence under `visual_validation`. Store screenshots and `visual-report.json` or `source-preview-report.json` under `outputs/<run-id>/visual-review/`. Browser automation defaults to Playwright-managed cached browsers and uses system browser channels only when explicitly requested. Source preview navigation uses a bounded timeout and defaults to `domcontentloaded`; use `networkidle` only for reliable static previews. Record a skipped check only when setup fails, browser launch is forbidden, or the user declines installation.

For final delivery, prefer the delivery orchestrator so HTML parsing and output validation are recorded with the visual evidence:

```bash
python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>
```
