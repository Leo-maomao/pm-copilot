# Evaluation Case: <Scenario Name>

## Metadata

| Field | Value |
|---|---|
| Case ID |  |
| Scenario |  |
| Platform | Web / H5 / App / Mini Program / Cross-platform |
| Product Area |  |
| Created |  |
| Last Updated |  |
| Fixture Scope | None / Fixture-scoped / Public generic |
| PM User Type | Novice PM / AI product manager / Senior PM / Growth PM / Data PM / Ops PM / Founder-operator |
| Risk Profile | Normal / Payment / Privacy / Security / Legal / Compliance / Regulated content / Operations / Data quality |

## Fixture Isolation Terms

Use this section only when `Fixture Scope` is `Fixture-scoped`. List borrowed host project names, local path segments, route prefixes, API vocabulary, brand terms, and domain phrases that must not leak into PM Copilot's universal surface.

- `<fixture-project-name>`

## Raw Request

```text
Paste the original realistic product request here.
```

## Context Files

- `context/product-context.local.yaml`

## Expected Workflow

- Discovery and clarification
- Preserve the generalization boundary: fixture-specific host facts may shape this eval, but must not become generic PM Copilot defaults.
- PRD
- Metrics and tracking sections inside PRD
- Flow diagrams inside PRD, when useful
- UI delivery
- Delivery check

## Required Artifacts

- `outputs/<run-id>/prd.md`
- UI deliverable reference: source-backed preview/delta files recorded in `run-log.yaml` when frontend source exists, or `outputs/<run-id>/prototype-<platform>.html` only for compatibility HTML mode
- `outputs/<run-id>/run-log.yaml` when trace is useful
- Optional exports such as `tracking-plan.csv` or `user-flow.mmd` when useful

## Artifact Expectation Matrix

| Artifact | Required When | Validation |
|---|---|---|
| `prd.md` | Requirement, review, launch, or engineering handoff is requested after clarification gates pass. | `python3 scripts/validate_outputs.py outputs/<run-id>` |
| UI deliverable | UI behavior, surface fit, visual parity, or interaction states are in scope. | `python3 scripts/validate_prototype_visual.py outputs/<run-id>` or `python3 scripts/validate_ui_preview.py <preview> --run-folder outputs/<run-id>` |
| `catalog.md` or `catalog.html` | Structured reference, model matrix, API catalog, parameter table, data dictionary, or vendor inventory is the requested handoff. | `python3 scripts/validate_outputs.py outputs/<run-id>` |
| `dev-tasks.yaml` | Engineering handoff, implementation planning, issue creation, or make-ready-for-engineering is requested. | `python3 scripts/run_delivery_checks.py outputs/<run-id>` |
| `launch-decision.yaml` | Release readiness, go/no-go support, rollout, rollback, or launch approval risk is in scope. | `python3 scripts/run_delivery_checks.py outputs/<run-id>` |
| `tracking-plan.csv` or PRD tracking table | Metrics, analytics, experiment, conversion, audit, or behavioral event review is in scope. | `python3 scripts/validate_outputs.py outputs/<run-id>` |

## Known Risks

- 
- Fixture-specific product details leaking into generic PM Copilot docs, prompts, templates, tools, agents, skills, or workflow.

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

## Pass Criteria

- The agent asks or records high-impact clarification questions.
- The agent stops before downstream generation when must-answer questions remain open.
- The agent stops before `Ready for engineering` when engineering-blocking confirmations remain open, unless the user explicitly asks for a draft with confirmation risk.
- PRD status, engineering handoff status, and launch status are recorded separately.
- Launch-only blockers do not get hidden behind `Ready for engineering`; they remain visible with owner and required confirmation.
- `prd.md` and the UI deliverable are generated after the clarification gate passes.
- Assumptions are explicit.
- Confirmed MVP scope is separated from optional, conditional, and future scope.
- Surface entry, navigation visibility, permission or eligibility states, and fallback behavior are explicit for existing-product changes.
- Reference or regulated content records source status, review owner, review status, disclaimer status, and launch impact.
- Tracking plan avoids forbidden sensitive properties.
- Tracking plan marks proposed taxonomy when no existing analytics convention was loaded.
- UI deliverable matches selected platform.
- UI visual validation is run with screenshots/diff evidence, or setup was attempted and the skipped reason is documented.
- PRD and UI deliverable agree on scope, logic, interactions, tracking, and blockers.
- Development handoff and launch decision artifacts preserve blockers when generated.
- Review findings include artifact, evidence, owner, required-before phase, and status, or an explicit no-finding summary.
- Validation results are concrete and consistent between PRD and run log.
- Fixture-specific names, local paths, domain nouns, route names, APIs, or business assumptions stay out of generic PM Copilot surfaces unless the eval is explicitly fixture-scoped.

## Latest Result

| Field | Value |
|---|---|
| Run ID |  |
| Status | Pass / Fail / Partial |
| Notes |  |
