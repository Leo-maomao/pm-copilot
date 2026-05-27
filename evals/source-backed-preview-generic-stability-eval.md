# Evaluation Case: Source-Backed Preview Generic Stability

## Metadata

| Field | Value |
|---|---|
| Case ID | source-backed-preview-generic-stability |
| Scenario | generic-repo-backed-preview-validation |
| Platform | Web / H5 / App / Mini Program |
| Product Area | General repo-backed UI delivery |
| Fixture Scope | None |
| PM User Type | AI product manager / Senior PM |
| Risk Profile | Operations / Data quality / Security |
| Created | 2026-05-27 |
| Last Updated | 2026-05-27 |

## Raw Request

```text
Use an arbitrary host product repository as a temporary pressure fixture. Pick one realistic UI requirement from its current frontend source, produce a source-backed preview or delta, and turn any PM Copilot weakness into a generic improvement. The borrowed product must not become PM Copilot's default domain, route vocabulary, business model, or examples.
```

## Context Files

- `<host-project>/package.json` or equivalent project manifest
- `<host-project>/<frontend-entry>`
- `<host-project>/<affected-route-or-screen>`
- `<host-project>/<affected-component-or-widget>`
- `<host-project>/<style-or-design-token-source>`

## Expected Workflow

- Classify the run as repo-backed and identify the host project only inside runtime evidence.
- Inspect relevant frontend source before deciding artifact mode.
- Use source-backed preview/delta by default when host frontend source can render.
- Keep production flows read-only unless the user explicitly requests implementation.
- Record host mutation policy, preview files changed, source-to-demo mapping, visual validation, and limitations in `run-log.yaml`.
- Convert PM Copilot defects into generic validators, contracts, guardrails, workflow rules, or eval cases.
- Remove or ignore generated host-specific `outputs/` evidence after the generic improvement is captured.

## Required Artifacts

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/run-log.yaml`
- `outputs/<run-id>/tool-results/delivery-check-report.json`
- `outputs/<run-id>/visual-review/source-preview-report.json` when source-backed preview exists

## Artifact Expectation Matrix

| Artifact | Required When | Validation |
|---|---|---|
| `prd.md` | Required after the selected host requirement is safe to draft. | `python3 scripts/validate_outputs.py outputs/<run-id> --language <en|zh>` |
| Source-backed UI preview/delta | Required when frontend source exists and UI delivery is in scope. | `python3 scripts/validate_ui_preview.py <preview> --run-folder outputs/<run-id>` |
| Compatibility HTML | Allowed only when raw request asks for portable HTML, no frontend source exists, or source rendering is concretely blocked. | `python3 scripts/validate_prototype_visual.py outputs/<run-id>` |
| `run-log.yaml` | Required to preserve host-source evidence and generalization boundary. | `python3 scripts/run_delivery_checks.py outputs/<run-id> --language <en|zh>` |

## Known Risks

- Treating a borrowed host product as PM Copilot's target product.
- Rewriting production flows when only review-preview work was requested.
- Falling back to standalone HTML while renderable frontend source exists.
- Claiming source fidelity without browser or screenshot evidence.
- Letting host-specific path names, API vocabulary, business nouns, or route names leak into generic docs, prompts, templates, tools, workflow, agents, skills, or guardrails.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Host-source inspection | 5 / 5 |
| Source-backed artifact mode | 5 / 5 |
| Visual validation evidence | 4 / 5 |
| Production mutation boundary | 5 / 5 |
| Generalization boundary | 5 / 5 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-27 | fixture-name-contamination | High | A borrowed host project name can persist in evals or evidence and make PM Copilot look domain-specific. | Replace named fixture evals with a generic source-backed preview stability eval and keep host terms out of tracked assets. |

## Pass Criteria

- Host-specific names, local absolute paths, business nouns, route names, and API terms do not appear in generic PM Copilot surfaces.
- Repo-backed UI delivery uses source-backed preview/delta when renderable source exists.
- `run-log.yaml` records concrete source files, render entrypoint, preview surface, preview files changed, visual-validation command, and limitations.
- Standalone HTML fallback is justified by raw request or concrete source-rendering blocker.
- `python3 scripts/run_delivery_checks.py outputs/<run-id> --language <en|zh> --source-preview <preview-url-or-file>` passes when a preview exists.
- `python3 scripts/validate_repo.py` passes and would fail if fixture-specific terms leaked into core tracked assets.

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pending |
| Notes | Generic replacement for named host-fixture preview stability checks. Future host runs should update this only with domain-neutral evidence summaries. |
