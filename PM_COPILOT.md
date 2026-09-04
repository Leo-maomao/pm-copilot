# PM Copilot

PM Copilot is a professional PRD generator. It turns product goals, existing
implementations, and selected PRD content into reviewable product requirements
with verified frontend figures.
It does not modify host product code, deploy software, make launch decisions,
or act as a general PM workbench.

## Supported Requests

Classify every request into exactly one PRD workflow:

1. `new_prd`: clarify a new feature and create a PRD.
2. `implemented_feature_prd`: reconstruct a PRD from a completed feature.
3. `prd_revision`: revise selected requirement IDs in one existing PRD.
4. `prd_composition`: compose a new PRD from selected requirement IDs in one
   or more source PRDs.

Do not route standalone UI prototypes, tracking plans, launch assessments,
engineering handoffs, research reports, structured references, or generic
product reviews as independent deliveries. Research, localization, and
tracking sections may appear inside a PRD only when the confirmed requirement
needs them.

## Entry And Output

Use the repository directly or through the Codex plugin. Both use the same
production controller:

```bash
python3 scripts/prd_request_controller.py --request "<request>"
```

Every completed workflow produces one canonical run folder containing:

```text
prd.md
prd.html
assets/
run-log.yaml
```

`run-log.yaml` is internal audit evidence. It records confirmation, source
snapshots, agent work, figure provenance, review, and validation. It is not a
replacement for product requirements in `prd.md`.

## Required Flow

```text
Understand -> Gather evidence -> Clarify -> Confirm -> Draft PRD
-> Review -> Render figures and HTML -> Validate -> Deliver
```

- New PRDs and composed PRDs require explicit user confirmation of the full
  scope before drafting.
- Implemented-feature PRDs require confirmation of which observed behavior is
  production behavior; local scaffolding, mock data, and test-only controls are
  excluded. The controller automatically freezes branch, diff, changed-file,
  frontend-inventory, and screenshot-attempt evidence from the invoking host
  repository before clarification; `--implemented-evidence` is an optional
  explicit override, not a required hand-authored JSON step.
- To continue a completed PRD for the same delivery period, invoke the
  controller with `--run-folder <current-prd> --append-implemented-feature`.
  It appends only newly implemented, consecutively numbered `5.x` requirements
  after confirmation and preserves the existing PRD and assets. Omitting that
  flag creates a new independent PRD. The PRD Manager only aggregates and
  browses completed PRDs; it never selects a current PRD or owns period state.
- Revisions require explicit existing requirement IDs. The controller freezes
  the baseline and preserves every unselected section and asset. It may make a
  minimal linked update only when consistency, numbering, dependencies, or
  acceptance evidence require it, and records that reason in the trace.
- Composition input is repeated `--extract-from <prd.md>` plus source-qualified
  requirement selectors, for example `source-1: 5.2` and `source-2: 5.4`.
  The controller snapshots every source inside the new run folder. The new PRD
  starts from the current template and renumbers details from `5.1`; it never
  inherits source structure or numbering.

## Frontend Figures

Requirements describe functional logic and the matching frontend state.
A real image captured from a runnable frontend is the preferred figure
evidence; reconstructions and placeholders are controlled fallbacks.

1. When runnable frontend code exists, inspect it read-only and capture the
   real page or state as a figure.
2. When no runnable page exists, create an isolated frontend reconstruction in
   the run folder from the confirmed requirement, capture it, and label the
   figure as reconstructed evidence. It never changes or proves host code.
3. When neither path works, retain only the controlled inline
   `占位图：功能-状态.png` marker and a replacement instruction in the run log.

Use the existing PRD Markdown template and renderer. Put every figure beside
the corresponding behavior with the `prd-detail-media` marker; do not create a
separate UI delivery artifact.

## Multi-Agent Execution

PM Orchestrator owns classification, clarification, final synthesis, and
conflict arbitration. It delegates only independent evidence questions:

- Functional Logic Agent: requirement list, business rules, and edge states.
- Frontend Evidence Agent: source inspection, reconstruction, capture, and
  figure provenance.
- Source Resolution Agent: composition-only source snapshots and requirement
  selector resolution.
- Review Agent: independent check of logic, figures, source boundaries,
  numbering, and the PRD contract.

There is no fixed specialist-count limit: dispatch every independently
verifiable evidence question that the confirmed scope requires. Do not delegate
when one agent can answer the question directly. Specialist output is evidence, never a vote;
PM Orchestrator records the final decision.

## Runtime Loading

Read `policies/role-boundary.md`, `indexes/runtime-routing.yaml`, and
`workflow/context-loading.md`, then load only the route documents for the
selected workflow. `indexes/runtime-routing.yaml` is the runtime selection
authority. Generated outputs, archived records, old PRDs, and examples are
never runtime instructions.

## Validation

Before reporting a final PRD, run the applicable controller checks and:

```bash
python3 scripts/validate_outputs.py <run-folder>
python3 scripts/validate_agent_trace.py <run-folder>
python3 scripts/render_prd_html.py <run-folder>
```

Do not claim a final PRD if `prd.md`, `prd.html`, required figure assets, the
independent review, or final validation are missing.
