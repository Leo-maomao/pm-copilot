# Practice-Driven Self-Iteration

Use this workflow when a real PM Copilot delivery exposes a defect and the user asks to improve PM Copilot itself.

## Trigger

Start this workflow after a completed or partially completed real run when there is concrete evidence such as:

- User correction or complaint.
- Failed delivery check.
- Manual artifact repair.
- Repeated tool or rendering workaround.
- Review finding that should have been caught by PM Copilot.

## Required Inputs

- The source run folder, especially `prd.md`, `prd.html`, `run-log.yaml`, and `tool-results/delivery-check-report.json` when present.
- The exact user correction or observed failure.
- The relevant PM Copilot source surfaces: workflow, skill, contract, template, validator, renderer, docs, or eval.
- The current `VERSION` and `CHANGELOG.md`.

## Workflow

1. Reconstruct what happened from artifacts and user correction, not memory.
2. Classify the failure with `docs/failure-taxonomy.md`.
3. Rewrite the failure as a generic PM Copilot capability gap. Remove host product names, local paths, APIs, routes, and domain-specific assumptions from generic source files.
4. Pick the smallest durable fix surface:
   - Validator or renderer when the issue is mechanically detectable.
   - Artifact contract when the output shape is ambiguous.
   - Template when the generated structure nudges the agent into a bad shape.
   - Skill or workflow when sequencing, ownership, or method is wrong.
   - Guardrail or agent contract when the issue is unsafe, overconfident, or cross-agent.
   - Docs when the behavior is already enforced but hard to operate.
5. Add or update a regression eval for high-severity, repeated, or cross-surface failures.
6. Update `templates/optimization-cycle-template.yaml` fields or create an equivalent local optimization note.
7. Bump `VERSION`, update `CHANGELOG.md`, and run release validation.
8. Sync embedded PM Copilot copies in local host repositories when requested.

## Completion Criteria

- The original failure would be prevented by instructions or caught by validation in a future run.
- The fix does not encode host-specific product vocabulary into generic PM Copilot surfaces.
- `python3 scripts/validate_repo.py` passes.
- Script bytecode validation passes for changed Python files.
- `git diff --check` passes.
- `CHANGELOG.md` describes the change under the new version.

## Recommended Validation

```bash
python3 scripts/validate_repo.py
python3 -m py_compile scripts/install_adapter.py scripts/render_prd_html.py scripts/run_delivery_checks.py scripts/validate_outputs.py scripts/validate_repo.py
git diff --check
```

