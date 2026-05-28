# Delivery Check Workflow

This workflow verifies that the PM-facing deliverables are complete and consistent.

## Inputs

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/catalog.md` or `outputs/<run-id>/reference.md` when structured reference is the primary delivery
- Document prototype HTML when the requested prototype is a browser-readable reference document
- UI deliverable reference, when user-facing UI is relevant: source-backed preview/delta files by default, or `outputs/<run-id>/prototype-<platform>.html` for compatibility standalone/fallback mode
- Optional exports such as `tracking-plan.csv` or `user-flow.mmd`
- Internal `run-log.yaml`, when available

## Delivery Check Steps

1. Verify `prd.md` exists and follows the PRD contract when PRD is in scope. If the user explicitly requested no PRD, verify the structured reference or document prototype is the primary delivery.
2. Verify the UI deliverable exists or is recorded when the requirement has user-facing UI.
3. Verify PRD and UI deliverable agree on scope, states, logic, interaction rules, tracking, and blockers.
4. Verify the PRD links the UI deliverable and says that detailed page-level design and interaction annotations live inside it.
5. For document-class delivery, verify the structured reference or document prototype includes source facts, product decisions, source/review status, typed attention points, change log, and completeness check.
6. Verify optional exports are genuinely useful or explicitly requested.
7. Verify readiness fields are separate: PRD status, engineering handoff status, and launch status.
8. Verify content source, review status, disclaimer status, and launch impact are recorded when relevant.
9. Verify structured review findings are reflected in the PRD with artifact, evidence, owner, required-before phase, and status.
10. Verify validation commands and limitations are recorded consistently in PRD and run log.
11. Verify tool preflight was run for final/full-loop delivery, or that an explicit reason is recorded.
12. Run or verify `python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>` and inspect `tool-results/delivery-check-report.json`.
13. For UI deliverables, verify browser screenshot/visual validation ran, or that setup was attempted/guided before a skipped status was recorded with the exact tooling limitation.
14. When requested, verify `dev-tasks.yaml` follows the development task contract and `launch-decision.yaml` follows the launch decision contract.

## Default Delivery Files

- `prd.md`
- Structured reference or document prototype when PRD is not in scope
- UI deliverable reference; `prototype-<platform>.html` only for compatibility standalone/fallback mode
- `run-log.yaml` as internal trace only
- Optional `dev-tasks.yaml` for controlled engineering handoff
- Optional `launch-decision.yaml` for release decision support

## Legacy Files

Do not generate `pm-package.md`, `final-package-summary.md`, `review-checklist.md`, `tracking-plan.md`, `user-flow.md`, or other split Markdown files by default. Keep the handoff centered on `prd.md` and the UI deliverable unless the user explicitly asks for an export.
