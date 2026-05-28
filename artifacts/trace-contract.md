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
external_research:
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
external_integrations:
human_inputs:
  clarification_questions:
  answers_received:
  default_options_selected:
  unanswered_questions:
  confirmations_required:
assumptions:
scope_decisions:
surface_decisions:
host_frontend_inventory:
style_evidence:
existing_ui_visual_baseline:
design_calibration:
content_sources:
structured_catalog:
structured_reference:
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
- For repo-backed UI deliveries, record `host_frontend_inventory` with platform source kind, frontend entry files, route/page/screen files, component-library files, style token/global style files, icon/asset sources, data/mock sources, render command, preview surface, and target-query ranking when a requirement or target surface is available. Missing host inventory means the UI Delivery Agent output is not complete when the user expects real-product UI.
- For repo-backed UI deliveries, record concrete `style_evidence` with host source files/assets, reused components, reused tokens or class patterns, icon/asset sources, UI delta, and limitations. Also record non-empty `source_to_demo_mapping` entries that explain how inspected host components/screens are represented in the UI deliverable. Missing or empty style evidence means the UI Delivery Agent output is not complete.
- For repo-backed UI-delivery-only work, record `isolated_ui_prototype` with host mutation policy, artifact mode, target surface, changed preview files when source-rendered, `baseline_import`, `delta_patch`, source-to-demo mapping, backend simulation method, parity claim, and limitations. The default policy is production flows read-only; frontend source presence should use isolated preview files instead of production flow edits or hand-written UI. Standalone fallback requires a raw-request portable/standalone/HTML request, a raw-request redesign/rebuild/from-scratch/no-original-UI-reuse request, or concrete attempted-render blocker; "only generate a prototype" is not that request. Multi-turn UI-delivery work should append to `delta_patch.multi_turn_change_log` and preserve `delta_patch.next_delta_anchor`.
- For repo-backed UI deliveries, record `existing_ui_visual_baseline` with status, source, target, screenshot paths, comparison method, and limitation. Do not claim pixel-level parity when no visual comparison ran. A renderable host frontend using standalone fallback needs either captured baseline evidence, a raw-request portable/standalone/HTML request, or a concrete source-rendering/browser limitation.
- For image-to-UI or screenshot reconstruction deliveries, record `image_reference_reconstruction` with the reference image source, dimensions, intended viewport, role, visual inventory summary, asset handling decisions, comparison method, mismatches fixed, remaining mismatches, and skipped-tool reason when screenshot comparison cannot run. Do not claim high, exact, 1:1, or pixel-level fidelity without exact-size implementation screenshot comparison evidence.
- In document-backed mode, record relevant PRDs, specs, notes, screenshots, analytics files, or other documents used for product-fit decisions.
- Record whether an analytics taxonomy was found. If none was found, tracking artifacts must be marked as proposed.
- Record external product research separately from repository context. `external_research` should include status, research question, competitor/comparable flow findings when relevant, sources, observed facts, product implications, limitations, and recommendation impact.
- Record the artifact language chosen from the user's request.
- Record files created or modified.
- Record agent transitions with status, input evidence, artifact delta, validation delta, readiness impact, conflict resolution, and next expected output.
- Agent transition deltas must use the canonical structured keys from `templates/agent-run-log-template.yaml`; do not record `artifact_delta: none`, list-only file paths, or prose-only `validation_delta` values.
- If a run is resumed, record `workflow.last_reliable_state` and `workflow.resume_source`.
- Before full-loop iteration, final delivery, or release checks, record tool preflight status from `python3 scripts/preflight_tools.py`.
- When external MCP/API/SaaS tools are requested or recommended, record `external_integrations` with candidate status, source type, source URL, cost risk, credentials, permission boundary, data risk, fallback, approval owner, and limitation.
- Record tool results using `artifacts/tool-result-contract.md` and tool IDs from `tools/tool-registry.yaml` where possible.
- When the delivery orchestrator runs, record `outputs/<run-id>/tool-results/delivery-check-report.json` or the reason it could not be created.
- Record validation commands actually run, their result, and skipped validations with reasons.
- For UI deliveries, record browser screenshot and visual diff validation under `visual_validation`. For compatibility HTML, `validate_prototype_visual.py` may be used; for source-backed preview/delta, run the host dev/preview/Storybook/simulator path and use `validate_ui_preview.py` when a browser URL or file target exists, or record equivalent simulator evidence. If Playwright or browser tooling is unavailable, attempt or guide setup first; record `status: skipped` only with the exact setup failure, environment restriction, or user-declined reason.
- Record generated engineering and launch handoff files under `handoff_artifacts` when `dev-tasks.yaml` or `launch-decision.yaml` is created.
- After every validation command has either run or been skipped, update `validation_results` to final states only. Do not leave stale placeholders such as `pending`, `待执行`, `should run`, or `to be verified`.
- Record structured review findings with artifact, evidence, owner, required-before phase, and status. If no Critical or High findings exist, record the checks performed and residual risk.
- For access control, audit log, private sharing, destructive action, account export/delete, or sensitive-admin workflows, record the security boundary, audit visibility, identity confirmation expectation, redaction expectation, retention/deletion assumption, and unresolved approval owner under `security_and_audit`.
- Record content source and review status when reference, policy, medical, legal, financial, safety, or operational content appears in the scope or UI deliverable.
- Record review scores when quality review is performed.
- Review score maximums and thresholds must match `docs/quality-rubric.md`.
- `review_scores`, `quality_thresholds`, `handoff_artifacts`, `content_sources`, `structured_catalog`, `structured_reference`, `guardrail_events`, and `security_and_audit` must keep the canonical field names from `templates/agent-run-log-template.yaml` so `validate_outputs.py` can reject ad hoc trace shapes.
- For document-class deliveries, record `structured_reference` with the delivery class, source facts, product decisions, entity/field/rule structure, attention points, calibration mode, object-level change log, and completeness check. Use `structured_catalog` for backward-compatible flat table handoffs and `structured_reference` for broader document reference or document prototype work.
- Document attention points must use typed values such as `source_gap`, `pm_override`, `conflict`, `engineering_must_read`, `launch_blocker`, `cost_or_quota_risk`, `security_or_compliance`, or `change_marker`, and each must target a concrete document, entity, field, rule, or decision.
- Multi-turn document calibration must preserve object-level continuity. If one entity, field group, or rule is updated, record the patch scope and protected objects instead of silently rewriting unrelated objects. If the user asks only to adjust presentation, set calibration workflow or patch scope to `presentation_only` and do not change structured content.
- Every unresolved question must be classified as exactly one of:
  - `must answer before generation`
  - `can draft with stated assumption`
  - `must confirm before development or launch`
- Every `must confirm before development or launch` item must include a blocking phase: engineering, launch, or both.
- If any `must answer before generation` question is unresolved and the user has not explicitly accepted assumption risk, `workflow.clarification_gate.stopped_before_generation` must be `true` and downstream artifacts must be empty or omitted.
- If any engineering-blocking `must confirm before development or launch` item is unresolved and the user has not explicitly accepted draft risk, `workflow.clarification_gate.stopped_before_generation` must be `true` before creating a `Ready for engineering` PRD/UI delivery.
- If only launch-blocking confirmations remain open, `readiness.launch_status` must be blocked and the launch blockers must be listed.
- If the user explicitly accepts assumption or confirmation risk, record the exact confirmation in `human_inputs.answers_received` or `workflow.clarification_gate.evidence` and set final status to `Draft with assumption risk` or `Draft with confirmation risk`.
- Review scores should use numeric rubric scores when a rubric exists. Descriptive labels may be added, but should not replace the score.
- Use `templates/agent-run-log-template.yaml` as the canonical run-log shape.

## Why This Matters

Without traces, optimization becomes guesswork. Traces make it possible to know whether a failure came from context, workflow, skill quality, tool use, or review quality.
