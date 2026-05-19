# Trace Contract

Every serious PM Copilot run should produce a trace or run log. A trace explains why the agent made decisions and which assumptions, tools, and skills shaped the output.

## Required Fields

```yaml
run_id:
date:
scenario:
language:
agent_platform:
model:
pm_copilot_version:
pm_copilot_revision:
task:
  request_source:
  brief_path:
  raw_request:
  requested_artifacts:
context:
  source_mode:
  files_loaded:
  host_project_root:
  host_project_files_loaded:
  product_documents_loaded:
  current_state_summary:
  current_state_facts:
  analytics_taxonomy_source:
  context_excluded:
  conflicts_found:
  conflict_resolution:
readiness:
  prd_status:
  engineering_handoff_status:
  launch_status:
  status_rationale:
  engineering_blockers:
  launch_blockers:
workflow:
  states_completed:
  states_skipped:
  skip_reasons:
  last_reliable_state:
  resume_source:
  clarification_gate:
    required:
    status:
    stopped_before_generation:
    assumption_risk_accepted:
    confirmation_risk_accepted:
    evidence:
  revision_loops:
agent_transitions:
agents_used:
skills_used:
tools_used:
tool_preflight:
human_inputs:
  clarification_questions:
  answers_received:
  default_options_selected:
  unanswered_questions:
  confirmations_required:
assumptions:
scope_decisions:
surface_decisions:
style_evidence:
existing_ui_visual_baseline:
design_calibration:
content_sources:
open_questions:
artifacts:
visual_validation:
handoff_artifacts:
guardrail_events:
security_and_audit:
review_findings:
review_scores:
quality_thresholds:
quality_decision:
validation_results:
failures:
final_status:
next_actions:
```

## Rules

- Do not include sensitive raw user data.
- Record tool limitations instead of hiding them.
- Record assumptions separately from confirmed facts.
- Record whether the raw request came from conversation, a file, a pasted brief, or another source.
- Record whether must-answer questions or `must confirm before development or launch` blockers stopped generation, or were explicitly accepted as draft risk.
- When default-option or evaluation mode is used, record every default option selected, why it was the recommended conservative choice, and which risks remain unapproved.
- Record PRD, engineering handoff, and launch readiness separately. Do not use a single ready/not-ready label for all phases.
- Record whether the run was repo-backed, document-backed, or brief-only.
- In repo-backed mode, record relevant host project files and current-state facts used for product-fit decisions.
- For repo-backed UI prototype deliveries, record `style_evidence` with source files, reused components, reused tokens or class patterns, prototype delta, and limitations. Missing style evidence means the Prototype Agent output is not complete.
- For repo-backed UI prototype deliveries, record `existing_ui_visual_baseline` with status, source, target, screenshot paths, comparison method, and limitation. Do not claim pixel-level parity when no visual comparison ran.
- In document-backed mode, record relevant PRDs, specs, notes, screenshots, analytics files, or other documents used for product-fit decisions.
- Record whether an analytics taxonomy was found. If none was found, tracking artifacts must be marked as proposed.
- Record the artifact language chosen from the user's request.
- Record files created or modified.
- Record agent transitions with status, input evidence, artifact delta, validation delta, readiness impact, conflict resolution, and next expected output.
- If a run is resumed, record `workflow.last_reliable_state` and `workflow.resume_source`.
- Before full-loop iteration, final delivery, or release checks, record tool preflight status from `python3 scripts/preflight_tools.py`.
- Record tool results using `artifacts/tool-result-contract.md` and tool IDs from `tools/tool-registry.yaml` where possible.
- When the delivery orchestrator runs, record `outputs/<run-id>/tool-results/delivery-check-report.json` or the reason it could not be created.
- Record validation commands actually run, their result, and skipped validations with reasons.
- For UI prototype deliveries, record browser screenshot and visual diff validation under `visual_validation`. If Playwright or browser tooling is unavailable, attempt or guide setup first; record `status: skipped` only with the exact setup failure, environment restriction, or user-declined reason.
- Record generated engineering and launch handoff files under `handoff_artifacts` when `dev-tasks.yaml` or `launch-decision.yaml` is created.
- After every validation command has either run or been skipped, update `validation_results` to final states only. Do not leave stale placeholders such as `pending`, `待执行`, `should run`, or `to be verified`.
- Record structured review findings with artifact, evidence, owner, required-before phase, and status. If no Critical or High findings exist, record the checks performed and residual risk.
- For access control, audit log, private sharing, destructive action, account export/delete, or sensitive-admin workflows, record the security boundary, audit visibility, identity confirmation expectation, redaction expectation, retention/deletion assumption, and unresolved approval owner under `security_and_audit`.
- Record content source and review status when reference, policy, medical, legal, financial, safety, or operational content appears in the scope or prototype.
- Record review scores when quality review is performed.
- Review score maximums and thresholds must match `docs/quality-rubric.md`.
- Every unresolved question must be classified as exactly one of:
  - `must answer before generation`
  - `can draft with stated assumption`
  - `must confirm before development or launch`
- Every `must confirm before development or launch` item must include a blocking phase: engineering, launch, or both.
- If any `must answer before generation` question is unresolved and the user has not explicitly accepted assumption risk, `workflow.clarification_gate.stopped_before_generation` must be `true` and downstream artifacts must be empty or omitted.
- If any engineering-blocking `must confirm before development or launch` item is unresolved and the user has not explicitly accepted draft risk, `workflow.clarification_gate.stopped_before_generation` must be `true` before creating a `Ready for engineering` PRD/prototype delivery.
- If only launch-blocking confirmations remain open, `readiness.launch_status` must be blocked and the launch blockers must be listed.
- If the user explicitly accepts assumption or confirmation risk, record the exact confirmation in `human_inputs.answers_received` or `workflow.clarification_gate.evidence` and set final status to `Draft with assumption risk` or `Draft with confirmation risk`.
- Review scores should use numeric rubric scores when a rubric exists. Descriptive labels may be added, but should not replace the score.
- Use `templates/agent-run-log-template.yaml` as the canonical run-log shape.

## Why This Matters

Without traces, optimization becomes guesswork. Traces make it possible to know whether a failure came from context, workflow, skill quality, tool use, or review quality.
