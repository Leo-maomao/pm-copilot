# Trace Contract

Every serious PM Copilot run should produce a trace or run log. A trace explains why the agent made decisions and which assumptions, tools, and skills shaped the output.

## Required Fields

```yaml
run_id:
date:
scenario:
agent_platform:
model:
task_brief:
context_files:
workflow_states:
agents_used:
skills_used:
tools_used:
human_inputs:
assumptions:
open_questions:
artifacts:
guardrail_events:
review_scores:
failures:
final_status:
```

## Rules

- Do not include sensitive raw user data.
- Record tool limitations instead of hiding them.
- Record assumptions separately from confirmed facts.
- Record files created or modified.
- Record review scores when quality review is performed.

## Why This Matters

Without traces, optimization becomes guesswork. Traces make it possible to know whether a failure came from context, workflow, skill quality, tool use, or review quality.
