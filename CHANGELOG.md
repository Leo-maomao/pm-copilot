# Changelog

All notable changes to PM Copilot are documented in this file.

The project uses three-segment semantic versioning: `MAJOR.MINOR.PATCH`.
Historical entries below are reconstructed from the git commit order so every committed change has a version entry.
See `docs/versioning.md` for upgrade rules, compatibility policy, and release checklist.

## [2.0.1] - 2026-05-19

Commit: pending release commit.

### Changed

- Bumped the project version to `2.0.1` for release metadata and README language cleanup.
- Simplified `README.md` so the default page is Chinese and switches to English through `README.en.md` instead of embedding a second full README.
- Expanded changelog coverage for missed README documentation releases and replaced stale pending commit markers with actual commit references where available.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Git whitespace validation passes with `git diff --check`.

## [2.0.0] - 2026-05-19

Commit: `cb76d9d` feat: add delivery tooling and handoff workflows.

### Added

- Added a stable Agent Interface runtime protocol with handoff status values, output envelopes, mutation boundaries, and exit checks.
- Added agent transition tracing to `run-log.yaml`, including artifact deltas, validation deltas, readiness impact, conflict resolution, resume source, and last reliable state.
- Added main workflow rules for Agent state discipline, idempotent run resume, and cross-agent conflict resolution.
- Added repository validation for required agent definition sections, Agent handoff status references, YAML template duplicate keys, and quality-threshold alignment with the rubric.
- Added repository validation for tool registry and `preflight_tools.py` capability ID alignment.

### Changed

- Bumped the project version to `2.0.0` because the Agent handoff payload and trace shape changed.
- Updated PM Orchestrator and specialist agents to use explicit status-bearing handoffs and preserve blockers through review and execution handoff.
- Updated PM Copilot entry and Prompt System so `agents/agent-interface.md` is part of the active prompt stack for workflow handoffs.
- Aligned evaluation thresholds, run-log score maxima, and optimization guidance with `docs/quality-rubric.md`.
- Updated the release checklist to include Agent interface compliance, duplicate-key template checks, and quality-threshold alignment.

### Fixed

- Removed a duplicate `fix_location` key from `templates/agent-run-log-template.yaml`.
- Fixed inconsistent delivery scoring references that still used `20 / 28` instead of `23 / 32`.
- Fixed missing `Handoffs` sections in Agent definitions that previously violated the shared Agent interface.
- Fixed stale adapter, direct-use, and tool-status wording so development/launch confirmation blockers and `external_runtime` preflight status are documented consistently.

### Validation

- Tool preflight passes with `python3 scripts/preflight_tools.py --strict`.
- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/validate_repo.py scripts/validate_outputs.py scripts/preflight_tools.py scripts/run_delivery_checks.py scripts/setup_visual_validation.py scripts/validate_prototype_visual.py`.
- Git whitespace validation passes with `git diff --check`.
- Prototype template HTML validation passes with `tidy -errors -quiet -utf8 templates/prototype-template.html`.

## [1.1.5] - 2026-05-19

Commit: `f24fe62` docs: show selected README language.

### Changed

- Updated README language switchers to show the currently selected language as plain text.

## [1.1.4] - 2026-05-19

Commit: `3247561` docs: use same-page README language anchors.

### Changed

- Adjusted README language navigation to use in-page anchors for the bilingual README layout.

## [1.1.3] - 2026-05-19

Commit: `531775e` docs: clarify README language links.

### Changed

- Clarified README language-switch links for Chinese and English readers.

## [1.1.2] - 2026-05-19

Commit: `7d6f34c` docs: add README demo screenshots.

### Added

- Added demo screenshots for the team-permissions and checkout-coupon README examples.

## [1.1.1] - 2026-05-19

Commit: `f215df1` docs: add bilingual README demos.

### Added

- Added `README.en.md` as the English README.
- Added bilingual practical demos to the README documentation.

### Changed

- Updated README validation coverage for bilingual documentation.

## [1.1.0] - 2026-05-18

Commit: `ed6c896` Add prompt system and local memory.

### Added

- Added a formal Prompt System covering prompt stack order, request classification, memory use, clarification rules, generation rules, memory update rules, tool use, and failover behavior.
- Added local file-based memory schemas for product memory, user preferences, and durable decision logs.
- Expanded the Memory Model into read order, priority rules, write rules, sensitive data rules, update prompts, and failover behavior.

### Changed

- Bumped the project version to `1.1.0` as a normal feature iteration.
- Updated PM Copilot entry rules to load memory, apply memory priority rules, and suggest memory updates after useful runs.
- Updated context loading rules so local memory helps reduce repeated questions while current user instruction and current product evidence remain higher priority.
- Updated README, direct-use, embedded-use, configuration, and validator coverage for Prompt System and Memory.

### Removed

- Removed `AGENTS.md`; embedded and direct usage now rely on `PM_COPILOT.md` plus host adapters instead of a Codex-only shim.
- Removed `.gitattributes`; committed HTML examples are no longer shipped, so language-stat tuning is no longer needed.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/install_adapter.py scripts/validate_repo.py`.
- Git whitespace validation passes with `git diff --check`.
- Prototype template HTML validation passes with `tidy -errors -quiet -utf8 templates/prototype-template.html`.

## [1.0.0] - 2026-05-18

Commit: `c77bebf` Slim PM Copilot repository structure.

### Changed

- Adopted the project versioning rule that broad refactors change the first segment, normal feature iterations change the second segment, and patches change the third segment.
- Bumped the project version from `0.1.10` to `1.0.0` because this release slims the repository structure and removes public example/package files.
- Clarified that `AGENTS.md` is only a Codex compatibility shim for directly opening this repository; embedded users should rely on the adapter installed into the host project.
- Updated README, direct-use, embedded-use, contribution, release, workflow, context, artifact, guardrail, and validation docs for the slimmer repository model.
- Merged local privacy guidance into `guardrails/guardrails.md`.

### Removed

- Removed committed example inputs and generated example outputs from `examples/` and `outputs/`.
- Removed scenario-library, quick-start, platform-guide, and prompt-recipe docs that duplicated the direct/embedded usage path.
- Removed legacy package contracts and templates for `pm-package.md`, `final-package-summary.md`, split tracking Markdown, split user-flow Markdown, review checklist Markdown, and task-brief Markdown.
- Removed the standalone `guardrails/privacy.md` file after merging its rules into the main guardrails.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/install_adapter.py scripts/validate_repo.py`.
- Git whitespace validation passes with `git diff --check`.
- Prototype template HTML validation passes with `tidy -errors -quiet -utf8 templates/prototype-template.html`.

## [0.1.10] - 2026-05-18

Commits: `a27d66e` Improve mini program prototype annotations; `e54f2b1` Align delivery model with PRD and prototype.

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
