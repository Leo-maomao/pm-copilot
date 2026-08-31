# Changelog

All notable changes to PM Copilot are documented in this file.

The project uses three-segment semantic versioning: `MAJOR.MINOR.PATCH`.
Historical entries below are reconstructed from the git commit order so every committed change has a version entry.
See `docs/versioning.md` for upgrade rules, compatibility policy, and release checklist.

## [6.2.38] - 2026-08-31

### Fixed

- Stage interactive PRD delivery outside the canonical run and promote `prd.md`, `prd.html`, `run-log.yaml`, and `assets/` only after validation passes.
- Resolve new PRD output folders from the invoking project's workspace, preserve user-provided visual assets, and require attributable provider/model execution evidence.
- Enforce the complete Chinese PRD requirement-list contract and keep all visual media inside the four canonical detail fields.
- Require every requirement-detail screenshot to use the fixed left-media/right-copy `prd-detail-media-block` structure; reject standalone Markdown images and bare `<img>` elements.

## [6.2.37] - 2026-08-27

### Added

- Add an explicit `--lan` mode that binds the PRD manager to the local network and prints a shareable LAN URL while keeping localhost-only startup as the default.

## [6.2.36] - 2026-08-27

### Fixed

- Disable smooth scrolling while restoring a PRD position so refresh jumps directly to the saved location without an animated transition.

## [6.2.35] - 2026-08-27

### Fixed

- Restore the active PRD anchor in the iframe URL before first paint, matching standalone HTML navigation while retaining pixel-level scroll correction.

## [6.2.34] - 2026-08-27

### Fixed

- Hide the PRD iframe until its persisted reading position has been restored, preventing a visible jump from the top after a page refresh.

## [6.2.33] - 2026-08-27

### Fixed

- Restore the selected PRD reading position after a full browser refresh, including a final save during page unload.

## [6.2.32] - 2026-08-27

### Fixed

- Refresh the local PRD index when opening search so deleted or newly changed documents do not remain in an already-open manager tab.

## [6.2.31] - 2026-08-27

### Fixed

- Persist each PRD's reading position so both index refresh and full manager reload can restore it.

## [6.2.30] - 2026-08-27

### Fixed

- Restore the selected PRD's iframe scroll position after index refresh, including delayed document layout.

## [6.2.29] - 2026-08-27

### Fixed

- Preserve the current PRD iframe scroll position when refreshing the local manager index.

## [6.2.28] - 2026-08-27

### Fixed

- Required new PRDs that reference or migrate another PRD to use the current new-document template; source PRDs now supply content and assets, not inferred document structure.

## [6.2.27] - 2026-08-27

### Fixed

- Carried the final confirmed PRD evidence into delivery and review, so explicitly confirmed source paths and development-stage follow-ups are not reclassified as generation blockers.
- Allowed a confirmed failed run to resume its first unaccepted stage, canonicalized promoted run-log paths, and accepted the controller's `interactive-run.json` as a valid interactive output file.

## [6.2.26] - 2026-08-27

### Fixed

- Persisted interactive PRD confirmation, artifact promotion, stage review, and validation checkpoints atomically so a controller interruption cannot leave generated files behind while the canonical state still waits for confirmation.
- Added truthful `recovery_required` status for legacy interrupted deliveries and explicit resume support that continues from the first stage without a persisted accepted review.

## [6.2.25] - 2026-08-27

### Fixed

- Aligned explicit `@pm-copilot` and natural-language PRD activation with the same canonical controller and interactive run-control contract.

## [6.2.24] - 2026-08-27

### Fixed

- Added a local PM Copilot MCP controller bridge so interactive PRD status, answers, and explicit delivery confirmation are read from and applied through the canonical run state instead of narrated by the chat model.

## [6.2.23] - 2026-08-27

### Fixed

- Stopped treating ordinary product-manager ownership and development/launch follow-ups as PRD generation blockers.
- Resumed explicitly confirmed interactive PRD runs through the canonical controller and report only recorded delivery state.
- Ran staged delivery and review Agents inside the project output staging directory so Codex sandbox writes can be promoted to the canonical PRD folder.

## [6.2.22] - 2026-08-27

### Fixed

- Removed the forced minimum height from PRD detail media columns so short screenshots no longer leave trailing blank space below their paired logic.

## [6.2.21] - 2026-08-27

### Fixed

- Normalized adjacent requirement-logic groups to one line break, preventing empty rows between numbered headings in image-linked detail blocks.

## [6.2.20] - 2026-08-27

### Fixed

- Added reviewed PRD media mappings so screenshots consume only their explicitly matched requirement logic instead of inheriting text by image order.
- Preserved unmatched logic as full-width content in the same `需求详情` cell and restarted numbering within each image-linked block.

## [6.2.19] - 2026-08-27

### Fixed

- Kept PRD Manager copy and open-directory actions stable beside long, wrapped document titles, with an explicit copied checkmark state.
- Improved legacy PRD requirement-detail media grouping for numbered Chinese rule blocks.

## [6.2.18] - 2026-08-27

### Fixed

- Consolidated legacy duplicate `需求详情` rows into one cell: text-only logic remains full-width while screenshot-linked logic uses fixed left-image/right-text blocks.
- Unified the repository, global runtime, and Codex plugin release version; runtime updates now refresh the local plugin cache when the Codex CLI is available.
- Added a PRD Manager action to copy an indexed PRD run directory to the macOS clipboard.

## [6.2.17] - 2026-08-27

### Fixed

- Reset numbered logic headings within each migrated screenshot block so split details start at `一、` and `1.`.
- Kept text-only requirement details in a clean single-column layout with consistent line spacing.

## [6.2.16] - 2026-08-27

### Changed

- Kept screenshots and their state logic inside the single PRD `需求详情` cell using fixed-column media blocks.
- Migrated legacy standalone figure rows during HTML rendering and removed visible duplicate image-name captions.
- Synchronized the published plugin manifest version with the runtime version.
- Route explicit PRD revisions to the identified canonical folder and compact remaining requirement-detail IDs after deletion.

## [6.2.15] - 2026-08-22

### Fixed

- Preserved the original PRD template TOC width while giving links a stable content box wide enough for long labels in every visual state.

## [6.2.14] - 2026-08-22

### Fixed

- Stabilized PRD template TOC link geometry across default, hover, and active backgrounds by fixing link width and reserving the scrollbar gutter.

## [6.2.13] - 2026-08-22

### Fixed

- Restored the PRD template TOC to its original 252px width and normal font weight while keeping active-state positioning deterministic and full titles untruncated.

## [6.2.12] - 2026-08-22

### Fixed

- Reverted the accidental PRD Manager sidebar width and folder-icon layout changes; the stable TOC fix remains scoped to the PRD template renderer.

## [6.2.11] - 2026-08-22

### Fixed

- Applied the full-title, state-stable TOC layout to the live PRD Manager sidebar and expanded its desktop width to match the available title length.

## [6.2.10] - 2026-08-22

### Fixed

- Increased the PRD HTML TOC layout budget and normalized link descendant weight so long full titles do not reflow when selected or hovered.

## [6.2.9] - 2026-08-22

### Fixed

- Fixed PRD HTML TOC active-state drift by selecting the last heading that has crossed a stable scroll threshold; full TOC titles wrap without changing weight when selected.

## [6.2.8] - 2026-08-22

### Fixed

- Fixed PRD manager sidebar document titles wrapping differently in the selected state; titles now use a stable single-line ellipsis layout with a full-title tooltip.

## [6.2.7] - 2026-08-22

### Fixed

- Renamed README demo assets to cache-busting names and synchronized README, HTML previews, and release metadata to `6.2.7`.

## [6.2.6] - 2026-08-22

### Changed

- Replaced the README demos with evidence-backed enterprise access governance and subscription release-gate scenarios.
- Refreshed both demo HTML snapshots and PNG previews to match the current runtime contract.

## [6.2.5] - 2026-08-22

### Changed

- Updated the public README, conduct, contribution, and security documents to match the current production-controller, canonical-output, model-evidence, and output-safety rules.
- Synchronized the published plugin manifest version with the repository release.

## [6.2.4] - 2026-08-22

### Fixed

- Added the missing `PyYAML` development dependency so GitHub Actions discovers and runs the complete evaluation regression suite.

## [6.2.3] - 2026-08-22

### Fixed

- Made direct Codex runtime tests inject a deterministic synthetic model so CI does not depend on a developer's local Codex configuration.

## [6.2.2] - 2026-08-22

### Fixed

- Made the PRD manager reveal endpoint regression test platform-aware: macOS verifies Finder opening, while Linux CI verifies the documented `501` response.

## [6.2.1] - 2026-08-22

### Changed

- Documented the single-`main` branch development policy in Chinese and English contribution guides.
- Updated the published security support table to reflect the current 6.x runtime line.

## [6.2.0] - 2026-08-22

### Added

- Added startup synchronization for copied global runtimes, including source checkout metadata, commit/version tracking, and an integrity manifest.

### Changed

- Global PM Copilot activation now automatically synchronizes a newer source checkout when the installed runtime is unmodified.
- Automatic synchronization refuses to overwrite locally modified runtime files and reports the changed paths as an actionable blocker.

### Validation

- Added regression coverage for clean auto-sync and local-modification protection.

## [6.1.0] - 2026-08-22

### Added

- Added provider-agnostic model capability discovery through `scripts/model_catalog.py`, with stage routing based on declared `standard` and `judgment` capabilities.
- Added `scripts/prd_request_controller.py` as the canonical natural-language PRD entry point.
- Added production-run gates requiring attributable provider/model Agent evidence for intake, clarification review, artifact delivery, and stage quality review.

### Changed

- PRD requests can no longer claim completion without explicit user confirmation, complete contracted artifacts, independent stage reviews, and passing final validation.
- Missing or unverifiable model/Agent evidence now produces `failed` or `blocked` state instead of a direct or synthetic PRD result.
- Sol/Terra are compatibility-only model aliases; they are not automatic model assumptions.
- Same-requirement revisions remain in one canonical run folder; collision-suffixed copies are prohibited.

### Validation

- Full repository test suite: 292 tests passed.
- Runtime routing, repository validation, Python compilation, and `git diff --check` passed.

## [6.0.1] - 2026-08-22

### Changed

- Centralized Agent model identifiers and adaptive routing policy constants in `scripts/runtime_policy.py` without changing provider discovery, CLI behavior, or fallback semantics.
- Centralized evaluation portfolio plan hashing in `scripts/portfolio_contract.py` so runner, auditor, and canonicalizer share one deterministic implementation.
- Added regression coverage for runtime-policy ownership and portfolio plan-digest stability.

### Validation

- Full repository validation, Python compilation, and 281 tests passed.

## [6.0.0] - 2026-08-22

### Changed

- Established a single canonical PRD directory per requirement. Only `--new-requirement` may create a new PRD; revisions must use `--run-folder <folder> --revise` in place.
- Made PRD visual rules, section numbering, required `prd.html`, and evidence boundaries canonical and validator-enforced across the workflow, templates, controllers, and evaluation paths.
- Unified evaluation and interactive execution around one canonical result and explicit blocker handling, preventing conflicting duplicate result branches.

### Breaking Changes

- Same-name PRD collisions no longer create `-2`, `-3`, or version-suffixed copies. Existing callers must identify the canonical run folder for revisions.

### Validation

- Added regression coverage for canonical PRD management, visual-contract consistency, evaluation portfolio reuse, and single-result execution.
- Full repository validation is recorded for this release.

## [5.0.3] - 2026-08-17

### Fixed

- Reordered Pandoc recovery so the official user-level binary is downloaded before Homebrew is considered. Homebrew remains an optional fallback, and the bundled renderer remains the final delivery fallback.

## [5.0.2] - 2026-08-17

### Fixed

- When Pandoc is missing, PRD rendering now attempts installation through an existing Homebrew installation before falling back to the bundled local renderer. It never installs a package manager or blocks PRD delivery when setup is unavailable.

## [5.0.1] - 2026-08-17

### Fixed

- Made `prd.html` a required deliverable for every PRD mode and made output validation reject a missing browser-readable PRD.
- Added in-place PRD revision semantics: an identified PRD is updated with its sibling HTML unless the user explicitly asks for a new version, while the execution run remains immutable and records revision evidence.
- Removed the hard runtime dependency on Pandoc. The PRD renderer now falls back to a bundled local Markdown renderer for headings, tables, lists, links, images, code blocks, and Mermaid when Pandoc is unavailable.
- Added an explicit preflight capability record for the PRD HTML renderer.

### Validation

- Added local-renderer regression coverage and updated PRD-contract fixtures for the required HTML artifact.

## [5.0.0] - 2026-08-06

### Fixed

- Made implemented-feature PRDs classify local self-test, demo, screenshot, debug, mock, fixture, and temporary presentation states as development-only scaffolding rather than release requirements.
- Defined requirement granularity by independently decided user outcomes, so related changes inside one dialog or flow stay in one requirement unless their audience, entry, outcome, priority, or release boundary differs.
- Required localization handoffs to keep every independently usable visible string on its own pure-text and mapping-table row while preserving literal continuous copy such as `3/10`.
- Aligned active PRD guidance with the controlled screenshot placeholder format, keeping capture explanations in the run trace instead of the PRD.

### Validation

- Added regressions for non-production PRD leakage, same-dialog requirement grouping, independent localization rows, and continuous slash-bearing copy.

## [4.9.13] - 2026-08-03

### Fixed

- Closed the implemented-feature PRD trace bypass: every reconstructed requirement now needs exactly one auditable visual decision, and a user-facing requirement cannot claim `not_required` merely by omitting `ui_surfaces`.
- Limited requirement-detail tables to their canonical fields. Boundary, state, exception, and permission rules must stay in `需求详情` or `设计与交互`; ad-hoc rows such as `边界规则` now fail validation.
- Bound `pm_copilot_version` in implemented-feature run logs to the active runtime `VERSION`, preventing stale or Agent-invented provenance from passing as a fresh plugin run.
- Made `validate_outputs.py` infer `zh` or `en` from `run-log.yaml` when callers omit `--language`, so Chinese artifact gates cannot be bypassed by a shortened validation command.

### Validation

- Added regressions for an omitted visual surface inventory, non-canonical detail-table fields, and evidence-backed placeholder capture paths.

## [4.9.12] - 2026-08-03

### Fixed

- Corrected requirement-detail group spacing: adjacent `一、` / `二、` groups now use one continuous line break, while the blank-line gap remains exclusive to separate figure assets.
- Added validation that rejects blank separators between multi-rule requirement-detail groups.

### Validation

- Added a regression for rejecting a doubled line break between requirement-detail groups.

## [4.9.11] - 2026-08-03

### Fixed

- Unified image and video figure rendering so both use the same `功能-状态` caption typography.
- Made multi-asset figure rows render as a vertical media list with a blank-line-height gap between assets, rather than a compact mixed-media grid.

### Validation

- Added a mixed image/video figure regression covering shared captions and vertical spacing.

## [4.9.10] - 2026-08-03

### Fixed

- Made user-provided video figures render as original local inline videos with browser playback controls even when the source was inserted with image syntax; they can no longer fall back to a static first-frame image.
- Made output validation reject video files rendered as `<img>` elements and require every referenced local video to have an inline player.

### Validation

- Added a renderer regression for image-syntax video input becoming a playable video element.

## [4.9.9] - 2026-08-03

### Fixed

- Made multi-rule `需求详情` cells use a readable, render-stable hierarchy: Chinese-numbered group headings and Arabic-numbered rules now require explicit `<br>` lines, with a blank `<br><br>` separator between groups.
- Rejected flat, paragraph-style numbered rules in requirement-detail tables so generated PRDs cannot silently lose visual separation in HTML rendering.

### Validation

- Added contract and guidance regressions for grouped requirement-detail line layout.

## [4.9.8] - 2026-08-03

### Fixed

- Made required visual recovery a loop success precondition for implemented-feature PRDs. The controller now continues while any required capability or capture route remains unrecorded, and reports budget exhaustion instead of falsely stopping successfully.
- Clarified that an empty Chrome DevTools browser-target list affects only that capture method; the Agent must still try preview discovery, project-runtime activation, test-state recovery, Playwright, and Computer Use when applicable.

### Validation

- Added a loop-controller regression proving that a superficially successful run continues after only the Chrome DevTools path reports no browser target.

## [4.9.7] - 2026-08-03

### Fixed

- Replaced the fixed-port screenshot assumption with an auditable runtime-capture capability chain: discover an existing preview, activate the project runtime from its own configuration, recover test state, then attempt Playwright, Chrome DevTools, and Computer Use.
- Made required figure placeholders invalid when any runtime or capture step is silently skipped. Every attempted or unavailable step now requires an action, evidence, and a non-empty local result file so a fallback can be reviewed and reproduced.

### Validation

- Added regression coverage for rejecting untried screenshot fallbacks and accepting capability-based evidence without assuming a specific local port.

## [4.9.6] - 2026-08-03

### Changed

- Replaced the implemented-feature PRD scaffold with one complete document skeleton: document context, background, optional research, requirement list, per-requirement details, optional localization, and optional tracking all have a stable place before empty blocks are removed from the delivered PRD.
- Added independent optional `用户流程图` and `操作流程图` blocks before each requirement table. The former describes interaction paths; the latter describes rules, conditions, states, permissions, and exceptions.
- Unified real figure captions and controlled placeholders as `功能-状态`; placeholders now use only `占位图：功能-状态.png`.

### Validation

- Added template regression coverage for complete-but-removable sections and controlled figure-name regression coverage for the `功能-状态` format.

## [4.9.5] - 2026-08-03

### Fixed

- Made the implemented-feature PRD gate reject a missing visual-coverage decision for any user-facing requirement, silent `not_required` decisions for named UI surfaces, and trace records that hide measurable actions or outcomes inside YAML comments.
- Required tracking omissions to be justified by product-measurement relevance rather than the absence of existing event definitions.
- Rejected non-canonical requirement-detail fields such as `验收标准`, Mermaid diagrams placed after their requirement table, and English source strings in a Chinese localization delivery while preserving parameter placeholders such as `{reason}`.

### Validation

- Added negative regressions for visual-coverage omission, commented tracking evidence, standalone acceptance fields, misplaced flowcharts, and English localization source copy.

## [4.9.4] - 2026-08-03

### Fixed

- Isolated generated artifacts from current product evidence: rewrites now require a new run folder and may use earlier PRDs only as comparison inputs, preventing stale run logs and tool results from steering a new delivery.
- Replaced omission-by-default with a per-requirement coverage review for visual evidence, changed copy, and measurement; reviewers must justify every `not_needed` decision before a PRD can omit localization or tracking content.
- Made implemented-feature traces fail when they disable their own route with `active: false`, skip the visual capture-recovery record, merge independent visual states, or place explanatory text in controlled placeholders.
- Enforced the final-row position and exact controlled syntax of PRD figure placeholders.

### Validation

- Added regression coverage for isolated implemented-feature runs, complete requirement coverage review, controlled placeholder recovery, figure-row ordering, and placeholder-only figure cells.

## [4.9.3] - 2026-08-03

### Fixed

- Kept implemented-feature PRDs deliverable when authenticated UI capture cannot be recovered: each required figure now remains as an inline controlled placeholder with a visible `图示待人工补全` reminder and a named manual replacement action in the run log.
- Made delivery validation reject placeholder PRDs that omit the visible reminder, the pending manual-completion status, the replacement instruction, or the `ready for review` PRD readiness state.
- Made a failed `run_delivery_checks.py` result explicitly block final-delivery claims.

### Validation

- Added regression coverage for a deliverable implemented-feature PRD with controlled placeholders and for rejection when its visible manual-completion reminder is missing.

## [4.9.2] - 2026-07-30

### Changed

- Changed the global project output default from the hidden `.pm-copilot/outputs/<run-id>/` path to the visible `pm-copilot-outputs/<run-id>/` path.
- Automatically migrate legacy hidden global outputs to the visible directory when PM Copilot next resolves the project workspace, while preserving embedded-project output compatibility and explicit project overrides.
- Made output validation recognize both embedded `outputs/` and visible global `pm-copilot-outputs/` run directories.
- Updated runtime tool guidance to use the resolved output root rather than hard-coding the embedded `outputs/` path.

### Validation

- Added regression coverage for visible global output creation, legacy-output migration, and visible-directory historical-output discovery.

## [4.9.1] - 2026-07-30

### Fixed

- Made the Seawork dry-run regression test select its declared provider explicitly, so it verifies the worker contract without requiring an authenticated local Agent session in CI.
- Installed `pandoc` in GitHub Actions before historical PRD upgrade tests and browser rendering checks, matching the renderer's required runtime dependency.

## [4.9.0] - 2026-07-30

### Added

- Added a browser-backed CI smoke test and a source-controlled PRD benchmark harness that checks required and forbidden product-document content without claiming model-quality judgment.
- Added a durable vendor-neutral `agent-events.jsonl` trace for delegated execution, including task lifecycle, worker, tool, evidence, review, and terminal events.
- Added a local task-envelope adapter with an explicit non-network A2A interoperability boundary and a versioned PM Copilot capability card.
- Added global PM Copilot installation, a Seawork-compatible Skill bundle, an installable Codex plugin bundle, and project-local output resolution for both embedded and global use.

### Improved

- Made global runtime replacement atomic, excluded project artifacts and local state from the installed runtime, and constrained project output overrides to remain inside the active project.
- Recompiled duplicate legacy tracking identifiers into distinct feature-and-action names, preventing repeated generic events from surviving evidence-led PRD migration.

### Validation

- Added regression coverage for global workspace resolution, isolated installation, PRD benchmark cases, event-ledger persistence, A2A envelope validation, and browser-rendered visual smoke checks.

## [4.8.13] - 2026-07-30

### Fixed

- Removed the legacy tracking rule that required explanatory “拟议” or taxonomy-source copy in PRDs; tracking validation now rejects raw sensitive values in `附加参数` instead.
- Rejected duplicate requirement identifiers in both PRD validation and historical-upgrade automation, and prevented the upgrader from mutating ambiguous documents.
- Unified optional tracking numbering: `埋点需求` is `六` when no localization section exists and `七` when it does.
- Rejected technical API, code-path, component, command, and implementation details when embedded in ordinary PRD content rather than only in dedicated technical headings.
- Made multi-figure layout deterministic at render time instead of relying on browser JavaScript, preserving wide figures and compact side-by-side evidence in static output.
- Added document language metadata and keyboard-accessible image-preview behavior; fixed macOS real-path handling in successful MOV-to-MP4 conversion.

### Validation

- Added regression coverage for tracking-copy boundaries, sensitive tracking parameters, duplicate requirements, optional tracking numbering, static figure layout, document language, image-preview accessibility, Mermaid integration, and successful media conversion.

## [4.8.12] - 2026-07-30

### Improved

- Rendered multiple figures in the same requirement-detail cell as an adaptive figure group: wide screenshots keep the full row while compact or vertical figures share a row when their rendered dimensions allow it.
- Kept each image name attached directly to its own image so parallel figures remain unambiguous and visual evidence stays readable.

### Validation

- Added regression coverage for adaptive figure grouping and retained figure-caption and media-rendering checks.

## [4.8.11] - 2026-07-30

### Fixed

- Made `artifacts/prd-contract.md` the single product-content standard for PRDs and removed conflicting guidance that reintroduced risk, acceptance, validation, technical evidence, duplicate function IDs, fixed optional-section numbering, or descriptive placeholder captions.
- Restricted PRD tracking to the five canonical columns; detailed event dictionaries, privacy notes, validation material, and taxonomy approval narration now require an explicitly requested analytics/engineering handoff.

### Validation

- Added active-guidance consistency tests covering placeholder display, requirement identifiers, optional-section numbering, concise tracking, and PRD/internal-evidence boundaries.

## [4.8.10] - 2026-07-30

### Fixed

- Unified PRD figure names to the relevant functional area and key state only, removing file extensions, capture markers, `图示：`, Demo-source notes, and other explanatory caption text.
- Required each real figure to repeat that exact display name immediately below the image and rejected double line breaks between consecutive figures.
- Simplified controlled figure placeholders to `占位图：图片名称`; capture rationale and location details remain in internal evidence rather than the PRD.

### Validation

- Added regression coverage for descriptive figure captions and double figure gaps, then normalized all local PRD figure rows.

## [4.8.9] - 2026-07-30

### Fixed

- Made implemented-feature PRDs declare requirement-level visual coverage and verify that real figures are local, hash-matched, and inline with their mapped requirement.
- Kept optional localization/tracking headings readable by requiring `埋点需求` to become `六` when `多语言需求` is omitted.
- Limited self-improvement delegation to three independent evidence roles and stopped dispatch immediately when the first worker reports a deterministic local runtime startup failure.
- Prevented terminal task ledgers from retaining running workers; historical failed dispatch evidence is now recorded as degraded rather than planned.

### Validation

- Added regression coverage for visual-coverage omission, valid real-figure mapping, optional-section numbering, bounded self-improvement roles, deterministic startup failure, and terminal ledger closure.

## [4.8.8] - 2026-07-29

### Fixed

- Bound every multi-Agent self-improvement ledger to its exact PM Copilot workspace, preventing a resumable task from being reused in a different same-named embedded copy.
- Added explicit embedded-copy identity and synchronization direction to specialist, review, and orchestration context so project-specific evidence cannot be conflated with a source repository or another host project's copy.

### Validation

- Added regression coverage for embedded-copy identity, workspace-scoped specialist prompts, and cross-copy resume rejection.

## [4.8.7] - 2026-07-29

### Fixed

- Reduced spacing between consecutive requirement images to a single visual line break.

## [4.8.6] - 2026-07-29

### Changed

- Made screenshot range an Agent visual-review decision: every capture must preserve the functional target plus the context required to locate and understand it, while removing only unrelated content.
- Added internal crop-review evidence and curated-asset rules so superseded raw captures do not remain in PRD assets.

## [4.8.5] - 2026-07-29

### Fixed

- Removed the descriptive `图示：` prefix from figure captions; captions now contain only the image name.
- Removed the viewport-height cap from images inside requirement tables so the document preserves the full source image rather than visually constraining it.

## [4.8.4] - 2026-07-29

### Fixed

- Required every real local image asset in a PRD output to be placed in the corresponding requirement detail; validation now rejects unreferenced images.
- Standardized inline requirement figures so each image is immediately followed by a concise `图示：…` caption, with spacing only between separate figures.
- Added a formatter that normalizes legacy figure rows without changing requirement content, then re-rendered local PRD HTML outputs.

### Validation

- Added regression coverage for per-image captions, multi-image spacing, and idempotent figure formatting.

## [4.8.3] - 2026-07-29

### Fixed

- Added historical PRD fidelity checks that compare source-backed requirement inventories and documented requirement-version changes against the current PRD, preventing silent scope contraction during migration.
- Stopped the historical PRD upgrader from deleting existing figure rows before attempting evidence-backed additions.
- Added a full local-output fidelity audit that separates mandatory restoration findings from visual-evidence reviews; restored all identified scope-contracted historical PRDs and completed the related semantic asset reviews.
- Blocked automatic historical upgrades when the source log shows a requirement inventory or requirement-version history that the current PRD no longer preserves.

### Validation

- Added regression coverage for requirement-scope and version-history loss, automatic-upgrade blocking, existing-figure preservation, tracking timing false positives, and all reviewed historical outputs.

## [4.8.2] - 2026-07-29

### Fixed

- Recompiled automatically generated tracking IDs from the measured requirement context so generic or duplicated names such as `journey_view` and repeated `*_view` rows become unique feature-and-action identifiers.
- Prioritized explicit result-display events over titles that happen to contain “结果”, preserving distinct view, operation, and result events in the same requirement flow.
- Expanded the evidence-led vocabulary for common product contexts including connection, renewal settings, permissions, media assets, homepage creation, purchase, and image-processing flows.

### Validation

- Reprocessed all 19 local historical PRDs and verified each with historical PRD validation after the tracking migration.

## [4.8.1] - 2026-07-29

### Changed

- Renamed PRD tracking columns to `事件`、`事件名称`、`上报时机`、`附加参数`、`备注`, and standardized generated engineering identifiers as semantic `feature_action` names instead of PRD-position identifiers.
- Simplified generated reporting moments to observable sentences, replaced empty tracking properties and notes with `/`, and removed default “拟议” filler from PRD tables.
- Standardized multilingual requirements as a copyable new-copy text block followed by `文案`、`使用位置`、`参数` checklist rows; placeholders such as `{reason}` are now explicit and testable.

### Validation

- Migrated and historically validated all local PRDs after the new tracking and multilingual rules, including rendered HTML.

## [4.8.0] - 2026-07-29

### Added

- Added evidence-led historical PRD migration that writes per-output evidence and upgrade reports, adds optional multilingual and tracking sections only from source evidence, and selects only same-run real screenshot assets.
- Added a historical-PRD validation mode that validates document structure, tracking quality, rendering, local assets, and evidence ledgers without fabricating missing legacy run traces.
- Added a durable multi-Agent task ledger with atomic persistence, artifact hashes, phase state, retries, resumability, and explicit degradation when a worker has no usable structured result.

### Changed

- Hardened PRD figure insertion so generated figure rows remain inside the relevant requirement-detail table; legacy misplaced generated rows are repaired on the next migration.
- Normalized legacy tracking identifiers to lowercase engineering identifiers without changing event names, timings, parameters, or notes.
- Required real structured worker, review, and arbitration handoffs before multi-Agent execution can be marked complete; outer CLI success or an agent ID alone is no longer accepted as a result.
- Added a recorded Seawork fallback path when the active model rejects structured execution; failed or timed-out runtime calls remain visible as degraded evidence rather than being claimed as collaboration success.

### Validation

- Added regression coverage for historical evidence artifacts, missing legacy run logs, tracking identifier normalization, durable ledger persistence, structured delegation ordering, and field/value requirement-detail HTML rendering.
- Reprocessed every discoverable local PM Copilot output under `Desktop/`; 19 PRDs were evidence-upgraded and passed historical PRD validation, while outputs without a PRD were explicitly skipped.

## [4.7.0] - 2026-07-28

### Added

- Added a safe local-output upgrader that migrates legacy run-folder names, updates internal run references, regenerates PRD HTML with the current renderer, and reports validation results without inventing or rewriting product requirements.
- Added safe embedded-copy synchronization that preserves each copy's `outputs/` and local context while refreshing PM Copilot source files; dirty Git copies require an explicit overwrite flag.
- Added targeted collaboration-trace regressions for evidence-backed cross-review and PM Orchestrator arbitration.

### Validation

- Added deterministic migration, protected-copy synchronization, and collaboration-protocol regression coverage.

## [4.6.0] - 2026-07-28

### Changed

- Strengthened PRD content guidance across document information, background, research, requirement list, requirement details, localization, and measurement without changing the standardized PRD structure or tracking-table columns.
- Defined tracking coverage from the user journey: access, meaningful operation, important outcome, and value behavior such as browsing duration, depth, exposure, completion, or retention.
- Defined `参数` as additional event context only; empty parameters remain blank, while generic placeholders and generic event names are rejected.

### Validation

- Added Chinese PRD tracking regressions for measurable event names and blank-vs-placeholder additional parameters.

## [4.5.0] - 2026-07-28

### Added

- Added a bounded multi-Agent control plane that selects role-specific evidence work, runs Review only after specialist handoffs, and keeps final arbitration with PM Orchestrator.
- Added a collaboration trace protocol for evidence-backed claims, targeted cross-review, and conflict arbitration; ungrounded debate and majority voting are prohibited.
- Added automatic runtime capability reporting that distinguishes a single-Agent fallback from a reachable Seawork multi-Agent loop.

### Validation

- Added deterministic delegation planning, mocked orchestration-order, runtime-degradation, and collaboration-protocol coverage.

## [4.4.0] - 2026-07-28

### Added

- Expanded the Agent Runtime adapter with headless discovery and execution support for Qwen Code, Kimi Code, Qoder CLI, and Tencent CodeBuddy Code.
- Added discovery-only visibility for domestic IDE tools such as Trae and Baidu Comate, so they are not misrepresented as background worker runtimes.

### Validation

- Added domestic CLI command-contract and active-runtime selection regressions.

## [4.3.0] - 2026-07-28

### Added

- Added a local Agent Runtime adapter that automatically discovers authenticated Seawork, Codex CLI, and Claude CLI installations without requesting API keys.
- Made automatic execution select the user's active host runtime and active model instead of imposing a fixed runtime default; Seawork-backed sessions retain their current Agent provider/model for worker loops.
- Added runtime readiness to tool preflight and documented the trace requirements for real delegated execution.

### Validation

- Added deterministic runtime-adapter regression coverage for active-runtime selection, dry-run commands, and credential redaction.

## [4.2.9] - 2026-07-28

### Changed

- Made PRD visual evidence evidence-first: the optional `图示` row normally uses an actual local screenshot or figure, while requirements without visual value omit the row. A controlled placeholder is permitted only for an essential unavailable figure after every trusted capture path fails, with an inline location-and-purpose caption.
- Defined autonomous evidence capture order: Playwright for previews, Chrome DevTools for authenticated browser surfaces, then Computer Use for non-automatable surfaces; each crop must retain the functional target and locating context.
- Added input-cleaning and fact-reliability rules so template instructions, process narration, vague filler, and model speculation cannot enter a PRD.
- Limited version history to initial creation and material product-requirement changes; formatting, rendering, validation, synchronization, and other document operations are excluded.
- Clarified that Loop Engineering is a bounded decision protocol, while model selection and multi-agent execution require host-runtime delegation support; unsupported runs now record single-agent execution instead of implying collaboration.

### Validation

- Added PRD contract regressions for screenshot placeholders, operation-only version entries, and template-guidance leakage.

## [4.2.8] - 2026-07-28

### Changed

- Refined screenshot selection to retain the functional target, locating context, and any comparison context required to understand the requirement.
- Updated the team-projects example so the first local crop shows both personal and team project areas, making the team-boundary behavior immediately understandable.

### Validation

- Re-rendered and validated the team-projects PRD with the revised contextual crop.

## [4.2.7] - 2026-07-28

### Changed

- Distinguished user-flow and operation-flow diagrams; when both are adjacent, PRD HTML renders them side by side on wide screens and stacks them on narrow screens.
- Required a requirement-detail table below either flow diagram, so the diagram cannot replace the detailed product specification.
- Added hierarchical `一、二、三` and `1.、2.、3.` guidance for complex detail cells, and made focused component/state crops the default screenshot evidence.

### Validation

- Added paired-flow rendering and missing-detail-table regression coverage; regenerated the team-projects example with dual flowcharts and focused crops.

## [4.2.6] - 2026-07-28

### Changed

- Removed the redundant `6.1` subsection and explanatory lead-in when a PRD has one multilingual-copy set.
- Simplified tracking headers to `名称`、`标识`、`时机`、`参数`、`备注`, while retaining Chinese event names and engineering identifiers in table values.
- Rejected explanatory copy-section labels and descriptive tracking headers in Chinese PRDs.

### Validation

- Updated templates, the team-projects example, and PRD contract regression coverage.

## [4.2.5] - 2026-07-28

### Changed

- Standardized every PRD requirement detail as five fields: `用户与场景`、`需求入口`、`需求详情`、`设计与交互`、`图示`.
- Merged normal flow, permissions, loading/empty/error feedback, recovery, and other boundaries into `需求详情`; removed the standalone state-and-exception field.
- Required optional Mermaid flowcharts to appear above the matching detail table.

### Validation

- Added regression coverage for the five required detail fields and updated the team-projects example.

## [4.2.4] - 2026-07-28

### Changed

- Made the `需求详情` section number, such as `5.1`, the sole identifier for each PRD requirement.
- Removed redundant `R1`-style labels and the duplicate `关联详情` column from requirement lists, templates, and the team-projects example.

### Validation

- Added regression coverage that rejects requirement-detail headings which append an `R` identifier after the detail number.

## [4.2.3] - 2026-07-28

### Changed

- Simplified requirement details into four default fields: user and scenario, operation flow and rules, UI and interaction, and states and exceptions.
- Removed risk, pending-confirmation, and acceptance-result fields from requirement details; requirements now record confirmed product behavior only.
- Reduced tracking requirements to Chinese event name, engineering event name, trigger timing, extra parameters, and notes.

### Validation

- Re-rendered and validated the team-projects PRD example with compact detail tables and the five-column tracking table.

## [4.2.2] - 2026-07-28

### Changed

- Replaced the PRD's decision-first eight-section structure with a standardized seven-section, user-driven structure: document information, background, optional research, requirement list, requirement details, optional localization, and optional tracking.
- Made `需求清单` mandatory and traceable: every requirement now identifies its target user, scenario, user value, priority, source status, and matching requirement detail.
- Moved user flow, UI/interaction, state handling, risk, open questions, and acceptance results into the corresponding requirement detail so the document does not disperse user needs across unrelated sections.

### Validation

- Added regression coverage for the new Chinese PRD structure and user-to-detail traceability.
- Re-rendered and validated the team-projects PRD example with the updated template.

## [4.2.1] - 2026-07-28

### Fixed

- Made PRDs product-only documents: removed technical implementation maps, code evidence sections, and technical handoff fields from contracts, skills, templates, and implemented-feature reconstruction guidance.
- Kept technical evidence in the run trace or a separately requested engineering handoff, while preserving product behavior, confidence, gaps, and acceptance results in the PRD.
- Added output-contract regression checks that reject technical implementation sections and fields in Chinese PRDs.

### Validation

- Ran PRD contract regression tests, runtime-routing validation, and repository validation.

## [4.2.0] - 2026-07-24

### Added

- Added repository-local capability selectors and `scripts/resolve_runtime_capabilities.py` so optional PM Copilot skills are selected by task mode and request trigger instead of relying on machine-local skill installation or directory-wide loading.
- Added `test-first-maintenance` and `repository-architecture-review` skills, both restricted to PM Copilot self-improvement work in this repository.
- Added a root `AGENTS.md` entry point, third-party source intake record, and validation for selector task modes, triggers, and active document paths.

### Changed

- Absorbed the requested visual-direction, UI-quality-audit, and structured-decision-interview practices into the existing design-system audit, delivery review, and requirement-intake canonical skills.
- Kept source notes and third-party intake records outside the runtime path; skills are now loaded only through the runtime index and matching optional capability selector.

### Validation

- Verified UI quality, visual-direction, decision-interview, test-first-maintenance, and repository-architecture selectors against their resolved local skill paths.
- Ran runtime-routing and repository validation.

## [4.1.0] - 2026-07-23

### Changed

- Repositioned PM Copilot as an auxiliary Product Agent Loop: it now supports evidence gathering, product judgment, PM artifacts, review, handoff, and learning without modifying host product code, deploying releases, or replacing human approval.
- Replaced the fixed serious-task first-read list with `indexes/runtime-routing.yaml`, which selects the smallest active workflow, contract, skill, and policy set for each task mode.
- Converted repo-backed UI delivery to read-only evidence-based prototypes, specifications, and existing UI extracts; proposed behavior must be separated from observed behavior and handed to a named human implementation owner.
- Added rule-governance policy and moved the one-off real-run UI plan into `docs/archive/` so historical repair guidance is not a runtime instruction.

### Validation

- Added `scripts/validate_runtime_routing.py` and repository integration to verify active routing paths, canonical rule ownership, task-mode coverage, and archive exclusion.
- Updated runtime, adapter, template, UI, and validation surfaces to enforce the review-only boundary.

## [4.0.2] - 2026-07-11

### Fixed

- Rendered local PRD video evidence as an inline HTML5 player instead of a plain link that navigates to or downloads the media file.
- Added `.mp4`, `.webm`, `.mov`, `.m4v`, `.ogv`, and `.ogg` detection with MIME-aware `<source>` elements, browser controls, inline playback, metadata preloading, and a source-link fallback.
- Added automatic MOV/M4V remuxing to a sibling browser-compatible MP4 when `ffmpeg` is available, with H.264/AAC transcoding fallback when stream-copy remuxing fails.
- Added output validation for local video paths, required controls, `playsinline`, MIME declarations, and Markdown-to-HTML media coverage.
- Extended run-log visual evidence types with `video` and documented MP4 H.264/AAC as the broad-compatibility delivery format.

### Validation

- Added `scripts/test_prd_media_rendering.py` and CI coverage for MOV/MP4 conversion, required player attributes, fallback links, parser detection, and non-video link preservation.
- Re-rendered the `canvas-menu-shortcuts-prd-2026-07-07` real-run case and verified that its shortcut-panel motion evidence is embedded as a controllable video player.

## [4.0.1] - 2026-07-11

### Changed

- Made real automated screenshots the default visual-evidence path for PRDs instead of a placeholder-first, human-replacement workflow.
- Added project-agnostic browser discovery, supported plugin or dependency setup and retry, authentication recovery through user sign-in or task-scoped tokens, and manual capture as the penultimate fallback.
- Added screenshot clarity requirements that reject blurred, blank, clipped, or unreadably small images and require retry with a larger viewport, higher device scale, focused target, or contextual crop.
- Restricted inline `占位图` output to the final fallback after automated capture, setup or repair, authentication recovery, and manual capture are unavailable or unsuccessful.
- Added credential-safety rules preventing tokens or login data from entering PRDs, logs, source-controlled environment files, image metadata, or user-visible output.

### Validation

- Added `evals/prd-automated-screenshot-recovery-eval.md` covering missing browser tooling, missing login state, sensitive-token handling, blurred element captures, cross-project generalization, and final placeholder fallback.
- Added optimization-cycle evidence in `docs/optimization-cycles/2026-07-11-automated-prd-screenshot-recovery.yaml`.

## [4.0.0] - 2026-07-10

### Added

- Added a model-independent bounded Agent Loop with `direct`, `execution`, `evaluator_optimizer`, `research`, and `self_improvement` strategies.
- Added Loop policy, runtime state, per-iteration evidence trace, stop summary, hard iteration/tool/time budgets, no-progress detection, and human checkpoints to the Agent run log.
- Added `scripts/evaluate_agent_loop.py` as an executable continue/stop controller and registered it as `control.agent_loop`.
- Added `scripts/test_agent_loop.py` and CI coverage for decision priority, every budget class, no-progress, terminal states, continue behavior, and invalid policy rejection.
- Added strict success, needs-input, blocked, budget, no-progress, human-checkpoint, and false-progress regression fixtures.
- Added bounded Agent Loop evaluation coverage and deterministic runtime tests.
- Added deterministic reflection-and-learning regressions for missing review recommendations, unresolved severe findings, unsafe sensitive-memory writes, and self-improvement without regression evidence.

### Changed

- Reframed workflow as the execution graph and Loop as the bounded controller that decides whether another evidence-producing pass is useful.
- Expanded PM Orchestrator and Review Agent responsibilities so the reviewer evaluates usefulness and progress while the orchestrator owns the final continue/stop judgment.
- Extended repository, delivery, scorecard, and runtime-evidence validation to measure Loop trace completeness and reject contradictory or nonsequential iteration claims.
- Made due human checkpoints take precedence over autonomous success so the Agent cannot approve its own gated action.
- Replaced the numbered S0-S12 workflow with a semantic, goal-routed execution graph.
- Renamed `agents/prototype-agent.md` to `agents/ui-delivery-agent.md` and unified UI runtime fields around `ui_delivery_preferences`, `ui_delivery_trace`, `ui_delta`, `representation`, and `ui_delivery` scoring.
- Renamed the active UI capability entry points to `artifacts/ui-delivery-contract.md` and `skills/multi-platform-ui-delivery/` so Agent routing no longer depends on obsolete prototype-generation terminology.
- Promoted standalone HTML from a compatibility fallback concept to a first-class `portable_html` delivery mode with explicit fidelity boundaries.
- Replaced the 11/14-section PRD templates with a decision-first 8/10-section structure that puts recommendation, confidence, scope, blockers, readiness, and next checkpoint before document administration.
- Made tracking, copy/i18n, UI handoff, test guidance, and UI-state requirements applicability-aware instead of forcing every PRD to emit the same tables and states.
- Rebuilt both README demo images as 4.0 Agent run snapshots showing product judgment, bounded Loop evidence, stop reasons, and resume conditions.
- Made review findings operationally closed: every Critical/High finding now requires a verified fix, an owned accepted risk, or a replan, and final recommendations must agree with unresolved findings.
- Made memory learning source-backed and sensitivity-aware, and made self-improvement runs prove their failure source, generalization boundary, fix surface, validation commands, and deterministic regression update.

### Removed

- Removed `workflow/package-workflow.md` and the version-specific migration documents from the active product surface.
- Removed compact legacy run-id support, permissive trace skipping, `--allow-legacy-run-id`, and `--strict-agent-trace`.
- Removed optional strict modes from Agent trace and Loop validation; complete runtime evidence is now mandatory for every final run.
- Removed legacy UI trace aliases such as `prototype_preferences`, `isolated_ui_prototype`, `prototype_delta`, `prototype_representation`, artifact `prototype`, and prototype quality-score keys.
- Removed the obsolete `self_contained_html_from_host_code` mode and the old prototype contract/skill paths; current runs must use `portable_html` and the UI Delivery entry points.
- Removed the duplicate top-level requirement-list pattern and retired pre-4.0 outputs as current demo evidence; historical runs are now labeled analysis baselines.

### Validation

- Release validation covers repository structure, Python compilation, mandatory Agent trace fixtures, every Loop stop branch, reflection/learning safety branches, decision-first PRD positive/negative branches, template HTML rendering, expected failure fixtures, obsolete-runtime guards, scorecard, historical evidence analysis, skill cleanup, and whitespace checks.

## [3.0.1] - 2026-07-10

### Added

- Added `action_closure.critical_path` to the Agent run log so final recommendations identify accountable owners, due phases, source decisions or blockers, completion evidence, and execution status.
- Added strict action-closure validation to `scripts/validate_agent_trace.py`, including decision/blocker reference checks and termination-condition alignment.
- Added dedicated action-closure regression coverage and scorecard metrics for runs that provide next steps without an executable critical path.

### Changed

- Updated PM Orchestrator, Review Agent, Agent Interface, operating model, prompt system, and final delivery contract so product recommendations remain externally auditable and actionable.

### Validation

- Repository, Python compilation, Agent trace fixtures, scorecard, historical evidence analysis, and whitespace validation are required for this iteration.

## [3.0.0] - 2026-07-09

### Added

- Repositioned PM Copilot as an AI Product Manager Agent System with a goal-driven operating model instead of a workflow-first kit.
- Added `agents/agent-operating-model.md` with Observe, Frame, Decide, Act, Verify, Learn, task modes, autonomy levels, replan triggers, and final delivery contract.
- Added user-facing docs for practical use cases, output gallery, agent modes, and 3.0 migration.
- Added `workflow/delivery-check-workflow.md` and kept `workflow/package-workflow.md` as a compatibility redirect.
- Added agentic run-log fields for strategy, task mode, autonomy level, success criteria, tool plan, decisions, replan triggers, review loop, memory candidates, and next actions.
- Added an eval for Agent System behavior that checks mode selection, product judgment, PM usefulness review, next actions, and memory candidates.

### Changed

- Rewrote `README.md` and `README.en.md` so the first screen explains practical AI PM outcomes instead of internal workflow assets.
- Simplified `PM_COPILOT.md` into an Agent front door that routes to operating model, workflow, artifact contracts, tool contracts, and task skills.
- Reworked `workflow/main-workflow.md` into an execution graph where S0-S12 remains the default path but can be skipped, merged, or revisited by task mode.
- Updated PM Orchestrator, Agent Interface, Review Agent, Prompt System, and Trace Contract so agents output judgment, confidence, alternatives, next actions, and PM usefulness review evidence.
- Expanded repository validation for the 3.0 operating model, README positioning, stale changelog markers, stale scorecards, adapter snippet drift, and orphan one-off plan docs.

### Fixed

- Replaced the historical `2.3.0` changelog placeholder commit marker with the real commit reference.
- Regenerated ignored scorecard evidence for the current eval portfolio.
- Shortened overlong skill descriptions while preserving trigger words and capability boundaries.
- Added explicit legacy run-id compatibility in delivery checks for retained local 2.x runtime evidence while preserving strict 3.0 naming for new outputs.

### Validation

- Repository validation covers the new Agent operating model and 3.0 docs.
- Required release validation was run for tool preflight, repository validation, Python compilation, scorecard, skill cleaner, delivery checks, visual validation, and git whitespace.

## [2.10.3] - 2026-07-09

### Fixed

- Prevented CI Python bytecode cache artifacts from being misclassified as PM Copilot core source changes by the self-iteration release guard.
- Disabled bytecode writes during the GitHub Actions compilation step to keep validation worktrees clean.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile scripts/*.py skills/skill-cleaner/scripts/skill_cleaner.py`.

## [2.10.2] - 2026-07-09

### Fixed

- Hardened the GitHub Actions validation workflow by pinning Python to 3.12 and splitting Python compilation, tool preflight, and repository validation into separate steps for clearer failure diagnostics.
- Added GitHub workflow files to the self-iteration release guard so CI workflow changes also require version, changelog, and optimization-cycle evidence.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/*.py skills/skill-cleaner/scripts/skill_cleaner.py`.
- Clean-clone validation passes for the pushed source state.

## [2.10.1] - 2026-07-09

### Fixed

- Strengthened PRD copy/i18n guidance so pure-text extraction only includes brand-new UI copy with no existing i18n key, while existing-key copy stays in the usage/key mapping.
- Added output validation that fails PRDs when copy declared as existing-key reuse is also present in the pure-text extraction block, with a guard for explicit "no existing key found" wording.
- Added a self-iteration release guard in repository validation: when PM Copilot core source files change in a git checkout, `VERSION`, `CHANGELOG.md`, and an optimization-cycle note must be changed in the same working tree.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/validate_outputs.py scripts/validate_repo.py`.
- Delivery validation passes for the source run that exposed the i18n extraction issue.

## [2.10.0] - 2026-07-07

### Changed

- Strengthened implemented-feature PRD image guidance so field/value requirement-detail tables must keep real images and missing-image markers inside the same `图示`/`截图` table cell.
- Clarified the table-cell placeholder format: `占位图：<file>.png<br>用途：<purpose>`, while preserving the two-line blockquote form for prose positions.
- Added practice-driven self-iteration workflow documentation and trace/template fields so real user corrections become generalized PM Copilot improvements with versioning, validation, regression, and embedded-copy sync steps.
- Added a regression eval for implemented-feature PRDs whose images or placeholders drift outside requirement-detail tables.

### Fixed

- Made `render_prd_html.py` remove the H1 title from the PRD HTML table of contents after stable heading IDs are assigned, including Pandoc output where TOC link attributes are line-wrapped.
- Added output validation that fails implemented-feature PRDs when images or missing-image placeholders appear outside a field/value requirement-detail table that represents the same requirement.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/install_adapter.py scripts/render_prd_html.py scripts/run_delivery_checks.py scripts/validate_outputs.py scripts/validate_repo.py`.
- Renderer and validator smoke checks pass for H1-free TOC output and table-contained missing-image placeholders.
- Git whitespace validation passes with `git diff --check`.

## [2.9.8] - 2026-06-30

### Changed

- Fixed PRD HTML table-of-contents styling so inline code in TOC links inherits the active, hover, and default link color instead of using the global code text color.
- Added output validation to prevent TOC inline code from visually breaking link color consistency.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/install_adapter.py scripts/render_prd_html.py scripts/run_delivery_checks.py scripts/validate_outputs.py scripts/validate_repo.py`.
- Git whitespace validation passes with `git diff --check`.

## [2.9.7] - 2026-06-30

### Changed

- Expanded PRD HTML rendering so the left table of contents includes numbered fourth-level sections, covering requirement-detail subsections such as per-model capability entries.
- Strengthened Chinese PRD copy/i18n guidance so pure-text extraction defaults to Chinese-only user-facing copy unless bilingual output is explicitly requested.
- Added output validation that numbered `h2`/`h3`/`h4` headings appear in `prd.html` TOC and that Chinese pure-text copy extraction does not silently mix English UI copy.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/install_adapter.py scripts/render_prd_html.py scripts/run_delivery_checks.py scripts/validate_outputs.py scripts/validate_repo.py`.
- Git whitespace validation passes with `git diff --check`.

## [2.9.6] - 2026-06-30

### Changed

- Aligned installer-generated Codex, Claude Code, and Cursor adapters with the bundled adapter templates so structured references, document handoffs, parameter tables, rule references, data dictionaries, and SOP/runbook requests also trigger the local PM Copilot workflow.
- Preserved the document-class no-PRD exception in installer-generated adapter snippets, preventing adapter installs from narrowing the workflow behavior compared with the source templates.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/install_adapter.py scripts/render_prd_html.py scripts/run_delivery_checks.py scripts/validate_outputs.py scripts/validate_repo.py`.
- Git whitespace validation passes with `git diff --check`.

## [2.9.5] - 2026-06-30

### Changed

- Clarified that `@pm-copilot` and equivalent wording in embedded repositories must resolve to the local `pm-copilot/PM_COPILOT.md` workflow, not external agents, MCP servers, plugins, or hosted Copilot tools.
- Updated Codex, Claude Code, Cursor, and installer-generated adapters to include the local PM Copilot reference rule.
- Required implemented-feature PRD delivery to always generate `prd.html`, while keeping ordinary PRD and structured-reference HTML generation request-driven.
- Strengthened implemented-feature PRD guidance so screenshots and placeholders stay inside the related requirement detail instead of detached screenshot lists.
- Added output validation that active implemented-feature PRDs require `prd.html`, local PRD image references must exist under `assets/`, and implemented-feature images/placeholders must stay inside the requirement detail section.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/install_adapter.py scripts/render_prd_html.py scripts/run_delivery_checks.py scripts/validate_outputs.py scripts/validate_repo.py`.
- Git whitespace validation passes with `git diff --check`.

## [2.9.4] - 2026-06-29

### Changed

- Standardized PRD templates around a fixed numbered structure: document information, version history, background, goals, research, requirement list, requirement details, tracking, i18n, acceptance criteria, and test suggestions.
- Required PRD titles to use a one-sentence requirement plus date format instead of loose topic lists ending in `PRD`.
- Moved flow diagrams into the specific requirement detail they explain, and made them conditional rather than global default sections.
- Added requirement-detail UI specification guidance for frontend page, component, visual-state, and interactive-control changes.
- Gated code implementation, code location, and validation sections to implemented-feature PRDs only.
- Updated contracts, prompts, skill guidance, and validators to hide non-applicable optional blocks instead of emitting empty placeholders.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/render_prd_html.py scripts/run_delivery_checks.py scripts/validate_outputs.py scripts/validate_repo.py`.
- Git whitespace validation passes with `git diff --check`.

## [2.9.3] - 2026-06-24

### Changed

- Improved PRD HTML rendering for multi-column requirement image rows so empty trailing content cells are merged with `colspan` and figures do not widen a single data column.
- Updated PRD contracts, templates, and workflow guidance to treat multi-column figure rows as whole-row requirement explanations.
- Added output validation to reject unmerged multi-column requirement image rows that leave empty trailing cells after a figure.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/render_prd_html.py scripts/run_delivery_checks.py scripts/validate_outputs.py scripts/validate_repo.py`.
- Git whitespace validation passes with `git diff --check`.

## [2.9.2] - 2026-06-24

### Changed

- Generalized the commerce PRD stability eval so PM Copilot source documentation keeps reusable quality rules without preserving host-project business wording.

### Validation

- Project-specific leakage scan passes across PM Copilot source files outside generated outputs and vendored assets.
- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/render_prd_html.py scripts/run_delivery_checks.py scripts/validate_outputs.py scripts/validate_repo.py`.
- Git whitespace validation passes with `git diff --check`.

## [2.9.1] - 2026-06-24

### Changed

- Sanitized release validation examples so PM Copilot source documentation uses generic output placeholders instead of host-project run identifiers.

### Validation

- Project-specific leakage scan passes across PM Copilot source files outside generated outputs and vendored assets.
- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/render_prd_html.py scripts/run_delivery_checks.py scripts/validate_outputs.py scripts/validate_repo.py`.
- Git whitespace validation passes with `git diff --check`.

## [2.9.0] - 2026-06-24

### Added

- Added a commerce PRD HTML stability eval covering payment SDK document links, inline requirement figures, i18n pure-text extraction, fixed PRD HTML TOC behavior, table alignment, and requirement-detail structure.
- Added output validation for copy-only pure-text i18n blocks so `key = copy` lines are rejected inside PM-facing copy extraction blocks.
- Added output validation for consistent left-aligned Chinese PRD tables, inline requirement image rows, and per-function requirement detail coverage when a PRD uses subsections instead of one large detail table.
- Added PRD HTML validation for the fixed PM Copilot document shell, stable ASCII heading/TOC anchors, left-aligned table styling, and H1-free table of contents.

### Changed

- Updated `scripts/render_prd_html.py` to replace Pandoc default styling with a fixed PM Copilot document style, normalize heading IDs to stable ASCII anchors, render the TOC from numbered sections only, and use a consistent left-navigation treatment.
- Updated delivery checks so browser-readable PRD documents may keep normal external documentation hyperlinks while still blocking remote scripts, stylesheets, images, and CDN runtimes.
- Updated PRD contract, implemented-feature workflow docs, templates, README, and quality rubric to separate requirement list vs requirement details, require inline figures/placeholders, keep pure copy separate from i18n key mapping, and stabilize PRD HTML presentation.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/render_prd_html.py scripts/run_delivery_checks.py scripts/validate_outputs.py scripts/validate_repo.py`.
- Commerce PRD regression validation passes with `python3 scripts/run_delivery_checks.py <host-repo>/pm-copilot/outputs/<run-id> --language zh --skip-repo`.
- Git whitespace validation passes with `git diff --check`.

## [2.8.0] - 2026-06-23

### Added

- Added vendored Mermaid 11.13.0 browser runtime under `vendor/mermaid/` so `scripts/render_prd_html.py` can copy `assets/mermaid.min.js` into each PRD output and render flow diagrams offline.
- Added implemented-feature PRD template sections for Mermaid functional flow diagrams and pure-text copy/i18n extraction.
- Added output validation for PRD flow sections, copy/i18n extraction blocks, table-of-contents reading sync, local Mermaid runtime presence, table-cell image retention, and forbidden Chinese missing-image labels such as `待补真实图`.

### Changed

- Improved `prd.html` rendering so the left table of contents starts from numbered `h2`/`h3` sections, excludes the H1 title, tracks the current reading position, and removes the Pandoc manual URL comment.
- Improved PRD table readability by using auto table layout, narrower two-column field cells, wider content cells, and table-cell image styling.
- Expanded image lightbox support from standalone figure images to both `figure img` and `td img`, preserving screenshots inside the requirement detail row they explain.
- Tightened PRD writing, workflow, artifact, README, and PM Copilot entry rules around page/window-level screenshot coverage, inline screenshot placement, Mermaid flowcharts instead of tables/PNGs, and pure-text i18n handoff.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/render_prd_html.py scripts/validate_outputs.py scripts/validate_repo.py`.
- Implemented-feature PRD delivery validation passes with `python3 scripts/run_delivery_checks.py <host-repo>/pm-copilot/outputs/<run-id> --language zh --skip-repo`.
- Renderer smoke validation confirms H1-free TOC, reading-position sync, plain Mermaid containers, local Mermaid runtime, table auto layout, table-image lightbox support, and no Pandoc manual URL.
- Git whitespace validation passes with `git diff --check`.

## [2.7.5] - 2026-06-18

### Added

- Added `docs/implemented-feature-prd-workflow.md` to codify the implemented-feature-to-PRD delivery flow, embedded output path, inline screenshot replacement loop, and HTML rendering expectations.
- Added `templates/implemented-feature-prd-template.md` for implementation-backed PRDs with parameters, rules, states, data/API requirements, real-data integration notes, acceptance criteria, and evidence mapping.
- Added `scripts/render_prd_html.py` to render `prd.md` into browser-readable `prd.html` with `pagetitle`, full-width document styling, wide-table handling, and image lightbox support.

### Changed

- Updated PM Copilot entry, README files, prompt rules, PRD skill, artifact contracts, direct/embedded use docs, workflow, and validation tooling so implemented-feature PRDs are generated under `outputs/<run-id>/` or embedded `pm-copilot/outputs/<run-id>/`.
- Tightened screenshot handling rules so real images and missing-image markers stay inline with the related requirement, and missing Chinese screenshots use only the exact `占位图` block.
- Clarified screenshot naming as content plus concrete state, such as `文件上传-上传中.png` and `文件上传-上传失败.png`, instead of generic figure numbers or `-状态` suffixes.
- Extended output validation to require direct `outputs/<run-id>` folders, reject `.DS_Store`, enforce one PRD H1, reject detached image lists, validate local image paths, and catch generic screenshot names.
- Extended repository validation to require the implemented-feature PRD workflow docs, template, renderer, and validation tokens.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/validate_outputs.py scripts/render_prd_html.py scripts/validate_repo.py`.
- Screenshot naming rule smoke validation passes for concrete-state names and rejects generic `-状态`, `-state`, and figure-number names.
- Git whitespace validation passes with `git diff --check`.

## [2.7.4] - 2026-06-15

### Added

- Added implemented-feature-to-PRD delivery guidance for reconstructing complete PRDs from current branch evidence, changed files, UI surfaces, screenshots/assets, validation, and unverified product intent.
- Added `prd.html` as a browser-readable PRD document artifact for external delivery, separate from UI prototypes and document prototypes.
- Added PRD HTML expectations for inline image placeholders, table-cell images, click-to-fullscreen image viewing, rendered Mermaid diagrams, readable wide tables, and neutral document styling.
- Added `implemented_feature_prd` run-log trace fields for diff evidence, changed files, behavior evidence, screenshots/placeholders, validation evidence, and completeness checks.

### Changed

- Updated PRD, workflow, package, artifact, and direct-use guidance so implemented branch behavior is fully represented in Markdown and HTML without detached screenshot lists or manual reviewer backfill.
- Updated output and delivery validators to accept and inspect `prd.html` alongside `prd.md`.
- Updated repository validation to ignore generated binary/review asset folders under `outputs/` during text scans.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/validate_outputs.py scripts/run_delivery_checks.py scripts/validate_repo.py scripts/validate_prototype_visual.py scripts/validate_ui_preview.py scripts/extract_ui_region.py scripts/preflight_tools.py scripts/inspect_host_frontend.py scripts/install_adapter.py scripts/agent_improvement_scorecard.py scripts/preflight_integrations.py scripts/setup_visual_validation.py`.
- Git whitespace validation passes with `git diff --check`.

## [2.7.3] - 2026-06-01

### Added

- Added an implementation-then-extraction UI delivery path for requests where the feature is first completed in the current host repository and then handed off as a 1:1 source-derived HTML artifact for engineering review.
- Added editable annotation-layer guidance so generated markers and notes are driven by a default configuration that users can add to, remove from, or edit without rewriting the product surface.
- Added fallback handoff guidance for missing PM Copilot git metadata: when the target repository cannot be found, write the source files to a same-name folder under the local Desktop and avoid claiming a remote push.

### Changed

- Updated the prototype template so annotation markers are generated from `annotationConfig.notes`, making the note set easier to edit while preserving body-only marker popovers and the right-side annotation list.
- Clarified that `source_extract_html` may be derived from an explicitly user-approved host implementation, not only from an isolated preview route, when the user asks to complete the feature in the current repository first.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/validate_outputs.py scripts/run_delivery_checks.py scripts/validate_repo.py scripts/validate_prototype_visual.py scripts/validate_ui_preview.py scripts/extract_ui_region.py scripts/preflight_tools.py`.
- Prototype template inline JavaScript validation passes with `node --check`.
- Dated `index.html` compatibility output smoke validation passes with `python3 scripts/validate_outputs.py /tmp/outputs/pmcopilot-index-smoke-2026-06-01 --language zh`.
- Git whitespace validation passes with `git diff --check`.

## [2.7.2] - 2026-06-01

### Added

- Added a real-run UI delivery improvement plan covering run naming, source-first parity, offline prototype expectations, annotation behavior, validation, and maintainer handoff.
- Added compatibility support for `index.html` as an offline UI delivery entry inside a dated run folder, while preserving `prototype-<platform>.html` and source-extracted HTML handoff support.
- Added validation for dated ASCII run folder names under `outputs/`.
- Added stricter annotation validation so marker popovers contain only annotation body text, avoid horizontal overflow, and the right-side annotation list closes when clicking outside the panel.

### Changed

- Updated the compatibility HTML template so marker popovers no longer render the annotation number, title, or close button; the full numbered note list remains in the right-side annotation panel.
- Updated UI delivery guidance to treat screenshot-only pages as evidence, not prototypes, unless backed by real interactive controls and source/style mapping.
- Updated run-id guidance from bare scenario slugs or compact timestamps to `requirement-slug-YYYY-MM-DD`, with a numeric suffix only for same-day collisions.

### Validation

- Repository validation passes with `python3 scripts/validate_repo.py`.
- Script bytecode validation passes with `python3 -m py_compile scripts/validate_outputs.py scripts/run_delivery_checks.py scripts/validate_repo.py scripts/validate_prototype_visual.py scripts/validate_ui_preview.py scripts/extract_ui_region.py scripts/preflight_tools.py`.
- Prototype template HTML and inline JavaScript validation passes with Python `html.parser` and `node --check`.
- Dated `index.html` compatibility output smoke validation passes with `python3 scripts/validate_outputs.py /tmp/outputs/pmcopilot-index-smoke-2026-06-01 --language zh`.

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

Commit: `124b519` feat: add image reference reconstruction mode.

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
