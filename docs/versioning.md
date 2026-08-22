# Versioning

PM Copilot uses three-segment semantic versioning:

```text
MAJOR.MINOR.PATCH
```

Example:

```text
2.0.0
```

## Development Branch

The repository has one canonical development branch: `main`. Updates are
developed, validated, committed, and pushed on `main`; temporary branches are
not part of the project workflow and must be removed after integration.

## Version Meaning

| Segment | Meaning |
|---|---|
| MAJOR | Broad refactors or core model changes that reshape repository structure, workflow, default deliverables, artifact contracts, or agent/skill/tool boundaries |
| MINOR | Normal feature iterations, new capabilities, new eval coverage, new platform behavior, or backward-compatible workflow improvements |
| PATCH | Patches, small fixes, copy edits, local documentation corrections, validator bug fixes, and narrow prompt refinements |

## Current Stability

`4.x` prioritizes Agent effectiveness and a single current runtime contract over compatibility with obsolete internal paths. Generated outputs remain user-owned evidence, but old run logs are not accepted as current final-delivery traces.

## Compatibility Policy

Breaking changes include:

- Renaming top-level directories.
- Removing required artifact sections.
- Changing required tracking plan columns.
- Changing agent handoff payload shape.
- Removing or renaming existing skills.
- Changing execution graph nodes in a way that breaks existing prompts.

Non-breaking changes include:

- Adding optional artifact sections.
- Adding new skills.
- Adding new eval cases.
- Improving wording in existing prompts.
- Adding new guardrails.
- Adding optional validation checks.

## Increment Rules

- Increment `MAJOR` for broad refactors, default delivery changes, repository slimming that removes public files, artifact contract changes, workflow state changes, or agent/skill/tool boundary changes.
- Increment `MINOR` for normal feature iterations, new backward-compatible capabilities, agent/skill additions, eval additions, platform behavior improvements, or workflow enhancements.
- Increment `PATCH` for small fixes, copy edits, narrow docs updates, validator bug fixes, and localized prompt/template refinements.
- Do not use prerelease suffixes or release-candidate labels.

## Upgrade Rules

Before upgrading:

1. Back up your customized `context/` files.
2. Back up generated `outputs/`.
3. Read `CHANGELOG.md`.
4. Run `python3 scripts/validate_repo.py`.
5. Compare your customized templates against the new templates manually.

After upgrading:

1. Re-run one known task.
2. Compare output quality and missing sections.
3. Review new guardrails and artifact contracts.
4. Update custom context fields only when needed.

## Release Checklist

Every release should update:

- `VERSION`
- `CHANGELOG.md`
- `docs/optimization-cycles/` note when the release comes from a practice-driven PM Copilot self-iteration
- `docs/release-checklist.md` if release rules changed
- README links if new major docs are added
- Evals or templates if artifact contracts changed

When a self-iteration changes PM Copilot core source files in a git checkout, repository validation requires `VERSION`, `CHANGELOG.md`, and a `docs/optimization-cycles/` note to be changed together. If the current folder is only an embedded copy without its own remote, record the skipped push reason and embedded-copy sync target status instead of claiming a release push.

## Removal Policy

Remove obsolete internal entry points, aliases, and permissive validation branches when they reduce Agent clarity or weaken evidence. Preserve user data and externally useful artifact formats, not historical implementation structure.
