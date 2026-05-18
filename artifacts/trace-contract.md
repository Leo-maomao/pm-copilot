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
context_source_mode:
product_documents:
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
- Record whether the run was repo-backed, document-backed, or brief-only.
- In repo-backed mode, record relevant host project files and current-state facts used for product-fit decisions.
- In document-backed mode, record relevant PRDs, specs, notes, screenshots, analytics files, or other documents used for product-fit decisions.
- Record the artifact language chosen from the user's request.
- Record files created or modified.
- Record review scores when quality review is performed.

## Why This Matters

Without traces, optimization becomes guesswork. Traces make it possible to know whether a failure came from context, workflow, skill quality, tool use, or review quality.
