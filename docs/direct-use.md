# Direct Use

This is the recommended user experience for product managers.

Instead of manually copying templates and creating task folders, open this repository in an agent workspace and say what you need.

## One-Shot Prompt

```text
<write your product request here>

If important information is missing, ask me first.
If enough information is available, create the full review-ready package.
Use my local product context if it exists; otherwise use the example context and mark assumptions.
```

The agent should automatically follow `PM_COPILOT.md` and:

- Infer a scenario name and unique run id.
- Create `examples/<run-id>/task-brief.md`.
- Create `outputs/<run-id>/`.
- Ask must-answer clarification questions before downstream generation.
- Stop and wait when critical information is missing.
- Generate PRD, metrics, tracking plan, flow, prototype, review checklist, final package, and run log.
- Run validation when possible.

## Codex and AGENTS.md

In Codex, `AGENTS.md` is an official project instruction file. PM Copilot's `AGENTS.md` is only a thin shim for standalone mode. The canonical cross-platform entry is `PM_COPILOT.md`.

If you start Codex from the `pm-copilot` folder, Codex should load `AGENTS.md`, which points it to `PM_COPILOT.md`.

```text
<write your product request here>
```

If PM Copilot is nested inside another development repository, use `docs/embedded-use.md` and the adapter templates in `adapters/`.

For one-command adapter installation, run:

```bash
python3 scripts/install_adapter.py --host /path/to/host-repo --tool all
```

Avoid putting PM Copilot's full workflow into the root `AGENTS.md` of an unrelated software repository. Use a small delegation adapter instead.

## Recommended Workspace Setup

Put `pm-copilot` in a place your agent can access, for example:

```text
/Users/<you>/Desktop/product_manage/pm-copilot
```

Then open the folder in your agent environment.

## Optional Product Context

For better results, create:

```text
context/product-context.local.yaml
```

You do not need to do this before the first run. If it is missing, the agent should use the example context and mark assumptions.

## Expected Flow

```text
User gives request
-> Agent reads PM_COPILOT.md directly or through an adapter
-> Agent loads workflow, guardrails, contracts, and context
-> Agent asks high-impact clarification questions before generation
-> User answers or explicitly says to proceed with assumptions
-> Agent creates scenario brief and outputs
-> Agent reviews package
-> Agent returns artifact paths and blockers
```

## Example

```text
We want to improve coupon usage on checkout. Users say they cannot find where to apply coupons, and support tickets are increasing.
```

Expected generated paths:

```text
examples/checkout-coupon/task-brief.md
outputs/checkout-coupon/
```

If the same scenario already exists, the agent should create a timestamped run folder such as:

```text
examples/checkout-coupon-20260518-1430/task-brief.md
outputs/checkout-coupon-20260518-1430/
```

## When to Use Manual Mode

Manual setup is still useful when:

- You want to prepare a carefully written task brief before running the agent.
- You are building regression evals.
- You are contributing examples to the repository.
- You want to compare outputs across multiple agent platforms.

For manual mode, see `docs/quick-start.md`.
