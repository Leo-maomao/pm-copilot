# Agent Optimization Playbook

This playbook explains how to improve PM Copilot from a good workflow kit into a reliable agent workflow for real product work.

The core idea: do not tune by feeling. Tune from traces, failures, and regression cases.

## What Is Hard After the Skeleton

The repository skeleton defines the intended behavior. Real usefulness depends on:

- Runtime execution quality
- Context selection
- Tool reliability
- Clarification behavior
- Artifact consistency
- Failure recovery
- Evaluation quality
- Regression prevention

Most agent work fails because teams keep rewriting prompts without knowing which failure mode they are fixing.

## Optimization Loop

Use this loop for every improvement cycle.

```text
1. Pick real tasks
2. Run the workflow without manual rescue
3. Save the trace and outputs
4. Score outputs with the quality rubric
5. Classify failures
6. Choose the smallest fix
7. Re-run the same cases
8. Add the case to regression tests
```

## Step 1: Pick Real Tasks

Start with 5 to 10 realistic PM tasks from your own work.

Use a mix:

- Clear request
- Ambiguous request
- Data-heavy request
- Cross-platform request
- Legal, privacy, or payment-sensitive request
- Backend or admin workflow
- Growth or experiment workflow

Do not only test clean demo prompts. Real tasks should contain missing information, unclear goals, and stakeholder shorthand.

## Step 2: Run Without Manual Rescue

During evaluation, avoid helping the agent mid-run unless the workflow explicitly asks for human input.

Record:

- Original request
- Product context loaded
- Clarifying questions asked
- User answers or assumptions
- Agents and skills used
- Tools used
- Generated artifacts
- Review findings
- Human intervention points

Use `templates/agent-run-log-template.yaml`.

## Step 3: Score Output Quality

Use `docs/quality-rubric.md`.

Minimum useful alpha thresholds:

| Area | Minimum |
|---|---|
| Package | 14 / 20 |
| PRD | 18 / 24 |
| Metrics and tracking | 15 / 20 |
| Prototype | 14 / 20 |
| Review checklist | 12 / 16 |

If a package misses a threshold, classify why before editing anything.

## Step 4: Classify Failures

Use `docs/failure-taxonomy.md`.

Common categories:

- Intent failure: misunderstood the product goal.
- Context failure: loaded wrong or insufficient context.
- Workflow failure: skipped a required step.
- Skill failure: method or template is weak.
- Tool failure: search, file, preview, or parser failed.
- Memory failure: reused stale or irrelevant facts.
- Guardrail failure: fabricated, over-assumed, or ignored sensitive risk.
- Artifact failure: output shape is incomplete or inconsistent.
- Review failure: failed to catch the package's own weakness.

## Step 5: Choose the Smallest Fix

Fix in this order:

1. Task brief clarity, if the input is unrealistic or missing expected baseline facts.
2. Context structure, if the agent had the right task but wrong background.
3. Artifact contract, if output shape is inconsistent.
4. Skill instruction, if method quality is weak.
5. Workflow state or handoff, if a step is skipped or ordered wrong.
6. Guardrail, if the agent hides uncertainty or unsafe behavior.
7. Tool protocol, if tool use is unreliable or unverifiable.
8. Agent role definition, if ownership is unclear.

Avoid broad prompt rewrites when a local contract or skill fix would solve the issue.

## Step 6: Re-Run and Compare

After a fix, re-run:

- The failed task
- At least two previously passing tasks

This prevents local improvements from breaking other scenarios.

Track:

- Score before
- Score after
- Failure category fixed
- New failures introduced
- Files changed

## Step 7: Build a Regression Set

Every serious failure should become an eval case under `evals/`.

Each eval case should include:

- Original task
- Expected artifacts
- Known risks
- Rubric thresholds
- Failure history
- Pass/fail notes

Use `templates/evaluation-case-template.md`.

## When to Tune What

| Symptom | Likely Fix |
|---|---|
| Agent asks too many low-value questions | Improve requirement-intake skill and clarification policy |
| Agent generates without asking critical questions | Strengthen workflow human checkpoints |
| PRD is verbose but not testable | Improve PRD contract and acceptance-criteria skill |
| Tracking plan has vague triggers | Improve tracking-plan skill and artifact contract |
| Prototype platform is wrong | Improve prototype contract and platform selection rules |
| Outputs contradict each other | Improve PM Orchestrator handoff and final review rules |
| Agent invents competitor facts | Strengthen research-agent and guardrails |
| Good case regresses after a change | Add regression eval and avoid global prompt rewrites |

## Maturity Levels

| Level | Description | Exit Criteria |
|---|---|---|
| L0 Skeleton | Agents, skills, contracts, examples exist | Repository validator passes |
| L1 Demo reliable | Curated examples work | All included examples pass rubric thresholds |
| L2 Real-task useful | Real PM tasks produce reviewable drafts | 70% of real tasks reach "Ready with risks" without major rescue |
| L3 Team usable | Multiple PMs can use with local context | Docs, config, and regression cases support repeated use |
| L4 Production workflow | Integrated with tools and human approvals | Runtime traces, tool reliability, evals, and monitoring are in place |

PM Copilot is currently designed for L0 to L1. The next serious work is moving toward L2 through real-task evaluation.

## Weekly Optimization Cadence

Recommended cadence:

- Monday: collect 2 to 3 real tasks.
- Tuesday: run PM Copilot without rescue.
- Wednesday: score outputs and classify failures.
- Thursday: make the smallest fixes.
- Friday: rerun failed and regression cases.

Keep a written optimization log. Do not rely on memory.
