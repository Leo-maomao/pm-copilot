---
name: pm-copilot
description: Use PM Copilot to generate PRDs in the current project.
---

# PM Copilot Plugin Adapter

Use `prd_start_request` for every PRD request. The installed plugin resolves
its sole source checkout automatically; never ask for a runtime path. Never invoke a PM Copilot controller from the shell. The host repository is read-only product
evidence and receives PRD outputs, never PM Copilot runtime changes.

The v2 protocol has one delivery path and one state file, `delivery-run.json`.
It creates `prd.md`, `prd.html`, `assets/`, and `run-log.yaml` atomically.
Historical unfinished runs are unsupported and must be restarted as v2 runs.

Call `prd_run_status` before reporting progress or failure. A sufficient
request delivers immediately. For `needs_input`, call `prd_submit_answer`; the
controller automatically continues through canonical artifact delivery.

For an in-place revision pass `run_folder`, `revise: true`, and the selected
requirement IDs. For an implemented-feature append pass the selected
`run_folder` and `append_implemented_feature: true`. Never route multiple
target PRDs through a revision.

Before reporting a failure, call the applicable MCP tool and report only its
returned `controller_exit_code`, `controller_stderr`, `status`, and
`last_error`; a historical run log is not evidence of a current failure.
