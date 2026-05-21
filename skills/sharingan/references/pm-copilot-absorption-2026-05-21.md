# PM Copilot Absorption Record - 2026-05-21

## Decision

`Adapt`

The external skill and tool material is useful, but PM Copilot should absorb it by strengthening existing canonical skills, not by copying many sibling skills from third-party repositories.

## Source Snapshot

- `sickn33/antigravity-awesome-skills`
  - Resource type: curated skill index and community skill catalog.
  - Inspected material: `skills_index.json`, including product analytics, A/B test, market research, competitor intelligence, and tool-builder themes.
  - Reuse stance: idea extraction only. Do not bulk-import catalog entries.
  - Limitation: catalog entries vary in risk and quality; treat each referenced skill as untrusted until inspected directly.

- `alirezarezvani/claude-skills`
  - Resource type: skill repository with product-team and business-operations skill families.
  - Inspected material: product discovery, experiment designer, roadmap communicator, competitive teardown, product analytics, UI design system, knowledge ops, and process mapper themes.
  - Reuse stance: rewrite into PM Copilot-native workflows and quality bars. Do not copy scripts, templates, long prose, or source-specific persona framing without separate license and safety review.
  - Limitation: several source skills depend on scripts and references that were not absorbed in this pass.

- `alchaincyf/huashu-design`
  - Resource type: design skill.
  - Inspected material: HTML-as-design-medium pattern, source-first asset protocol, existing-context-first workflow, and browser validation habit.
  - Reuse stance: absorb the design review discipline into `design-system-audit` and PM Copilot prototype rules. Do not copy style prompts or broad design-authority assumptions.
  - Limitation: concrete design-generation providers still require tool vetting before use.

- External tool candidates in `tools/external-tool-catalog.json`
  - Resource type: official and community MCP/API/tool candidates.
  - Inspected material: source URL, source type, cost risk, credentials, data risk, permission boundary, fallback, and candidate status.
  - Reuse stance: catalog as candidates only. Runtime use requires preflight and approval where credentials, OAuth, billing, workspace data, or writes are involved.

## Canonical Skill Mapping

| Capability type | Canonical PM Copilot skill | Absorbed external themes |
|---|---|---|
| Opportunity validation | `skills/opportunity-discovery/SKILL.md` | product discovery, assumption mapping, opportunity tree, validation decision rules |
| Feedback synthesis | `skills/feedback-synthesis/SKILL.md` | interview synthesis, support-ticket clustering, review mining, bias notes |
| Experiment design | `skills/experiment-design/SKILL.md` | A/B tests, fake-door tests, beta cohorts, primary metric and guardrail discipline |
| Competitor research | `skills/competitor-research/SKILL.md` | competitive teardown, pricing comparison, onboarding flow review, battlecard inputs |
| Roadmap communication | `skills/roadmap-communication/SKILL.md` | now-next-later, release notes, stakeholder update framing |
| Knowledge operations | `skills/knowledge-ops/SKILL.md` | SOP/runbook/KB hygiene, 5W2H completeness, owner/review metadata |
| Process mapping | `skills/process-mapping/SKILL.md` | handoffs, cycle time, wait/rework, bottleneck analysis |
| Design system audit | `skills/design-system-audit/SKILL.md` | token extraction, component consistency, accessibility, visual evidence |
| Product ops analysis | `skills/product-ops-analysis/SKILL.md` | funnel, retention, cohort, dashboard, support signal, data-quality limits |
| Tool governance | `skills/tool-vetting/SKILL.md` | official-source preference, candidate/runtime split, cost/data/permission fallback |
| Resource absorption | `skills/sharingan/SKILL.md` | risk gate, duplicate-skill prevention, rejected-material recording |

## Rejected Material

- Bulk-importing large third-party skill catalogs.
- Creating a separate `competitive-teardown` skill after `competitor-research` already owned that capability type.
- Copying third-party prose, scripts, templates, or source references wholesale.
- Running third-party setup commands or tool servers during absorption.
- Treating GitHub stars, curated-list inclusion, or source URL reachability as runtime tool availability.
- Treating SaaS, OAuth, API-key, paid, or write-capable tools as default-on.
- Importing source-specific persona language, hype labels, or one-off examples that do not generalize to PM Copilot.

## Validation

- Repository validation must pass after absorption changes.
- External integration preflight must distinguish `available`, `candidate`, `setup_required`, `blocked`, and `hold`.
- `--require-ready` must fail when a required integration is only `candidate`, `hold`, `setup_required`, `unavailable`, or `blocked`.
- A realistic absorption run should strengthen a canonical skill or add a reference/script to it, not create a duplicate skill folder.

## Remaining Work

- Consider adding deterministic helper scripts only where the task is repeated and fragile, such as experiment sample-size estimation, KB/runbook checks, process-cycle calculations, or design-token extraction.
- Keep evaluating whether each helper belongs in an existing canonical skill before adding it.
