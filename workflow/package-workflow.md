# Delivery Check Workflow

This workflow verifies that the PM-facing deliverables are complete and consistent.

## Inputs

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/prototype-<platform>.html`, when a user-facing prototype is relevant
- Optional exports such as `tracking-plan.csv` or `user-flow.mmd`
- Internal `run-log.yaml`, when available

## Delivery Check Steps

1. Verify `prd.md` exists and follows the PRD contract.
2. Verify the prototype exists when the requirement has user-facing UI.
3. Verify PRD and prototype agree on scope, states, logic, interaction rules, tracking, and blockers.
4. Verify the PRD links the prototype and says that detailed page-level design and interaction annotations live inside the prototype.
5. Verify optional exports are genuinely useful or explicitly requested.
6. Verify readiness fields are separate: PRD status, engineering handoff status, and launch status.
7. Verify content source, review status, disclaimer status, and launch impact are recorded when relevant.
8. Verify structured review findings are reflected in the PRD with artifact, evidence, owner, required-before phase, and status.
9. Verify validation commands and limitations are recorded consistently in PRD and run log.

## Default Delivery Files

- `prd.md`
- `prototype-<platform>.html`
- `run-log.yaml` as internal trace only

## Legacy Files

Do not generate `pm-package.md`, `final-package-summary.md`, `review-checklist.md`, `tracking-plan.md`, `user-flow.md`, or other split Markdown files by default. Keep the handoff centered on `prd.md` and the prototype unless the user explicitly asks for an export.
