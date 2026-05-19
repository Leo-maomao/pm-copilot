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

## Required Behavior

- Run `python3 scripts/preflight_tools.py` before full-loop iteration, embedded host evaluation, or release checks.
- Use `python3 scripts/preflight_tools.py --strict` before release validation so required `setup_required`, `unavailable`, or `skipped` capabilities block the release check.
- Run `python3 scripts/run_delivery_checks.py` for final run-folder validation whenever a run folder exists.
- Do not leave validation placeholders after commands run.
- Record every command and result using `artifacts/tool-result-contract.md`.

## Visual Prototype Checks

For UI prototypes, the delivery orchestrator runs:

```bash
python3 scripts/validate_prototype_visual.py outputs/<run-id>
```

The visual validator checks every supported prototype file in the run folder unless `--prototype <file>` is used to isolate one platform. It captures screenshots and records DOM smoke evidence for each viewport: body text length, visible interactive controls, horizontal overflow, console errors, page errors, and access-state leakage from unauthenticated account triggers. If an auto-detected system browser fails to launch, it should fall back to Playwright's default/bundled Chromium path and attempt setup before reporting a browser limitation.

When `run_delivery_checks.py` skips a duplicate visual run because a previous visual validation already passed, it must read `visual-review/visual-report.json` and confirm that the report is passed, covers every prototype, and includes DOM smoke evidence, including access-state evidence. A legacy report that only proves nonblank screenshots is not enough for reuse.

If Playwright or a browser is missing, run:

```bash
python3 scripts/setup_visual_validation.py
```

A skipped visual check is valid only when setup fails, browser launch is forbidden, or installation is declined.

## HTML Checks

`run_delivery_checks.py` always runs a Python `html.parser` check for prototype files. If `tidy` is available, it also records `tidy` output as optional evidence. Older `tidy` compatibility failures must not be described as browser validation failures.
