# Release Checklist

Use this checklist before tagging or publishing a release.

## Required Metadata

- `VERSION` is updated.
- `CHANGELOG.md` includes the new version.
- README links still work.
- License is present.
- Security and contribution docs are present.

## Structure

- Required top-level directories exist.
- Each skill has `SKILL.md`.
- Each skill has `name` and `description` frontmatter.
- Agent definitions follow `agents/agent-interface.md`.
- Artifact contracts match templates.
- Optimization docs and eval templates are present.

## Examples

- Every scenario in `examples/` has matching output folder in `outputs/`.
- Every output folder has:
  - `clarifying-questions.md`
  - `assumptions.md`
  - `prd.md`
  - `metrics-tree.md`
  - `tracking-plan.csv`
  - `user-flow.mmd`
  - `review-checklist.md`
  - `final-package-summary.md`
- At least one platform-specific prototype exists when the scenario is user-facing.

## Validation

Run:

```bash
python3 scripts/validate_repo.py
```

Optional:

```bash
tidy -q -e outputs/membership-auto-renewal/prototype-h5.html
```

## Content Quality

- Examples use synthetic or anonymized data.
- Tracking plans avoid forbidden sensitive properties.
- Research claims include sources or are labeled as assumptions.
- Human confirmation points are visible for privacy, payment, legal, finance, or compliance issues.
- Prototypes are labeled low fidelity.
- Serious real-task failures are added to `evals/` as regression cases.

## Release Notes

Release notes should include:

- New capabilities
- Breaking changes
- Migration notes
- Validation results
- Known limitations
