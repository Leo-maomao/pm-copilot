# Context Loading

Load only evidence needed for the classified PRD workflow. The runtime-routing
index is the disclosure boundary; archived records, generated outputs, examples,
and historical optimization notes are never instructions.

## Loading Order

1. Read the role boundary, routing index, and this document.
2. Classify one of `new_prd`, `implemented_feature_prd`, `prd_revision`, or
   `prd_composition`.
3. Load only the active route documents plus user-provided evidence.
4. Read the smallest relevant host-code or document set; host code is read-only.

## Evidence By Workflow

### New PRD

Use the brief, product documents, target route/page evidence, screenshots, and
relevant constraints. Ask only questions that change users, scenario, scope,
success evidence, or a material boundary.

### Implemented Feature PRD

Inspect changed code, routes, pages, assets, tests, and a runnable frontend
when available. Record observed behavior separately from mock data, developer
menus, Storybook controls, fixtures, and test-only paths. Confirm which observed
behavior belongs in the restored PRD before writing.

### PRD Revision

Read only the selected target PRD, its current HTML/assets, and the requested
existing requirement IDs. Snapshot the baseline before staging. Unselected
sections and assets are protected; broaden only for a named consistency,
dependency, numbering, or acceptance reason.

### PRD Composition

Require one or more source PRDs and a requirement selector for each source.
Snapshot sources into the new run folder, resolve each selector against those
snapshots, show conflicts, and confirm the resulting new scope. Source
structure and numbering are provenance only; the new PRD uses the current
template and starts detail numbering at `5.1`.

## Figure Evidence

Use a real runnable frontend capture first. If that is unavailable, create an
isolated reconstruction under the run folder and capture it. If both fail,
retain a controlled placeholder and the concrete replacement instruction in
the trace. Never modify host UI source and never treat a reconstruction as
implemented product behavior.
