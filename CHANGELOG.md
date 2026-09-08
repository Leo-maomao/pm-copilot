# Changelog

## Unreleased

## 8.0.0 - 2026-09-08

- Replaced every production PRD entry with the v2 deterministic delivery
  protocol and removed the v1 interactive controller, state file, recovery
  migrations, and tests.
- Made evidence-sufficient requests deliver all canonical artifacts without a
  confirmation stop. Missing critical product decisions produce one
  consolidated question, then continue automatically after the answer.
- Unified new, implemented-feature, composition, revision, append, source
  selector, and input-asset delivery through one atomic transaction.

- Replaced the production controller path with the v2 deterministic delivery
  engine. It builds Markdown, HTML, asset decisions, and trace evidence from
  one typed PRD model, validates semantic requirement coverage and template
  conformance, then publishes all canonical artifacts atomically.
- Introduced the v2 run-state protocol. Historical unfinished interactive
  runs are intentionally not migrated; new requests use one consolidated
  missing-decision prompt and continue through the same delivery transaction.

- Made every new PRD run deterministic-first: the controller owns scope
  collection, artifact structure, review, rendering, and validation, while a
  single optional model pass may only formalize confirmed PRD prose.
- Removed model retries, model-led clarification, specialist dispatch, and
  stage-review calls from the default PRD path.
- Added an explicit MCP entry for a new in-place PRD revision. Subsequent
  revisions now create a fresh canonical baseline instead of being resumed as
  a prior delivery attempt.
- Made MCP PRD starts, answers, and delivery confirmations asynchronous so a
  long-running model stage cannot block the MCP service or status queries.
- Persisted background controller startup leases and recover them after a
  bounded grace period, so a child-process crash cannot leave a PRD permanently
  reported as `starting`.
- Made each new in-place revision deterministic by default, preventing an old
  PRD without a model setting from launching an unnecessary Codex intake call.
- Made resumed selected-requirement revisions consume an explicit answer
  deterministically too, so legacy states cannot repeat the same intake prompt.
- Allowed an interrupted pre-intake revision to restart through the normal
  revision entry point instead of rejecting it as an active canonical PRD.
- Prevented the node-size fallback from overwriting an in-place layout revision;
  explicit four-column detail tables now convert to the requested two-column
  `维度｜需求说明` structure while preserving their confirmed cell content.
- Checkpointed intake operations before model work begins and exposed their
  active operation and lease in status responses for recovery diagnostics.
- Rejected multi-output PRD rearrangements before they can overwrite a source
  PRD as an in-place revision, and terminate the complete Codex process group
  when a stage times out or the controller exits unexpectedly.

## 7.0.5 - 2026-09-04

- Declared UTF-8 for every active runtime source containing non-ASCII content
  and added a direct-controller execution regression test for the plugin's
  Python interpreter.

## 7.0.4 - 2026-09-04

- Required the Codex plugin to use MCP-returned controller evidence before
  reporting a PRD startup failure, preventing historical or inferred Python
  errors from being presented as a current run result.

## 7.0.3 - 2026-09-04

- Removed the legacy runtime environment override from the Codex plugin. It
  now resolves only the installed personal-marketplace source and launches its
  MCP bridge with Python 3, preventing stale global runtimes from being used.

## 7.0.2 - 2026-09-04

- Removed the user-visible Codex runtime-path requirement. The plugin now
  resolves its installed source checkout and starts PRD workflows through MCP.

## 7.0.1 - 2026-09-04

- Restored the local Codex plugin release hook without restoring a copied
  global runtime: version commits refresh the plugin cachebuster and reinstall
  the personal-marketplace plugin from the repository checkout.

## 7.0.0 - 2026-09-04

- Reduced PM Copilot to four PRD workflows: new PRD, implemented-feature PRD,
  scoped PRD revision, and one-or-more-source PRD composition.
- Kept the local PRD manager, verified frontend figures, the Codex plugin, and
  on-demand multi-agent evidence and review work.
- Removed legacy provider adapters, global-runtime distribution, standalone UI
  delivery, generic PM artifacts, evaluation portfolios, and historical
  compatibility paths.
- Removed the remaining unreferenced workspace-identity and implemented-feature
  placeholder modules, obsolete standalone UI reconstruction guide, and empty
  ignored runtime directories.
