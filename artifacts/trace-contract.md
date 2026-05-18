# Trace Contract

Every serious PM Copilot run should produce a trace or run log. A trace explains why the agent made decisions and which assumptions, tools, and skills shaped the output.

## Required Fields

```yaml
run_id:
date:
scenario:
language:
agent_platform:
model:
task_brief:
context_files:
host_project_context:
current_state_summary:
workflow_states:
clarification_gate:
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
- Record whether must-answer questions blocked generation or were explicitly accepted as assumption risk.
- In embedded mode, record relevant host project files and current-state facts used for project-fit decisions.
- Record the artifact language chosen from the user's request.
- Record files created or modified.
- Record review scores when quality review is performed.

## Why This Matters

Without traces, optimization becomes guesswork. Traces make it possible to know whether a failure came from context, workflow, skill quality, tool use, or review quality.
