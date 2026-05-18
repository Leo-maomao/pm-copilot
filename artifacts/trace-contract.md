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
  clarification_gate:
    required:
    status:
    stopped_before_generation:
    assumption_risk_accepted:
    confirmation_risk_accepted:
    evidence:
  revision_loops:
agents_used:
skills_used:
tools_used:
human_inputs:
  clarification_questions:
  answers_received:
  unanswered_questions:
  confirmations_required:
assumptions:
scope_decisions:
surface_decisions:
content_sources:
open_questions:
artifacts:
guardrail_events:
review_findings:
review_scores:
validation_results:
failures:
final_status:
next_actions:
```

## Rules

- Do not include sensitive raw user data.
- Record tool limitations instead of hiding them.
- Record assumptions separately from confirmed facts.
- Record whether the raw request came from conversation, a file, a scenario-library task brief, or another source.
- Record whether must-answer or pre-development confirmation questions blocked generation, or were explicitly accepted as draft risk.
- Record PRD, engineering handoff, and launch readiness separately. Do not use a single ready/not-ready label for all phases.
- Record whether the run was repo-backed, document-backed, or brief-only.
- In repo-backed mode, record relevant host project files and current-state facts used for product-fit decisions.
- In document-backed mode, record relevant PRDs, specs, notes, screenshots, analytics files, or other documents used for product-fit decisions.
- Record whether an analytics taxonomy was found. If none was found, tracking artifacts must be marked as proposed.
- Record the artifact language chosen from the user's request.
- Record files created or modified.
- Record validation commands actually run, their result, and skipped validations with reasons.
- Record structured review findings with artifact, evidence, owner, required-before phase, and status. If no Critical or High findings exist, record the checks performed and residual risk.
- Record content source and review status when reference, policy, medical, legal, financial, safety, or operational content appears in the scope or prototype.
- Record review scores when quality review is performed.
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
