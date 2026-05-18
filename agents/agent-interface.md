# Agent Interface Contract

Every agent definition in this repository follows the same interface.

## Required Sections

- Purpose
- Responsibilities
- Inputs
- Outputs
- Completion Criteria
- Handoffs
- Failover, when applicable

## Output Rules

- Always distinguish facts, assumptions, and open questions.
- Never hide uncertainty.
- When an agent cannot complete a task, return the closest lower-fidelity artifact plus a limitation note.
- Preserve upstream decisions unless there is a clear contradiction.

## Handoff Payload

```yaml
from_agent:
to_agent:
workflow_state:
task_goal:
inputs:
artifacts_available:
assumptions:
open_questions:
human_confirmation_required:
risks:
next_expected_output:
```
