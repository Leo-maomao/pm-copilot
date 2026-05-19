# Prototype Tooling Notes

Prototypes should be generated as self-contained HTML files.

## Requirements

- No build step.
- No external network dependency.
- Inline CSS and JavaScript are acceptable for a prototype artifact.
- Use semantic buttons and links for interactions.
- Include a visible prototype-only / not-production-code boundary.
- When current product UI evidence exists, match the current surface before adding the new requirement.
- Use left-side prototype plus right-side numbered annotation panel by default.
- Use matching numbered callouts such as `①`, `②`, and `③` beside the UI element and in the annotation panel.

## Suggested Verification

- Open the file locally.
- Click through the main path.
- Confirm text does not overflow the mobile frame.
- Confirm the selected platform shape is obvious.
- Confirm numbered callouts map to matching right-side notes.
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
