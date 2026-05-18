# Prompt Recipes

Use these prompts as copy-paste starting points. Replace `<run-id>` and file paths as needed.

## Run a New PM Copilot Task

Use this simple version first:

```text
<write your product request here>

If important information is missing, ask me first.
If enough information is available, create the full review-ready package in `outputs/<run-id>/pm-package.md`.
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
- outputs/<run-id>/task-brief.md

Follow the default workflow:
intake -> clarification -> consolidated PM package -> prototype -> validation.

Write all outputs under:
outputs/<run-id>/

Use a unique run id. If the scenario folder already exists, append a local timestamp.

Ask clarification questions before generation if missing information materially changes current product fit, scope, metrics, privacy, payment, legal, or prototype direction.
If must-answer questions or pre-development confirmation questions exist, stop after writing the task brief, clarifying questions, assumptions, and run log. Continue only after I answer. If I explicitly ask you to proceed without answers, mark unresolved must-answer items as draft assumption risk and unresolved pre-development confirmations as draft confirmation risk.
Do not require a software repository if product documents provide enough context.
Do not create split Markdown files unless I ask for them or they are needed as exports. Put PRD, metrics, tracking table, user flow, review checklist, assumptions, and next actions inside `pm-package.md`.
```

## Create Only Clarifying Questions

```text
Use PM Copilot's Discovery Agent and requirement-intake skill.

Read:
- workflow/context-loading.md
- guardrails/guardrails.md
- context/product-context.local.yaml
- outputs/<run-id>/task-brief.md

Output:
- must-answer questions
- assumptions that can be used only in a draft
- items that must be confirmed before development or launch
- current-state fit summary, if repository or document context is available
- recommended next agent

Do not generate the PRD yet.
```

## Generate A Split PRD File

```text
Use PM Copilot's Requirements Agent and PRD-related skills.

Read:
- artifacts/prd-contract.md
- templates/prd-template.md
- context/product-context.local.yaml
- outputs/<run-id>/task-brief.md
- outputs/<run-id>/clarifying-questions.md
- outputs/<run-id>/assumptions.md

Generate:
- outputs/<run-id>/prd.md

Use this only when a separate PRD file is needed. Otherwise place the PRD section in `pm-package.md`.
Keep goals measurable, scope explicit, non-goals visible, and acceptance criteria testable.
Use tables and stable requirement IDs instead of long unordered lists.
```

## Generate Split Metrics And Tracking Files

```text
Use PM Copilot's Analytics Agent, metrics-tree skill, and tracking-plan skill.

Read:
- artifacts/tracking-plan-contract.md
- context/product-context.local.yaml
- outputs/<run-id>/prd.md

Generate:
- outputs/<run-id>/metrics-tree.md
- outputs/<run-id>/tracking-plan.md
- outputs/<run-id>/tracking-plan.csv

Use split files only when analytics or engineering needs separate exports. Otherwise place the metrics tree and tracking tables in `pm-package.md`.
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
- outputs/<run-id>/user-flow.md
- outputs/<run-id>/user-flow.mmd
- outputs/<run-id>/prototype-<platform>.html

The user flow must be a renderable Mermaid diagram in Markdown, not a prose list.
The prototype must be local, self-contained, clickable, annotated, and fidelity-appropriate for UI and engineering reference.
If existing UI or demo context is available, adapt that surface and show the new requirement delta instead of creating a new product.
```

## Review an Existing Package

```text
Use PM Copilot's Review Agent and review-checklist skill.

Read:
- artifacts/artifact-contracts.md
- guardrails/guardrails.md
- outputs/<run-id>/

Generate or update only when a separate review file is needed:
- outputs/<run-id>/review-checklist.md

Lead with findings by severity.
Check PRD, metrics, tracking, flow, prototype, assumptions, privacy, and human confirmation points.
```

## Package Final Outputs

```text
Use PM Copilot's PM Orchestrator Agent and artifact-packaging skill.

Read:
- workflow/package-workflow.md
- artifacts/final-package-contract.md
- outputs/<run-id>/

Generate:
- outputs/<run-id>/pm-package.md

Make `pm-package.md` the primary review artifact. Include PRD, metrics, tracking table, user flow diagram, prototype notes, artifact index, key decisions, assumptions, open questions, risks, review status, and recommended review agenda.
Do not create `final-package-summary.md` unless I ask for a legacy summary.
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
- outputs/<scenario>/clarifying-questions.md
- outputs/<scenario>/assumptions.md
- outputs/<scenario>/pm-package.md
- outputs/<scenario>/prototype-<platform>.html

Create optional split source or export files such as `tracking-plan.csv`, `user-flow.mmd`, or `prd.md` only when the scenario needs them.
Use synthetic data only.
Run python3 scripts/validate_repo.py after adding the scenario.
```
