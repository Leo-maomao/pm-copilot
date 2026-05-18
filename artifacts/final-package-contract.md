# Legacy Package Contract

PM Copilot no longer creates a consolidated `pm-package.md` or `final-package-summary.md` by default.

Default delivery is:

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/prototype-<platform>.html` when UI is in scope
- `outputs/<run-id>/run-log.yaml` as internal trace only

Use this contract only when the user explicitly asks for a legacy consolidated package or an external workflow requires one.

## Legacy Package Rules

- Do not duplicate the full PRD. Link `prd.md` and summarize only what helps navigation.
- Do not duplicate prototype annotations. Link the HTML prototype and summarize covered screens/states.
- Preserve readiness separation: PRD status, engineering handoff status, and launch status.
- Keep unresolved assumptions, open confirmations, and validation limitations visible.
- Preserve content source, review status, disclaimer status, and launch impact when those items appear in `prd.md`.
- Preserve structured review findings with artifact, evidence, owner, required-before phase, and status.
- Clearly label the file as a legacy convenience package, not the canonical PM handoff.
