# Direct Use

This is the recommended user experience for product managers.

Instead of manually copying templates and creating task folders, open this repository in an agent workspace and say what you need.

## One-Shot Prompt

```text
<write your product request here>

If important information is missing, ask me first.
If enough information is available, create `prd.md` and the matching clickable prototype.
If must-answer questions or unresolved `must confirm before development or launch` blockers exist, stop and wait for my answer before generating downstream artifacts.
Use my local product context if it exists; otherwise use the example context and mark assumptions.
Use my request language for headings, labels, statuses, notes, and prototype annotations.
```

The agent should automatically follow `PM_COPILOT.md` and:

- Infer a scenario name and unique run id.
- Create all generated run artifacts under `outputs/<run-id>/`.
- Ask must-answer clarification questions before downstream generation.
- Stop and wait when critical information is missing or an unresolved development/launch confirmation blocks the requested readiness.
- Generate `prd.md`, a prototype when relevant, optional exports when useful, and an internal run log.
- Keep requirement input, clarified answers, assumptions, research/reference findings, metrics, tracking plan tables, flow diagrams, risks, acceptance criteria, and validation results inside `prd.md` by default.
- Run tool preflight and validation when required by `tools/tool-registry.yaml`.
- Prefer `python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>` before final delivery.
- Run browser screenshot/visual diff validation for prototypes. If Playwright/browser tooling is missing, first run or guide `python3 scripts/setup_visual_validation.py`; skip only when setup fails, the environment forbids browser launch, or the user declines installation.
- Generate `dev-tasks.yaml` or `launch-decision.yaml` only when you ask for engineering handoff, issue planning, release readiness, or launch decision support.

## Direct Entry

The canonical entry is:

```text
PM_COPILOT.md
```

If your agent does not automatically inspect repository instructions, tell it to read `PM_COPILOT.md` before handling the request.

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

## Using Product Documents Instead of a Repository

You can use PM Copilot without a software repository. Put relevant product documents in the workspace or attach them in the agent conversation, then ask for the PRD and prototype.

Good context sources include:

- Historical PRDs, specs, release notes, and roadmap docs
- Screenshots, wireframes, prototype notes, and UX review notes
- Research summaries, customer feedback, support tickets, and meeting notes
- Analytics exports, KPI definitions, and tracking plans
- Business rules, pricing notes, compliance constraints, and rollout plans

The agent should treat those documents as current product context, ask must-answer questions if they do not answer core product-fit questions, and wait before downstream generation when critical context is missing.

## Optional Product Context

For better results, create:

```text
context/product-context.local.yaml
```

You do not need to do this before the first run. If it is missing, the agent should use the example context and mark assumptions.

For long-term use, create memory files from the examples:

```text
context/product-memory.local.yaml
context/user-preferences.local.yaml
context/decision-log.local.yaml
```

These files let PM Copilot remember stable product facts, your writing/prototype preferences, and durable product decisions. They are ignored by Git.

## Expected Flow

```text
User gives request
-> Agent reads PM_COPILOT.md directly or through an adapter
-> Agent loads workflow, guardrails, contracts, and context
-> Agent asks high-impact clarification questions before generation
-> User answers or explicitly says to proceed as a draft with assumption or confirmation risk
-> Agent creates PRD/prototype outputs under one run folder
-> Agent checks delivery consistency
-> Agent returns artifact paths and blockers
```

When `scripts/validate_outputs.py` is available, the final check should include the generated output folder:

```bash
python3 scripts/preflight_tools.py
python3 scripts/run_delivery_checks.py outputs/<run-id> --language zh
```

For explicit self-iteration or benchmark runs where you ask the agent to choose recommended defaults, the agent should still generate the full `prd.md`, prototype, and `run-log.yaml` for each round, record the default choices in the run log, and keep unresolved launch or sensitive approvals visible.

If you ask for unattended development handoff, PM Copilot can generate issue-ready task candidates, but blocked work remains blocked. If you ask for unattended launch decision support, PM Copilot can generate a conservative gate result; it cannot approve launch-sensitive gates from defaults.

## Example

```text
We want to improve coupon usage on checkout. Users say they cannot find where to apply coupons, and support tickets are increasing.
```

Expected generated paths:

```text
outputs/checkout-coupon/prd.md
outputs/checkout-coupon/prototype-h5.html
```

If the same scenario already exists, the agent should create a timestamped run folder such as:

```text
outputs/checkout-coupon-20260518-1430/prd.md
outputs/checkout-coupon-20260518-1430/prototype-h5.html
```

## When to Prepare Extra Context

Extra setup is still useful when:

- You want to prepare a carefully written task brief before running the agent.
- You are building regression evals.
- You want to compare outputs across multiple agent platforms.

In those cases, put the extra source material in the workspace and reference it in the request. The default delivery should still be `prd.md` plus a prototype unless you ask for a specific export.
