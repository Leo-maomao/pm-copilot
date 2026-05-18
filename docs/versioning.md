# Versioning

PM Copilot uses three-segment semantic versioning:

```text
MAJOR.MINOR.DEBUG
```

Example:

```text
0.1.10
```

## Version Meaning

| Segment | Meaning |
|---|---|
| MAJOR | Breaking changes to repository structure, artifact contracts, workflow states, or agent interfaces |
| MINOR | New agents, skills, artifact types, examples, templates, or backward-compatible workflow capabilities |
| DEBUG | Fixes, documentation improvements, example corrections, non-breaking template refinements, and commit-by-commit maintenance updates |

## Current Stability

`0.1.x` means:

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
- Adding new examples.
- Improving wording in existing prompts.
- Adding new guardrails.
- Adding optional validation checks.

## Increment Rules

- Increment `MAJOR` for breaking repository structure, artifact contract, workflow state, or agent interface changes.
- Increment `MINOR` for new backward-compatible capabilities, artifact types, agent/skill additions, examples, or workflow features.
- Increment `DEBUG` for each normal committed change, including fixes, docs, templates, guardrails, eval updates, and validation refinements.
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
- Example outputs if artifact contracts changed

## Deprecation Policy

When changing a public artifact contract, keep the old field documented for at least one minor release unless the field is unsafe. Mark deprecated items clearly in the changelog.
