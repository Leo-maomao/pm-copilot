# PM Copilot Use Cases

This page is written for PM work, not for explaining internal architecture.
Use these prompts as starting points and let PM Copilot choose task mode, autonomy level, and execution path.

## 1. New Feature PRD

Prompt:

```text
We want to add <feature> for <target users>. The business goal is <goal>. Please inspect available product context, ask blocking questions first, then create a PRD and UI delivery plan.
```

Expected artifacts: `prd.md`, UI deliverable reference, `run-log.yaml`.
Context needed: current product behavior, target user, platform, business goal, constraints, metrics.
Validation: `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en`.

## 2. Implemented Feature To PRD

Prompt:

```text
The feature is already implemented on this branch. Inspect the diff, relevant code, screenshots/assets, tests, and validation evidence. Reconstruct the implementation into PRD Markdown and generate prd.html.
```

Expected artifacts: `prd.md`, `prd.html`, `run-log.yaml`.
Context needed: current branch, changed files, UI entry points, screenshots/assets, tests, launch intent.
Validation: `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en`.

## 3. Existing UI Delta Delivery

Prompt:

```text
Please update the existing <surface> UX for <goal>. Reuse current components and styles. If source exists, produce a source-backed preview or delta, not a standalone redesign.
```

Expected artifacts: source-backed preview/delta reference, UI notes in PRD or run log, optional `prototype-<platform>.html` only when justified.
Context needed: frontend source, route/screen, component library, design tokens, target states.
Validation: `python3 scripts/validate_ui_preview.py <preview-url-or-file> --run-folder outputs/<run-id>`.

## 4. No-Code H5 Prototype

Prompt:

```text
We only have a product brief for <mobile flow>. Please create a PRD and H5 UI delivery artifact. Ask first if payment, privacy, legal, or core flow details are missing.
```

Expected artifacts: `prd.md`, `prototype-h5.html`, `run-log.yaml`.
Context needed: target user, entry points, main flow, edge states, copy, business rules.
Validation: `python3 scripts/validate_prototype_visual.py outputs/<run-id>`.

## 5. Tracking Plan

Prompt:

```text
Please design the tracking plan for <feature>. Include primary metric, guardrails, event names, required properties, trigger timing, privacy notes, and validation suggestions.
```

Expected artifacts: tracking table inside `prd.md` or `tracking-plan.csv` when requested.
Context needed: product goal, user actions, existing analytics taxonomy, privacy constraints.
Validation: `python3 scripts/validate_outputs.py outputs/<run-id>`.

## 6. Launch Readiness

Prompt:

```text
Review whether <feature/release> is ready to launch. Separate engineering readiness from launch readiness, list blockers, owners, validation evidence, rollback, and approval gaps.
```

Expected artifacts: review findings, optional `launch-decision.yaml`, updated readiness in PRD or run log.
Context needed: PRD, implementation state, test evidence, analytics, support/legal/payment/compliance owner status.
Validation: `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en`.

## 7. Development Handoff

Prompt:

```text
Turn this confirmed PRD and UI delivery into issue-ready engineering tasks. Preserve open blockers and do not mark anything ready if a decision is still missing.
```

Expected artifacts: `dev-tasks.yaml`, handoff summary, validation results.
Context needed: confirmed scope, PRD, UI deliverable, dependencies, technical constraints.
Validation: `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en`.

## 8. Structured Reference

Prompt:

```text
Please turn these documents into a structured reference for engineering and PM review. Capture source facts, product decisions, field dictionary, attention points, review status, and implementation notes. No PRD is needed.
```

Expected artifacts: `catalog.md`, `reference.md`, `catalog.html`, `reference.html`, or document prototype.
Context needed: source documents, owner, review status, domain rules, update cadence.
Validation: `python3 scripts/validate_outputs.py outputs/<run-id>`.

## 9. Product Review

Prompt:

```text
Review this PRD/UI delivery for PM usefulness. Identify unclear goals, missing scope, weak metrics, edge cases, risks, validation gaps, and next actions.
```

Expected artifacts: structured review findings, risk log, required fixes, go/no-go recommendation.
Context needed: artifact files, intended audience, launch/engineering expectations.
Validation: `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en`.

## 10. Competitor-Informed PRD

Prompt:

```text
We are designing <feature>. Please inspect current product context, do source-backed comparable-product research, and use the findings to recommend scope and UX direction before drafting the PRD.
```

Expected artifacts: `prd.md` with research/reference findings, product implications, and confidence.
Context needed: product goal, target market, competitors/comparable products, current product constraints.
Validation: `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en`.

## 11. AI Product Manager Self-Improvement

Prompt:

```text
This PM Copilot run exposed a reusable failure: <failure>. Please generalize it, update the right repo surfaces, add or update regression coverage, bump version, and run validation.
```

Expected artifacts: code/docs changes, eval or validator update, `VERSION`, `CHANGELOG.md`, optimization-cycle note.
Context needed: source run artifacts, user correction, failure evidence, desired durability.
Validation: `python3 scripts/validate_repo.py`.

## 12. Mixed Delivery

Prompt:

```text
I need one run that produces the PRD, UI delivery, tracking plan, dev handoff, and launch readiness view for <feature>. Choose the right order and tell me where risks block progress.
```

Expected artifacts: `prd.md`, UI delivery reference, tracking, optional `dev-tasks.yaml`, optional `launch-decision.yaml`, `run-log.yaml`.
Context needed: product context, target users, platform, metrics, UI direction, launch constraints.
Validation: `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en`.
