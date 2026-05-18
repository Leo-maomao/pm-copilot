# Changelog

All notable changes to PM Copilot are documented in this file.

The project uses semantic versioning with pre-1.0 alpha releases. See `docs/versioning.md` for upgrade rules, compatibility policy, and release checklist.

## [0.1.0-alpha.4] - 2026-05-18

### Added

- Added adapter installer:
  - `scripts/install_adapter.py`
- Added embedded install documentation for one-command setup.

### Changed

- Embedded mode no longer requires manual adapter copying; users can install Codex, Claude Code, Cursor, or all adapters with one command.

## [0.1.0-alpha.3] - 2026-05-18

### Added

- Added canonical cross-platform entry:
  - `PM_COPILOT.md`
- Added embedded host-project adapters:
  - `adapters/codex/AGENTS.snippet.md`
  - `adapters/claude-code/CLAUDE.snippet.md`
  - `adapters/cursor/.cursor/rules/pm-copilot.mdc`
  - `adapters/cursor/CURSOR_RULE.snippet.md`
- Added embedded usage guide:
  - `docs/embedded-use.md`

### Changed

- `AGENTS.md` is now a thin Codex standalone shim that points to `PM_COPILOT.md`.
- Direct-use docs no longer require users to remember or say `Use PM Copilot`; natural PM requests should trigger the workflow once adapters are installed.
- Documentation now distinguishes standalone mode from embedded mode.
- Validator now requires canonical entry and adapter files.

## [0.1.0-alpha.2] - 2026-05-18

### Added

- Added direct agent activation entrypoint:
  - `AGENTS.md`
  - `docs/direct-use.md`
  - `templates/direct-request-template.md`
- Updated quick start and prompt recipes so the recommended experience is now one-shot direct use instead of manual template copying.

### Changed

- Validator now requires direct-use activation files.
- README now presents direct invocation as the default path and manual setup as the advanced path.
- Direct-use docs now clarify that Codex loads `AGENTS.md` automatically and users should not treat it as a normal `@` attachment.

## [0.1.0-alpha.1] - 2026-05-18

### Added

- Added detailed open-source onboarding docs:
  - `docs/quick-start.md`
  - `docs/configuration.md`
  - `docs/platform-guides.md`
  - `docs/prompt-recipes.md`
  - `docs/quality-rubric.md`
  - `docs/optimization-playbook.md`
  - `docs/failure-taxonomy.md`
  - `docs/scenario-library.md`
  - `docs/release-checklist.md`
  - `docs/versioning.md`
- Added maintenance docs:
  - `CONTRIBUTING.md`
  - `SECURITY.md`
  - `CODE_OF_CONDUCT.md`
- Added GitHub collaboration and CI configuration:
  - `.github/ISSUE_TEMPLATE/bug_report.md`
  - `.github/ISSUE_TEMPLATE/feature_request.md`
  - `.github/ISSUE_TEMPLATE/scenario_request.md`
  - `.github/PULL_REQUEST_TEMPLATE.md`
  - `.github/workflows/validate.yml`
- Added `VERSION` file for machine-readable project version.
- Added lightweight repository validator at `scripts/validate_repo.py`.
- Added runtime optimization assets:
  - `artifacts/trace-contract.md`
  - `templates/agent-run-log-template.yaml`
  - `templates/evaluation-case-template.md`
  - `evals/membership-auto-renewal-eval.md`
- Added additional scenario coverage for:
  - Web: team permission management
  - App: content save and offline reading
  - Mini Program: appointment booking
- Added complete output packages and platform-specific HTML prototypes for the new scenarios.
- Added clarifying questions, assumptions, and metrics trees for every included scenario.

### Changed

- Expanded `README.md` to link to onboarding, configuration, scenario, contribution, and release docs.
- Clarified that v1 is a platform-neutral Agent Workflow Kit, not a runtime framework.
- Strengthened validation rules so every example scenario must include full core outputs.

### Validation

- Repository structure validation passes with `python3 scripts/validate_repo.py`.
- All prototype HTML files and the prototype template pass `tidy` HTML checks.
- Tracking plan CSV files parse successfully.

## [0.1.0-alpha.0] - 2026-05-18

### Added

- Initial PM Copilot repository structure:
  - `agents/`
  - `skills/`
  - `context/`
  - `workflow/`
  - `artifacts/`
  - `tools/`
  - `guardrails/`
  - `templates/`
  - `examples/`
  - `outputs/`
- Added 7 agent definitions:
  - PM Orchestrator Agent
  - Discovery Agent
  - Research Agent
  - Requirements Agent
  - Analytics Agent
  - Prototype Agent
  - Review Agent
- Added 12 core skills:
  - requirement-intake
  - prd-writing
  - user-stories
  - acceptance-criteria
  - scope-edge-cases
  - metrics-tree
  - tracking-plan
  - competitor-research
  - user-flow
  - multi-platform-prototype
  - review-checklist
  - artifact-packaging
- Added core workflow and context loading rules.
- Added product context example.
- Added artifact contracts for PRD, tracking plan, prototype, and final package.
- Added guardrails for non-fabrication, assumptions, privacy, product safety, and prototype boundaries.
- Added failover rules for missing input, unavailable research, unavailable tools, incomplete artifacts, and conflicting context.
- Added tool-use protocol and prototype tooling notes.
- Added reusable templates:
  - task brief
  - PRD
  - tracking plan
  - Mermaid user flow
  - review checklist
  - final package
  - HTML prototype
- Added complete H5 example:
  - Membership Auto-Renewal Optimization

### Validation

- Skill count and frontmatter checked.
- Repository ASCII check passed.
- H5 prototype and prototype template passed `tidy` HTML validation.
- Membership tracking plan parsed successfully.
