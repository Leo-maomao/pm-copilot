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

For every screenshot captured, cropped, or retained as-is for a PRD, add an internal `visual_capture_review` record in the run log or tool result. This evidence never appears in the PRD itself:

```yaml
visual_capture_review:
  requirement: "5.1"
  asset: "assets/团队项目区-已选择团队.png"
  functional_target: "团队项目入口及已选择状态"
  locating_context: "项目列表中的个人项目与团队项目分区"
  comparison_context: "个人项目区，仅在说明两类项目边界时保留"
  crop_decision: "cropped" # cropped | retained_full | retained_source
  retained_regions: ["目标控件", "定位上下文", "必要对比区域"]
  removed_regions: ["无关全局导航", "无关空白区域"]
  rationale: "去除无关导航后仍能定位入口并理解个人/团队边界。"
  readability_check: "passed"
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
- Visual validation: UI deliverable file names or preview surfaces, screenshot paths, viewport names, browser channel, nonblank ratios, report path, baseline/diff status. For source-backed previews, include the preview URL/file, host render command, and `source-preview-report.json` path when `validate_ui_preview.py` is used.
- PRD screenshot capture: for every captured or cropped image, record the functional target, locating context, optional comparison context, crop decision, removed regions, rationale, and readability result. A visual decision based only on image dimensions, filename, or a fixed crop percentage is invalid.
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
