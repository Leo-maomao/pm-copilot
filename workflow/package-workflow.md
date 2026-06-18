# Delivery Check Workflow

This workflow verifies that the PM-facing deliverables are complete and consistent.

## Inputs

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/prd.html` when browser-readable PRD delivery is requested
- `outputs/<run-id>/catalog.md` or `outputs/<run-id>/reference.md` when structured reference is the primary delivery
- Document prototype HTML when the requested prototype is a browser-readable reference document
- UI deliverable reference, when user-facing UI is relevant: source-backed preview/delta files by default, or `outputs/<run-id>/prototype-<platform>.html` for compatibility standalone/fallback mode
- Optional exports such as `tracking-plan.csv` or `user-flow.mmd`
- Internal `run-log.yaml`, when available

## Delivery Check Steps

1. Verify `prd.md` exists and follows the PRD contract when PRD is in scope. If the user explicitly requested no PRD, verify the structured reference or document prototype is the primary delivery.
2. For implemented-feature PRD delivery, verify implementation evidence exists in the run log and PRD, and that visible branch behavior is represented as requirements, acceptance criteria, or explicit gaps.
3. For implemented-feature PRD delivery, verify output files are under `outputs/<run-id>/` or embedded `pm-copilot/outputs/<run-id>/`, follow `templates/implemented-feature-prd-template.md`, and use `scripts/render_prd_html.py` when `prd.html` is present.
4. Verify `prd.html` exists when requested and renders as a normal readable PRD document, not a UI prototype or screenshot appendix.
5. Verify `prd.html` preserves complete tables, renders Mermaid diagrams, uses local image paths, supports click-to-fullscreen for real images, and keeps images/placeholders inline at the relevant PRD position.
6. Verify missing screenshots use only the inline `占位图` block, real images live under `assets/`, and state screenshot names use object plus concrete state such as `文件上传-上传中.png` instead of `文件上传-状态.png`.
7. Verify the UI deliverable exists or is recorded when the requirement has user-facing UI.
8. Verify PRD and UI deliverable agree on scope, states, logic, interaction rules, tracking, and blockers.
9. Verify the PRD links the UI deliverable and says that detailed page-level design and interaction annotations live inside it.
10. For document-class delivery, verify the structured reference or document prototype includes source facts, product decisions, source/review status, typed attention points, change log, and completeness check.
11. Verify optional exports are genuinely useful or explicitly requested.
12. Verify readiness fields are separate: PRD status, engineering handoff status, and launch status.
13. Verify content source, review status, disclaimer status, and launch impact are recorded when relevant.
14. Verify structured review findings are reflected in the PRD with artifact, evidence, owner, required-before phase, and status.
15. Verify validation commands and limitations are recorded consistently in PRD and run log.
16. Verify tool preflight was run for final/full-loop delivery, or that an explicit reason is recorded.
17. Run or verify `python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>` and inspect `tool-results/delivery-check-report.json`.
18. For UI deliverables, verify browser screenshot/visual validation ran, or that setup was attempted/guided before a skipped status was recorded with the exact tooling limitation.
19. When requested, verify `dev-tasks.yaml` follows the development task contract and `launch-decision.yaml` follows the launch decision contract.

## Default Delivery Files

- `prd.md`
- `prd.html` when browser-readable PRD delivery is requested
- Structured reference or document prototype when PRD is not in scope
- UI deliverable reference; `prototype-<platform>.html` only for compatibility standalone/fallback mode
- `run-log.yaml` as internal trace only
- Optional `dev-tasks.yaml` for controlled engineering handoff
- Optional `launch-decision.yaml` for release decision support

## Legacy Files

Do not generate `pm-package.md`, `final-package-summary.md`, `review-checklist.md`, `tracking-plan.md`, `user-flow.md`, or other split Markdown files by default. Keep the handoff centered on `prd.md` and the UI deliverable unless the user explicitly asks for an export.
