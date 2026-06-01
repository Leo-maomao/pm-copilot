---
name: multi-platform-prototype
description: Use when generating annotated UI deliverables for Web, H5, App, or Mini Program product scenarios, including repo-backed source-rendered preview/delta artifacts, source-extracted HTML handoffs, and standalone HTML compatibility artifacts.
---

# Multi-Platform UI Delivery

## Goal

Generate an annotated UI deliverable that matches the selected product platform and is useful for product review, UI reference, and engineering handoff. In repo-backed UI work, the deliverable must be an isolated mirror of the real product surface: read real frontend code and assets, keep host production files unchanged by default unless the user explicitly asks for implementation work, render the original baseline from source whenever frontend source exists, and show only the requested feature as the new delta. When the PM workflow needs a file that can be handed to engineering outside the host app, first render or implement the desired UI in the host project, then extract the target region into annotated standalone HTML as `source_extract_html`. Standalone HTML is therefore either a source-derived handoff or a compatibility artifact; it is not permission to invent a new product shell.

For document-class HTML requests, use Document Prototype Mode instead of a normal product UI prototype. The surface is a readable reference document, not an app screen, so source/review status, structured tables, hierarchical fields, attention points, changes, and completeness checks matter more than UI callout mechanics.

## Platform Selection

- Web: desktop admin, SaaS, dashboards, tables, complex forms.
- H5: mobile browser, landing page, lightweight campaign or payment flow.
- App: native mobile flows, persistent app navigation, account or content scenarios.
- Mini Program: mini-program container, authorization, booking, ordering, lightweight forms.

## Workflow

1. Choose the platform based on PRD scenario.
2. Load `artifacts/prototype-contract.md` when available.
3. Inspect existing demos, screenshots, routes, components, design-system files, or user-provided UI reference images when available; activate Image Reference Reconstruction Mode for screenshot-to-UI, image-to-UI, visual reconstruction, "图片还原", "截图还原", or similar requests.
4. In repo-backed frontend products, run `python3 scripts/inspect_host_frontend.py --host <host-repo> --query "<requirement or target surface>" --pretty` when available, then complete any missing host frontend inventory manually: platform source kind, frontend entry files, route/page/screen files, component-library files, style token/global style files, icon/asset sources, data/mock sources, render command, and preview surface. Cover Web/H5, Mini Program/Taro/uni-app, React Native/Flutter/native App, and other frontend stacks with their native page/component/style files. If the source or render entry cannot be found and the user expects real-product UI, stop for the missing host path or preview instead of inventing a shell.
5. Run a source-rendering/style reuse pass: inspect the host app shell/root layout, global stylesheet or theme config, design-system/component-library files, affected route/page/component files, local assets/icons, and relevant screenshots or demos; extract navigation, tab bar, colors, spacing, typography, icons, card density, radius, shadows, copy tone, and component states; prefer rendering host components directly; record `host_frontend_inventory` and `style_evidence` in the run log.
6. For repo-backed UI-delivery work, define the isolation boundary and artifact mode before writing UI. Host production flows are read-only by default, but host frontend source presence authorizes isolated preview-only source files. Use `source_delta_patch` by default whenever host frontend source and a preview surface exist: import/render the original host page/screen/components/styles/assets as baseline, then add the requested feature only in preview-only delta files. Platform-specific variants are `code_preview_route`, `storybook_or_demo`, `mini_program_preview`, and `app_preview_screen`. Use `source_extract_html` when the requested or inferred handoff path is: PM generates or adjusts the target UI inside the original project first, then extracts that finished region as an independent annotated HTML file for engineering. If the user explicitly asks to implement the feature in the current repo first, record that user-approved source-change scope and extract from the running implementation. Use `self_contained_html_from_host_code` only when the user's raw request explicitly asks for a portable/standalone/HTML artifact without source implementation, explicitly asks to redesign/rebuild/from-scratch/stop reusing the original UI, or source rendering was attempted and blocked by a concrete command, browser, simulator, dependency, or preview-surface failure. "Only generate a prototype" means review scope only; it does not authorize standalone HTML or greenfield UI. Production files being read-only is not a blocking reason because isolated preview files are allowed. In fallback mode, capture an existing UI visual baseline when possible and mark the parity claim as fidelity-limited.
7. For source-backed previews, record the preview command, route/story/screen, and changed preview/delta or user-approved implementation files; do not hand off only a localhost URL. For `source_extract_html`, generate `prototype-<platform>.html` or offline `index.html` after the host-source preview or implementation renders, and record the extraction selector, source preview target, source-region screenshot, extracted-region screenshot, region diff result, interaction replay scope and results, extraction command, style capture method, asset handling, editable annotation layer/configuration, source-change scope, and limitation. For compatibility direct HTML, generate `prototype-<platform>.html` only when standalone compatibility mode is selected; `index.html` is allowed as the offline folder entry only when the user explicitly asks for a portable/offline handoff.
8. For document prototypes, start from `templates/document-prototype-template.html`, declare `<meta name="pm-copilot-artifact" content="document_prototype">`, and render the structured reference data with document navigation, anchors, tables, hierarchy, source/review state, typed `attention_points`, change log, and completeness check. Do not add UI `annotation-marker` controls unless the artifact is also a product-page UI.
9. Build a source-to-demo map for repo-backed UI before drafting: target route or screen, page/component source files, reusable component-library components, token and class sources, local assets or icon sources, data shape or mock source, permission/state gates, and backend behavior represented by mock data plus annotations. Each mapped source needs a visible `prototype_representation`. Record this under `isolated_ui_prototype` and `style_evidence`.
10. Split the repo-backed UI deliverable into two layers: `baseline_import` imports/renders unchanged product UI from the host repository and visual baseline without rewriting it; `delta_patch` contains only new or changed feature UI, marked with numbered callouts and explanation dialogs. For multi-turn UI-delivery work, continue from `delta_patch.next_delta_anchor` and append to `multi_turn_change_log`.
11. Keep annotation markers and UI-delivery controls from degrading the baseline layer: they must not resize, crop, recolor, or cover critical unchanged UI. If a marker is attached to an unchanged component, the note must distinguish the baseline component from the new delta behavior.
12. Capture or record an existing UI visual baseline when possible: running host app screenshot, preview route, Storybook/demo screenshot, or user-provided image. Record `existing_ui_visual_baseline` with status, source, target, screenshot paths, comparison method, and limitation.
13. Explain whether the UI deliverable extends an existing surface or creates a new surface, and why.
14. Run a design calibration pass after the host style is understood: choose layout variance, motion intensity, and visual density from the product surface, not from generic AI taste; operational tools should stay dense and scannable, while marketing/editorial pages may use more asymmetry and motion.
15. Choose fidelity: high when enough visual context exists, mid by default, low only for exploratory work. Repo-backed work cannot claim high, exact, 1:1, or pixel-level parity unless it uses source-rendered preview or has a captured baseline comparison. `source_extract_html` may claim source-derived region fidelity only for the extracted selector and captured state, not for unextracted routes or runtime host behavior. Compatibility standalone HTML must be labeled fidelity-limited in metadata/run log, not as repeated visible product copy.
16. Create a single self-contained HTML file with no CDN, remote font, remote script, or network image dependency only when `source_extract_html` or standalone compatibility HTML is the selected artifact mode. For source extraction, inline or copy only the styles/assets needed by the selected region and list any unresolved asset or pseudo-state gaps. Do not use a screenshot-only page as the prototype; screenshots are evidence, while the HTML artifact still needs real DOM layout, live controls, state changes, and annotations.
17. Include a hidden `style-source-summary` comment or `data-style-source` attribute that names the host style evidence used when HTML is generated. For `source_extract_html`, also include `data-source-extract="true"` and a non-visible extraction metadata block or comment with source preview target, selector, capture timestamp, and limitations.
18. Include main path interaction and make every visible primary control produce a visible product state change.
19. Include relevant non-happy states through realistic UI controls, form submissions, permission gates, retry actions, or mocked API/data transitions. Do not use a top-level row of state tabs as a substitute for real behavior.
20. Show eligible and ineligible user states when access depends on account, role, setup, plan, consent, location, or permission.
21. Check access-state coherence before delivery: logged-out, guest, and no-permission controls must not reveal signed-in-only profile data, user IDs, account-management actions, sync actions, logout actions, or privileged navigation.
22. Use production-quality product-surface copy. Avoid visible `示例`, `演示`, `Demo`, `Sample`, `Prototype`, `Not production code`, or `不是生产代码` labels in the product UI. Put delivery-boundary and draft/placeholder status in metadata, comments, run log, PRD notes, or annotations unless visible draft status is part of the product requirement.
23. Build an editable annotation map before writing UI: number, page/screen, UI element or marker selector, logic note, interaction note, data or permission note, and tracking note when relevant. Generate marker UI from that map so the user can add, remove, reorder, or edit notes without rewriting the product DOM.
24. Add numbered callout markers on the UI surface and matching notes in marker-triggered dialogs. Default markers are small red circular badges with `annotation-marker`, `data-annotation-id`, and `data-annotation-placement="top-right"` placed at a safe top-right spot on the annotated component. Badge text must be plain digits such as `1`, `2`, and `3`, not circled numeral glyphs or nested badge content. Do not use negative offsets inside clipping containers, do not let markers force labels to wrap, and do not cover key controls. Marker visual style must not change when opened. Clicking a marker opens a small local `annotation-dialog` popover beside that marker; clicking the same marker again closes it. Marker popovers must contain only the annotation body text, with no repeated number badge, title/name, or close button, and must wrap long content without horizontal scrolling. It must not open a full-screen/global modal or backdrop.
25. Add a draggable annotation floating control using only `注释` in Chinese outputs or `Notes` in English outputs. Clicking it hides the floating control and slides in a right-edge full-height `annotation-list` panel for current page/state notes; closing the panel restores the floating control. The side panel may include numbered entries and titles, and it must also close when the user clicks the page outside the side panel.
26. For document prototypes, replace the annotation toggle/panel requirement with document-native `attention_points`. Valid types are `source_gap`, `pm_override`, `conflict`, `engineering_must_read`, `launch_blocker`, `cost_or_quota_risk`, `security_or_compliance`, and `change_marker`, each with a concrete `target_ref`.
27. Keep reviewer-only page/state switching controls collapsed, fixed outside the product layout, and marked `data-reviewer-only="true"` when such controls are needed. They must not look like product navigation and must not replace real interactions.
28. For personalization, ordering, layout, or preference features, show the edit mode, save/apply behavior, reset/default behavior, unavailable items, and sync or persistence failure state when relevant.
29. For Web UI deliverables, run a shell/responsive checklist before delivery: desktop navigation visible, page header visible, content density matches the host app, mobile breakpoint or responsive notes are present, touch target and mis-tap risks are considered for mobile Web, desktop regression risk is named, and visitor/signed-in/permission states are represented when relevant.
30. For public Web or SEO surfaces, annotate indexable content, metadata/structured-data expectations, noindex/private-page boundary, and cache/fallback behavior when relevant.
31. For Mini Program UI deliverables, run a chrome/page-level checklist before delivery: status or capsule area visible, primary tab pages use the existing tab bar style, secondary pages show page-header/back behavior, and ineligible/setup states are represented when relevant.
32. When validation scripts are available, run UI visual validation or the delivery checks and record the evidence.

## Image Reference Reconstruction Mode

Use this mode when the request includes screenshot-to-UI, image-to-UI, image reference, visual reconstruction, "图片还原", "截图还原", or similar wording.

- Treat the latest supplied reference image as the visual source of truth for the requested surface or delta, while still preserving source-backed baseline rules when host frontend source exists.
- Record each reference image path/source, exact pixel dimensions, intended viewport, whether it is an existing baseline, target mockup, asset reference, or cropped fragment, and any text or asset uncertainty.
- Inventory the full visible UI before writing code: section order, grid ratios, containers, text, controls, icons, logos, badges, image crops, typography groups, colors, radii, shadows, separators, responsive intent, crowding risks, and data visualizations.
- First implement against the primary reference viewport in CSS pixels. Do not use page-scale hacks such as CSS `zoom`, root transforms, or inflated canvases to fake a match.
- Capture an implementation screenshot at the same viewport when browser tooling is available, compare it against the reference by side-by-side review or visual diff, list visible mismatches, and iterate through structure, fine-detail, and responsive passes before marking the UI delivery complete.
- Represent every visible asset honestly: use supplied or host assets when available, generate/edit missing raster assets only when an approved image-generation capability is available, or use dimensionally accurate placeholders plus one standalone asset-generation prompt per missing asset.
- A high or pixel-level fidelity claim requires exact-size screenshot evidence plus recorded comparison results; otherwise mark the output fidelity-limited and list the verification gap.

## Output

- UI deliverable: source-rendered preview/delta files, source-extracted HTML handoff, or standalone HTML compatibility artifact
- Source-extracted standalone HTML handoff when selected: `prototype-<platform>.html` or offline `index.html` derived from the running host-source preview or user-approved implementation
- Document prototype HTML when the selected artifact mode is a browser-readable structured reference
- Platform rationale
- Fidelity rationale
- Annotation notes
- Existing-surface mapping and change summary
- Isolation boundary and source-to-demo map
- Baseline layer and delta layer summary
- Style-source summary
- Style evidence: source files, reused host components, reused tokens or class patterns, UI delta, limitations
- Existing UI visual baseline: status, source, target, screenshots, comparison method, limitation
- Image reference reconstruction notes when used: reference sources, dimensions, element inventory, asset handling, comparison passes, mismatches fixed, and remaining fidelity limits
- Design calibration summary: layout variance, motion intensity, visual density, and any deliberate anti-generic choices
- Numbered annotation map
- Document attention point map when Document Prototype Mode is active
- Permission and fallback state notes
- Interaction notes
- Cross-platform differences if multiple UI deliverables are needed
- Visual validation result or skipped reason

## Quality Bar

- Standalone HTML opens locally without build tooling; source-rendered previews run through the host app's normal dev, preview, Storybook, simulator, or platform tooling.
- Source-extracted HTML is generated only after the host-source preview renders and uses a concrete selector or region target; it must preserve the extracted region's DOM order, visible text, dimensions, key computed styles, and local assets as far as the extraction tool can capture. A same-viewport screenshot diff between the source region and extracted region is required before claiming visual equivalence. For dynamic pages, replay representative interactions against both the source preview and extracted HTML before claiming behavioral equivalence; without replay, call it snapshot-only.
- Standalone HTML requires no external assets; source-rendered previews may use verified host-project dependencies and assets.
- The platform container is obvious.
- Text fits inside the frame.
- The UI is polished enough to guide UI and engineering; avoid bare placeholders when product context exists.
- Main states, validation, errors, empty states, permission states, and success feedback are represented when relevant.
- Primary controls are not dead ends; every click either changes state or is clearly disabled.
- Text, callouts, and controls do not overlap at desktop or mobile-sized widths.
- Access-gated surfaces include eligible and ineligible states or an explicit not-applicable note.
- Access-gated controls do not leak authenticated account data or actions from logged-out, guest, or no-permission states.
- Placeholder or unreviewed content is visibly labeled and does not look launch-approved.
- If current product UI exists, the UI deliverable preserves the existing structure and shows the new requirement as a delta.
- If host frontend source exists, the UI deliverable reuses the current app shell, component density, design tokens, and class patterns; it must not use a generic new shell or unrelated palette unless the raw request explicitly asks to redesign/rebuild/from-scratch/stop reusing the original UI.
- Repo-backed style evidence must name real host files/assets/icons and explain how inspected components are represented in the UI deliverable. Empty `host_frontend_inventory`, empty `source_files`, generic component names, or a style-source summary without a source-to-demo map are not complete.
- When host frontend source exists, use `source_delta_patch` or a platform-specific source-rendered preview route/story/demo/page/screen using the real component library or native platform screen instead of hand-recreating icons and components in standalone HTML. When an independent HTML file is required for handoff, derive it through `source_extract_html` after the source preview or user-approved implementation renders. Do not treat production read-only policy as a blocker because isolated preview files are allowed. If host rendering is blocked, record the attempted command or setup failure and clearly mark the self-contained HTML parity claim as limited or degraded.
- Source-extracted HTML must hand off both layers: the host-source preview command/route/files and the extracted HTML path/selector/screenshot/report. Reviewers should be able to audit the extracted HTML back to the source preview region.
- Repo-backed UI-delivery-only work leaves host production files unchanged unless the user explicitly requested production-oriented implementation.
- Backend-dependent behavior is represented with coherent mock data, loading/empty/error/permission states, and annotations that name the expected API or data contract when known.
- If an existing UI screenshot or rendered host app is available, the UI deliverable uses it as a visual baseline for unchanged regions. If not available, the run log records the limitation and does not claim pixel parity.
- If a user-provided image is the target UI reference, the UI deliverable must match the reference viewport first, preserve all visible controls/icons/assets, and record screenshot comparison evidence or a clear verification limitation before claiming high fidelity.
- Keep the product surface full width. Do not reserve layout space or shrink the page for notes; marker notes live in local popovers beside the marker, can be toggled closed by clicking the marker again, and the annotation list opens as a right-edge full-height slide-in panel for the current page/state.
- For many pages, many states, or content beyond one screen, preserve the host product's real scroll behavior and state structure. Do not place the product inside an artificial fixed-height frame that clips dialogs or long content.
- UI controls must be live. Before delivery, check that standalone HTML JavaScript parses when HTML is generated, primary buttons visibly change state, annotation markers open body-only dialogs, the annotation toggle opens/closes the right-side current-state panel, the right-side page annotation panel shows plain digit number badges, clicking outside the side panel closes it, the floating toggle can be dragged away from host controls, state switchers stay fixed, and compact tabs or segmented controls do not fold text because of annotations.
- Design calibration improves the existing surface without overriding it. Do not import React, Next.js, Tailwind, Framer Motion, icon libraries, fonts, or external assets into standalone HTML. For source-rendered previews, use verified host-project dependencies and assets through the host build path.
- Avoid generic AI UI signatures: unrelated hero layouts, equal 3-card feature rows, decorative gradient blobs, invented palettes, default avatars/names, fake round numbers, dead controls, and static success-only screens.
- Use complete interaction states: loading skeletons shaped like the final layout, empty states, inline form errors, disabled/loading/success feedback, and tactile active states where they match the host style.
- Prefer CSS Grid for stable multi-column layouts. Keep fixed-format elements dimensionally stable, collapse complex desktop layouts to one column on mobile, and avoid full-screen height assumptions that cause mobile viewport jumps.
- Use motion sparingly for UI deliverables. If motion is shown, animate only transform and opacity, avoid scroll listeners and layout-changing animations, and keep it secondary to reviewability.
- Annotations are tied to specific pages, components, or interactions, not mixed into one generic notes list.
- Annotation notes are concrete enough for engineering. Examples: text length limit and ellipsis rule, tap result, hover tooltip, long-press behavior, disabled/loading/error behavior, data source, permission rule, and tracking event.
- Document attention points are concrete enough for reviewers. Examples: missing source, product override of a vendor default, conflicting field requirement, launch-blocking confirmation, quota/cost risk, security/compliance risk, and implementation-critical field behavior.
- Mini Program UI deliverables preserve the current mini-program chrome, tab bar, visual density, and component style when any current UI evidence is available.
- Mini Program UI deliverables make page hierarchy explicit: primary-tab screens and secondary-page screens should use different chrome that matches the host route model.
- Preference and layout UI deliverables make reversible actions, unavailable modules, and persistence/sync failures visible instead of only showing the final customized state.
- Web UI deliverables preserve the app shell and include responsive behavior or explicit breakpoint notes, especially when the host product has both desktop and mobile usage.
- Responsive Web requirements specify breakpoint behavior, priority of information on small screens, touch target expectations, and desktop parity or intentional differences.
