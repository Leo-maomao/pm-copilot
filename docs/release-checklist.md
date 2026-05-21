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
- New or absorbed skill capability maps to one canonical skill instead of creating a duplicate sibling.
- Agent definitions follow `agents/agent-interface.md`, include required sections, and use stable handoff status values.
- Artifact contracts match templates.
- YAML templates do not contain duplicate keys at the same mapping level.
- Run-log quality score maximums and thresholds match `docs/quality-rubric.md`.
- Optimization docs and eval templates are present.

## Regression Cases

- Real failures that should not regress are captured in `evals/`.
- Evaluation cases describe expected artifacts without committing generated runtime outputs.
- Generated `outputs/` folders are not shipped as repository examples.
- Multi-scenario evaluation covers at least one permissions/security case, one privacy/data-minimization case, one operational workflow, one reliability/offline case, one personalization/UI-state case, and one release/readiness case before claiming broad improvement.
- Multi-runtime products cover at least one contract scenario across frontend, BFF/API, public capability layer, storage/auth, and deployment or SEO/runtime boundaries when those layers exist.

## Validation

Run:

```bash
python3 scripts/preflight_tools.py --strict
python3 scripts/validate_repo.py
```

When a release claim depends on external research or source-backed examples, run preflight with a concrete network check:

```bash
python3 scripts/preflight_tools.py --check-network <url> --require-network --strict
```

Optional:

```bash
python3 scripts/run_delivery_checks.py outputs/<run-id> --language zh
tidy -errors -quiet -utf8 templates/prototype-template.html
```

## Content Quality

- Evals use synthetic or anonymized data.
- Tracking plans avoid forbidden sensitive properties.
- Tracking plans record taxonomy source and mark proposed events when no existing convention is loaded.
- Research claims include sources or are labeled as assumptions.
- Human confirmation points are visible for privacy, payment, legal, finance, or compliance issues.
- PRD, engineering handoff, and launch readiness are separated; launch blockers are not hidden behind engineering-ready status.
- Reference or regulated content records source status, review owner, review status, disclaimer status, and launch impact.
- UI deliverables state the source-backed or standalone compatibility boundary and include enough annotations for UI and engineering review.
- UI visual validation has run with screenshot/diff evidence, or setup was attempted and the skipped reason is a concrete setup failure, environment restriction, or user-declined installation.
- Tool registry, preflight, delivery orchestrator, and tool result contracts are updated together when tool behavior changes.
- Review findings include artifact, evidence, owner, required-before phase, and status.
- `dev-tasks.yaml` and `launch-decision.yaml`, when generated, pass their contracts and do not mark blocked work or unapproved launch gates as ready.
- Serious real-task failures are added to `evals/` as regression cases.
- Passing validators do not replace product, security, legal, analytics, or launch approval. Release notes must still list known limitations, required human approvals, and rollback expectations.
- Contract checks should identify breaking field changes, fixture coverage, compatibility expectations, and rollback/downgrade paths. They do not replace integration tests or release approval.

## Release Notes

Release notes should include:

- New capabilities
- Breaking changes
- Migration notes
- Validation results
- Known limitations
- Regression scenarios covered
- Rollback or downgrade expectations when a workflow or artifact contract changes
