# Prompt Recipes

Use these prompts as copy-paste starting points. Replace `<run-id>` and file paths as needed.

## Run a New PM Copilot Task

Use this simple version first:

```text
<write your product request here>

If important information is missing, ask me first.
If enough information is available, create `outputs/<run-id>/prd.md` and the matching `outputs/<run-id>/prototype-<platform>.html`.
Use my local product context if it exists; otherwise use the example context and mark assumptions.
Inspect the relevant current product context before drafting.
If there is no code repository, use any PRDs, product docs, screenshots, analytics exports, or other documents I provide as current product context.
Use my request language for headings, table labels, statuses, notes, and prototype annotations.
```

Use this explicit version when the agent does not automatically follow `PM_COPILOT.md`:

```text
Use PM Copilot.

Read:
- README.md
- workflow/main-workflow.md
- workflow/context-loading.md
- guardrails/guardrails.md
- guardrails/failover.md
- artifacts/artifact-contracts.md
- context/product-context.local.yaml

Follow the default workflow:
intake -> clarification -> PRD -> prototype -> delivery check -> validation.

Write all outputs under:
outputs/<run-id>/

Use a unique run id. If the scenario folder already exists, append a local timestamp.

Ask clarification questions before generation if missing information materially changes current product fit, scope, metrics, privacy, payment, legal, or prototype direction.
If must-answer questions or pre-development confirmation questions exist, stop and wait for my answer before creating PRD or prototype deliverables. If I explicitly ask you to proceed without answers, mark unresolved must-answer items as draft assumption risk and unresolved pre-development confirmations as draft confirmation risk.
Do not require a software repository if product documents provide enough context.
Do not create `task-brief.md`, `clarifying-questions.md`, `assumptions.md`, `pm-package.md`, or split Markdown files unless I ask for them or they are needed as exports. Put requirement input, clarified answers, assumptions, research/reference findings, metrics, tracking table, flow diagrams, risks, acceptance criteria, and validation results inside `prd.md`.
```

## Create Only Clarifying Questions

```text
Use PM Copilot's Discovery Agent and requirement-intake skill.

Read:
- workflow/context-loading.md
- guardrails/guardrails.md
- context/product-context.local.yaml

Output:
- must-answer questions
- assumptions that can be used only in a draft
- items that must be confirmed before development or launch
- current-state fit summary, if repository or document context is available
- recommended next agent

Do not generate the PRD yet.
```

## Generate The PRD

```text
Use PM Copilot's Requirements Agent and PRD-related skills.

Read:
- artifacts/prd-contract.md
- templates/prd-template.md
- context/product-context.local.yaml

Generate:
- outputs/<run-id>/prd.md

Make `prd.md` the primary product-manager handoff artifact. Include version history, requirement input and confirmation record, background, research/reference findings, goals/metrics, scope, requirement list, requirement details, flow diagrams when useful, tracking plan, prototype reference, risks/open confirmations, acceptance criteria, and validation results.
Use tables and stable requirement IDs instead of long unordered lists.
```

## Generate Optional Analytics Export

```text
Use PM Copilot's Analytics Agent, metrics-tree skill, and tracking-plan skill.

Read:
- artifacts/tracking-plan-contract.md
- context/product-context.local.yaml
- outputs/<run-id>/prd.md

Generate:
- outputs/<run-id>/tracking-plan.csv

Use split files only when analytics or engineering needs separate exports. Otherwise place metrics and tracking tables in `prd.md`.
Do not create `metrics-tree.md` or `tracking-plan.md` unless I explicitly ask for legacy split Markdown files.
Do not include forbidden sensitive properties.
Use a Markdown event table and property dictionary as the primary review artifact.
Add privacy notes and validation notes for each event.
```

## Generate User Flow Export And Prototype

```text
Use PM Copilot's Prototype Agent, user-flow skill, and multi-platform-prototype skill.

Read:
- artifacts/prototype-contract.md
- tools/prototype-tooling.md
- context/product-context.local.yaml
- outputs/<run-id>/prd.md

Choose the correct platform: Web, H5, App, Mini Program, or multiple if the scenario requires cross-platform output.

Generate:
- outputs/<run-id>/prototype-<platform>.html
- optional outputs/<run-id>/user-flow.mmd only when an export is useful

The user flow should normally be a renderable Mermaid diagram inside `prd.md`, not a prose list.
The prototype must be local, self-contained, clickable, annotated, and fidelity-appropriate for UI and engineering reference.
If existing UI or demo context is available, adapt that surface and show the new requirement delta instead of creating a new product.
```

## Review Existing PRD And Prototype

```text
Use PM Copilot's Review Agent and review-checklist skill.

Read:
- artifacts/artifact-contracts.md
- guardrails/guardrails.md
- outputs/<run-id>/

Lead with findings by severity.
Check PRD, metrics, tracking, flow, prototype, assumptions, privacy, validation results, and human confirmation points. Write findings into the PRD unless a separate review file is requested.
```

## Check Final Delivery

```text
Use PM Copilot's PM Orchestrator Agent and artifact-packaging skill.

Read:
- workflow/package-workflow.md
- artifacts/artifact-contracts.md
- outputs/<run-id>/

Verify:
- outputs/<run-id>/prd.md
- outputs/<run-id>/prototype-<platform>.html

Do not create `pm-package.md` or `final-package-summary.md` unless I ask for a legacy summary.
```

## Improve an Existing Skill

```text
Improve the PM Copilot skill at:
skills/<skill-name>/SKILL.md

Keep the skill concise.
Preserve YAML frontmatter with name and description.
Keep the body focused on goal, workflow, output, and quality bar.
Move long examples or detailed references outside the skill body.
Run python3 scripts/validate_repo.py after editing.
```

## Add a New Scenario

```text
Add a PM Copilot scenario named <scenario>.

Create:
- examples/<scenario>/task-brief.md
- outputs/<scenario>/prd.md
- outputs/<scenario>/prototype-<platform>.html

Create optional split source or export files such as `tracking-plan.csv` or `user-flow.mmd` only when the scenario needs them.
Use synthetic data only.
Run python3 scripts/validate_repo.py after adding the scenario.
```
