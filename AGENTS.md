# PM Copilot Repository Guidance

This repository is the source of truth for PM Copilot. For product work or PM Copilot maintenance, read `PM_COPILOT.md` before producing an artifact or changing runtime instructions.

## Runtime Loading

1. Read the bootstrap documents listed in `indexes/runtime-routing.yaml`.
2. Classify the request into a task mode, then load only that mode's route documents.
3. Resolve `capability_selectors` with `python3 scripts/resolve_runtime_capabilities.py --task-mode <mode> --request <request>` when optional capability selection is relevant. Load only the returned skill documents in addition to the base route.
4. Do not discover skills by scanning the entire `skills/` tree. The index is the disclosure boundary.

## Boundaries

- PM Copilot is an auxiliary product agent, not a host-product implementation or deployment agent.
- Skills limited to `self_improvement` may change this repository only; they must never be used to modify an embedded host product.
- Before invoking a skill that records durable decisions or proposes repository changes, obtain explicit user confirmation for the decision or change.

## Verification

After editing routing, skills, workflow instructions, or validation scripts, run:

```bash
python3 scripts/validate_runtime_routing.py
python3 scripts/validate_repo.py
```
