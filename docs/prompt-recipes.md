# Prompt Recipes

Use these prompts as copy-paste starting points. Replace `<scenario>` and file paths as needed.

## Run a New PM Copilot Task

Use this simple version first:

```text
<write your product request here>

If important information is missing, ask me first.
If enough information is available, create the full review-ready package.
Use my local product context if it exists; otherwise use the example context and mark assumptions.
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
- examples/<scenario>/task-brief.md

Follow the default workflow:
intake -> clarification -> PRD -> metrics -> tracking -> user flow -> prototype -> review -> final package.

Write all outputs under:
outputs/<scenario>/

Ask clarification questions before generation if missing information materially changes scope, metrics, privacy, payment, legal, or prototype direction.
If I do not answer, continue only with explicit assumptions and mark open questions.
```

## Create Only Clarifying Questions

```text
Use PM Copilot's Discovery Agent and requirement-intake skill.

Read:
- workflow/context-loading.md
- guardrails/guardrails.md
- context/product-context.local.yaml
- examples/<scenario>/task-brief.md

Output:
- must-answer questions
- assumptions that can be used for a draft
- questions that can be decided later
- recommended next agent

Do not generate the PRD yet.
```

## Generate a PRD From an Existing Brief

```text
Use PM Copilot's Requirements Agent and PRD-related skills.

Read:
- artifacts/prd-contract.md
- templates/prd-template.md
- context/product-context.local.yaml
- examples/<scenario>/task-brief.md
- outputs/<scenario>/clarifying-questions.md
- outputs/<scenario>/assumptions.md

Generate:
- outputs/<scenario>/prd.md

Keep goals measurable, scope explicit, non-goals visible, and acceptance criteria testable.
```

## Generate Metrics and Tracking Plan

```text
Use PM Copilot's Analytics Agent, metrics-tree skill, and tracking-plan skill.

Read:
- artifacts/tracking-plan-contract.md
- context/product-context.local.yaml
- outputs/<scenario>/prd.md

Generate:
- outputs/<scenario>/metrics-tree.md
- outputs/<scenario>/tracking-plan.csv

Do not include forbidden sensitive properties.
Add privacy notes for each event.
```

## Generate User Flow and Prototype

```text
Use PM Copilot's Prototype Agent, user-flow skill, and multi-platform-prototype skill.

Read:
- artifacts/prototype-contract.md
- tools/prototype-tooling.md
- context/product-context.local.yaml
- outputs/<scenario>/prd.md

Choose the correct platform: Web, H5, App, Mini Program, or multiple if the scenario requires cross-platform output.

Generate:
- outputs/<scenario>/user-flow.mmd
- outputs/<scenario>/prototype-<platform>.html

The prototype must be local, low-fidelity, self-contained, and interactive for the main path.
```

## Review an Existing Package

```text
Use PM Copilot's Review Agent and review-checklist skill.

Read:
- artifacts/artifact-contracts.md
- guardrails/guardrails.md
- outputs/<scenario>/

Generate or update:
- outputs/<scenario>/review-checklist.md

Lead with findings by severity.
Check PRD, metrics, tracking, flow, prototype, assumptions, privacy, and human confirmation points.
```

## Package Final Outputs

```text
Use PM Copilot's PM Orchestrator Agent and artifact-packaging skill.

Read:
- workflow/package-workflow.md
- artifacts/final-package-contract.md
- outputs/<scenario>/

Generate:
- outputs/<scenario>/final-package-summary.md

Include artifact index, key decisions, assumptions, open questions, risks, review status, and recommended review agenda.
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
- outputs/<scenario>/prd.md
- outputs/<scenario>/metrics-tree.md
- outputs/<scenario>/tracking-plan.csv
- outputs/<scenario>/user-flow.mmd
- outputs/<scenario>/prototype-<platform>.html
- outputs/<scenario>/review-checklist.md
- outputs/<scenario>/final-package-summary.md

Use synthetic data only.
Run python3 scripts/validate_repo.py after adding the scenario.
```
