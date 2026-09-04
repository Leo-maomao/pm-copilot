# PM Copilot Adapter for Codex

Add this snippet to the host repository's root `AGENTS.md` when PM Copilot is nested inside another project.

```markdown
## PM Copilot

When the user asks to create a new PRD, restore a PRD from implemented
behavior, revise selected requirement IDs in an existing PRD, or compose a new
PRD from selected requirement IDs across PRDs, read
`pm-copilot/PM_COPILOT.md` and follow that workflow.

When the user writes `@pm-copilot`, "按 pm-copilot 规范", "按仓库内 pm-copilot/PM_COPILOT.md 工作流产出 PRD", or equivalent local-project wording, treat it as a reference to the local `pm-copilot/PM_COPILOT.md` file. Do not search for or invoke an external agent, MCP server, plugin, hosted Copilot product, or tool-discovery target because of `@pm-copilot`.

Do not require the user to say "Use PM Copilot" when the request clearly maps
to one of the four PRD workflows.

For every PRD request, invoke the PM Copilot production controller before
writing any PRD artifact:

```bash
python3 pm-copilot/scripts/prd_request_controller.py --request "<user request>"
```

When the user names an existing PRD directory and asks to modify it, pass the
canonical folder explicitly and use in-place revision mode:

```bash
python3 pm-copilot/scripts/prd_request_controller.py --run-folder "<canonical folder>" --revise --request "<revision>"
```

Do not draft a PRD directly in the chat. A PRD may be delivered only when the
controller state records clarification, explicit confirmation, required agent
evidence and review, and final validation in one canonical run folder.

Before generating a PRD, inspect current product context. Read host project
files as evidence only; use PRDs, specs, docs, screenshots, support material,
or meeting notes when code context is absent. Ask only questions that change
scope or behavior. The controller creates the PRD and its frontend figures;
never modify host source, deploy software, or deliver a standalone prototype.

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
Create a PRD for checkout coupon optimization. Clarify the scope first, then
generate it after confirmation.
```

Codex should load the host `AGENTS.md`, detect the PM task, then read `pm-copilot/PM_COPILOT.md`.
