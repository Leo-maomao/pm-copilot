# Real-Run UI Delivery Improvement Plan

This plan captures reusable PM Copilot improvements found during an actual multi-turn UI delivery run. The source product and local output are host-run evidence only; the improvements below are generic PM Copilot capability changes.

## 1. Product Workflow

- Use a dated ASCII run folder for every real user run: `requirement-slug-YYYY-MM-DD`.
- Keep the date at day precision. If a same-day folder already exists, append `-2`, `-3`, and so on rather than adding minute-level timestamps.
- Treat requests for offline handoff as artifact-mode requirements. The output must still be an interactive prototype or source-backed preview, not a static screenshot.
- Support the real PM workflow where the current repository is first updated until the target UI is correct, and then the finished source-rendered region is extracted into a 1:1 offline HTML handoff for engineering.
- Preserve the user-requested delivery scope. If the user explicitly says no PRD is needed, do not create a PRD or explanatory package.

## 2. Context And Fidelity

- In repo-backed UI work, read the host frontend source before recreating any UI.
- If the user asks to implement the UI in the current repo first, the source implementation or isolated preview becomes the source of truth for extraction. The extracted HTML must record whether it came from production-oriented source changes, preview-only delta files, or another user-approved source branch.
- When the user requests 1:1 parity, source-rendered preview/delta remains the default. A standalone HTML file can be produced for offline handoff only when the run records that it is a compatibility artifact, source-extracted handoff, or documented fallback and names the source/style evidence used.
- Screenshot captures are visual evidence. They are not a prototype by themselves unless the resulting artifact has real layout, text, controls, state changes, and annotation interactions.
- Keep generated runtime evidence under `outputs/<run-id>/`; do not promote host-specific nouns, routes, or screenshots into generic PM Copilot docs.

## 3. Annotation UX

- Surface markers are small numbered red badges attached to the annotated element.
- Default annotations should be generated from one editable annotation map or configuration block. Users can add, remove, reorder, or edit notes from that config without changing the copied product DOM.
- Marker popovers are local, lightweight, and contain only the annotation body text. Do not repeat the number, annotation title, or a close button inside the popover.
- Clicking the same marker closes its popover.
- The floating annotation control opens the full right-side annotation list. The list can include numbers and titles, and it closes through its close control or by clicking outside the side panel.
- Annotation overlays must not introduce horizontal overflow or reserve layout width that shrinks the product surface.

## 4. Offline HTML Contract

- `prototype-<platform>.html` remains the platform-specific compatibility HTML name.
- `index.html` is also allowed when the user needs a self-contained offline folder where the folder name carries the requirement name and date.
- Standalone HTML must not depend on remote scripts, fonts, CSS, or network images.
- An offline artifact must be inspectable through direct browser open and pass HTML/script/visual smoke checks where tooling is available.

## 5. Validation

- Validate run folder naming under `outputs/` with the dated ASCII pattern.
- Validate generated HTML scripts with `node --check` when Node is available.
- Validate marker popovers visually: only body content, local placement, no marker style change, second click closes, and no horizontal scroll.
- Validate the right-side annotation list: full-height right slide-in panel, floating toggle hidden while open, close control works, and outside-page click closes the panel.
- Validate that screenshot-only artifacts fail unless they also contain interactive DOM controls and source/style mapping evidence.

## 6. Maintainer Handoff

- Version and changelog updates are required for PM Copilot capability changes.
- Generated `outputs/` folders remain ignored and are not published as examples.
- When PM Copilot is embedded without its own `.git` metadata, do not claim a push to the PM Copilot repository until an actual PM Copilot remote is available.
- If the target PM Copilot repository cannot be found but a same-name local source folder exists on the Desktop, write the changed source files there and tell the user that they can push from that folder.
