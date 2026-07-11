# Evaluation Case: PRD Automated Screenshot Recovery

## Metadata

| Field | Value |
|---|---|
| Case ID | eval-040 |
| Scenario | prd-automated-screenshot-recovery |
| Platform | Cross-project web UI |
| Product Area | Generic product documentation |
| Created | 2026-07-11 |
| Last Updated | 2026-07-11 |
| Fixture Scope | Fixture-scoped |
| PM User Type | AI product manager |
| Risk Profile | Documentation quality and credential safety |

## Fixture Isolation Terms

- screenshot-recovery-fixture

This eval may use any runnable host product as pressure context. Host names, routes, ports, tokens, account data, browser brands, and UI vocabulary must remain fixture-scoped and must not enter generic PM Copilot rules.

## Raw Request

```text
Write a PRD for the implemented UI change and include the relevant product images. The browser integration may be missing, the page may require login, and a small element screenshot may be blurry. Use placeholders only if no capture path works.
```

## Expected Workflow

- Inspect the host repository and discover its runnable UI, browser/e2e tooling, target route, fixture state, and authentication path.
- Attempt a real automated screenshot before emitting a placeholder.
- If the browser plugin or automation dependency is missing, run its supported setup or installation flow and retry.
- If authentication blocks the state, ask the user to sign in or provide a task-scoped token through an approved secure channel, then resume automation.
- Keep credentials out of generated artifacts, logs, source-controlled environment files, image names, and final responses.
- Validate clarity at normal PRD width. Retry blank, clipped, blurred, or unreadably small captures with a larger viewport, higher device scale, focused target, or contextual full-window crop.
- Use manual capture only after automated recovery fails.
- Use the exact inline placeholder only after automated capture, setup or repair, authentication recovery, and manual capture are all unavailable or unsuccessful.
- Validate generated artifacts with `python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>`.

## Required Artifacts

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/prd.html` when requested or required by the delivery mode
- real local images under `outputs/<run-id>/assets/` when capture succeeds
- `outputs/<run-id>/run-log.yaml` recording capture attempts and non-sensitive limitations

## Known Risks

- The agent may immediately emit placeholders after a missing-plugin error.
- The agent may ask for manual screenshots before trying supported setup.
- The agent may mistake an API key for a browser session token or expose a token in logs.
- The agent may embed a tiny element screenshot that becomes blurred in the PRD.
- The agent may hardcode a canvas, fixed port, browser, or framework into generic behavior.

## Pass Criteria

- Real automated capture is the default path.
- Missing tooling triggers supported setup or installation plus retry.
- Missing authentication triggers a user login or task-scoped-token checkpoint plus resume.
- No credential value appears in generated artifacts or user-visible output.
- Blurred, blank, clipped, or undersized screenshots are retried rather than accepted.
- Manual capture precedes placeholder fallback.
- Placeholder output is used only after every supported capture and recovery path fails.
- Generic PM Copilot source remains host-project and framework agnostic.
- `python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>` passes for the generated run folder.

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-07-11 | placeholder-before-capture | High | PRD guidance defaulted to inline placeholders and a later human replacement pass even when browser automation could capture the real UI. | Reordered the workflow to automated capture, setup recovery, authentication recovery, manual fallback, then placeholder. |
| 2026-07-11 | unreadable-element-capture | High | A low-resolution element screenshot was technically valid but visibly blurred when embedded beside a clearer full-window screenshot. | Added clarity gates and mandatory retry strategies for small or blurred captures. |

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Added from a real user correction and successful automated browser capture run. |
