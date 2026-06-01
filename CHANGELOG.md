# Changelog

All notable changes to PM Copilot are documented in this file.

The project uses three-segment semantic versioning: `MAJOR.MINOR.PATCH`.
Historical entries below are reconstructed from the git commit order so every committed change has a version entry.
See `docs/versioning.md` for upgrade rules, compatibility policy, and release checklist.

## [2.7.1] - 2026-06-01

### Added

- Added source-extracted HTML UI handoff support for turning selected source regions into deliverable UI handoff artifacts.
- Added `scripts/extract_ui_region.py` for extracting bounded UI source regions.
- Added `evals/source-extracted-html-handoff-eval.md` to cover source-extracted HTML handoff behavior.

### Changed

- Updated prototype, tooling, validation, and documentation guidance so source-extracted HTML handoffs are recorded as a supported delivery path.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/validate_outputs.py scripts/run_delivery_checks.py scripts/validate_repo.py scripts/validate_prototype_visual.py scripts/validate_ui_preview.py scripts/extract_ui_region.py scripts/preflight_tools.py`.
- Git whitespace validation passes with `git diff --check`.

## [2.7.0] - 2026-05-28

### Added

- Added document-class delivery across workflow, agents, skills, contracts, templates, adapters, validation, and evals so structured references and document prototypes do not have to be forced into PRD or product-page UI flows.
- Added `templates/document-prototype-template.html` for browser-readable reference documents with navigation, structured tables, hierarchy, source/review status, and typed `attention_points`.
- Added structured reference run-log fields for entities, fields, rules, decisions, source facts, product decisions, calibration, object-level change logs, completeness checks, and document attention points.
- Added document prototype validation that accepts document-native `attention_points` instead of requiring product UI `annotation-marker` controls.

### Changed

- Extended the structured catalog contract and template into a broader structured reference contract while preserving existing `structured_catalog` compatibility.
- Updated adapters and prompt/workflow guidance so document-class requests can omit `prd.md` when the user explicitly says no PRD is needed.
- Delivery check reports now separate optional warnings, such as non-required HTML tidy results, from required failures.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/validate_outputs.py scripts/run_delivery_checks.py scripts/validate_repo.py scripts/validate_prototype_visual.py`.
- Git whitespace validation passes with `git diff --check`.
- Temporary document-class delivery validation passes with `python3 scripts/validate_outputs.py /tmp/pmcopilot-doc-test --language en`.
- Delivery orchestrator smoke validation passes with `python3 scripts/run_delivery_checks.py /tmp/pmcopilot-doc-test --language en --skip-repo --skip-visual --skip-visual-reason document-prototype-smoke-test-no-browser-required`.

## [2.6.0] - 2026-05-27

Commit: `cc6ecd5` feat: add structured catalog handoff.

### Added

- Added `artifacts/structured-catalog-contract.md` and `templates/structured-catalog-template.md` for table-first engineering handoffs such as model parameter matrices, API capability catalogs, vendor matrices, data dictionaries, and migration inventories.
- Added output validation for `catalog.md` and `catalog.html`, including structured catalog metadata, field dictionaries, localized machine-token table headers, required row cells, model-specific parameter columns, source/review status, self-contained HTML checks, and run-log trace requirements.
- Added a model integration catalog eval covering model IDs, modalities, context windows, required/optional parameters, rate limits, pricing source, deprecation status, source freshness, and engineering handoff notes.

### Changed

- Updated the main workflow, direct-use guidance, run-log template, trace contract, knowledge-ops skill, and scorecard so pure text/table requests can produce `catalog.md` or `catalog.html` without being forced into PRD/UI delivery.
- Extended scorecard artifact expectations and capability coverage with `structured_catalog` and `knowledge_catalog`.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/validate_outputs.py scripts/validate_repo.py scripts/agent_improvement_scorecard.py`.
- Temporary structured catalog delivery checks pass with `python3 scripts/run_delivery_checks.py /tmp/pmcopilot-catalog-test --language en`.
- Improvement scorecard reports no current risks after 27 non-fixture eval cases, including 1 structured-catalog eval.

## [2.5.0] - 2026-05-27

Commit: `6b3b8dc` feat: replace fixture evals with generic scenarios.

### Removed

- Removed named fixture evals and local evidence tied to borrowed host projects so the tracked eval portfolio is fully generic.
- Removed tracked borrowed-host names, path fragments, and domain vocabulary from PM Copilot assets.

### Added

- Added a generic source-backed preview stability eval that preserves repo-backed UI validation without naming a borrowed host project.
- Added 10 non-fixture scenario evals for payment refund/chargeback support, marketplace seller suspension appeals, cross-region data retention, AI customer-message review, offline sync conflict resolution, pricing/tax/invoice currentness, incident status communication, API deprecation migration, age-gated community safety, and bulk notification fatigue controls.

### Changed

- Rebalanced the eval portfolio so fixture-scoped cases are no longer required for current scorecard coverage.
- Kept source-backed preview pressure as a universal product-agent capability rather than a host-project story.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Improvement scorecard reports no current risks after 26 non-fixture eval cases and 5 delivery-checked runtime runs.

## [2.4.0] - 2026-05-27

Commit: `613a708` feat: harden universal product agent evidence.
Backfills pushed commit: `123e787` feat: harden pm copilot self-improvement.

### Added

- Added `skill-cleaner` for local skill hygiene checks and duplicate/packaging review.
- Added Playwright-based source preview validation through `scripts/validate_ui_preview.py`, `requirements-dev.txt`, and delivery-check integration.
- Added `scripts/agent_improvement_scorecard.py` and `docs/self-improvement-system.md` for evidence-based PM Copilot self-iteration.
- Added scenario portfolio metadata, fixture isolation terms, edge-case pressure coverage, and new regression evals for source-backed host previews, regulated health clarification gates, and B2B permission handoff.
- Added `templates/optimization-cycle-template.yaml` for recording improvement cycles.
- Added artifact expectation matrices so evals can declare when PRD, UI delivery, tracking, engineering handoff, launch decision, or pre-clarification artifacts are required.
- Added broad non-fixture regression coverage for prompt-injection/tool-permission admin agents, accessibility-critical checkout recovery, public-sector source currentness, and a ten-scenario universal product-agent stress portfolio.
- Added a passed non-fixture runtime evidence run for prompt-injection/tool-permission engineering handoff and launch blocking.

### Changed

- Established the generalization boundary: borrowed host projects are fixtures, not PM Copilot product defaults.
- Hardened repository validation so fixture-specific terms stay out of the universal PM Copilot surface and public regression assets such as `evals/` cannot be hidden by `.gitignore`.
- Extended scorecard reporting across eval quality, runtime evidence, visual evidence, fixture/non-fixture proof, edge-case pressure, and engineering handoff artifacts.
- Extended scorecard reporting for scenario-set rounds, passed-evidence portfolio coverage, artifact expectations, and passed handoff/launch-decision runtime evidence.
- Broadened eval metadata with fixture scope, PM user type, risk profile, rubric thresholds, and failure history.
- Improved output validation for source-backed UI evidence, backend/API boundary annotations, visual-validation trace shape, and pre-clarification stops.
- Hardened `dev-tasks.yaml` and `launch-decision.yaml` validation so handoff and release artifacts must contain actionable task fields, blockers, gate evidence, human approvals, and rollback plans.
- Tightened guardrails and contracts for untrusted input/tool permissions, source currentness for high-stakes claims, accessibility-preserving checkout or consent flows, and non-dark-pattern UI delivery.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Tool preflight passes with `python3 scripts/preflight_tools.py --strict`.
- Script bytecode validation passes with `python3 -m py_compile scripts/*.py skills/skill-cleaner/scripts/skill_cleaner.py`.
- Delivery checks pass for the recorded non-fixture and fixture evidence runs, including membership auto-renewal, document-backed checkout, regulated-health pre-clarification, B2B permission handoff, and prompt-injection/tool-permission admin handoff scenarios.
- Improvement scorecard reports no current risks after 18 eval cases and 6 delivery-checked runtime runs.

## [2.3.0] - 2026-05-22

Commit: pending

### Added

- Absorbed the transferable workflow from `Ixe1/ui-from-image` into the canonical UI Delivery skill as Image Reference Reconstruction Mode.
- Added `skills/multi-platform-prototype/references/image-reference-reconstruction.md` for screenshot/mockup/image-to-UI intake, inventory, asset handling, and screenshot comparison rules.
- Added `image_reference_reconstruction` run-log fields so reference dimensions, viewport, visual inventory, asset decisions, comparison method, mismatches, and fidelity limits are auditable.
- Added a regression eval for image-reference UI reconstruction and duplicate-skill prevention.

### Changed

- Updated the UI Delivery Agent, UI delivery contract, tooling notes, trace contract, README, and PM Copilot entry so screenshot/image-to-UI work uses `multi-platform-prototype` rather than a duplicate skill.
- Required high, exact, 1:1, or pixel-level image reconstruction claims to have exact-size implementation screenshot comparison evidence.
- Documented the external source absorption boundary: no direct code/template/prose reuse because the inspected repository had no declared license.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Git whitespace validation passes with `git diff --check`.
- Script bytecode validation passes with `python3 -m py_compile scripts/inspect_host_frontend.py scripts/validate_outputs.py scripts/validate_repo.py scripts/preflight_tools.py scripts/preflight_integrations.py scripts/run_delivery_checks.py scripts/validate_prototype_visual.py scripts/setup_visual_validation.py scripts/install_adapter.py`.

## [2.2.9] - 2026-05-22

Commit: `dd3ce87` fix: require realistic ui delivery states.

### Changed

- Tightened UI delivery rules so source-backed previews must provide changed preview files and run commands, not only a localhost URL.
- Clarified that direct standalone HTML remains available for no-source, explicit portable HTML, explicit redesign/greenfield, or blocked source-rendering cases, but exact repo-backed parity should stay source-rendered.
- Removed visible "example/demo/not production code" labeling from the product surface; delivery boundaries now belong in metadata, run logs, PRD notes, or comments unless regulated content requires visible draft status.
- Required realistic product interactions and state transitions instead of using a top-level state-tab storyboard as a substitute for behavior.
- Updated compatibility HTML validation and the base template to reject legacy prominent state-tab strips and require boundary metadata.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/inspect_host_frontend.py scripts/validate_outputs.py scripts/validate_repo.py scripts/preflight_tools.py scripts/preflight_integrations.py scripts/run_delivery_checks.py scripts/validate_prototype_visual.py scripts/setup_visual_validation.py scripts/install_adapter.py`.
- Git whitespace validation passes with `git diff --check`.
- Tool preflight passes with `python3 scripts/preflight_tools.py --strict`.
- Prototype template visual validation passes with `PLAYWRIGHT_BROWSER_CHANNEL=chrome python3 scripts/validate_prototype_visual.py /tmp/pmcopilot-prototype-template-check --browser-channel chrome --no-auto-setup`.

## [2.2.8] - 2026-05-21

Commit: `2f57f53` fix: redefine ui delivery as source backed.

### Changed

- Redefined UI output as a source-first UI deliverable instead of a hand-written prototype by default.
- Updated the main entry, workflow, agent roles, skills, artifact contracts, templates, adapters, guardrails, docs, context examples, and evals so repo-backed frontend source produces source-backed preview/delta files unless fallback gates explicitly allow standalone HTML.
- Kept legacy machine names such as `prototype-<platform>.html`, `validate_prototype_visual.py`, and `isolated_ui_prototype` as compatibility names while documenting that they do not imply standalone HTML or fake UI.
- Updated adapter installation output so newly installed host adapters also enforce the source-backed UI delivery rule.
- Changed Chinese PRD output validation to expect a `UI 交付` reference section instead of the old `原型` section wording.
- Updated evaluation templates, execution handoff inputs, release checks, and validation messages so current guidance says UI deliverable/source-backed UI delivery, while legacy `prototype-*` names remain compatibility file and field names.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/inspect_host_frontend.py scripts/validate_outputs.py scripts/validate_repo.py scripts/preflight_tools.py scripts/preflight_integrations.py scripts/run_delivery_checks.py scripts/validate_prototype_visual.py scripts/setup_visual_validation.py scripts/install_adapter.py`.
- Git whitespace validation passes with `git diff --check`.
- Tool preflight passes with `python3 scripts/preflight_tools.py --strict`.
- Source-backed UI delivery validation now enforces the `source_rendering_decision` vocabulary and source-rendered modes without relying on project-specific release fixtures.

## [2.2.7] - 2026-05-21

Commit: `9e6df82` fix: default prototypes to source-backed UI.

### Changed

- Added a source-code-first prototype invariant: repo-backed frontend source presence now requires source-rendered preview/delta artifacts by default, without relying on the user to ask for exact UI parity.
- Allowed freeform/greenfield prototype UI only when there is no frontend source/current surface, source rendering is concretely blocked, the raw request asks for standalone/portable HTML, or the raw request explicitly asks to redesign/rebuild/from-scratch/stop reusing the original UI.
- Extended output validation so any non-source-rendered repo-backed prototype mode fails when frontend source exists unless the raw request or concrete blocker permits the fallback.
- Added `user_explicit_greenfield` as a controlled `source_rendering_decision` value and require matching raw-request redesign/greenfield wording.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/inspect_host_frontend.py scripts/validate_outputs.py scripts/validate_repo.py scripts/preflight_tools.py scripts/preflight_integrations.py scripts/run_delivery_checks.py scripts/validate_prototype_visual.py`.
- Git whitespace validation passes with `git diff --check`.
- Tool preflight passes with `python3 scripts/preflight_tools.py --strict`.
- Template script, annotation badge, and source-first fallback smoke checks pass.
- Prototype template visual validation passes with `python3 scripts/validate_prototype_visual.py /tmp/pmcopilot-prototype-template-check --browser-channel chrome --no-auto-setup`.
- Host frontend inventory smoke confirms render entrypoint, preview surface, `source_rendering_decision: "used"`, and `recommended_artifact_mode: source_delta_patch` on a repo-backed fixture.
- Regression check rejects a standalone fallback output with `Repo-backed prototype host_frontend_inventory.source_rendering_decision must be one of required, used, blocked, user_explicit_portable, user_explicit_greenfield, or not_required`.

## [2.2.6] - 2026-05-21

Commit: `b1680b1` fix: require raw request standalone consent.

### Changed

- Tightened standalone HTML fallback detection so validation only treats the user's raw request as explicit portable/standalone/HTML consent, instead of trusting self-reported `user_explicit_html_prototype_only` fields in `run-log.yaml`.
- Clarified that "only generate a prototype" means prototype scope only and does not authorize standalone HTML when a repo-backed source-rendered preview is available.
- Required `source_rendering_decision` to use a fixed vocabulary; `user_explicit_portable` now requires raw-request HTML/portable wording, and `blocked` requires a concrete source-rendering limitation.
- Reframed the Prototype Agent and multi-platform prototype skill around artifact modes so renderable repo-backed UI defaults to source-rendered preview/delta files instead of hand-written local HTML.
- Tightened annotation badge guidance and validation so UI markers, marker dialogs, and right-side annotation-panel numbers share the same red/white borderless badge sizing and centered digit alignment.
- Fixed prototype-only output validation so `prototype-web.html` checks no longer crash when `prd.md` is intentionally omitted.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/inspect_host_frontend.py scripts/validate_outputs.py scripts/validate_repo.py scripts/preflight_tools.py scripts/preflight_integrations.py scripts/run_delivery_checks.py scripts/validate_prototype_visual.py`.
- Git whitespace validation passes with `git diff --check`.
- Tool preflight passes with `python3 scripts/preflight_tools.py --strict`.
- Prototype template script, annotation badge, and fallback-gate smoke checks pass.
- Prototype template visual validation passes with `python3 scripts/validate_prototype_visual.py /tmp/pmcopilot-prototype-template-check --browser-channel chrome --no-auto-setup`.
- Host frontend inventory smoke confirms render entrypoint, preview surface, and `recommended_artifact_mode: source_delta_patch` on a repo-backed fixture.
- Regression check rejects a standalone fallback output with `Repo-backed prototype host_frontend_inventory.source_rendering_decision must be one of required, used, blocked, user_explicit_portable, or not_required`.

## [2.2.5] - 2026-05-21

Commit: `7eeada6` fix: enforce source-rendered prototype fallback gates.

### Changed

- Added target-query ranking to host frontend inventory so repo-backed UI work can locate relevant routes/components from the requirement text instead of relying on broad repository scan order.
- Tightened repo-backed prototype validation so a renderable host frontend that recommends source-rendered mode cannot silently fall back to standalone HTML unless the user explicitly requested a portable artifact or source rendering was attempted and blocked with concrete evidence.
- Required standalone fallback runs to capture an existing UI visual baseline or record a concrete source-rendering/browser limitation when the host frontend is renderable.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/inspect_host_frontend.py scripts/validate_outputs.py scripts/validate_repo.py scripts/preflight_tools.py scripts/preflight_integrations.py scripts/run_delivery_checks.py scripts/validate_prototype_visual.py`.
- Git whitespace validation passes with `git diff --check`.
- Tool preflight passes with `python3 scripts/preflight_tools.py --strict`.
- Prototype template script parsing passes with a Node syntax smoke check.
- Prototype template visual validation passes with `python3 scripts/validate_prototype_visual.py /tmp/pmcopilot-prototype-template-check --browser-channel chrome --no-auto-setup`.
- Annotation digit badge contract validation passes for the template.
- Host frontend query inventory smoke passes on a repo-backed fixture and ranks the target component as `preview_surface`.
- Regression check rejects an old standalone fallback output after annotation-number normalization with `Repo-backed renderable frontend should not fall back to standalone HTML unless the user explicitly requested a portable/standalone artifact or source rendering was attempted and blocked`.

## [2.2.4] - 2026-05-21

Commit: `602dc31` fix: validate annotation panel badge numbers.

### Changed

- Extended runtime visual validation to inspect every right-side page annotation panel number badge, not just the marker popover badge.
- Tightened annotation guidance so the page annotation panel list items must also use plain digit red/white borderless badges without circled numeral glyphs or nested badge content.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/inspect_host_frontend.py scripts/validate_outputs.py scripts/validate_repo.py scripts/preflight_tools.py scripts/preflight_integrations.py scripts/run_delivery_checks.py scripts/validate_prototype_visual.py`.
- Git whitespace validation passes with `git diff --check`.
- Prototype template script parsing passes with a Node syntax smoke check.
- Prototype template visual validation passes with `python3 scripts/validate_prototype_visual.py /tmp/pmcopilot-prototype-template-check --browser-channel chrome --no-auto-setup`, including right-side page annotation panel number badge checks.
- Annotation digit badge contract validation passes for the template.
- Tool preflight passes with `python3 scripts/preflight_tools.py --strict`.

## [2.2.3] - 2026-05-21

Commit: `24f8a49` fix: use plain annotation badge numbers.

### Changed

- Changed annotation dialog and panel number badges to use plain digits inside the red/white badge instead of circled numeral glyphs, preventing nested red badge visuals.
- Updated prototype guidance and validation to reject circled numeral glyphs or nested badge content in annotation number badges and require plain digit mappings for each marker ID.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/inspect_host_frontend.py scripts/validate_outputs.py scripts/validate_repo.py scripts/preflight_tools.py scripts/preflight_integrations.py scripts/run_delivery_checks.py scripts/validate_prototype_visual.py`.
- Git whitespace validation passes with `git diff --check`.
- Prototype template script parsing passes with a Node syntax smoke check.
- Prototype template visual validation passes with `python3 scripts/validate_prototype_visual.py /tmp/pmcopilot-prototype-template-check --browser-channel chrome --no-auto-setup`.
- Annotation digit badge contract validation passes for the template.
- Tool preflight passes with `python3 scripts/preflight_tools.py --strict`.

## [2.2.2] - 2026-05-21

Commit: `e6adf3a` feat: add source delta prototype mode.

### Changed

- Enforced red-fill, white-text, borderless annotation badges for both page markers and matching annotation number badges.
- Reworked the annotation floating control so it shows only `注释` or `Notes`, hides when opened, and controls a right-edge full-height annotation panel that restores the floating control when closed.
- Required page/state switch controls to stay fixed outside the product layout when prototypes need state switching.
- Added `scripts/inspect_host_frontend.py` to scan host frontend entry files, routes/screens, components, styles, icons/assets, data/mocks, render commands, and recommended source-rendered artifact mode.
- Added `source_delta_patch` as the default exact-fidelity repo-backed mode: import/render the original baseline from host source and add new requirements only in isolated delta patch files, with a multi-turn continuation anchor.
- Promoted repo-backed source rendering from guidance to a default requirement for exact UI parity: PM Copilot now records host frontend inventory and uses isolated preview routes, Storybook stories, demos, Mini Program preview pages, or App preview screens when real icons/components/runtime styles must match the source.
- Extended output and visual validation for host frontend inventory, icon/asset evidence, source-rendered artifact mode, annotation panel behavior, fixed state tabs, and borderless marker styling.
- Removed active `baseline_layer`/`delta_layer`, top-right annotation-list, and isolated-HTML-default wording from prototype tooling and contracts in favor of `baseline_import`/`delta_patch`.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/inspect_host_frontend.py scripts/validate_outputs.py scripts/validate_repo.py scripts/preflight_tools.py scripts/preflight_integrations.py scripts/run_delivery_checks.py scripts/validate_prototype_visual.py`.
- Git whitespace validation passes with `git diff --check`.
- Prototype template visual validation passes with `python3 scripts/validate_prototype_visual.py /tmp/pmcopilot-prototype-template-check --browser-channel chrome --no-auto-setup`.
- Tool preflight passes with `python3 scripts/preflight_tools.py --strict`.
- Output contract smoke validation passes for annotation marker rules, `source_delta_patch`, and cross-platform repo-backed host frontend inventory.
- Host frontend inventory smoke validation passes with `python3 scripts/inspect_host_frontend.py --host . --pretty`.

## [2.2.1] - 2026-05-21

Commit: `f8abf50` chore: release 2.2.1.

### Changed

- Tightened repo-backed prototype guidance so style evidence must name concrete host files/assets, component-library sources, and source-to-demo mappings before a prototype can claim completion.
- Changed the prototype template and annotation contract so marker clicks open local popovers beside the marked component; full-screen/global marker note modals and annotation backdrops are now rejected.
- Extended prototype visual validation to click an annotation marker and verify the opened note is locally anchored rather than a centered/global dialog.
- Refined annotation behavior so markers do not change visual style on click and clicking the same marker again closes its local popover.
- Added host-rendered preview guidance for repo-backed high-fidelity prototypes so exact icons, component-library behavior, and source-level visual parity use `code_preview_route` or `storybook_or_demo` when allowed, instead of relying on hand-recreated standalone HTML.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/validate_outputs.py scripts/validate_repo.py scripts/preflight_tools.py scripts/preflight_integrations.py scripts/run_delivery_checks.py scripts/validate_prototype_visual.py`.
- Git whitespace validation passes with `git diff --check`.
- Prototype template visual validation passes with `python3 scripts/validate_prototype_visual.py /tmp/pmcopilot-prototype-template-check --browser-channel chrome --no-auto-setup`.

## [2.2.0] - 2026-05-21

Commit: `fe0c5c1` chore: release 2.2.0 skill docs.

### Added

- Added canonical PM skills for opportunity discovery, feedback synthesis, experiment design, roadmap communication, knowledge ops, process mapping, design-system audit, and Sharingan resource absorption.
- Added a Sharingan regression case and references for risk gating, absorption reporting, duplicate-skill prevention, and external resource compatibility review.

### Changed

- Simplified README skill documentation into grouped, concise indexes in Chinese and English.
- Updated `PM_COPILOT.md` so every current skill has a clear trigger group while still loading only request-relevant skills.
- Updated configuration and release checklist docs for candidate-tool readiness and canonical skill mapping.
- Strengthened external integration preflight so `candidate` and `hold` tools fail `--require-ready` instead of being treated as usable required dependencies.
- Extended existing competitor, metrics, tracking, and product-ops skills with explicit boundaries to prevent duplicate sibling skills.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/validate_outputs.py scripts/validate_repo.py scripts/preflight_tools.py scripts/preflight_integrations.py scripts/run_delivery_checks.py scripts/validate_prototype_visual.py`.
- Git whitespace validation passes with `git diff --check`.
- Integration preflight correctly fails candidate/setup-required tools with `python3 scripts/preflight_integrations.py --tier recommended --require-ready`.

## [2.1.0] - 2026-05-21

Commit: `ded7084` chore: release 2.1.0.

### Added

- Added repo-backed isolated UI prototype rules so PM Copilot reads host frontend code, assets, styles, data shapes, screenshots, and state rules while keeping production files read-only by default.
- Added a two-layer UI prototype model: `baseline_layer` restores unchanged product UI from host evidence, while `delta_layer` contains new feature UI, numbered markers, explanation dialogs, backend simulation notes, tracking notes, and edge-case annotations.
- Added `isolated_ui_prototype` run-log fields for host mutation policy, target surface, baseline layer, delta layer, source-to-demo mapping, backend simulation, parity claim, and limitations.
- Added external integration governance, tool vetting, external tooling catalog, and integration preflight guidance so third-party MCP servers, APIs, SaaS tools, and automation connectors are treated as candidates until source, credentials, permissions, cost, and fallback are explicit.
- Added product operations analysis guidance for metrics, funnels, retention, conversion, support signals, experiment results, dashboards, CSV exports, BI tools, and analytics sources.

### Changed

- Strengthened repo-backed prototype validation so outputs must record isolated UI prototype evidence in addition to style evidence and existing UI visual baseline evidence.
- Updated prototype, workflow, artifact, trace, review, direct-use, embedded-use, configuration, and quality rubric docs to separate baseline reconstruction from new-feature annotation behavior.
- Extended tool preflight and tool-use guidance to account for external integrations and safer local/manual fallbacks.
- Expanded analytics and orchestration guidance for product-ops analysis and integration governance handoffs.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/validate_outputs.py scripts/validate_repo.py scripts/preflight_tools.py scripts/preflight_integrations.py`.
- Git whitespace validation passes with `git diff --check`.

## [2.0.6] - 2026-05-19

Commit: `ee427a2` fix: remove scenario-specific research gate.

### Changed

- Bumped the project version to `2.0.6` to remove scenario-specific research validation from the generic PM Agent.
- Replaced prior scenario wording with a general competitor/comparable flow research method: entry point, required input, primary path, fallback path, platform difference, observed fact, and product implication.
- Kept prototype interaction safeguards generic: JavaScript syntax checks, draggable annotation toggles, unclipped marker placement, and compact-control wrap checks.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/validate_outputs.py scripts/validate_repo.py scripts/run_delivery_checks.py scripts/validate_prototype_visual.py`.
- Git whitespace validation passes with `git diff --check`.
- Search checks confirm the core research rules no longer contain scenario-specific validation tokens from the prior regression patch.

## [2.0.5] - 2026-05-19

Commit: `5f573b7` feat: tighten auth research and prototype validation.

### Changed

- Bumped the project version to `2.0.5` for common-flow research and prototype interaction validation fixes.
- Strengthened PRD research rules so common-flow work must include competitor or comparable-product flow evidence, not only generic policy, security, or implementation references.
- Updated prototype guidance and the HTML template so annotation toggles are draggable, markers use safe unclipped placement, and compact tabs/buttons should not fold because of annotations.
- Added static prototype JavaScript syntax validation to `validate_outputs.py` so broken scripts fail even when browser visual validation is skipped.
- Extended visual-report checks to record annotation layout issues and compact-control wrapping issues alongside access-state evidence.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/validate_outputs.py scripts/validate_repo.py scripts/run_delivery_checks.py scripts/validate_prototype_visual.py`.
- Prototype template HTML parser and extracted JavaScript syntax checks pass.
- Direct Node syntax checking catches generated prototype inline-handler string errors that would otherwise make all prototype controls inactive.
- Git whitespace validation passes with `git diff --check`.

## [2.0.4] - 2026-05-19

Commit: `b9a5174` docs: refresh readme demos.

### Changed

- Bumped the project version to `2.0.4` for refreshed README demos and user-facing usage documentation.
- Refreshed README and direct-use demos to show the stronger repo-backed style-reuse workflow, red component annotations, access-state validation, external research, engineering handoff, and launch decision gates.
- Replaced the checkout coupon README demo image with a membership auto-renewal demo that better exercises payment, privacy, legal, and launch readiness behavior.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Git whitespace validation passes with `git diff --check`.
- README demo images are verified at `1200 x 720` with `sips`.

## [2.0.3] - 2026-05-19

Commit: `4896261` feat: tighten artifact validation gates.

### Changed

- Bumped the project version to `2.0.3` for stricter post-run artifact validation after regression testing.
- Made PRD solution shaping record `external_research` separately from repository context, so implementation facts cannot be used as a substitute for competitor, benchmark, comparable-feature, or other source-backed product research.
- Updated prototype annotation guidance toward full-width product surfaces with red component callouts, marker dialogs, and a top-right annotation list instead of persistent side panels that shrink or crop the product UI.
- Added access-state coherence requirements for Prototype Agent and Review Agent so logged-out, guest, or no-permission controls must not reveal signed-in-only account data or actions.

### Validation

- `validate_outputs.py` now rejects ad hoc run-log shapes for `agent_transitions`, `review_scores`, `quality_thresholds`, `handoff_artifacts`, `content_sources`, `guardrail_events`, and `security_and_audit`.
- `validate_prototype_visual.py` now records access-state smoke evidence and fails when an unauthenticated account trigger reveals signed-in-only data or actions.
- `run_delivery_checks.py` now rejects reused visual reports that lack the new access-state evidence.
- Legacy generated outputs are expected to fail the stricter gates until regenerated when their run logs lack canonical `external_research` / score / transition structure or their unauthenticated states reveal signed-in-only controls.

## [2.0.2] - 2026-05-19

Commit: `20a3a9d` chore: release prototype validation gates 2.0.2.

### Changed

- Bumped the project version to `2.0.2` for prototype validation and repo-backed prototype quality gates.
- Strengthened repo-backed prototype generation so UI deliveries must load Prototype Agent plus `multi-platform-prototype`, record style evidence, and reuse host frontend component/style sources instead of inventing a new shell.
- Added an existing UI visual baseline requirement for repo-backed prototypes so runs must capture or record a running-app/demo/screenshot reference, comparison method, and limitation before claiming visual fit.
- Updated prototype annotation guidance and template markers to use red `annotation-marker` badges with stable `data-annotation-id` mappings to matching numbered notes.
- Changed prototype annotations from a persistent side-board pattern to component-corner red badge markers, marker-triggered dialogs, and a top-right current-state annotation list.
- Added PRD research guidance so “Research and reference findings” uses source-backed competitor, benchmark, or comparable-product research for solution shaping, while repository files stay under current-state context or engineering implementation notes.
- Added prototype geometry guidance for long pages, multi-state screens, and modals so generated HTML preserves real scrolling behavior instead of clipping content inside artificial frames.
- Integrated a design calibration pass from the reviewed external design skill: prototypes now record visual density, layout variance, motion intensity, and anti-generic UI choices while preserving host style precedence.
- Extended output validation to fail prototype deliveries that skip the prototype skill, omit design calibration, omit repo-backed style evidence, or lack traceable top-right component annotation markers.
- Strengthened prototype visual validation with DOM smoke evidence for visible text, interactive controls, horizontal overflow, console errors, and page errors; duplicate visual skips must reuse a passed report with that evidence.
- Updated repository validation to ignore local system/cache files such as `.DS_Store`, `Thumbs.db`, `.pytest_cache`, and `__pycache__`.
- Localized the default GitHub community documents to Chinese, moved English switch pages under `docs/en/` so GitHub keeps the Chinese community files as defaults, and kept the MIT license text canonical in English.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/validate_outputs.py scripts/validate_repo.py scripts/run_delivery_checks.py scripts/validate_prototype_visual.py`.
- Legacy regression output now fails as expected with `Run log missing multi-platform-prototype skill for prototype delivery`; legacy visual reports without DOM smoke evidence are also rejected for duplicate-skip reuse.
- Git whitespace validation passes with `git diff --check`.

## [2.0.1] - 2026-05-19

Commit: `ef58675` chore: update release notes and README language switch.

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
