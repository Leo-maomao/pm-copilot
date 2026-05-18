# PM Copilot

PM Copilot is an open-source, platform-neutral Agent Workflow Kit for product managers. It helps a PM turn an ambiguous product request into two practical handoff artifacts: a complete PRD and a clickable annotated prototype.

The project is intentionally not a web app, CLI, or Figma plugin in v1. It is a reusable repository of agent definitions, skills, artifact contracts, workflow rules, guardrails, and templates that can be adapted to agent environments such as Codex, Claude Code, Cursor, or internal agent platforms.

PM Copilot supports three context modes: `repo-backed`, `document-backed`, and `brief-only`. The agent should choose the mode from available inputs before drafting, so it does not require a code repository when product documents or a short brief are the actual starting point.

## What It Produces

- `prd.md` suitable for product, design, engineering, QA, and analytics review
- Version history, requirement input, clarified answers, assumptions, and open confirmations inside the PRD
- Research and reference findings, including competitor, user, historical PRD, current implementation, or technical solution references when useful
- Requirement list and detailed requirement tables with logic, content, rules, interactions, data, permissions, edge states, tracking links, and acceptance links
- Goals, metrics, tracking plan, and flow diagrams inside the PRD
- Local clickable annotated HTML prototype for Web, H5, App, or Mini Program scenarios
- `run-log.yaml` as an internal trace when useful, not as the PM-facing deliverable

## Quick Start

For direct agent usage, see `docs/direct-use.md`. For embedded project usage, see `docs/embedded-use.md`.

1. Open this repository in your agent-enabled workspace.
2. Say your product-manager request naturally, for example: `I need a PRD and tracking plan for checkout coupon optimization.`
3. The agent should follow `PM_COPILOT.md`, inspect relevant context, ask must-answer clarification questions before generation, then create `prd.md` and a prototype automatically.
4. Optional: create `context/product-context.local.yaml` later for better product-specific results.

Suggested prompt:

```text
We want to improve coupon usage on checkout. Users say they cannot find where to apply coupons, and support tickets are increasing.

If important information is missing, ask me first.
If enough information is available, create `prd.md` and the matching clickable prototype.
```

## Use Inside an Existing Project

This is the expected setup when you want to import PM Copilot into a real software project:

```text
host-repo/
|-- AGENTS.md or CLAUDE.md or .cursor/rules/
|-- src/
`-- pm-copilot/
    `-- PM_COPILOT.md
```

Copy or clone this repository into the host project as `pm-copilot/`, then install a small adapter in the host repository root:

```bash
cd host-repo/pm-copilot
python3 scripts/install_adapter.py --host .. --tool all
```

The adapter is required for reliable embedded use. Simply placing the `pm-copilot/` folder inside another project does not guarantee that Codex, Claude Code, Cursor, or another agent will automatically discover nested instructions.

In embedded mode, PM Copilot should inspect the current host project before drafting. Existing routes, data models, UI patterns, permissions, analytics conventions, and docs should shape the new requirement; the agent should not assume a greenfield product unless you ask for one.

After the adapter is installed, users can ask natural PM requests from the host project without naming PM Copilot:

```text
Help me write the PRD and clickable prototype for team permission management.
```

For details and manual adapter snippets, see `docs/embedded-use.md`.

## Use Without a Code Repository

PMs do not need a software repository to use PM Copilot. If the product context lives in documents, place or attach the relevant files in the workspace and ask naturally.

Useful context can include:

- Historical PRDs, specs, and release notes
- Product docs, screenshots, wireframes, and prototype notes
- Research summaries, user feedback, support tickets, and meeting notes
- Analytics exports, KPI definitions, and existing tracking plans
- Business rules, compliance constraints, pricing notes, and rollout plans

PM Copilot should read those documents as the current product context, ask must-answer questions when the documents are insufficient, and then generate `prd.md` and the prototype after the clarification gate passes.

## Repository Structure

```text
PM_COPILOT.md  Canonical cross-platform PM Copilot entry
AGENTS.md      Thin Codex shim for directly opening this repository
adapters/      Host-project adapters for Codex, Claude Code, Cursor
agents/        Agent roles, responsibilities, inputs, outputs, handoffs
skills/        Reusable PM methods and task skills
context/       Product memory, user preferences, business rules, metrics
workflow/      State machine, human checkpoints, execution order
artifacts/     Output contracts and quality bars
tools/         Tool-use protocol and capability matrix
guardrails/    Safety, privacy, source, assumption, and failover rules
templates/     Reusable artifact templates
evals/         Regression-oriented evaluation cases
docs/          User, maintainer, and release documentation
scripts/       Lightweight local validation
```

## Core Workflow

```text
Request intake
-> Current product context scan
-> Requirement clarification
-> User answer or explicit assumption approval
-> PRD with goals, research, requirements, metrics, tracking, and flows
-> Multi-platform clickable prototype
-> Delivery check
```

The default interaction mode is "clarify before generation." If must-answer information is missing, the agent should ask and stop before creating PRD or prototype deliverables. It should continue only after the user answers or explicitly accepts assumption risk. PRD status, engineering handoff status, and launch status are separate: engineering-blocking confirmations prevent `Ready for engineering`, while launch-only blockers must remain visible with owner and required confirmation.

For reference, policy, medical, legal, financial, safety, or operational content, PM Copilot records source status, review owner, review status, disclaimer status, and launch impact. Unreviewed content must be labeled as placeholder or draft even when the surrounding product framework is ready for engineering.

Each real requirement run gets one generated-artifact folder under `outputs/<run-id>/`, normally containing `prd.md`, `prototype-<platform>.html`, and optionally `run-log.yaml`. The `outputs/` folder is generated at runtime and is not shipped with example artifacts. If the inferred run id already exists, PM Copilot should append a local timestamp, for example `checkout-coupon-20260518-1430`.

PM Copilot follows the user's language for generated artifacts: Chinese requests should produce Chinese headings, labels, statuses, notes, and PM content; English requests should produce English equivalents. File names and machine-readable identifiers stay ASCII.

## About AGENTS.md

`AGENTS.md` is included only because Codex treats it as a repository instruction file when this repository is opened directly. It is a thin shim that points Codex to `PM_COPILOT.md`.

For real embedded use, do not rely on the nested `pm-copilot/AGENTS.md`. Run `scripts/install_adapter.py` so the host project's own agent instruction file delegates PM work to `pm-copilot/PM_COPILOT.md`.

## Platform-Neutral Design

PM Copilot avoids dependency on a specific agent framework. Each agent and skill is written as a portable Markdown contract:

- Agents define ownership, inputs, outputs, decision points, handoffs, and failover behavior.
- Skills define reusable procedures, standards, and artifact rules.
- Artifact contracts define required output shape and minimum quality.
- Guardrails define what the agent must not fabricate or silently assume.

## Documentation

- `docs/direct-use.md` - direct one-shot agent usage
- `docs/embedded-use.md` - using PM Copilot inside another development repository
- `docs/configuration.md` - product context configuration
- `docs/quality-rubric.md` - manual scoring rubric for generated PRD/prototype deliveries
- `docs/optimization-playbook.md` - real-task optimization loop
- `docs/failure-taxonomy.md` - failure classification and fix mapping
- `docs/versioning.md` - versioning and compatibility policy
- `docs/release-checklist.md` - release readiness checklist
- `CONTRIBUTING.md` - contribution rules
- `SECURITY.md` - security and privacy policy
- `CHANGELOG.md` - detailed version history

## Embedded Install

When PM Copilot is nested inside another development repository, install a small adapter into the host project:

```bash
python3 scripts/install_adapter.py --host /path/to/host-repo --tool all
```

After that, users can ask natural PM requests without saying the project name.

## Validation

Run:

```bash
python3 scripts/validate_repo.py
```

The GitHub workflow in `.github/workflows/validate.yml` runs the same validator on pushes and pull requests.

## Optimization

PM Copilot should be improved through real task runs, traces, quality scoring, failure classification, and regression cases.

Start with:

- `docs/optimization-playbook.md`
- `docs/failure-taxonomy.md`
- `docs/quality-rubric.md`
- `templates/agent-run-log-template.yaml`
- `templates/evaluation-case-template.md`

## Privacy Default

Use local files by default. Do not paste sensitive production data, user personal data, private credentials, unreleased financials, or confidential partner details unless your environment is approved for that data. When real business context is needed, prefer anonymized examples and sampled metrics.

## License

MIT License. See `LICENSE`.
