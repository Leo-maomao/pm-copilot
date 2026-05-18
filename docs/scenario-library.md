# Scenario Library

PM Copilot includes example scenarios across common product surfaces.

Scenario library folders are stable examples for regression and documentation. Real user runs should keep generated artifacts in `outputs/<run-id>/` only, with a timestamp appended when a similar run already exists. Do not create `examples/<run-id>/` for ordinary user runs.

## Included Scenarios

| Scenario | Platform | Purpose |
|---|---|---|
| `membership-auto-renewal` | H5 | Subscription renewal and payment recovery |
| `team-permissions` | Web | Admin/SaaS permission management |
| `content-save-app` | App | Native mobile content save and offline access |
| `mini-program-booking` | Mini Program | Appointment booking with authorization and form flow |

## How to Use a Scenario

1. Read `examples/<scenario>/task-brief.md`.
2. Ask your agent to run the main workflow.
3. Compare generated results with `outputs/<scenario>/`.
4. Copy the scenario and replace the brief with your own product request.

## How to Add a Scenario

Create:

```text
examples/<scenario>/task-brief.md
outputs/<scenario>/prd.md
outputs/<scenario>/prototype-<platform>.html
```

Put confirmations, assumptions, metrics, tracking, flows, review status, and validation results inside `prd.md`. Optional export files can be added only when they are useful for external tools, such as `tracking-plan.csv` or `user-flow.mmd`.

## Scenario Quality Bar

- The raw request should be realistic and slightly ambiguous.
- The output should include assumptions, not pretend all information is known.
- `prd.md` should let reviewers understand the requirement without opening every source file.
- The prototype should match the selected platform, be clickable, and include annotations or implementation notes.
- Tracking should use event and property tables with privacy notes inside `prd.md` or a linked export.
- User flow should be a renderable Mermaid diagram inside `prd.md` or a linked export.
- Risks and open confirmations should identify at least one realistic open decision inside `prd.md`.
