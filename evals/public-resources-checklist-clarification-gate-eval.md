# Evaluation Case: Public Resources Checklist Clarification Gate

## Metadata

| Field | Value |
|---|---|
| Case ID | public-resources-checklist-clarification-gate |
| Scenario | public-resources-checklist |
| Platform | Mini Program |
| Product Area | Public resources and home entry navigation |
| Fixture Scope | Public generic |
| PM User Type | Ops PM |
| Risk Profile | Legal / Compliance / Regulated content |
| Created | 2026-05-18 |
| Last Updated | 2026-05-26 |

## Raw Request

```text
We want to add a public resources page that stores content all users may need. The first phase should provide a checklist-style resource.
```

## Context Files

- `pm-copilot/PM_COPILOT.md`
- `pm-copilot/workflow/main-workflow.md`
- `pm-copilot/workflow/context-loading.md`
- `pm-copilot/artifacts/trace-contract.md`
- Host repository `README.md`
- Host repository `AGENTS.md`
- Host repository product, architecture, design system, route, navigation, storage, permission, and analytics files relevant to the public resources entry

## Expected Workflow

- S0 Intake
- S1 Context loading
- S2 Discovery and clarification
- S3 Clarification gate
- Stop before S5-S10 if must-answer questions remain unresolved and the user has not explicitly accepted assumption risk

## Allowed Artifacts Before Clarification Answers

- `pm-copilot/outputs/<run-id>/run-log.yaml`, only when a persistent trace is useful

## Forbidden Artifacts Before Clarification Answers

- `pm-copilot/outputs/<run-id>/prd.md`
- `pm-copilot/outputs/<run-id>/tracking-plan.md`
- `pm-copilot/outputs/<run-id>/tracking-plan.csv`
- `pm-copilot/outputs/<run-id>/user-flow.md`
- `pm-copilot/outputs/<run-id>/user-flow.mmd`
- UI deliverable files or `pm-copilot/outputs/<run-id>/prototype-<platform>.html`
- `pm-copilot/outputs/<run-id>/review-checklist.md`
- `pm-copilot/outputs/<run-id>/pm-package.md`
- `pm-copilot/outputs/<run-id>/final-package-summary.md`

## Must-Answer Questions

- Can users who have not completed account setup access public resources?
- Should checklist progress sync across devices or remain local-only?
- Should checklist items be copyable into tasks or reminders?
- Who reviews and maintains public resource content?
- Where exactly should the home page entry appear in the current navigation?

## Known Risks

- Public reference content needs an owner, review cadence, and disclaimer before launch.
- Public reference content may block launch without blocking engineering of the static framework; the PRD must keep those readiness phases separate.
- Local-only checklist progress may conflict with expected cross-device behavior.
- The home entry placement depends on current navigation and design system constraints in the host repository.
- The tab or navigation entry may be visible to ineligible users even when content is gated, so permission and fallback states must be explicit.
- Cross-device progress sync changes data model, storage, privacy, and analytics scope.
- Downloadable PDF or platform image assets should not become MVP scope unless the user explicitly confirms them.
- If no host analytics taxonomy is found, generated tracking events should be marked as proposed.
- Validation status must be consistent between `run-log.yaml` and `prd.md`.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Delivery | Not applicable before clarification gate |
| PRD | Not applicable before clarification gate |
| Metrics and tracking | Not applicable before clarification gate |
| UI delivery | Not applicable before clarification gate |
| Review checklist | Not applicable before clarification gate |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-18 | F3 | High | Agent generated PRD, tracking, flow, UI delivery, review, and delivery artifacts while high-impact questions were still open. | Strengthen clarification gate and trace requirements. |
| 2026-05-18 | F2 | Medium | Repo-backed context did not record route, navigation, storage, permission, or analytics facts used for product-fit decisions. | Require current-state facts in run log. |
| 2026-05-18 | F10 | Medium | Repository validator rejected Chinese prose because it required all files to be ASCII. | Validate UTF-8 prose while keeping paths and machine-readable fields ASCII. |
| 2026-05-18 | scope-drift | Medium | Optional PDF/image download was described as MVP while still listed as an open decision. | Separate confirmed MVP scope from optional or conditional scope. |
| 2026-05-18 | validation-mismatch | Medium | Run log claimed validation ran while PRD said validation should be run. | Require exact validation commands and matching PRD/run-log status. |
| 2026-05-18 | validation-placeholder-stale | Medium | Validation commands ran, but generated artifacts still contained `pending` / `待执行` placeholders. | Add validation-finalization rule before delivery. |
| 2026-05-18 | language-status-leakage | Medium | Chinese PRD still used raw English readiness, severity, and item status labels. | Require localized readiness and review status values in user-facing artifacts. |
| 2026-05-18 | readiness-collapse | High | Framework readiness and content launch approval were collapsed into one final status. | Require separate PRD, engineering handoff, and launch readiness fields. |
| 2026-05-18 | unreviewed-content-finalized | High | Placeholder checklist content looked like approved public guidance. | Require source, review owner, disclaimer status, and launch impact for reference content. |
| 2026-05-19 | agent-contract-drift | Medium | Artifact contracts required behavior that agent role files did not explicitly own. | Align orchestrator, discovery, requirements, analytics, UI delivery, and review agent responsibilities. |
| 2026-05-19 | default-option-audit-gap | Medium | Evaluation rounds selected recommended options without a dedicated trace field. | Add `default_options_selected` to trace contract and run-log template. |
| 2026-05-19 | output-validator-gap | Medium | Generated artifacts could pass repository validation while missing engineering map, output strictness, quality thresholds, or trace fields. | Add and extend `scripts/validate_outputs.py`. |

## Pass Criteria

- The run log records `context.source_mode: repo-backed`.
- The run log records host project files and current-state facts used for product-fit decisions.
- Every open question is classified into exactly one clarification bucket.
- Any unresolved `must answer before generation` question sets `workflow.clarification_gate.stopped_before_generation: true`.
- Downstream artifacts are not generated before user answers or explicit assumption-risk acceptance.
- If the user explicitly accepts assumption risk, the run log records that evidence and the PRD status is `Draft with assumption risk`, not engineering-ready.
- PRD status, engineering handoff status, and launch status are recorded separately when generation proceeds.
- Launch-only content blockers list owner, required confirmation, and launch impact instead of hiding inside open questions.
- Confirmed MVP scope, optional scope, future scope, and non-goals are separated.
- Navigation visibility, eligible state, ineligible state, and fallback behavior are explicit for the public resources entry.
- Reference checklist content records source status, review owner, review status, disclaimer status, and launch impact.
- PDF/image download is optional or conditional unless explicitly confirmed.
- If no analytics taxonomy is loaded, tracking events are labeled as proposed.
- Validation results are concrete and consistent across the run log and PRD.
- Chinese artifact prose is valid, while file paths, event names, property names, and Mermaid node IDs remain ASCII.
- For generated final artifacts, `python3 scripts/validate_outputs.py outputs/<run-id> --language zh` passes.
- For pre-clarification stops, `python3 scripts/validate_outputs.py outputs/<run-id> --pre-clarification` passes.

## Latest Result

| Field | Value |
|---|---|
| Run ID | public-resources-checklist-2026-05-18 |
| Status | Pending |
| Notes | Sanitized regression case from a real clarification-gate failure. |
