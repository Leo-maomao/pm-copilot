# PM Copilot PRD Workflow

PM Copilot classifies every request before loading any optional context. There
are exactly four delivery workflows.

| Mode | Input | Confirmation boundary | Delivery behavior |
| --- | --- | --- | --- |
| `new_prd` | Brief, documents, code, screenshots | Confirm clarified scope | Create a new PRD from the canonical document structure. |
| `implemented_feature_prd` | Observed code and runnable-product evidence | Confirm included production behavior | Restore a PRD without treating scaffolding as behavior. |
| `prd_revision` | One existing PRD and requirement IDs | Confirm selected IDs and requested change | Freeze baseline; modify only selected requirements and necessary linked consistency changes. |
| `prd_composition` | One or more `PRD path + requirement ID` selectors | Confirm source selections, conflicts, and new scope | Snapshot sources and create an independently structured, renumbered PRD. |

## Required Sequence

```text
Classify -> Gather minimal evidence -> Clarify if required -> Draft PRD
-> Review -> Produce figure evidence -> Render HTML -> Validate -> Deliver
```

## Execution Policy

New runs are deterministic across all four workflows. The controller collects
explicit scope facts, snapshots sources, materializes confirmed facts, renders
figures and HTML, and runs the delivery validators locally.

New PRDs, compositions, implemented-feature PRDs, and revisions draft directly
when their evidence is sufficient. They issue one consolidated question only
when a key product decision cannot be safely inferred.

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

## Completion

A completed run contains `prd.md`, `prd.html`, `assets/`, and `run-log.yaml`.
The trace records confirmation, scope, figure provenance, source snapshots,
review, and validation. `prd.md` remains the user-facing product
document; implementation paths, source code names, and operational planning do
not belong in it.
