# Image Reference Reconstruction

Use this reference when a user asks PM Copilot to turn a screenshot, mockup, generated concept image, or cropped UI image into a UI deliverable.

## Trigger

Activate this mode for wording such as screenshot-to-UI, image-to-UI, recreate this image, match this mockup, visual reconstruction, "图片还原", "截图还原", "把图转成 UI", or when the supplied image is clearly intended as the visual target.

This mode extends `skills/multi-platform-prototype/SKILL.md`; it is not a separate skill. Repo-backed source-first rules still apply when host frontend source exists.

## Intake

Before drafting UI, record:

- Reference image source or path.
- Exact pixel dimensions.
- Intended CSS viewport or device frame, if known.
- Role of the image: existing product baseline, target mockup, component crop, asset reference, or ambiguous reference.
- Text that is uncertain or illegible.
- Missing assets, logos, illustrations, charts, maps, icons, or media that cannot be recovered from the reference alone.

## Visual Inventory

Build a compact inventory before writing code:

- Page or screen sections in order.
- Major container boundaries, grid ratios, and alignment.
- Text blocks, labels, helper text, values, and visible states.
- Controls, menus, fields, tabs, pagination, chips, badges, status dots, and call-to-action hierarchy.
- Navigation, platform chrome, and toolbar details.
- Iconography and logo marks, including tiny carets, search icons, row actions, and status symbols.
- Typography groups, including family/source, size, weight, line height, and wrapping behavior.
- Color roles, opacity, borders, shadows, radii, separators, and surface treatment.
- Images, media crops, chart proportions, map regions, diagrams, and data visualization geometry.
- Crowding risks, one-line constraints, scroll regions, sticky panels, and responsive intent.

Do not start coding until the inventory explains every visually meaningful element.

## Implementation Rules

- Match the primary reference viewport first in CSS pixels.
- Use host components, tokens, fonts, icons, and assets when adapting an existing frontend.
- Do not add a second styling system only because the image reconstruction is difficult.
- Do not redesign, simplify, or "improve" the reference unless responsiveness or ambiguity requires a documented choice.
- Do not use CSS `zoom`, root-level transforms, screenshot-as-background shortcuts, or inflated canvases to fake similarity.
- Give fixed-format UI elements stable dimensions so hover states, labels, icons, and dynamic values do not shift the layout.
- Treat small missing icons as fidelity defects, not optional decoration.

## Asset Handling

For each visible asset, use exactly one of these paths:

- Reuse a supplied or host-project asset.
- Generate or edit a missing raster asset only when an approved image-generation capability is available and the user request allows it.
- Use an honest placeholder that matches the asset's dimensions, crop, radius, and visual weight, then provide one standalone generation prompt for that missing asset.

Do not invent brand logos, proprietary marks, regulated content, or real-person imagery unless the user explicitly authorizes a temporary stand-in.

## Verification

When browser tooling is available:

- Capture the implementation at the same CSS viewport as the reference.
- Compare the screenshots side by side or with a visual diff.
- Iterate in this order: structure and composition, fine visual details, responsive behavior.
- Recheck typography, icon completeness, image crops, text wrapping, internal scroll regions, and panel/table overflow after each major layout adjustment.
- Record screenshot paths, comparison method, mismatches fixed, remaining mismatches, and any skipped-tool limitation in `run-log.yaml`.

High, exact, 1:1, or pixel-level fidelity requires exact-size screenshot comparison evidence. Without that evidence, describe the result as fidelity-limited even if it is visually polished.

## Handoff

In the UI delivery handoff, include:

- Reference source and dimensions.
- Artifact mode and target surface.
- Baseline source or target mockup role.
- Visual inventory summary.
- Asset handling summary.
- Screenshot comparison or skipped reason.
- Remaining mismatch list, if any.
