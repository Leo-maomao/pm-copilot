# Tool Result Contract

Every non-trivial tool call must leave a compact, inspectable result. The goal is not verbose logging; it is preventing PM Copilot from claiming that a check, source lookup, screenshot, export, or launch gate happened when it did not.

## Canonical Shape

Use this shape in `run-log.yaml`, `tool-results/*.json`, or a PRD validation table when a human-readable summary is needed.

```yaml
tool_id: "" # matches tools/tool-registry.yaml
tool_name: ""
purpose: ""
trigger: "" # why the tool was required or why it was optional
input_summary: ""
command: ""
started_at: ""
finished_at: ""
status: "" # passed | failed | skipped | setup_required | not_applicable
exit_code: null
output_summary: ""
artifacts_created:
  - path: ""
    type: "" # prd | ui_deliverable | prototype | screenshot | visual_report | run_log | dev_tasks | launch_decision | report | other
evidence:
  - kind: "" # file | source | screenshot | command_output | browser_channel | approval | limitation
    value: ""
limitations: []
fallback_used:
  tool_id: ""
  reason: ""
requires_user_action: false
```

## Status Rules

- `passed`: The tool ran and produced inspectable evidence.
- `failed`: The command or tool returned an error, timed out, or produced invalid output.
- `skipped`: The tool was intentionally not run; this requires a concrete reason.
- `setup_required`: The tool cannot run until an install/configuration step succeeds.
- `not_applicable`: The capability does not apply to this run, for example no UI deliverable exists.

Capability preflight uses availability status instead of execution status. Valid preflight values are `available`, `setup_required`, `unavailable`, `skipped`, `external_runtime`, and `not_applicable`. Use `external_runtime` only when the capability is supplied by the active agent environment and cannot be meaningfully probed by a local shell command. Optional checks that were not requested should be `skipped` with evidence, not a custom status such as `not_checked`.

## Required Evidence

- Source-backed research: title, URL, access date, and observed fact.
- File reads: paths inspected and the product fact learned from each path.
- Visual validation: UI deliverable file names or preview surfaces, screenshot paths, viewport names, browser channel, nonblank ratios, report path, baseline/diff status.
- Output validation: command, language mode, status, and any failing marker.
- Development handoff: `dev-tasks.yaml` path, task count, blocked count, and readiness mode.
- Launch decision: `launch-decision.yaml` path, decision mode, gate statuses, blockers, and required approvals.

## Prohibited Claims

- Do not write `passed` when only the command recommendation was written.
- Do not hide a failed setup attempt behind `skipped`.
- Do not claim issue creation, deployment, launch approval, source verification, or browser preview without tool evidence.
- Do not cite model memory or template examples as external research.

## Storage

Generated run folders may contain machine-readable tool reports under:

```text
outputs/<run-id>/tool-results/
```

These files are internal evidence, similar to `run-log.yaml` and `visual-review/`. They should not replace the PRD validation summary; they support it.
