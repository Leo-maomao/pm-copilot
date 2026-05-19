# Artifact Contracts

Every generated artifact must follow the relevant contract. If a section cannot be completed, keep the section and mark it as `Unknown`, `Assumed`, or `Not applicable`.

Use the user's language for all human-facing artifact content, including headings, table column labels, status labels, notes, prototype annotations, and review labels. For analytics tables, localize reviewer-facing labels and keep machine field names such as `event_name` or `required_properties` visible in code formatting when implementation needs them. Keep file names, event names, property names, Mermaid node IDs, and other machine-readable identifiers in ASCII.

Readiness values, review severity labels, and review item statuses inside `prd.md` are human-facing and must be localized. Internal traces may keep stable English codes when useful, but Chinese PRDs should use Chinese statuses such as `可进入评审`, `框架范围可进入开发`, `发布前阻塞`, `高`, `中`, `低`, `未关闭`, or equivalent localized wording.

Repository templates are structure guides, not literal English copy. Translate template headings and labels when the requested output language is not English.

## Default Delivery

The default product-manager delivery contains only:

- `outputs/<run-id>/prd.md`
- `outputs/<run-id>/prototype-<platform>.html` when a user-facing prototype is relevant

`outputs/<run-id>/run-log.yaml` is an internal trace artifact for debugging, regression, and auditability. It is not a PM-facing deliverable.

Generated run folders may also contain internal tool evidence under `outputs/<run-id>/tool-results/`, especially `delivery-check-report.json` from `scripts/run_delivery_checks.py`. These files are not PM-facing deliverables; they support auditability and regression scoring.

Do not create separate `task-brief.md`, `clarifying-questions.md`, `assumptions.md`, `pm-package.md`, `metrics-tree.md`, `tracking-plan.md`, `user-flow.md`, `review-checklist.md`, or `final-package-summary.md` by default. Create split files only when the user asks, an external workflow needs them, or a machine-readable export is useful.

When the user asks for engineering handoff, issue planning, unattended task planning, release readiness, or launch decision support, PM Copilot may additionally create:

- `outputs/<run-id>/dev-tasks.yaml`
- `outputs/<run-id>/launch-decision.yaml`

These are controlled handoff artifacts. They must follow `artifacts/dev-task-contract.md` and `artifacts/launch-decision-contract.md`.

The original request, clarified answers, low-risk assumptions, scope decisions, metrics, tracking plan, flow diagrams, risks, and validation results belong in `prd.md`.

## Clarification Gate

Clarification output must not contradict itself. Do not mark one question as both blocking and assumed. Use distinct buckets:

- `must answer before generation`
- `can draft with stated assumption`
- `must confirm before development or launch`

If must-answer questions are unresolved, ask the user and stop before generating `prd.md` or prototype HTML. User silence is not approval.

Default readiness is `Ready for engineering` for the confirmed engineering scope. If engineering-blocking confirmations are missing, the agent must stop and ask. It may generate a draft only when the user explicitly requests a draft or accepts the risk, and the PRD status must reflect that downgrade. Launch readiness is a separate field; a PRD may be ready for engineering while launch remains blocked by content, legal, compliance, operational, or analytics approval.

## PRD

Required sections:

- Title
- Version history
- Requirement input and confirmation record
- Readiness summary
- Background
- Research and reference findings
- Project goals and metrics
- Requirement scope
- Surface and permission states, when relevant
- Content source and review status, when relevant
- Requirement list
- Requirement details
- Flow diagrams, when useful
- Tracking plan
- Prototype reference
- Risks and open confirmations
- Acceptance criteria
- Delivery review findings
- Validation results

Required formatting:

- Use tables for version history, confirmations, goals, scope, requirement list, requirement details, tracking, risks, and acceptance criteria when there are multiple items.
- Use stable IDs such as `R1`, `F1`, `AC1`, and `E1`.
- Use short paragraphs for background, research conclusions, and rationale.
- Avoid long undifferentiated unordered lists.
- Keep confirmed MVP scope separate from optional, conditional, future, and non-goal scope.
- Acceptance criteria cover confirmed MVP requirements only.
- PRD status, engineering handoff status, and launch status are separate and non-contradictory.
- Existing-product entry points, navigation visibility, permission or eligibility states, and fallback states are explicit when the feature adds or changes a surface.

Requirement details must be implementation-grade. For each functional item, include the relevant subset of:

- Function ID and function name
- User scenario
- Entry point or trigger
- Page or content requirements
- Business logic
- Interaction rules
- Data rules
- Permission or eligibility rules
- Edge and fallback states
- Tracking event links
- Acceptance criteria links

Minimum quality bar:

- A PM, designer, engineer, QA, and analytics reviewer can understand the requirement from `prd.md` plus the prototype.
- Goals are measurable or tied to a measurement plan.
- Research and reference findings explain why the solution is shaped this way using source-backed competitor, benchmark, comparable feature, user research, public docs, screenshots, or technical solution references.
- Current implementation findings from the host repository are product context, not a substitute for external product research. Put them in background, current-state notes, or the engineering implementation map unless they are clearly labeled as implementation constraints.
- Requirements are testable.
- Edge cases include error, empty, permission, payment, rollback, content-review, and launch-blocking cases where relevant.
- Open questions and launch blockers are visible, not hidden inside prose.
- Validation results list the exact command, pass/fail/skipped status, and limitation. The PRD must not conflict with `run-log.yaml` about what was validated.
- Tool results follow `artifacts/tool-result-contract.md` and use capability IDs from `tools/tool-registry.yaml` where possible.
- Validation results must be finalized after tools run. Do not leave placeholder statuses such as `pending`, `待执行`, `should run`, or `to be verified` in delivered artifacts once the corresponding command has already been executed or intentionally skipped.
- Prototype validation should include browser screenshot and visual diff checks. If tooling is unavailable, PM Copilot should attempt or guide setup first. A skipped visual check must include the setup failure, environment restriction, or user-declined reason in `run-log.yaml` and the PRD validation section.
- Content source, review owner, review status, and disclaimer status are visible when the requirement includes reference, policy, medical, legal, financial, safety, or operational content. Unreviewed content is labeled as placeholder or draft and blocks launch.
- Delivery review findings include artifact, evidence, owner, required-before phase, and status, or explicitly state that no Critical or High findings were found after review.

## Tracking Plan

The tracking plan is a PRD section by default.

Required event table semantic columns. CSV exports must use the exact machine column names below; Markdown review tables may localize the visible label and include the machine name in code formatting.

- event_name
- description
- trigger
- platform
- actor
- required_properties
- optional_properties
- success_criteria
- validation_notes
- privacy_notes

Required property table semantic columns. CSV exports must use the exact machine column names below; Markdown review tables may localize the visible label and include the machine name in code formatting.

- property_name
- type
- required
- example
- description
- allowed_values
- privacy_level
- source

Minimum quality bar:

- Event names follow the configured taxonomy.
- If no configured taxonomy was found, the tracking plan is labeled as a proposed taxonomy and records the context source or absence of source.
- Each core user action has coverage or an explicit omission reason.
- Every property used by any event is defined once in the property dictionary.
- Sensitive properties are flagged and minimized.

## Flow Diagrams

Flow diagrams are PRD sections by default. Create `user-flow.mmd` only when a Mermaid source export is useful or requested.

Useful diagram types:

- Functional flow: system or feature-level logic, branches, and states.
- Operation flow: user-facing action path across pages or controls.

Minimum quality bar:

- Diagrams are standard Mermaid flowcharts when Markdown rendering is expected.
- Branch labels are meaningful.
- The flow matches the confirmed PRD scope.
- Notes explain only assumptions or edge cases that cannot fit cleanly in the diagram.

## HTML Prototype

Required elements:

- Runs locally without build tooling.
- Simulates the selected platform container.
- Matches existing product style when current screenshots, demos, routes, components, or design-system references are available.
- For repo-backed frontend products, records `style_evidence` in `run-log.yaml` and includes `style-source-summary` or `data-style-source` in the HTML.
- For repo-backed frontend products, records `existing_ui_visual_baseline` in `run-log.yaml`, including captured/provided screenshot evidence or an explicit skipped reason.
- Includes key screens and states.
- Includes interaction for the main path.
- States its fidelity level: `low`, `mid`, or `high`.
- Does not reserve a side annotation board by default. The product UI should keep its real layout width and height.
- Places compact numbered callouts at the top-right corner of the concrete UI component, state, or transition being explained, offset just outside the corner when needed to avoid covering content.
- Uses small red `annotation-marker` badges with `data-annotation-id` and `data-annotation-placement="top-right"` on the prototype surface. Clicking a marker opens an `annotation-dialog` or popover for that marker. A fixed top-right `annotation-toggle` opens an `annotation-list` overlay for all markers in the current page/state.

Prototype annotations must cover the relevant subset of:

- Product design intent
- Logic rule
- Interaction behavior such as tap, hover, long-press, disabled, loading, error, and success
- Text length limit, truncation, and ellipsis behavior
- Content source and placeholder status
- Data source and refresh behavior
- Permission or eligibility behavior
- Tracking hook
- Engineering handoff note

Minimum quality bar:

- No external assets are required.
- Text fits in the layout.
- Callouts do not cover critical copy or controls.
- Prototype annotation overlays must not change product layout, reserve persistent side space, or shrink the product viewport.
- The prototype does not claim to be production code.
- The prototype shows real screens, state changes, validation, empty states, errors, permissions, and success feedback where relevant.
- When existing product UI exists, the prototype adapts the existing surface and highlights the new requirement delta instead of inventing an unrelated product surface.
- When host frontend code exists, the prototype reuses the current app shell, component structure, tokens, spacing density, and copy tone rather than introducing a separate visual system.
- For long pages, multi-state flows, and modals, preserve the product's real scrolling behavior. Do not clip modal contents or force the whole product into a fixed-height frame unless the host product does that.
- When existing screenshots or a runnable host app are available, unchanged regions are compared or reviewed against that visual baseline; without baseline evidence, the artifact must not claim pixel-level parity.
- Browser screenshot validation covers at least one primary desktop or default viewport and one constrained/mobile viewport when the platform has responsive behavior. Visual diff baselines are required for regression suites and optional for first-run exploratory artifacts.

## Engineering and Launch Handoff

`dev-tasks.yaml` and `launch-decision.yaml` are optional controlled handoff artifacts.

Minimum quality bar:

- Development tasks trace to PRD requirement IDs, function IDs, or acceptance criteria IDs.
- Blocked tasks are not marked issue-ready.
- Launch decisions separate evidence-backed gates from missing approvals.
- Unattended launch decisions cannot mark `ready_to_launch` unless explicit human approval evidence is present.
- Allowed and disallowed next actions are explicit.

## Optional Exports

Split PRD, split tracking Markdown, split user-flow Markdown, review checklist files, `pm-package.md`, and `final-package-summary.md` must not be generated by default. Create a separate file only when the user explicitly asks for it or an external tool requires a machine-readable export such as CSV, Mermaid source, development task YAML, launch decision YAML, or visual review artifacts.
