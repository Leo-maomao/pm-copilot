# Prototype Tooling Notes

Prototypes should be generated as self-contained HTML files.

## Requirements

- No build step.
- No external network dependency.
- Inline CSS and JavaScript are acceptable for a prototype artifact.
- Use semantic buttons and links for interactions.
- Include a visible prototype-only / not-production-code boundary.
- When current product UI evidence exists, match the current surface before adding the new requirement.
- In repo-backed prototype-only work, keep host production files read-only by default: read real frontend code and assets, then generate an isolated HTML demo that mirrors the current online surface plus the requested feature delta.
- Split repo-backed UI prototypes into `baseline_layer` and `delta_layer`: baseline reconstructs unchanged host UI; delta contains only the new feature UI, markers, explanation dialogs, interactions, backend simulation notes, and tracking or edge-case annotations.
- In repo-backed frontend work, inspect the host app shell/root layout, global stylesheet or theme config, design-system components, affected route/page/component files, and screenshots or demos before writing HTML.
- Record `isolated_ui_prototype` in `run-log.yaml`: host mutation policy, target route or screen, source-to-demo mapping, backend simulation method, parity claim, and limitations.
- Record `style_evidence` in `run-log.yaml`: source files, reused components, reused tokens or class patterns, prototype delta, and limitations.
- Add a hidden `style-source-summary` comment or `data-style-source` attribute in the prototype HTML.
- Capture or record `existing_ui_visual_baseline` for repo-backed UI work when possible: running host app screenshot, preview route, Storybook/demo screenshot, existing screenshot asset, or user-provided image. If unavailable, record the limitation and do not claim pixel parity.
- After style evidence is captured, run a design calibration pass: match the host product's visual density, layout variance, and motion intensity; remove generic AI patterns that do not belong to the current surface.
- Keep the product surface full-width; do not reserve a persistent side annotation board by default.
- Use matching numbered callouts at a safe top-right position on the annotated component and marker-triggered dialogs. Default UI markers are small red circular badges with `annotation-marker`, `data-annotation-id`, and `data-annotation-placement="top-right"`; `annotation-toggle` uses `data-draggable="true"` and opens an `annotation-list` overlay for all markers in the current page/state.

## Suggested Verification

- Open the file locally.
- Click through the main path.
- Confirm text does not overflow the mobile frame.
- Confirm the selected platform shape is obvious.
- Confirm long pages, multi-state screens, and modals are scrollable like the host product and are not clipped by an artificial frame.
- Confirm prototype JavaScript parses and primary buttons, tabs, dialogs, annotation markers, and the annotation toggle all produce visible state changes.
- Confirm repo-backed prototype-only work did not modify host production routes, pages, components, styles, assets, package files, or backend code unless explicitly requested.
- Confirm unchanged baseline UI is not redesigned or explained inline, and that delta markers/dialogs do not resize, crop, recolor, or cover critical unchanged UI.
- Confirm repo-backed HTML contains a source-to-demo map in the run log and a style source summary in the artifact.
- Confirm repo-backed prototypes have style evidence and visibly reuse the host app shell, components, tokens, and density.
- Confirm repo-backed prototypes include existing UI visual baseline evidence or a concrete skipped reason.
- Confirm backend-dependent behavior is simulated with mock data plus loading, empty, error, permission, and success states where relevant, rather than silently implying real backend implementation.
- Confirm the prototype includes loading, empty, error, disabled, and success feedback where relevant, and does not rely on a static success-only screen.
- Confirm motion, if any, uses stable CSS transform/opacity and does not destabilize screenshot validation.
- Confirm numbered callouts sit at a visible, unclipped top-right position, do not make compact text wrap, and map to matching marker dialogs and the current-state annotation list.
- Confirm the top-right annotation toggle can be dragged away from host-product controls.
- Confirm notes describe concrete logic, interaction, text limit, data, permission, state, and tracking rules where relevant.
- Confirm no external image, font, or script is required.
- If `tidy` is available, run it and record its version or compatibility limitation. Older macOS `tidy` builds may report valid HTML5 elements such as `main`, `section`, `aside`, `meta charset`, or ARIA attributes as errors.
- When `tidy` is incompatible with modern HTML, also run a fallback parser check such as Python `html.parser` and record both results instead of treating the fallback as if `tidy` passed.
- Run `python3 scripts/validate_prototype_visual.py outputs/<run-id>` to capture desktop/mobile screenshots and a visual report for every supported prototype file in the run folder. Use `--prototype <file>` only when intentionally validating one platform. If Playwright/browser tooling is missing, run or guide `python3 scripts/setup_visual_validation.py` first; if an auto-detected system browser fails, the validator should attempt the bundled/default Chromium fallback before recording the limitation.
- For regression suites, pass `--baseline-dir <baseline-path>` and compare screenshots. Use `--update-baseline` only when intentionally accepting a new visual baseline.
- For final delivery, prefer `python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>` so visual, HTML, repository, and output checks are recorded in one report.
- Record screenshot paths, nonblank ratio, diff status, report path, and any skipped-tool limitation in `run-log.yaml` and the PRD validation section. A skipped status must show that setup was attempted or guided first unless browser launch is explicitly forbidden or installation was declined.

## Platform Hints

- Web: use a desktop-like layout with navigation, panels, tables, or forms.
- H5: use a narrow mobile browser frame with scrollable single-column content.
- App: use a native-style top bar and bottom navigation when relevant.
- Mini Program: include a capsule area and mini-program style top chrome.
