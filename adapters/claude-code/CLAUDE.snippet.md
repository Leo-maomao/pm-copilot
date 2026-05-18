# PM Copilot Adapter for Claude Code

Add this snippet to the host repository's `CLAUDE.md` when PM Copilot is nested inside another project.

```markdown
## PM Copilot

When the user asks for product-manager work such as PRD, requirements, user stories, acceptance criteria, metrics, tracking plans, analytics events, user flows, prototypes, competitor research, review checklists, or equivalent Chinese-language PM tasks, read `pm-copilot/PM_COPILOT.md` and follow that workflow.

Do not require the user to say "Use PM Copilot". Natural product-manager requests should trigger it.

Before generating PM artifacts, inspect relevant host project context and ask must-answer questions if current product fit, scope, platform, metrics, or risk is unclear. Do not generate the full package until those questions are answered or the user explicitly accepts assumptions.

Write generated PM Copilot artifacts under `pm-copilot/outputs/<run-id>/` unless the user asks for another location.
```

## Usage

1. Put the PM Copilot folder under the host project:

```text
<host-repo>/pm-copilot/
```

2. Append the snippet above to:

```text
<host-repo>/CLAUDE.md
```

3. Then users can say:

```text
Help me write the PRD, tracking plan, and prototype for team permission management.
```
