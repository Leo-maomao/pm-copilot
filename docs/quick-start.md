# Quick Start

This guide explains the manual setup path. For the simpler direct-use experience, see `docs/direct-use.md`.

Recommended direct prompt:

```text
<write your product request here>

If important information is missing, ask me first.
If enough information is available, create the full review-ready package.
If must-answer information is missing, stop and wait for my answer before generating downstream artifacts.
Use any product docs I provide as current context; a software repository is optional.
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

## 3. Create a Task Brief

Copy:

```text
templates/task-brief-template.md
```

To:

```text
outputs/<run-id>/task-brief.md
```

Write the raw request exactly as you received it. Do not over-polish the request. The Discovery Agent is expected to clarify it.

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
- outputs/<run-id>/task-brief.md

Follow the workflow and produce a review-ready package under:
outputs/<run-id>/

Ask clarification questions before generation if high-impact information is missing.
If must-answer questions exist, stop after writing the task brief, clarifying questions, assumptions, and run log. Continue only after I answer or explicitly tell you to proceed with assumptions.
```

## 5. Review the Package

Check that the output includes:

- Clarifying questions
- Assumptions
- Consolidated PM package
- PRD
- Metrics tree
- Tracking plan Markdown table and CSV export
- Renderable user flow diagram and Mermaid source
- Platform-specific clickable annotated HTML prototype
- Review checklist
- Final package summary

## 6. Validate Repository Structure

Run:

```bash
python3 scripts/validate_repo.py
```

This checks required folders, skill frontmatter, example package structure, CSV parsing, and basic HTML file presence.

## Recommended First Run

Start with:

```text
examples/membership-auto-renewal/task-brief.md
```

Compare the result with:

```text
outputs/membership-auto-renewal/
```
