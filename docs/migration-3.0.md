# Migration To PM Copilot 3.0

PM Copilot 3.0 changes the product positioning and default runtime model from workflow-first to Agent-first.
The old paths remain compatible where possible.

## What Changed

- Public positioning is now AI Product Manager Agent System.
- `PM_COPILOT.md` is a lighter Agent front door.
- Detailed behavior lives in `agents/agent-operating-model.md`, `workflow/`, `artifacts/`, `tools/`, and task skills.
- `workflow/main-workflow.md` is now an execution graph. S0-S12 remains the default safe path but is no longer the only route.
- `run-log.yaml` has additive Agent trace fields such as `agent_strategy`, `task_mode`, `autonomy_level`, `tool_plan`, `decision_record`, `review_loop`, `memory_candidates`, and `next_actions`.
- `workflow/delivery-check-workflow.md` is the current delivery-check entry.

## Compatibility

Existing prompts still work.
Users do not need to mention task modes or state numbers.
Natural product goals are now recommended, for example:

```text
Please inspect current product context and create a PRD, UI delivery, tracking plan, and launch readiness recommendation for this feature.
```

Old references to `workflow/package-workflow.md` still resolve because the file remains as a compatibility redirect.
New docs and prompts should use `workflow/delivery-check-workflow.md`.

Existing run logs remain readable.
New run-log fields are additive and should not break old artifacts.

Embedded usage remains the same:

```text
Follow the local pm-copilot/PM_COPILOT.md workflow to produce the PRD.
```

The adapter still resolves `@pm-copilot` to the local repository file, not to an external tool.

## Recommended Upgrade Practice

- Keep old user prompts, but prefer natural product goals over internal workflow terms.
- For implemented-feature PRD delivery, keep expecting `prd.md` and required `prd.html`.
- For final delivery, prefer `python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>`.
- For UI delivery, keep source-backed preview/delta as the default when frontend source exists.
- For PM Copilot repository changes, update `VERSION`, `CHANGELOG.md`, and an optimization-cycle note.
