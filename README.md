# PM Copilot

PM Copilot is an open-source, platform-neutral Agent Workflow Kit for product managers. It helps a PM turn an ambiguous product request into a review-ready package: clarified requirements, PRD, metrics, tracking plan, user flow, low-fidelity multi-platform prototype, review checklist, and final handoff summary.

The project is intentionally not a web app, CLI, or Figma plugin in v1. It is a reusable repository of agent definitions, skills, artifact contracts, workflow rules, guardrails, templates, and examples that can be adapted to agent environments such as Codex, Claude Code, Cursor, or internal agent platforms.

## What It Produces

- Clarifying questions and explicit assumptions
- PRD suitable for product, design, engineering, QA, and analytics review
- KPI tree and success metrics
- Tracking plan with events, properties, triggers, and validation notes
- Mermaid user flow
- Local low-fidelity HTML prototype for Web, H5, App, or Mini Program scenarios
- Review checklist and risk log
- Final package summary

## Quick Start

For direct agent usage, see `docs/direct-use.md`. For manual setup, see `docs/quick-start.md`.

1. Open this repository in your agent-enabled workspace.
2. Say your product-manager request naturally, for example: `I need a PRD and tracking plan for checkout coupon optimization.`
3. The agent should follow `PM_COPILOT.md`, inspect relevant context, ask must-answer clarification questions before generation, then create scenario files and outputs automatically.
4. Optional: create `context/product-context.local.yaml` later for better product-specific results.

Suggested prompt:

```text
We want to improve coupon usage on checkout. Users say they cannot find where to apply coupons, and support tickets are increasing.

If important information is missing, ask me first.
If enough information is available, create the full review-ready package.
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
Help me write the PRD, metrics tree, tracking plan, and prototype for team permission management.
```

For details and manual adapter snippets, see `docs/embedded-use.md`.

## Repository Structure

```text
PM_COPILOT.md  Canonical cross-platform PM Copilot entry
AGENTS.md      Thin Codex shim for standalone mode
adapters/      Host-project adapters for Codex, Claude Code, Cursor
agents/        Agent roles, responsibilities, inputs, outputs, handoffs
skills/        Reusable PM methods and task skills
context/       Product memory, user preferences, business rules, metrics
workflow/      State machine, human checkpoints, execution order
artifacts/     Output contracts and quality bars
tools/         Tool-use protocol and capability matrix
guardrails/    Safety, privacy, source, assumption, and failover rules
templates/     Reusable artifact templates
examples/      Input briefs and scenario setup
outputs/       Complete example outputs
evals/         Regression-oriented evaluation cases
docs/          User, maintainer, and release documentation
scripts/       Lightweight local validation
```

## Core Workflow

```text
Request intake
-> Current context and host project scan
-> Requirement clarification
-> User answer or explicit assumption approval
-> PRD
-> Metrics tree
-> Tracking plan
-> User flow
-> Multi-platform low-fidelity prototype
-> Review checklist
-> Final package
```

The default interaction mode is "clarify before generation." If must-answer information is missing, the agent should stop after creating the brief, clarifying questions, assumptions, and run log. It should continue only after the user answers or explicitly accepts assumption risk.

Each requirement run gets its own folder under `examples/<run-id>/` and `outputs/<run-id>/`. If the inferred scenario already exists, PM Copilot should append a local timestamp, for example `checkout-coupon-20260518-1430`.

PM Copilot follows the user's language for generated artifacts: Chinese requests should produce Chinese PM outputs, English requests should produce English PM outputs. File names and machine-readable identifiers stay ASCII.

## Platform-Neutral Design

PM Copilot avoids dependency on a specific agent framework. Each agent and skill is written as a portable Markdown contract:

- Agents define ownership, inputs, outputs, decision points, handoffs, and failover behavior.
- Skills define reusable procedures, standards, and artifact rules.
- Artifact contracts define required output shape and minimum quality.
- Guardrails define what the agent must not fabricate or silently assume.

## Included Scenarios

| Scenario | Platform | Purpose |
|---|---|---|
| `membership-auto-renewal` | H5 | Subscription renewal and payment recovery |
| `team-permissions` | Web | Admin/SaaS permission management |
| `content-save-app` | App | Native mobile content save and offline reading |
| `mini-program-booking` | Mini Program | Appointment booking with authorization and forms |

See `docs/scenario-library.md`.

## Documentation

- `docs/direct-use.md` - direct one-shot agent usage
- `docs/embedded-use.md` - using PM Copilot inside another development repository
- `docs/quick-start.md` - first run guide
- `docs/configuration.md` - product context configuration
- `docs/platform-guides.md` - Codex, Claude Code, Cursor, and internal platform usage
- `docs/prompt-recipes.md` - copy-paste prompts for common workflows
- `docs/quality-rubric.md` - manual scoring rubric for generated packages
- `docs/optimization-playbook.md` - real-task optimization loop
- `docs/failure-taxonomy.md` - failure classification and fix mapping
- `docs/scenario-library.md` - available examples and how to add more
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
