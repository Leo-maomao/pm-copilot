# Validation Tooling

Validation is a required part of final delivery, not an optional afterthought.

## Default Commands

Run repository validation after PM Copilot source changes:

```bash
python3 scripts/validate_repo.py
```

Run output validation after generating a run folder:

```bash
python3 scripts/validate_outputs.py outputs/<run-id> --language zh
python3 scripts/validate_outputs.py outputs/<run-id> --language en
```

Run the delivery orchestrator before final delivery or iteration scoring:

```bash
python3 scripts/run_delivery_checks.py outputs/<run-id> --language zh
```

Render implemented-feature PRD HTML before final validation when `prd.html` is requested:

```bash
python3 scripts/render_prd_html.py outputs/<run-id>
```

## Required Behavior

- Run `python3 scripts/preflight_tools.py` before full-loop iteration, embedded host evaluation, or release checks.
- Use `python3 scripts/preflight_tools.py --strict` before release validation so required `setup_required`, `unavailable`, or `skipped` capabilities block the release check.
- Run `python3 scripts/run_delivery_checks.py` for final run-folder validation whenever a run folder exists.
- For implemented-feature PRD folders, validate that outputs live directly under `outputs/<run-id>`, PRD Markdown has one top-level title, `prd.html` is a document rendering, images or `占位图` blocks remain inline, no detached screenshot list exists, and screenshot names use content plus concrete state such as `文件上传-上传中.png`.
- Do not leave validation placeholders after commands run.
- Record every command and result using `artifacts/tool-result-contract.md`.

## UI Visual Checks

For compatibility HTML UI deliverables, the delivery orchestrator runs:

```bash
python3 scripts/validate_prototype_visual.py outputs/<run-id>
```

The visual validator checks every supported compatibility HTML file in the run folder, including offline `index.html` entries, unless `--prototype <file>` is used to isolate one platform. It captures screenshots and records DOM smoke evidence for each viewport: body text length, visible interactive controls, horizontal overflow, console errors, page errors, access-state leakage from unauthenticated account triggers, editable `annotationConfig.notes`, body-only marker popovers, side-panel outside-click closing, and annotation overflow. Source-backed UI previews should run through the host dev/preview/Storybook/simulator path, then use `python3 scripts/validate_ui_preview.py <preview-url-or-file> --run-folder outputs/<run-id>` when a browser target is available; record equivalent simulator evidence under `visual_validation` when it is not. For source-extracted HTML handoffs, run `python3 scripts/extract_ui_region.py --target <preview-url-or-file> --selector '<css-selector>' --output outputs/<run-id>/prototype-<platform>.html --run-folder outputs/<run-id>`, which writes source-region and extracted-region screenshots plus a `region_diff` comparison. The target may be an isolated preview or a user-approved implementation already running in the host repository. Add repeated `--interaction` arguments for dynamic behavior that matters; the extraction report then replays those actions on both the source preview and extracted HTML and compares the resulting region screenshots. Then validate both the preview target and extracted HTML. Browser automation defaults to Playwright-managed cached browsers; use a system browser only with explicit `--browser-channel` or `PLAYWRIGHT_BROWSER_CHANNEL`. Source preview navigation defaults to `domcontentloaded` with a bounded navigation timeout so dev-server HMR or long-lived requests do not hang validation; use `--wait-until networkidle` only for static pages where that state is reliable.

When `run_delivery_checks.py` skips a duplicate visual run because a previous visual validation already passed, it must read `visual-review/visual-report.json` and confirm that the report is passed, covers every compatibility HTML file, and includes DOM smoke evidence, including access-state evidence. A legacy report that only proves nonblank screenshots is not enough for reuse.

If Playwright or a browser is missing, run:

```bash
python3 scripts/setup_visual_validation.py
```

A skipped visual check is valid only when setup fails, browser launch is forbidden, or installation is declined.

## HTML Checks

`run_delivery_checks.py` always runs a Python `html.parser` check for compatibility HTML files. If `tidy` is available, it also records `tidy` output as optional evidence. Older `tidy` compatibility failures must not be described as browser validation failures.

For source-backed preview final checks, pass the preview target to the delivery orchestrator:

```bash
python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en> --source-preview <preview-url-or-file>
```
