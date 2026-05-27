# Evaluation Case: Source-Backed Host Preview Stability

## Metadata

| Field | Value |
|---|---|
| Case ID | source-backed-host-preview-stability |
| Scenario | source-backed preview validation in a borrowed host project fixture |
| Platform | Web |
| Product Area | General repo-backed UI delivery |
| Fixture Scope | Fixture-scoped |
| PM User Type | AI product manager |
| Risk Profile | Operations / Data quality |
| Created | 2026-05-26 |
| Last Updated | 2026-05-26 |

## Fixture Isolation Terms

- `/Users/mac142/Desktop/ai-video`
- `ai-video`
- `SeaArt`
- `seavideo`
- `EpisodeStoryboard`
- `StoryboardToolbar`
- `storyboard-batch`
- `pm-copilot/storyboard`
- `批量出片`
- `分镜`

## Raw Request

```text
借用一个本地主机项目，你自己想一个真实需求做测试，然后自我迭代。注意：宿主项目只能作为能力压测夹具，不能进入 PM Copilot 的通用产品事实。
```

## Context Files

- `<host-project>/README.md`
- `<host-project>/package.json`
- `<host-project>/src/**/affected-route-or-page.*`
- `<host-project>/src/**/affected-component.*`
- `<host-project>/src/**/design-system-or-ui-components.*`
- `<host-project>/src/**/global-styles.*`

## Expected Workflow

- Classify the run as `repo-backed`.
- Treat the borrowed host as a fixture, not as PM Copilot's target product, default scenario, or permanent product context.
- Inspect the host frontend before deciding artifact mode.
- Select a realistic product requirement from current host context without copying the host's domain into generic PM Copilot docs, templates, prompts, skills, or workflow defaults.
- Prefer a source-backed preview/delta when frontend source exists and UI evidence is part of the iteration.
- Keep host production flows read-only unless production implementation is explicitly in scope.
- Generate `prd.md` and `run-log.yaml` with concrete host-source evidence.
- Run host type/lint checks when affected files are in a typed/linted frontend.
- Run `validate_ui_preview.py` for source-backed previews and `run_delivery_checks.py --source-preview`.
- Convert any discovered PM Copilot defect into a validator, scorecard, guardrail, workflow rule, or regression case.

## Required Artifacts

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/run-log.yaml`
- `outputs/<run-id>/tool-results/delivery-check-report.json`
- `outputs/<run-id>/visual-review/source-preview-report.json` when source-backed UI preview exists
- Host preview/delta file list recorded under `run-log.yaml`

## Known Risks

- Treating a dirty host repository as safe to rewrite.
- Letting a host product's domain vocabulary, paths, APIs, or business assumptions leak into PM Copilot's universal docs, templates, prompts, workflow, or default examples.
- Creating a generic-looking PRD that ignores the real host route, component, state, permission, and API constraints.
- Claiming exact backend behavior when the inspected host contract does not expose it.
- Passing delivery validation while missing source-backed UI preview evidence.
- Counting a host-specific workaround as a universal PM Copilot default instead of turning the underlying failure into a general guardrail.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Delivery | 23 / 32 |
| PRD | 31 / 40 |
| Metrics and tracking | 21 / 28 |
| UI delivery | 24 / 32 |
| Delivery review inside PRD | 15 / 20 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-26 | validator-nested-yaml-false-positive | High | `validate_outputs.py` misread nested `artifact_delta:` and `validation_delta:` as prose scalars because `\s+` crossed line breaks. | Restrict scalar detection whitespace to non-newline spaces. |
| 2026-05-26 | scorecard-ui-evidence-gap | Medium | Improvement scorecard counted runtime evidence but did not surface explicit skipped source-backed UI evidence. | Add visual-required and explicit UI-gap risk detection to `agent_improvement_scorecard.py`. |
| 2026-05-26 | host-preview-e2e-noise | Medium | Source preview initially failed with black first capture, external SDK console errors, authenticated data requests, dev overlay pollution, and compact button wrapping. | Add an isolated source-backed preview route, stabilize E2E preview mode, limit global background queries to relevant surfaces, and revalidate with `validate_ui_preview.py`. |
| 2026-05-26 | fixture-specific-leakage-risk | High | A borrowed host fixture can accidentally become part of PM Copilot's general product story or examples. | Add a generalization boundary and validate that fixture-specific vocabulary stays out of core docs, prompts, templates, tools, workflow, agents, and skills. |

## Pass Criteria

- Host context cites real fixture files during the run without turning them into PM Copilot defaults.
- Core PM Copilot docs, prompts, templates, tools, agents, skills, and workflow remain domain-neutral.
- Host-specific names, local absolute paths, and business-domain terms are allowed only in generated runtime evidence or explicitly fixture-scoped eval cases.
- The PRD identifies current host behavior, existing entry points, affected surface, state model, API/contract gaps, and engineering blockers without inventing product state.
- Tracking plan avoids prompt text, asset URLs, raw balances, raw backend error details, and other host-sensitive payloads.
- Run log records source-backed preview files, host mutation policy, visual validation command, screenshots, and limitations.
- `python3 scripts/validate_outputs.py outputs/<run-id> --language zh` passes for Chinese runs.
- `python3 scripts/run_delivery_checks.py outputs/<run-id> --language zh --source-preview <preview-url>` passes when a browser preview exists.
- `python3 scripts/agent_improvement_scorecard.py` shows runtime visual evidence and no explicit UI evidence gap.
- `python3 scripts/validate_repo.py` fails if fixture-specific vocabulary leaks into the generic PM Copilot surface.

## Latest Result

| Field | Value |
|---|---|
| Run ID | source-backed-host-preview-20260526-1710 |
| Status | Passed |
| Notes | PRD/run-log, source-backed host preview route, browser validation, host type check, and delivery checks with `--source-preview` passed. Launch/engineering blockers remain visible when backend contract facts are unconfirmed. |
