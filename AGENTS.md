# Repository Instructions

## Technical baseline

- Use Node 24 and pnpm workspaces. Keep TypeScript in strict mode.
- `apps/` contains user-facing applications, `packages/` contains reusable framework-independent code, and `plugins/` contains Codex plugin packages.
- `apps/manager-web` may only use the same-origin API exposed by `services/local-server`; it must not call arbitrary local or remote services. Shared framework-independent code belongs in `packages/core`.
- Markdown is the future persisted document format. Do not introduce a database, ORM, cloud SDK, telemetry SDK, or third-party model SDK without an ADR.

## Engineering rules

- Read relevant code and documentation before editing. Keep changes focused and avoid unrelated refactors.
- Code, variables, API identifiers, and commit types use English. Repository documentation uses Chinese unless a file has an established language.
- Never commit secrets, private project data, generated artifacts, local configuration, or dependency directories.
- New dependencies, persisted formats, browser permissions, network listeners, and cross-package interfaces require a decision record in `docs/decisions/`.
- Add tests in proportion to risk. Before handing off a change, run `pnpm check`, `pnpm test`, and `pnpm build`, or state why one cannot run.

## Codex skills

- Use `plugin-creator` to create or update Codex plugin packages.
- Use `frontend-ui-engineering` for user-facing management-page changes.
- Use `browser-testing-with-devtools` to validate browser-facing changes in a real browser.
- Consult `openai-docs` before changing Codex-specific integration behavior.
