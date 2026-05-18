# Quick Start

This guide explains the manual setup path. For the simpler direct-use experience, see `docs/direct-use.md`.

Recommended direct prompt:

```text
<write your product request here>

If important information is missing, ask me first.
If enough information is available, create `prd.md` and the matching clickable prototype.
If must-answer or pre-development confirmation information is missing, stop and wait for my answer before generating downstream artifacts.
Use any product docs I provide as current context; a software repository is optional.
Use my request language for headings, labels, statuses, notes, and prototype annotations.
```

## 1. Choose an Agent Workspace

Use any agent environment that can read files and write artifacts, such as:

- Codex
- Claude Code
- Cursor
- Internal company agent workspace

PM Copilot is a workflow kit, not a runtime. The agent reads the repository instructions and produces files.

## 2. Configure Product Context

Copy:

```text
context/product-context.example.yaml
```

To:

```text
context/product-context.local.yaml
```

Then fill in:

- Product name and category
- Platforms
- Business model
- User segments
- Business goals
- PRD preferences
- Tracking taxonomy
- Known competitors
- Prototype preferences
- Privacy policy

See `docs/configuration.md` for field-by-field guidance.

This step is optional for the first direct run. If `context/product-context.local.yaml` is missing, the agent should use `context/product-context.example.yaml` and mark assumptions.

If you do not have a code repository, collect any available product documents instead: historical PRDs, specs, screenshots, research notes, support tickets, analytics exports, tracking plans, meeting notes, or release notes. PM Copilot should use those documents as product context.

## 3. Prepare Context

You do not need to create task-brief, clarifying-question, or assumption files. Paste the raw request directly into the agent. The original request, answered clarifications, and low-risk assumptions are recorded inside `prd.md` after the clarification gate passes.

## 4. Run the Workflow

Use this prompt:

```text
Follow PM_COPILOT.md.

Read:
- workflow/main-workflow.md
- workflow/context-loading.md
- guardrails/guardrails.md
- guardrails/failover.md
- artifacts/artifact-contracts.md
- context/product-context.local.yaml

Follow the workflow and produce PRD/prototype deliverables under:
outputs/<run-id>/

Ask clarification questions before generation if high-impact information is missing.
If must-answer or pre-development confirmation questions exist, stop and wait for my answer before creating PRD or prototype deliverables. If I explicitly ask you to proceed without answers, mark unresolved must-answer items as draft assumption risk and unresolved pre-development confirmations as draft confirmation risk.
Create `prd.md` and `prototype-<platform>.html` by default. Put requirement input, clarified answers, assumptions, research/reference findings, metrics, tracking table, flow diagrams, risks, acceptance criteria, and validation results inside `prd.md`. Create split files only if needed or requested.
```

## 5. Review the Delivery

Check that the output includes:

- `prd.md`
- Version history, requirement input, confirmed answers, and assumptions inside the PRD
- Research/reference findings inside the PRD
- Requirement list and detailed requirement tables inside the PRD
- Metrics and tracking plan table inside the PRD
- Flow diagrams inside the PRD when useful
- Platform-specific clickable annotated HTML prototype
- PRD/prototype readiness, risks, acceptance criteria, and validation results
- Optional exports such as CSV or Mermaid source when useful

## 6. Validate Repository Structure

Run:

```bash
python3 scripts/validate_repo.py
```

This checks required folders, skill frontmatter, example PRD/prototype structure, CSV parsing, and basic HTML file presence.

## Recommended First Run

Start with:

```text
examples/membership-auto-renewal/task-brief.md
```

Compare the result with:

```text
outputs/membership-auto-renewal/
```
