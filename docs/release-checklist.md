# Release Checklist

Use this checklist before tagging or publishing a release.

## Required Metadata

- `VERSION` is updated.
- Run `python3 scripts/sync_plugin_version.py` after changing `VERSION`; the Codex plugin manifest must use the same base version plus one `+codex.<cachebuster>` suffix.
- `CHANGELOG.md` includes the new version.
- PM Copilot self-iterations that touch core workflow, contract, template, skill, guardrail, agent, or validator files include a `docs/optimization-cycles/` note with version change, validation, remote-push status, and embedded-copy sync targets.
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

- Real failures that should not regress are captured in private local evaluation cases or anonymized public regression notes.
- Evaluation cases describe expected artifacts without committing generated runtime outputs.
- Generated `outputs/` folders are not shipped as repository examples.
- Multi-scenario evaluation covers at least one permissions/security case, one privacy/data-minimization case, one operational workflow, one reliability/offline case, one personalization/UI-state case, and one release/readiness case before claiming broad improvement.
- Multi-runtime products cover at least one contract scenario across frontend, BFF/API, public capability layer, storage/auth, and deployment or SEO/runtime boundaries when those layers exist.

## Validation

Run:

```bash
python3 scripts/preflight_tools.py --strict
python3 scripts/validate_repo.py
python3 -m py_compile scripts/*.py skills/skill-cleaner/scripts/skill_cleaner.py
python3 scripts/test_agent_collaboration_trace.py
python3 scripts/test_agent_task_ledger.py
python3 scripts/test_prd_evidence_upgrade.py
python3 scripts/test_upgrade_local_outputs.py
python3 scripts/test_sync_embedded_copies.py
```

When a release claim depends on external research or source-backed examples, run preflight with a concrete network check:

```bash
python3 scripts/preflight_tools.py --check-network <url> --require-network --strict
```

Optional:

```bash
python3 scripts/run_delivery_checks.py outputs/<run-id> --language zh
python3 scripts/validate_outputs.py outputs/<historical-run-id> --historical-prd-upgrade --language zh
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
- UI deliverables state the source-backed or portable HTML boundary and include enough annotations for UI and engineering review.
- UI visual validation has run with screenshot/diff evidence, or setup was attempted and the skipped reason is a concrete setup failure, environment restriction, or user-declined installation.
- Tool registry, preflight, delivery orchestrator, and tool result contracts are updated together when tool behavior changes.
- Review findings include artifact, evidence, owner, required-before phase, and status.
- `dev-tasks.yaml` and `launch-decision.yaml`, when generated, pass their contracts and do not mark blocked work or unapproved launch gates as ready.
- Serious real-task failures are added to private local evaluation cases or anonymized public regression notes.
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
