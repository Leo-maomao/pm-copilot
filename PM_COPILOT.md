# PM Copilot Entry

This is the canonical cross-platform entry for PM Copilot.

Use this file when an agent needs to run product manager work such as PRD, tracking plan, product requirements, prototype, competitor research, metrics, review checklist, or full product review package generation.

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
Agent: I will clarify the key unknowns first, then create the review package.
Agent: <asks high-impact questions or proceeds with assumptions>
Agent: <creates examples/<scenario>/ and outputs/<scenario>/>
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

2. Load product context:
   - Prefer `context/product-context.local.yaml` if it exists.
   - Otherwise use `context/product-context.example.yaml`.
   - If using the example context, tell the user it is a generic placeholder and ask only for missing context that materially affects the task.

3. Infer a scenario slug:
   - Use a short lowercase kebab-case name.
   - Example: `membership-renewal`, `checkout-coupon`, `team-permissions`.

4. Create or update:
   - `examples/<scenario>/task-brief.md`
   - `outputs/<scenario>/clarifying-questions.md`
   - `outputs/<scenario>/assumptions.md`
   - `outputs/<scenario>/prd.md`
   - `outputs/<scenario>/metrics-tree.md`
   - `outputs/<scenario>/tracking-plan.csv`
   - `outputs/<scenario>/user-flow.mmd`
   - `outputs/<scenario>/prototype-<platform>.html`
   - `outputs/<scenario>/review-checklist.md`
   - `outputs/<scenario>/final-package-summary.md`
   - `outputs/<scenario>/run-log.yaml`

5. Ask clarification questions before generation when missing information materially changes:
   - Product goal
   - Target user
   - Scope
   - Platform
   - Metrics
   - Tracking
   - Prototype direction
   - Payment, privacy, legal, compliance, security, or financial risk

6. If the user does not answer:
   - Continue only with explicit assumptions.
   - Keep unanswered questions visible in the final package.

7. Choose prototype platform:
   - Web for desktop admin, SaaS, dashboards, tables, complex forms.
   - H5 for mobile web, landing pages, campaigns, lightweight checkout.
   - App for native mobile product flows.
   - Mini Program for mini-program containers, authorization, booking, ordering, and lightweight forms.
   - Generate multiple prototypes only for true cross-platform requirements.

8. Run validation after file changes when possible:
   - `python3 scripts/validate_repo.py`
   - HTML checks with `tidy` if available.

## Embedded Repository Mode

If PM Copilot is stored inside another software repository, do not assume nested `AGENTS.md` files are loaded by every tool.

Instead, the host repository should contain a tiny adapter instruction that says:

```text
For product-manager tasks such as PRD, requirements, tracking plans, prototypes, user flows, or competitor research, read `pm-copilot/PM_COPILOT.md` and follow it.
```

See `adapters/` for Codex, Claude Code, and Cursor examples.

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
- Do not present low-fidelity HTML prototypes as production code.
- Require human confirmation for payment, privacy, legal, compliance, financial, or security-sensitive decisions.
