# Versioning

PM Copilot uses three-segment semantic versioning:

```text
MAJOR.MINOR.PATCH
```

Example:

```text
1.0.0
```

## Version Meaning

| Segment | Meaning |
|---|---|
| MAJOR | Broad refactors or core model changes that reshape repository structure, workflow, default deliverables, artifact contracts, or agent/skill/tool boundaries |
| MINOR | Normal feature iterations, new capabilities, new eval coverage, new platform behavior, or backward-compatible workflow improvements |
| PATCH | Patches, small fixes, copy edits, local documentation corrections, validator bug fixes, and narrow prompt refinements |

## Current Stability

`1.x` means:

- Suitable for early users and contributors.
- Interfaces may still change.
- Artifact contracts are usable but not final.
- Users should copy their own `context/` and generated `outputs/` before upgrading.

## Compatibility Policy

Breaking changes include:

- Renaming top-level directories.
- Removing required artifact sections.
- Changing required tracking plan columns.
- Changing agent handoff payload shape.
- Removing or renaming existing skills.
- Changing workflow states in a way that breaks existing prompts.

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
- `docs/release-checklist.md` if release rules changed
- README links if new major docs are added
- Evals or templates if artifact contracts changed

## Deprecation Policy

When changing a public artifact contract, keep the old field documented for at least one minor release unless the field is unsafe. Mark deprecated items clearly in the changelog.
