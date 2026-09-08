# PM Copilot PRD Workflow

PM Copilot classifies every request before loading any optional context. There
are exactly four delivery workflows.

| Mode | Input | Confirmation boundary | Delivery behavior |
| --- | --- | --- | --- |
| `new_prd` | Brief, documents, code, screenshots | Confirm clarified scope | Create a new PRD from the current template. |
| `implemented_feature_prd` | Observed code and runnable-product evidence | Confirm included production behavior | Restore a PRD without treating scaffolding as behavior. |
| `prd_revision` | One existing PRD and requirement IDs | Confirm selected IDs and requested change | Freeze baseline; modify only selected requirements and necessary linked consistency changes. |
| `prd_composition` | One or more `PRD path + requirement ID` selectors | Confirm source selections, conflicts, and new scope | Snapshot sources and create an independently structured, renumbered PRD. |

## Required Sequence

```text
Classify -> Gather minimal evidence -> Clarify if required -> Draft PRD
-> Review -> Produce figure evidence -> Render HTML -> Validate -> Deliver
```

## Execution Policy

New runs are deterministic-first across all four workflows. The controller
collects explicit scope facts, snapshots sources, materializes confirmed facts,
renders figures and HTML, and runs the delivery validators locally. It does not
dispatch specialist, clarification-review, or stage-review model calls by
default. A model has at most one role: one constrained PRD prose-edit pass that
turns the controller-frozen facts into formal, engineering-ready language. It
cannot add or reinterpret product decisions, and it is never retried as a
review or repair agent.

`--model-enhancement` is an explicit opt-in for model-led intake, specialist
evidence, and stage review. It may improve prose or evidence breadth, but the
final delivery gate remains the deterministic renderer and validators.

New PRDs, compositions, implemented-feature PRDs, and revisions draft directly
when their evidence is sufficient. They issue one consolidated question only
when a key product decision cannot be safely inferred.

This is the PRD-specific Agent Execution Graph for the bounded
`Observe -> Frame -> Decide -> Act -> Verify -> Learn` model in
`agents/agent-operating-model.md`; it does not authorize host-product changes.

## Figure Evidence

Every requirement detail that presents a frontend state needs a matching inline
figure evidence decision:

1. Capture a real runnable page or state when available.
2. Otherwise create a self-contained reconstruction under the run folder,
   capture it, and record `reconstructed_figure` provenance.
3. Otherwise retain a controlled placeholder and an actionable replacement
   instruction in `run-log.yaml`.

The figure follows the requirement inside its `需求详情` cell using the existing
`prd-detail-media` marker. It is never a separate product deliverable.

## Multi-Agent Execution

PM Orchestrator owns task classification, clarification, final synthesis, and
arbitration. In model-enhancement mode, it may dispatch independently
verifiable specialist questions required by the confirmed scope:

- Functional Logic Agent for user scenarios, rules, and edge states.
- Frontend Evidence Agent for source inspection, capture, reconstruction, and
  provenance.
- Source Resolution Agent only for `prd_composition`, to snapshot sources and
  resolve selectors.
- Review Agent independently verifies logic, figures, scope, numbering, and
  the PRD contract.

Delegate only when the evidence question is independently verifiable. Outputs
are evidence, not a vote; the PM Orchestrator records the final decision.

## Completion

A completed run contains `prd.md`, `prd.html`, `assets/`, and `run-log.yaml`.
The trace records confirmation, scope, figure provenance, source snapshots,
delegation, review, and validation. `prd.md` remains the user-facing product
document; implementation paths, source code names, and operational planning do
not belong in it.
