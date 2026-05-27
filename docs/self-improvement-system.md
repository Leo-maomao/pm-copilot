# Self-Improvement System

PM Copilot should improve by evidence, not iteration count. The operating loop is:

1. Run realistic product tasks end to end.
2. Preserve generated artifacts, run logs, delivery checks, and visual evidence.
3. Score the result against `docs/quality-rubric.md`.
4. Classify defects with `docs/failure-taxonomy.md`.
5. Fix the smallest responsible surface.
6. Turn each serious failure into an eval case.
7. Re-run failed cases plus previously passing cases.

Self-iteration is for PM Copilot's agent capability, not for the reference project used in a run. A host project is only a pressure fixture. Durable improvements must be phrased as general product-agent capabilities that help product managers across domains.

Use this command to see the current improvement state:

```bash
python3 scripts/agent_improvement_scorecard.py
```

Use JSON output for automation:

```bash
python3 scripts/agent_improvement_scorecard.py --json --report outputs/improvement-scorecard.json
```

The scorecard is expected to surface portfolio gaps. A passing run from a borrowed host project proves source-backed execution for that fixture; it does not prove broad PM-agent quality until non-fixture, document-backed, brief-only, and screenshot-backed cases also pass.

## Capability Areas

The scorecard tracks eval and runtime evidence across these areas:

- `context_intake`: repo-backed, document-backed, brief-only, host-source, and uploaded-context handling.
- `clarification_control`: must-answer questions, default-option mode, and pre-generation stop behavior.
- `prd_reasoning`: scope, non-goals, acceptance criteria, status separation, and assumptions.
- `metrics_tracking`: metrics, analytics, events, property quality, and privacy-safe instrumentation.
- `ui_delivery`: source-backed preview, platform fidelity, visual evidence, and annotation quality.
- `risk_readiness`: legal, privacy, security, payment, compliance, launch, and blocker handling.
- `tool_validation`: preflight, output validation, delivery checks, visual checks, and source preview validation.
- `handoff_execution`: engineering handoff, rollout, rollback, dev tasks, and launch decisions.
- `skill_governance`: canonical skill ownership, external absorption, duplicate prevention, and tool candidate gating.

## Scenario Portfolio

Use varied PM work, not one favorite host product, to choose the next iteration. A healthy portfolio should rotate across:

- Context modes: repo-backed, document-backed, brief-only, screenshot-backed, and mixed context.
- Product types: consumer, B2B SaaS, marketplace, internal operations, creator tools, content/reference products, commerce, payments, onboarding, analytics, and admin systems.
- PM tasks: discovery, PRD, metrics, tracking, UI delivery, research, experiment design, launch readiness, engineering handoff, and post-launch review.
- Risk profiles: normal UX, payment, privacy, security, legal/compliance, regulated content, operational failure, and data-quality risk.
- Platforms: Web, H5, App, Mini Program, and cross-platform.
- User maturity: novice PM, AI product manager, senior PM, growth PM, data PM, ops PM, and founder/operator.
- Edge-case pressures: regulated or safety-critical requests, ambiguous or conflicting input, sensitive-data handling, launch/bypass pressure, missing/non-repo context, and source-fidelity pressure.

Reference projects can appear in runtime evidence or fixture-scoped eval cases, but not in PM Copilot's generic docs, prompts, templates, tools, agents, skills, workflow, or default examples.

## Iteration Selection

Choose the next improvement by the highest product-agent leverage:

1. A repeated high-severity failure.
2. A missing validator that allowed bad output to pass.
3. A capability area with weak or stale eval evidence.
4. A scenario class missing from the portfolio.
5. A workflow step that requires human discipline but can become a tool or contract.
6. A host-project defect that generalizes to many repo-backed products.

## What Counts As Progress

Progress is not more files or longer prompts. Progress means:

- More real runs pass delivery checks with fewer high-severity review findings.
- More eval cases have recent non-pending results.
- Capability gaps shrink across the scorecard areas.
- Scenario portfolio gaps shrink across PM user types, platforms, context modes, and risk profiles.
- Failures move from repeated runtime surprises into explicit evals or validators.
- Fixes become smaller because the responsible surface is clear.

## Anti-Patterns

- Counting iteration rounds without score deltas.
- Adding broad prompt rules before classifying the failure.
- Optimizing demo readability while runtime evidence is missing.
- Treating a passed repository validator as proof of product-agent quality.
- Keeping serious failures only in conversation history instead of evals or validators.
- Letting a reference project's domain, route names, local paths, API vocabulary, or business assumptions leak into PM Copilot's universal surface.
