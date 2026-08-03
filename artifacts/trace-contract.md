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
agent_strategy:
  task_mode:
  secondary_modes:
  autonomy_level:
  effort_budget:
  goal:
  success_criteria:
  user_value:
  selected_path:
  skipped_path:
  rejected_alternatives:
  final_delivery_contract:
delegation_plan:
agent_task_ledger:
collaboration_protocol:
resume_checkpoint:
termination_condition:
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
tool_plan:
decision_record:
replan_triggers:
review_loop:
loop_policy:
loop_state:
iteration_trace:
loop_summary:
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
self_iteration:
failures:
final_status:
memory_candidates:
next_actions:
action_closure:
```

## Rules

- Do not include sensitive raw user data.
- Record tool limitations instead of hiding them.
- Record assumptions separately from confirmed facts.
- Record whether the raw request came from conversation, a file, a pasted brief, or another source.
- Record `agent_strategy.task_mode`, `agent_strategy.autonomy_level`, success criteria, selected path, skipped path, and rejected alternatives before or during artifact generation.
- `scripts/run_agent_delegation.py --execute` automatically writes `tool-results/agent-events.jsonl` beside its durable task ledger. External adapters and other auditable multi-Agent runs must write the same format with `scripts/agent_event_ledger.py`. Each event records a stable event id, timestamp, run id, workspace, event type, and non-sensitive data. This event ledger is the vendor-neutral source for trace export and replay; `run-log.yaml` remains the human-readable summary.
- Record `agent_strategy.effort_budget` as `fast-pass`, `standard-loop`, `deep-agentic`, `research-intensive`, or `release/self-iteration`.
- Record `delegation_plan` when PM Orchestrator splits work across specialist agents or external worker loops.
- When delegated execution is used, retain an `agent_task_ledger` under the run folder. The ledger is the durable execution source; `delegation_plan` and `collaboration_protocol` are its readable trace projection. A completed ledger requires persisted worker outputs and a structured claim or arbitration result. Record whether worker isolation is provider-enforced or only prompt-restricted; do not overstate the boundary.
- When `delegation_plan.active: true`, record `collaboration_protocol`. It must either state `trigger: not_required` with a concrete reason, or retain the material claims, targeted cross-review, evidence comparison, and PM Orchestrator arbitration that resolved the conflict. Do not create a debate merely to satisfy the trace.
- A cross-review may challenge only a named claim with an evidence gap, user conflict, scope conflict, or metric conflict. The response and arbitration must compare evidence and user impact; majority vote and silent overwrite are invalid.
- An arbitration that escalates to a human blocks the affected engineering or launch decision until the named confirmation is received.
- Record `resume_checkpoint` for long, resumed, interrupted, or self-iteration runs.
- Record `termination_condition` before final response; do not treat reaching the last workflow state as completion by itself.
- Record task mode values as one of `prd_delivery`, `implemented_feature_prd`, `ui_delivery`, `tracking_plan`, `launch_readiness`, `dev_handoff`, `structured_reference`, `product_review`, `self_improvement`, or `mixed_delivery`.
- Record autonomy level as `clarify-first`, `draft-with-risk`, `full-loop`, or `self-iteration`.
- Record `tool_plan` before high-impact tool use when the run needs validation, research, repo inspection, UI rendering, or release checks.
- Record `decision_record` for product judgments, selected paths, rejected alternatives, `high|medium|low` confidence, and the evidence that shaped the choice.
- Record `replan_triggers` when evidence is insufficient, the user changes the goal, a tool fails, artifacts conflict, or review finds High/Critical issues.
- Record `review_loop` with a nonnegative iteration count, Critical/High findings, exact `finding_closures`, unresolved findings, and one final recommendation. Every severe finding must have a matching closure whose disposition is `fixed`, `accepted_risk`, or `replan` and whose evidence proves the disposition. Accepted risks additionally require owner, due phase, and rationale. A `complete` run cannot retain unresolved findings.
- Record `loop_policy` before autonomous iteration. Full-loop, deep-agentic, research-intensive, and self-iteration work must define bounded iteration, tool-call, elapsed-time, and no-progress budgets.
- Record one `iteration_trace` item per completed loop. Every progress claim must identify at least one evidence, artifact, decision, or validation delta; repeating the same action without delta is `no_progress`.
- Record `loop_state` after every iteration and `loop_summary` before final delivery. The summary stop reason must match success, input, blocker, budget, no-progress, human-checkpoint, or failure evidence. When a material specialist conflict exists, `loop_state.conflict_resolution_status` must be `reconcile`, `needs_input`, or `blocked`; only `clear` permits normal delivery progression.
- A human checkpoint pauses the loop once `current_iteration` reaches `required_after_iteration`. User silence is not approval, a declined checkpoint is terminal for that path, and a due checkpoint is evaluated before autonomous success.
- Record `memory_candidates` for durable product facts, user preferences, or decisions learned during the run, or record `none: true`. Product facts require source, confidence, sensitivity, and safe write recommendation; preferences require source and write recommendation; decisions require rationale, source, and write recommendation. Sensitive or private facts may only use `ask_before_writing` or `do_not_store`.
- Record `action_closure.critical_path` for the smallest actions that move the product decision forward. Every item must name an action id, owner, due phase, source decision or blocker id, completion evidence, and status.
- Keep `next_actions` as the functional-area summary. Use `action_closure` as the accountable execution path; generic suggestions such as "align later" or "follow up" are not closure evidence.
- When termination is `needs_input` or `blocked`, at least one critical-path item must use the matching status and identify what evidence or answer unblocks the run.
- Record whether must-answer questions or `must confirm before development or launch` blockers stopped generation, or were explicitly accepted as draft risk.
- When default-option or evaluation mode is used, record every default option selected, why it was the recommended conservative choice, and which risks remain unapproved.
- Record PRD, engineering handoff, and launch readiness separately. Do not use a single ready/not-ready label for all phases.
- Record whether the run was repo-backed, document-backed, or brief-only.
- In repo-backed mode, record relevant host project files and current-state facts used for product-fit decisions.
- For repo-backed UI deliveries, record `host_frontend_inventory` with platform source kind, frontend entry files, route/page/screen files, component-library files, style token/global style files, icon/asset sources, data/mock sources, render command, preview surface, and target-query ranking when a requirement or target surface is available. Missing host inventory means the UI Delivery Agent output is not complete when the user expects real-product UI.
- For repo-backed UI deliveries, record concrete `style_evidence` with host source files/assets, reused components, reused tokens or class patterns, icon/asset sources, UI delta, and limitations. Also record non-empty `source_to_demo_mapping` entries that explain how inspected host components/screens are represented in the UI deliverable. Missing or empty style evidence means the UI Delivery Agent output is not complete.
- For repo-backed UI-delivery-only work, record `ui_delivery_trace` with host mutation policy, artifact mode, target surface, changed preview files when source-rendered, `baseline_import`, `delta_patch`, source-to-demo mapping, backend simulation method, parity claim, and limitations. The default policy is production flows read-only; frontend source presence should use isolated preview files instead of production flow edits or hand-written UI. Standalone fallback requires a raw-request portable/standalone/HTML request, a raw-request redesign/rebuild/from-scratch/no-original-UI-reuse request, or concrete attempted-render blocker; "only generate a prototype" is not that request. Multi-turn UI-delivery work should append to `delta_patch.multi_turn_change_log` and preserve `delta_patch.next_delta_anchor`.
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
- When `task_mode: self_improvement` or `autonomy_level: self-iteration`, enable `loop_type: self_improvement` and record `self_iteration.triggered: true`. The section must include source run or failure evidence, user correction or failure evidence, generalized failure, selected fix surface, regression update, generalization boundary, validation commands, and version impact. Embedded-copy sync targets remain required when copies exist.
- Record validation commands actually run, their result, and skipped validations with reasons.
- For UI deliveries, record browser screenshot and visual review evidence under `visual_validation`. Use `validate_prototype_visual.py` for portable review artifacts; use `validate_ui_preview.py` only to inspect an existing host preview supplied as evidence. If browser tooling is unavailable, attempt or guide setup first; record `status: skipped` only with the exact setup failure, environment restriction, or user-declined reason.
- Record generated engineering and launch handoff files under `handoff_artifacts` when `dev-tasks.yaml` or `launch-decision.yaml` is created.
- After every validation command has either run or been skipped, update `validation_results` to final states only. Do not leave stale placeholders such as `pending`, `待执行`, `should run`, or `to be verified`.
- Record structured review findings with artifact, evidence, owner, required-before phase, and status. If no Critical or High findings exist, record the checks performed and residual risk.
- For access control, audit log, private sharing, destructive action, account export/delete, or sensitive-admin workflows, record the security boundary, audit visibility, identity confirmation expectation, redaction expectation, retention/deletion assumption, and unresolved approval owner under `security_and_audit`.
- Record content source and review status when reference, policy, medical, legal, financial, safety, or operational content appears in the scope or UI deliverable.
- Record review scores when quality review is performed.
- Review score maximums and thresholds must match `docs/quality-rubric.md`.
- `review_scores`, `quality_thresholds`, `handoff_artifacts`, `content_sources`, `structured_catalog`, `structured_reference`, `guardrail_events`, and `security_and_audit` must keep the canonical field names from `templates/agent-run-log-template.yaml` so `validate_outputs.py` can reject ad hoc trace shapes.
- For document-class deliveries, use `structured_catalog` for flat parameter tables or capability matrices and `structured_reference` for broader document references or document prototypes.
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
