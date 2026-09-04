---
name: pm-copilot
description: Use a checked-out PM Copilot repository for PRD generation in the current project.
---

# PM Copilot Plugin Adapter

Use the repository selected by `PM_COPILOT_REPOSITORY`. It must point to a
source checkout containing `PM_COPILOT.md`; the plugin does not install, copy,
or synchronize a second runtime directory. If it is absent or invalid, pause
and ask the user to select a checkout. Do not substitute the plugin cache or
the current working directory.

Then read the runtime's `PM_COPILOT.md` and resolve the project workspace:

```bash
python3 "$PM_COPILOT_REPOSITORY/scripts/project_workspace.py" --cwd "$PWD" --ensure
```

Never place product outputs in the plugin or repository checkout directory. Use
`pm-copilot/outputs/<run-id>/` for embedded projects and
`pm-copilot-outputs/<run-id>/` for projects without an embedded PM Copilot
directory.

For every PRD request, route through the production controller before writing
any artifact:

```bash
python3 "$PM_COPILOT_REPOSITORY/scripts/prd_request_controller.py" --request "<request>"
```

For an implemented feature in the current host repository, include that it is
already implemented in the request. The controller automatically freezes the
branch, diff, relevant code, frontend inventory, and real-screenshot attempt
before it asks for scope confirmation; do not require the user to prepare an
implementation-evidence JSON file. To add the next implemented feature to a
completed PRD in the same delivery period, use the explicit target folder:

```bash
python3 "$PM_COPILOT_REPOSITORY/scripts/prd_request_controller.py" \
  --run-folder "<current-prd-folder>" \
  --append-implemented-feature \
  --request "为已实现的 <feature> 追加 PRD"
```

Do not infer an active/current PRD or delivery period. The caller selects the
target folder for an append; omitting it creates a new PRD. The PRD Manager is
read-only aggregation and browsing, never PRD creation or schedule ownership.

For an active interactive PRD run, use the `prd_run_status` MCP tool before
every progress or failure reply. The tool result is the only source of truth;
never infer a stage from chat text, a planned command, or an Agent narrative.

- For `needs_input`, use `prd_submit_answer` with the user's answer, then report
  the returned state.
- For `awaiting_confirmation`, show the clarified scope. After an unambiguous
  user reply such as "确认执行" or "确认生成 PRD", use
  `prd_confirm_delivery`, then report its returned state.
- For `recovery_required`, report the recorded interruption and promoted
  artifacts. After explicit user confirmation, use `prd_confirm_delivery` to
  resume from the first stage without a persisted accepted review.
- For a failed run whose user-confirmation record remains true, explain the
  recorded failure. After an explicit user request to retry, use
  `prd_confirm_delivery` to resume the first unaccepted stage; do not ask the
  user to restate already confirmed scope.
- Say an artifact is generating only when `delivery_calls` contains a recorded
  delivery call for that artifact. Say it was created only when it appears in
  `artifacts`.
- On failure, report `status`, `last_error`, and the returned controller exit
  result. Never relabel an unconfirmed run or a sandbox-path error as a write
  syntax failure or a process hang.

Do not return a direct model-written PRD. The controller must provide one
canonical run folder, reviewed PRD artifacts, and final validation evidence.
