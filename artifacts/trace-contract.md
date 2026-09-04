# PRD Run Trace Contract

`run-log.yaml` is controller-owned evidence for one PRD delivery. It is not a
second PRD, a generic PM work log, or an external-agent ledger.

## Supported Workflows

Only these task modes are valid:

1. `new_prd`
2. `implemented_feature_prd`
3. `prd_revision`
4. `prd_composition`

Each completed run delivers `prd.md`, `prd.html`, `assets/`, and `run-log.yaml`.

## Required Evidence

```yaml
run_id:
task:
  raw_request:
agent_strategy:
  task_mode:
  goal:
confirmation:
  status: confirmed
  scope:
artifact_lineage:
  mode:
  source_prds: []
  revision_baseline: {}
frontend_figure_evidence: []
requirement_coverage_review: []
specialist_evidence: []
pm_arbitration:
  decisions: []
review:
  status:
  findings: []
validation_results: []
quality_decision:
  passed: false
final_status:
```

- `confirmation` records the scope confirmation before delivery. For a revision
  it records the selected requirement IDs; for an implemented feature it records
  the observed product behavior included in the PRD.
- `artifact_lineage.mode` is `new_run`, `implemented_feature_run`,
  `in_place_revision`, or `composition_run`. Composition contains one or more
  immutable, run-local source snapshots and their selectors. Revision contains
  the frozen baseline and the approved linked changes, if any.
- `frontend_figure_evidence` has one item for every figure-bearing requirement.
  Its `kind` is `real_capture`, `reconstructed`, or `placeholder`. A placeholder
  has both `missing_reason` and `replacement_action`.
- `requirement_coverage_review` is required only for an implemented-feature PRD.
  It is controller-derived from the final PRD and immutable evidence packet, so
  it preserves the visual decision and explicit localization/tracking links for
  each final requirement without duplicating implementation evidence in the log.
- `specialist_evidence` is created only for independently useful work. It may
  contain any number of functional-logic, frontend-evidence, or source-resolution
  specialists. A failed specialist remains evidence of a failed attempt, never
  product truth.
- `pm_arbitration.decisions` records the PM Orchestrator's conclusion whenever
  specialist claims conflict or a specialist result is not adopted.
- `review` records the independent PRD review. A complete delivery has no open
  Critical or High finding.
- `validation_results` records renderer, output, trace, and delivery checks for
  the exact staged bytes. `quality_decision.passed` is true only after they pass.

Do not add research plans, release decisions, engineering handoffs, task
trackers, prototype delivery, agent-loop budgets, memory candidates, or generic
PM readiness fields to this contract.

## Validation

```bash
python3 scripts/render_prd_html.py <run-folder>
python3 scripts/validate_outputs.py <run-folder>
python3 scripts/validate_agent_trace.py <run-folder>
python3 scripts/run_delivery_checks.py <run-folder>
```
