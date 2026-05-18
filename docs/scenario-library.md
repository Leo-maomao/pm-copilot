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
outputs/<scenario>/clarifying-questions.md
outputs/<scenario>/assumptions.md
outputs/<scenario>/pm-package.md
outputs/<scenario>/prd.md
outputs/<scenario>/metrics-tree.md
outputs/<scenario>/tracking-plan.md
outputs/<scenario>/tracking-plan.csv
outputs/<scenario>/user-flow.md
outputs/<scenario>/user-flow.mmd
outputs/<scenario>/prototype-<platform>.html
outputs/<scenario>/review-checklist.md
outputs/<scenario>/final-package-summary.md
```

## Scenario Quality Bar

- The raw request should be realistic and slightly ambiguous.
- The output should include assumptions, not pretend all information is known.
- `pm-package.md` should let reviewers understand the requirement without opening every source file.
- The prototype should match the selected platform, be clickable, and include annotations or implementation notes.
- Tracking should use Markdown event and property tables with privacy notes.
- User flow should be a renderable Mermaid diagram in Markdown.
- Review checklist should identify at least one realistic open decision.
