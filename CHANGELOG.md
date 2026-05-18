# Changelog

All notable changes to PM Copilot are documented in this file.

The project uses three-segment semantic versioning: `MAJOR.MINOR.DEBUG`.
Historical entries below are reconstructed from the git commit order so every committed change has a version entry.
See `docs/versioning.md` for upgrade rules, compatibility policy, and release checklist.

## [0.1.10] - 2026-05-18

Commit: current 0.1.10 release commit.

### Added

- Added repository validation checks that keep key contracts, templates, example PRDs, and default output files aligned with the consolidated PRD/prototype delivery model.
- Added richer example PRDs with version history, requirement input and confirmation records, research/reference findings, goals and metrics, scope, requirement details, Mermaid flow diagrams, tracking tables, prototype references, risks, acceptance criteria, and validation results.
- Added run-log fields for readiness, surface decisions, content sources, structured review findings, analytics taxonomy source, scope decisions, open questions, guardrail events, and validation results.
- Added regression criteria for language consistency, existing-UI prototype deltas, mini-program callout annotations, public-resource clarification gates, proposed tracking taxonomy, and validation consistency.

### Changed

- Bumped the project version to `0.1.10`.
- Changed the default PM-facing delivery model to `outputs/<run-id>/prd.md` plus `outputs/<run-id>/prototype-<platform>.html`.
- Moved requirement input, clarified answers, low-risk assumptions, research, metrics, tracking, flow diagrams, review status, and validation results into `prd.md` by default.
- Reclassified `pm-package.md`, `final-package-summary.md`, `task-brief.md`, `clarifying-questions.md`, `assumptions.md`, `metrics-tree.md`, `tracking-plan.md`, `user-flow.md`, and `review-checklist.md` as legacy or explicit-request outputs, not default deliverables.
- Updated the PM Copilot entry, main workflow, delivery workflow, adapters, agents, skills, tools, guardrails, artifact contracts, templates, docs, evals, and examples to use the PRD/prototype delivery model consistently.
- Strengthened the PRD contract and template so each requirement detail covers function, scenario, entry/trigger, content requirements, business logic, interaction rules, data rules, permissions, edge states, tracking links, and acceptance links.
- Strengthened prototype rules for existing-product changes, mini-program style adaptation, and numbered callout annotations tied to page-specific right-side notes.
- Consolidated curated example outputs so each scenario now shows only `prd.md` and one paired prototype by default.
- Switched project versioning documentation from prerelease labels to plain three-segment versions.
- Strengthened PRD, tracking plan, legacy package, and review contracts to separate confirmed MVP scope from optional, conditional, future, and non-goal scope.
- Strengthened readiness handling across PM Copilot, workflow, agents, skills, contracts, templates, guardrails, and evals so PRD, engineering handoff, and launch statuses are separate.
- Added content-source and launch-review requirements for reference, policy, medical, legal, financial, safety, and operational content.
- Added surface and permission-state requirements for existing-product changes, including entry point, navigation visibility, eligible state, ineligible state, and fallback behavior.
- Required structured review findings with artifact, evidence, owner, required-before phase, and status.
- Clarified that tracking plans must be marked as proposed when no existing analytics taxonomy is found.
- Clarified that `Ready for review` PRDs must state whether engineering handoff or launch remains blocked.
- Updated PRD, tracking, legacy package, review checklist, and direct-request templates to carry scope, readiness, taxonomy, validation status, and default-delivery boundaries explicitly.
- Updated agent and skill contracts for orchestrator, discovery, requirements, analytics, prototype, review, PRD writing, acceptance criteria, tracking, review checklist, and packaging behavior.
- Updated validation guidance to use UTF-8-aware `tidy` checks for localized HTML prototypes.

### Removed

- Removed default split Markdown and CSV artifacts from curated example outputs; tracking and flow content now lives inside each example PRD unless an export is explicitly requested.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/install_adapter.py scripts/validate_repo.py`.
- Git whitespace validation passes with `git diff --check`.
- Prototype template HTML validation passes with `tidy -errors -quiet -utf8 templates/prototype-template.html`.

## [0.1.9] - 2026-05-18

Commit: `ae6654b` Tighten PM package readiness rules.

### Added

- Added Chinese-language consistency and existing-UI prototype delta eval cases.
- Added stricter prototype and package readiness guidance across agents, contracts, skills, and templates.

### Changed

- Tightened clarification and readiness rules so unresolved pre-development or pre-launch confirmations block `Ready for engineering`.
- Improved localized template requirements for Chinese artifacts.
- Reduced default split-file expectations and reinforced `pm-package.md` as the reviewer-facing package.
- Updated adapters and docs to carry the tighter PM Copilot behavior into embedded host repositories.

## [0.1.8] - 2026-05-18

Commit: `f4f11d8` Add sanitized clarification gate regression.

### Added

- Added a public-resources checklist regression case based on a real clarification-gate failure.
- Captured expected behavior for repo-backed context loading, run-log facts, and stopping before downstream artifacts when must-answer questions remain.

## [0.1.7] - 2026-05-18

Commit: `3fba118` Make context rule operational.

### Changed

- Clarified that context source mode must be chosen and applied before product generation.
- Updated README and optimization guidance to reinforce context-mode execution instead of assuming repo-backed work.

## [0.1.6] - 2026-05-18

Commit: `b87a326` Clarify single output folder usage.

### Changed

- Clarified that ordinary runs write artifacts under `outputs/<run-id>/`.
- Updated prompt recipes, scenario docs, and eval templates to avoid shared or ambiguous output folders.

## [0.1.5] - 2026-05-18

Commit: `bfeeb4e` Improve PM package artifact quality.

### Added

- Added richer `pm-package.md` outputs, tracking Markdown, and user-flow Markdown for included example scenarios.
- Added `templates/pm-package-template.md`, `templates/tracking-plan-template.md`, and `templates/user-flow-template.md`.
- Added stronger prototype, tracking plan, trace, and final package contract guidance.

### Changed

- Improved package reviewability by making `pm-package.md` the primary narrative artifact.
- Improved prototype quality requirements, annotation expectations, and local HTML boundaries.
- Expanded repository validation for tracking plans, user flows, UTF-8 text files, and machine-readable paths.

## [0.1.4] - 2026-05-18

Commit: `a904057` Support document-backed PM context.

### Added

- Added document-backed context mode for PM work driven by PRDs, specs, screenshots, analytics exports, support tickets, or meeting notes.
- Added document-backed regression coverage.

### Changed

- Updated PM Copilot entry, adapters, agents, failover rules, and templates so a software repository is not required when product documents provide enough context.

## [0.1.3] - 2026-05-18

Commit: `0e6f7ed` Tighten embedded PM workflow gates.

### Added

- Added embedded clarification-gate regression coverage.
- Added adapter installer support and stronger host-project context loading rules.

### Changed

- Strengthened embedded-mode clarification gates before downstream artifact generation.
- Updated adapters, docs, agents, guardrails, templates, and workflow files to inspect relevant host context before proposing product changes.

## [0.1.2] - 2026-05-18

Commit: `5b48e6a` Tune GitHub language statistics.

### Added

- Added `.gitattributes` rules to tune GitHub language statistics.

## [0.1.1] - 2026-05-18

Commit: `2d94ff2` Clarify embedded project setup.

### Changed

- Expanded README guidance for embedded project setup and host-repository usage.

## [0.1.0] - 2026-05-18

Commit: `33a120e` Initial commit.

### Added

- Added the initial PM Copilot repository structure:
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
- Added canonical PM Copilot entry and direct-use activation files.
- Added core workflow, context loading rules, product context example, artifact contracts, guardrails, failover rules, tool protocol, reusable templates, and example scenario outputs.
- Added onboarding, configuration, platform, prompt, quality, optimization, failure-taxonomy, scenario, release, versioning, contribution, security, and code-of-conduct documentation.
- Added GitHub issue, pull request, and validation workflow configuration.
- Added `VERSION` and `scripts/validate_repo.py`.

### Validation

- Initial repository validation passed with the available repository checks.
