# PM Copilot

<h2 align="center"><a href="https://github.com/Leo-maomao/pm-copilot#zh-cn">简体中文</a> | English</h2>

<a id="english"></a>

PM Copilot is an open-source, platform-neutral Agent Workflow Kit for product managers. It helps a PM turn an ambiguous product request into two practical handoff artifacts: a complete PRD and a clickable annotated prototype.

中文简介：PM Copilot 是面向产品经理的开源 AI Agent 工作流套件，支持生成 PRD、需求文档、埋点方案、可点击标注原型、研发交接和上线决策材料。

The project is intentionally not a web app, CLI, or Figma plugin. It is a reusable repository of agent definitions, skills, prompt rules, memory rules, artifact contracts, workflow rules, guardrails, and templates that can be adapted to agent environments such as Codex, Claude Code, Cursor, or internal agent platforms.

PM Copilot supports three context modes: `repo-backed`, `document-backed`, and `brief-only`. The agent should choose the mode from available inputs before drafting, so it does not require a code repository when product documents or a short brief are the actual starting point.

## Language Support

PM Copilot treats English and Chinese as first-class user-facing languages. Generated PM artifacts, prototype labels, annotations, review findings, readiness statuses, and validation notes should follow the user's language with the same workflow, artifact set, and quality bar. File names, event names, property names, requirement IDs, and other machine-readable identifiers stay ASCII for portability.

## What It Produces

- `prd.md` suitable for product, design, engineering, QA, and analytics review
- Version history, requirement input, clarified answers, assumptions, and open confirmations inside the PRD
- Research and reference findings, including competitor, user, historical PRD, current implementation, or technical solution references when useful
- Requirement list and detailed requirement tables with logic, content, rules, interactions, data, permissions, edge states, tracking links, and acceptance links
- Goals, metrics, tracking plan, and flow diagrams inside the PRD
- Local clickable annotated HTML prototype for Web, H5, App, or Mini Program scenarios
- `run-log.yaml` as an internal trace when useful, not as the PM-facing deliverable
- Tool preflight, delivery orchestration, HTML parsing, browser screenshots, and optional visual diff validation for HTML prototypes; missing Playwright/browser tooling should trigger setup before any skipped status is recorded
- Optional `dev-tasks.yaml` and `launch-decision.yaml` for controlled engineering handoff and release decision support

## Quick Start

For direct agent usage, see `docs/direct-use.md`. For embedded project usage, see `docs/embedded-use.md`.

1. Open this repository in your agent-enabled workspace.
2. Ask the agent to read `PM_COPILOT.md`, then say your product-manager request naturally, for example: `I need a PRD and tracking plan for checkout coupon optimization.`
3. The agent should inspect relevant context, ask must-answer clarification questions before generation, then create `prd.md` and a prototype automatically.
4. Optional: create local memory files later for better product-specific results and personal working preferences.

Suggested prompt:

```text
We want to improve coupon usage on checkout. Users say they cannot find where to apply coupons, and support tickets are increasing.

If important information is missing, ask me first.
If enough information is available, create `prd.md` and the matching clickable prototype.
```

## Two Practical Demos

Paste either request into an agent-enabled workspace. PM Copilot should classify the context mode first, ask blocking questions when required, and generate the PRD, clickable prototype, and optional handoff artifacts only after the clarification gate passes.

### Demo 1: Team Permission Management in an Existing Project

Use this to show that PM Copilot does more than write generic docs: it should inspect the current repository and fit the requirement into existing routes, role models, permission logic, and UI patterns.

![Team permission management demo screenshot](docs/assets/readme-demo-team-permissions.png)

```text
We need team permission management in the admin console.

Please inspect the existing routes, role model, member management page, permission checks, and component patterns first.
If important information is missing, ask me before generation.
If enough information is available, create the PRD, a Web clickable annotated prototype, and issue-ready engineering tasks.
```

A useful run should produce:

| Artifact | What to look for |
|---|---|
| `outputs/team-permissions/prd.md` | Target users, current-product constraints, MVP/optional/future scope, member invites, role changes, permission blocking, audit logs, loading/empty/error/no-permission states |
| `outputs/team-permissions/prototype-web.html` | Admin member list, invite drawer, role-change confirmation, permission notice, numbered product annotations |
| `outputs/team-permissions/dev-tasks.yaml` | Issue-ready engineering tasks, dependencies, acceptance criteria, test notes |
| `outputs/team-permissions/run-log.yaml` | Host project files loaded, assumptions used, blockers, validation commands and results |

This demo highlights `repo-backed` context loading, Chinese or English PRDs, Web prototypes, tracking design, engineering handoff, and permission/edge-state coverage.

### Demo 2: Checkout Coupon Optimization Without a Code Repository

Use this to show that PM Copilot can start from a brief or product documents, without requiring a code repository, and still produce review-ready product work.

![Checkout coupon optimization demo screenshot](docs/assets/readme-demo-checkout-coupon.png)

```text
We want to improve the H5 checkout coupon experience. Users say they cannot find the coupon entry, and support tickets are increasing.

The business goal is to increase coupon usage without materially hurting payment conversion.
If you need existing rules, coupon types, unavailable reasons, or metric definitions, ask me first.
When enough information is available, create the PRD, H5 clickable annotated prototype, and tracking plan.
```

A useful run should produce:

| Artifact | What to look for |
|---|---|
| `outputs/checkout-coupon/prd.md` | User problem, business goals, metric definitions, coupon entry, usable/unusable coupons, default recommendation, error states, launch risks, acceptance criteria |
| `outputs/checkout-coupon/prototype-h5.html` | Checkout entry, coupon list sheet, unavailable reasons, price refresh after selection, mobile annotations |
| Tracking table inside the PRD | Events such as `checkout_coupon_entry_view`, `coupon_select_submit`, `coupon_apply_result`, plus a property dictionary |
| `outputs/checkout-coupon/run-log.yaml` | Clarifying questions, default assumptions, unresolved promotion/finance/legal risks, validation records |

This demo highlights `document-backed` or `brief-only` mode, localized delivery, mobile prototypes, metrics and tracking, and explicit promotion-rule risk handling.

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
adapters/      Host-project adapters for Codex, Claude Code, Cursor
agents/        Agent roles, responsibilities, inputs, outputs, handoffs
skills/        Reusable PM methods and task skills
prompts/       Prompt assembly, memory use, clarification, and generation rules
context/       Product memory, user preferences, decisions, business rules, metrics
workflow/      State machine, human checkpoints, execution order
artifacts/     Output contracts and quality bars
tools/         Tool registry, tool-use protocol, and capability-specific tooling notes
guardrails/    Safety, privacy, source, assumption, and failover rules
templates/     Reusable artifact templates
evals/         Regression-oriented evaluation cases
docs/          User, maintainer, and release documentation
scripts/       Lightweight local validation
```

## Core Workflow

```text
Request intake
-> Tool preflight
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

When UI prototypes are generated, PM Copilot should run `python3 scripts/validate_prototype_visual.py outputs/<run-id>`. If Playwright or browser tooling is missing, it should first run or guide `python3 scripts/setup_visual_validation.py`; a skipped status is allowed only after setup fails, the environment forbids browser launch, or the user declines installation. Before final delivery, prefer `python3 scripts/run_delivery_checks.py outputs/<run-id> --language en` and store tool evidence under `outputs/<run-id>/tool-results/`. When the user asks for engineering handoff or release readiness, the same run folder may also contain `dev-tasks.yaml` and `launch-decision.yaml`.

PM Copilot follows the user's language for generated artifacts: Chinese requests should produce Chinese headings, labels, statuses, notes, and PM content; English requests should produce English equivalents. File names and machine-readable identifiers stay ASCII.

## Memory

PM Copilot uses local file-based memory so repeated use can become smoother without a hosted service:

- `context/product-memory.local.yaml` for stable product facts
- `context/user-preferences.local.yaml` for the user's working style
- `context/decision-log.local.yaml` for durable product decisions
- `outputs/<run-id>/run-log.yaml` for single-run traces
- `outputs/<run-id>/tool-results/delivery-check-report.json` for delivery-orchestrator tool evidence
- `outputs/<run-id>/visual-review/visual-report.json` for prototype screenshot and visual diff evidence after setup succeeds
- `outputs/<run-id>/dev-tasks.yaml` for issue-ready engineering handoff when requested
- `outputs/<run-id>/launch-decision.yaml` for launch decision support when requested

The repository ships `.example.yaml` schemas only. `.local.yaml` memory files are ignored by Git and should stay private. Current user instructions and current product context always override memory.

## Platform-Neutral Design

PM Copilot avoids dependency on a specific agent framework. Each agent and skill is written as a portable Markdown contract:

- Agents define ownership, inputs, outputs, decision points, handoffs, and failover behavior.
- Skills define reusable procedures, standards, and artifact rules.
- Prompt rules define request classification, memory use, clarification behavior, and generation boundaries.
- Artifact contracts define required output shape and minimum quality.
- Guardrails define what the agent must not fabricate or silently assume.

## Documentation

- `README.md` - Chinese README
- `docs/direct-use.md` - direct one-shot agent usage
- `docs/embedded-use.md` - using PM Copilot inside another development repository
- `docs/configuration.md` - product context configuration
- `docs/quality-rubric.md` - manual scoring rubric for generated PRD/prototype deliveries
- `docs/optimization-playbook.md` - real-task optimization loop
- `docs/failure-taxonomy.md` - failure classification and fix mapping
- `docs/versioning.md` - versioning and compatibility policy
- `docs/release-checklist.md` - release readiness checklist
- `tools/tool-registry.yaml` - tool capability registry
- `artifacts/tool-result-contract.md` - tool result contract
- `CONTRIBUTING.md` - contribution rules
- `SECURITY.md` - security and privacy policy
- `CHANGELOG.md` - detailed version history

## Feedback and Contributions

Use GitHub issues to share real usage feedback:

- Bug reports: `.github/ISSUE_TEMPLATE/bug_report.md`
- Feature requests: `.github/ISSUE_TEMPLATE/feature_request.md`
- Scenario requests: `.github/ISSUE_TEMPLATE/scenario_request.md`

Synthetic or anonymized product context is preferred. Do not post private product data, credentials, unreleased financials, or real user data in public issues.

## Embedded Install

When PM Copilot is nested inside another development repository, install a small adapter into the host project:

```bash
python3 scripts/install_adapter.py --host /path/to/host-repo --tool all
```

After that, users can ask natural PM requests without saying the project name.

## Validation

Run:

```bash
python3 scripts/preflight_tools.py --strict
python3 scripts/validate_repo.py
```

The GitHub workflow in `.github/workflows/validate.yml` runs the same validator on pushes and pull requests.

To validate a generated output folder during a PM Copilot run:

```bash
python3 scripts/run_delivery_checks.py outputs/<run-id> --language en
python3 scripts/validate_outputs.py outputs/<run-id> --language en
```

If delivery depends on external research or source checks, run `python3 scripts/preflight_tools.py --check-network <url> --require-network --strict`. When `--prototype` is omitted, `validate_prototype_visual.py` validates every supported prototype file in the run folder.

## Optimization

PM Copilot should be improved through real task runs, traces, quality scoring, failure classification, and regression cases.

Start with:

- `docs/optimization-playbook.md`
- `docs/failure-taxonomy.md`
- `docs/quality-rubric.md`
- `templates/agent-run-log-template.yaml`
- `templates/dev-tasks-template.yaml`
- `templates/launch-decision-template.yaml`
- `templates/evaluation-case-template.md`

## Privacy Default

Use local files by default. Do not paste sensitive production data, user personal data, private credentials, unreleased financials, or confidential partner details unless your environment is approved for that data. When real business context is needed, prefer anonymized examples and sampled metrics.

## License

MIT License. See `LICENSE`.
