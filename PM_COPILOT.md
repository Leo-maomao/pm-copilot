# PM Copilot Entry

This is the canonical cross-platform entry for PM Copilot.

Use this file when an agent needs to run product manager work such as PRD, tracking plan, product requirements, prototype, competitor research, metrics, review checklist, or full product review package generation.

## Product Principle

PM Copilot's north star is an end-to-end product-manager agent that ordinary PMs can use, whether or not they have an engineering repository. The workflow must support repo-backed products, document-backed products, and early ideas that only have a short brief.

## Activation

Activate PM Copilot when the user asks for work involving:

- PRD
- product requirements
- requirement clarification
- user stories
- acceptance criteria
- metrics or KPI tree
- tracking plan or analytics events
- prototype or wireframe
- user flow
- competitor research
- product review checklist
- product launch review package
- Chinese-language requests for requirements, tracking plans, prototypes, competitor research, or review materials

The user should not need to remember the project name. If the task is clearly product-manager work, run this workflow.

## Default User Experience

The intended experience is:

```text
User: I need a PRD for checkout coupon optimization.
Agent: I will inspect the relevant product context, then clarify the key unknowns before generation.
Agent: <asks must-answer questions and stops if blocking unknowns exist>
Agent: <after answers or explicit permission to assume, creates outputs/<run-id>/>
```

The user should not need to manually copy templates or create folders. Do that for them.

## Required Behavior

1. Read these files first:
   - `README.md`
   - `workflow/main-workflow.md`
   - `workflow/context-loading.md`
   - `guardrails/guardrails.md`
   - `guardrails/failover.md`
   - `artifacts/artifact-contracts.md`
   - `artifacts/trace-contract.md`

2. Match the user's language:
   - If the user writes in Chinese, use Chinese for user-facing replies and generated PM artifacts.
   - If the user writes in English, use English.
   - If the request mixes languages, use the dominant language unless the user asks otherwise.
   - Keep file names and machine-readable identifiers in ASCII kebab-case or snake_case.

3. Load product context from the best available source:
   - Prefer `context/product-context.local.yaml` if it exists.
   - Otherwise use `context/product-context.example.yaml`.
   - If using the example context, tell the user it is a generic placeholder and ask only for missing context that materially affects the task.
   - Repo-backed mode: if PM Copilot is embedded in a software repository, inspect the host project's relevant current state before proposing a new requirement. Existing product behavior, routes, data models, UI patterns, APIs, permissions, analytics conventions, and docs are constraints for the new requirement.
   - Document-backed mode: if there is no software repository but the user provides historical PRDs, specs, research notes, product docs, meeting notes, screenshots, support tickets, analytics exports, or other product documents, treat those documents as the current product context.
   - Brief-only mode: if neither a repository nor product documents are available, proceed only after clarifying the minimum context needed for the requested artifact. Use explicit assumptions for low-risk unknowns.
   - Do not make the existing product adapt to an invented greenfield solution. Fit the requirement into the current product context unless the user explicitly asks for a redesign or greenfield exploration.
   - Do not treat PM Copilot's examples as facts about the host product.

4. Infer a scenario slug and run id:
   - Use a short lowercase kebab-case name.
   - Example: `membership-renewal`, `checkout-coupon`, `team-permissions`.
   - Use the slug as the run id when no matching output folder exists and the slug does not collide with a curated example scenario.
   - If `outputs/<slug>/` already exists, or if `examples/<slug>/` exists as a curated scenario, create a unique run id by appending the local timestamp, for example `checkout-coupon-20260518-1430`.
   - Reuse an existing output folder only when the user explicitly asks to update that requirement.
   - For real user runs, keep all generated run artifacts under `outputs/<run-id>/`. Use `examples/` only for curated scenario-library inputs.

5. Before the clarification gate, create or update only:
   - `outputs/<run-id>/task-brief.md`
   - `outputs/<run-id>/clarifying-questions.md`
   - `outputs/<run-id>/assumptions.md`
   - `outputs/<run-id>/run-log.yaml`

6. Enforce the clarification gate before generation:
   - Ask must-answer questions before creating PRD, metrics, tracking, user flow, prototype, review checklist, or final package when missing information materially changes:
     - Product goal
     - Target user
     - Scope
     - Platform
     - Existing product fit, affected modules, or relevant historical product decisions
     - Metrics
     - Tracking
     - Prototype direction
     - Payment, privacy, legal, compliance, security, or financial risk
   - If any must-answer question exists, write only the task brief, clarifying questions, assumption log, and run log, then stop and wait for the user's answer.
   - Do not treat user silence as approval to continue.
   - Do not label the same unknown as both `must answer before generation` and `can draft with stated assumption`.
   - Use three distinct buckets: `must answer before generation`, `can draft with stated assumption`, and `must confirm before development or launch`.

7. After the clarification gate passes, create or update:
   - `outputs/<run-id>/pm-package.md`
   - `outputs/<run-id>/prd.md`
   - `outputs/<run-id>/metrics-tree.md`
   - `outputs/<run-id>/tracking-plan.md`
   - `outputs/<run-id>/tracking-plan.csv`
   - `outputs/<run-id>/user-flow.mmd`
   - `outputs/<run-id>/user-flow.md`
   - `outputs/<run-id>/prototype-<platform>.html`
   - `outputs/<run-id>/review-checklist.md`
   - `outputs/<run-id>/final-package-summary.md`

8. Continue with assumptions only when:
   - The user explicitly says to proceed without answers, or
   - The unknown is clearly low-impact and listed as `can draft with stated assumption` or `must confirm before development or launch`.
   - Keep every unanswered must-answer question visible in the final package if the user explicitly accepts the risk.
   - Keep unanswered questions visible in the final package.

9. Choose prototype platform:
   - Web for desktop admin, SaaS, dashboards, tables, complex forms.
   - H5 for mobile web, landing pages, campaigns, lightweight checkout.
   - App for native mobile product flows.
   - Mini Program for mini-program containers, authorization, booking, ordering, and lightweight forms.
   - Generate multiple prototypes only for true cross-platform requirements.

10. Run validation after file changes when possible:
   - `python3 scripts/validate_repo.py`
   - HTML checks with `tidy` if available.

## Embedded Repository Mode

If PM Copilot is stored inside another software repository, do not assume nested `AGENTS.md` files are loaded by every tool.

Instead, the host repository should contain a tiny adapter instruction that says:

```text
For product-manager tasks such as PRD, requirements, tracking plans, prototypes, user flows, or competitor research, read `pm-copilot/PM_COPILOT.md` and follow it.
```

See `adapters/` for Codex, Claude Code, and Cursor examples.

When embedded, first identify the host project root and load only relevant host context before drafting. Typical sources include the host README, product docs, route definitions, API contracts, existing PRDs, analytics conventions, package metadata, and nearby UI or service modules. If there is no host project or the agent cannot determine the current product state, it must ask for available product documents or the minimum missing context before generating the full package.

## Output Style

Keep user-facing progress concise. Do not restate the entire workflow unless the user asks.

Final response should include:

- Scenario name
- Output folder
- Key artifacts created
- Open questions or launch blockers
- Validation result

## Guardrails

- Do not fabricate competitor sources.
- Do not claim a tool was used if it was not.
- Do not collect forbidden sensitive tracking properties.
- Do not hide assumptions.
- Do not present HTML prototypes as production code.
- Require human confirmation for payment, privacy, legal, compliance, financial, or security-sensitive decisions.
