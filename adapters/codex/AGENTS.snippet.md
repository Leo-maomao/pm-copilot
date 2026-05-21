# PM Copilot Adapter for Codex

Add this snippet to the host repository's root `AGENTS.md` when PM Copilot is nested inside another project.

```markdown
## PM Copilot

When the user asks for product-manager work such as PRD, requirements, user stories, acceptance criteria, metrics, tracking plans, analytics events, user flows, UI deliverables, prototypes, competitor research, review checklists, or equivalent Chinese-language PM tasks, read `pm-copilot/PM_COPILOT.md` and follow that workflow.

Do not require the user to say "Use PM Copilot". Natural product-manager requests should trigger it.

Before generating PM artifacts, inspect relevant current product context. Use host project files when available, and use PRDs, specs, docs, screenshots, analytics exports, support tickets, or meeting notes when no code context exists. Ask must-answer questions and identify development or launch confirmation blockers if current product fit, scope, platform, metrics, or risk is unclear. Do not generate PRD/UI deliverables until those questions are answered, unless the user explicitly asks for a draft with risk. For repo-backed UI work, user wording like "prototype" or "only generate a prototype" means review scope only; use source-backed preview/delta files when frontend source exists, and use standalone HTML only for explicit portable HTML, explicit redesign/greenfield, no-source, or concretely blocked source rendering.

Write generated PM Copilot artifacts under `pm-copilot/outputs/<run-id>/` unless the user asks for another location.

Keep normal software-engineering tasks governed by this host repository's regular instructions.
```

## Usage

1. Put the PM Copilot folder under the host project:

```text
<host-repo>/pm-copilot/
```

2. Append the snippet above to:

```text
<host-repo>/AGENTS.md
```

3. Then users can say:

```text
I need a PRD and tracking plan for checkout coupon optimization.
```

Codex should load the host `AGENTS.md`, detect the PM task, then read `pm-copilot/PM_COPILOT.md`.
