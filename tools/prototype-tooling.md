# UI Delivery Tooling Notes (Legacy Prototype Tooling)

UI deliverables should use the artifact mode that matches source availability first. Standalone HTML is for portable review, true no-source situations, explicit redesign/greenfield work, or concrete source-rendering blockers; repo-backed UI with frontend source should use a source-rendered delta patch.

## Requirements

- No build step for standalone HTML compatibility artifacts. Source-rendered preview artifacts use the host app's normal dev, preview, Storybook, simulator, or platform tooling.
- No external network dependency unless the host app already requires it and the limitation is recorded.
- Inline CSS and JavaScript are acceptable only for standalone HTML artifacts.
- Use semantic buttons and links for interactions.
- Include compatibility-review boundary metadata or comments for standalone HTML; do not add visible "example/demo/not production" copy to the product UI.
- When current product UI evidence exists, match the current surface before adding the new requirement.
- In repo-backed UI-delivery-only work, keep production flows read-only by default: read real frontend code and assets, then use `source_delta_patch` whenever host frontend source exists. Import/render the original baseline from host source and add the requested feature only through isolated preview/delta files.
- Split repo-backed UI deliverables into `baseline_import` and `delta_patch`: baseline import renders unchanged host UI; delta patch contains only preview composition, mock state, new feature UI, markers, explanation dialogs, interactions, backend simulation notes, and tracking or edge-case annotations.
- In repo-backed frontend work, run `python3 scripts/inspect_host_frontend.py --host <host-repo> --query "<requirement or target surface>" --pretty` when available, then inspect the host app shell/root layout, global stylesheet or theme config, design-system components, affected route/page/component files, local icons/assets, and screenshots or demos before writing any delta patch.
- Record `isolated_ui_prototype` in `run-log.yaml`: host mutation policy, artifact mode, target route or screen, preview files, `baseline_import`, `delta_patch`, source-to-demo mapping, backend simulation method, parity claim, and limitations.
- Record `host_frontend_inventory` and `style_evidence` in `run-log.yaml`: source files, reused components, reused tokens or class patterns, icon/asset sources, UI delta, and limitations.
- Source-backed previews must hand off the preview command, route/story/screen, and changed preview/delta files; do not give only a localhost URL. Standalone compatibility mode must hand off the generated HTML path.
- Use standalone HTML fallback only when the user's raw request explicitly requests portability/standalone/HTML output, explicitly asks to redesign/rebuild/from-scratch/stop reusing the original UI, or source rendering is attempted and blocked by concrete command, browser, simulator, dependency, or preview-surface evidence. "Only generate a prototype" means review scope only; it does not authorize standalone HTML or greenfield UI. Production read-only policy is not a blocker because isolated preview files are allowed.
- Add a hidden `style-source-summary` comment or `data-style-source` attribute only in generated HTML artifacts.
- Capture or record `existing_ui_visual_baseline` for repo-backed UI work when possible: running host app screenshot, preview route, Storybook/demo screenshot, existing screenshot asset, or user-provided image. If a renderable host frontend falls back to standalone HTML, a missing baseline must cite a raw-request portable/standalone/HTML request or concrete attempted-render/browser/setup failure.
- After style evidence is captured, run a design calibration pass: match the host product's visual density, layout variance, and motion intensity; remove generic AI patterns that do not belong to the current surface.
- Keep the product surface full-width; annotation notes must not reserve layout space or shrink the product viewport.
- Model real interactions and states. Use primary product controls, form submissions, retry actions, permission gates, and mocked data/API transitions; reviewer-only state switching must be fixed, collapsed, marked `data-reviewer-only="true"`, and secondary.
- Use matching numbered callouts at a safe top-right position on the annotated component and marker-triggered dialogs. Default UI markers, marker dialog note numbers, and right-side page annotation panel note numbers are red/white borderless circular badges with `annotation-marker`, `data-annotation-id`, and `data-annotation-placement="top-right"`. They must share the same rendered diameter, font size, font weight, line height, and centered digit alignment; use one shared badge style or CSS variables so note numbers do not inherit heading or list typography. Badge text must be plain digits such as `1`, `2`, and `3`, not circled numeral glyphs or nested badge content. The short `注释`/`Notes` floating control uses `data-draggable="true"` and opens a right-edge full-height `annotation-list` panel for current page/state notes.

## Suggested Verification

- Open the file locally.
- Click through the main path.
- Confirm text does not overflow the mobile frame.
- Confirm the selected platform shape is obvious.
- Confirm long pages, multi-state screens, and modals are scrollable like the host product and are not clipped by an artificial frame.
- Confirm standalone HTML JavaScript parses when HTML is generated, and primary buttons, product tabs, dialogs, annotation markers, and the annotation toggle all produce visible state changes. Confirm marker dialogs and the right-side page annotation panel both show matching plain digit number badges with the same rendered size, font sizing, and centered alignment as the UI markers.
- Confirm repo-backed UI-delivery-only work did not modify host production routes, pages, components, styles, assets, package files, or backend code unless explicitly requested.
- Confirm unchanged baseline UI is not redesigned or explained inline, and that delta markers/dialogs do not resize, crop, recolor, or cover critical unchanged UI.
- Confirm source-rendered repo-backed UI deliverables import/render the baseline from host source, record `baseline_import`, and change only `delta_patch` preview files.
- Confirm repo-backed HTML fallbacks contain a source-to-demo map in the run log and a style source summary in the artifact.
- Confirm repo-backed UI deliverables have host frontend inventory, style evidence, and use the host app shell, components, tokens, assets, and density.
- Confirm repo-backed UI deliverables include existing UI visual baseline evidence or a concrete skipped reason.
- Confirm backend-dependent behavior is simulated with mock data plus loading, empty, error, permission, and success states where relevant, rather than silently implying real backend implementation.
- Confirm the product surface does not contain visible `示例`, `演示`, `Demo`, `Sample`, `Prototype`, `Not production code`, or `不是生产代码` labels unless the requirement explicitly needs visible draft status.
- Confirm the UI deliverable includes loading, empty, error, disabled, and success feedback where relevant, and does not rely on a static success-only screen.
- Confirm motion, if any, uses stable CSS transform/opacity and does not destabilize screenshot validation.
- Confirm numbered callouts sit at a visible, unclipped top-right position, do not make compact text wrap, and map to matching marker dialogs and the current-state annotation panel.
- Confirm the annotation floating control can be dragged away from host-product controls, hides while the right-side panel is open, and reappears when it closes.
- Confirm notes describe concrete logic, interaction, text limit, data, permission, state, and tracking rules where relevant.
- Confirm no external image, font, or script is required.
- If `tidy` is available, run it and record its version or compatibility limitation. Older macOS `tidy` builds may report valid HTML5 elements such as `main`, `section`, `aside`, `meta charset`, or ARIA attributes as errors.
- When `tidy` is incompatible with modern HTML, also run a fallback parser check such as Python `html.parser` and record both results instead of treating the fallback as if `tidy` passed.
- Run `python3 scripts/validate_prototype_visual.py outputs/<run-id>` to capture desktop/mobile screenshots and a visual report for every supported compatibility HTML file in the run folder. Use `--prototype <file>` only when intentionally validating one platform. For source-backed previews, run the host dev/preview/Storybook/simulator path and record equivalent evidence. If Playwright/browser tooling is missing, run or guide `python3 scripts/setup_visual_validation.py` first; if an auto-detected system browser fails, the validator should attempt the bundled/default Chromium fallback before recording the limitation.
- For regression suites, pass `--baseline-dir <baseline-path>` and compare screenshots. Use `--update-baseline` only when intentionally accepting a new visual baseline.
- For final delivery, prefer `python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>` so visual, HTML, repository, and output checks are recorded in one report.
- Record screenshot paths, nonblank ratio, diff status, report path, and any skipped-tool limitation in `run-log.yaml` and the PRD validation section. A skipped status must show that setup was attempted or guided first unless browser launch is explicitly forbidden or installation was declined.

## Platform Hints

- Web: use a desktop-like layout with navigation, panels, tables, or forms.
- H5: use a narrow mobile browser frame with scrollable single-column content.
- App: use a native-style top bar and bottom navigation when relevant.
- Mini Program: include a capsule area and mini-program style top chrome.
