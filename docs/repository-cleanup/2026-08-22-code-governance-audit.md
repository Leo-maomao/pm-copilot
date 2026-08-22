# Code Governance Audit

Date: 2026-08-22
Scope: repository-owned PM Copilot source, tests, tools, plugins, and routing

## Audit Findings

- `scripts/agent_runtime.py` and `scripts/run_evaluation_scenario.py` each
  owned copies of the adaptive model names and routing-policy identifier.
- Stable runtime contracts and test fixtures also contain intentional literals:
  artifact names, CLI flags, schema keys, protocol values, fixture paths, and
  the fixed PRD-manager port. These are not environment configuration.
- Environment/session-dependent selection is already discovered at runtime by
  `agent_runtime.py`; it must not be replaced with a static provider setting.
- The repository contains no byte-identical duplicate source files in the
  audited source roots. Low-reference scripts were not treated as dead code:
  they may be external CLI entry points or dynamically imported modules.
- The skill cleaner found four identical duplicate groups in external
  `~/.agents/skills` and `~/.codex/skills` roots (`sac`, `seawork`,
  `seawork-handoff`, `seawork-loop`). They are outside this repository and were
  not modified.

## Canonical Decisions

| Concern | Canonical owner | Decision |
|---|---|---|
| Standard stage model | `scripts/runtime_policy.py` | `STANDARD_MODEL` |
| Highest-judgment stage model | `scripts/runtime_policy.py` | `HIGH_JUDGMENT_MODEL` |
| Legacy model aliases | `scripts/runtime_policy.py` | Compatibility fallback only; normal routing uses `scripts/model_catalog.py` |
| Adaptive routing policy id | `scripts/runtime_policy.py` | `MODEL_ROUTING_POLICY` |
| Active provider/session | `scripts/agent_runtime.py` | Runtime discovery remains authoritative |
| PRD manager port | `scripts/prd_manager.py` | Fixed local tool contract; not deployment configuration |

## Applied Batch

- Added `scripts/runtime_policy.py`.
- Updated `agent_runtime.py` and `run_evaluation_scenario.py` to import the
  shared policy constants while preserving compatibility aliases.
- Added `scripts/test_runtime_policy.py` and removed duplicate literal
  assertions from existing tests.

The change does not alter CLI arguments, provider discovery, model selection,
fallback behavior, artifact paths, or error semantics.

## Applied Batch 2

- Added `scripts/portfolio_contract.py` as the canonical owner of evaluation
  plan hashing.
- Updated `run_evaluation_portfolio.py`, `audit_evaluation_portfolio.py`, and
  `canonicalize_evaluation_portfolio.py` to use the shared function.
- Added an order-stability regression test in `test_portfolio_contract.py`.

The portfolio digest algorithm and serialized output are unchanged; only the
ownership and test surface moved.

## Applied Batch 4

- Added `scripts/model_catalog.py` to read user/provider-declared models from
  `PM_COPILOT_MODEL_CATALOG`, `PM_COPILOT_MODELS`, active runtime context, and
  Codex provider configuration.
- Updated stage routing and Agent Runtime dispatch to select by declared
  `standard`/`judgment` capability, record `selected`/`degraded`/`blocked`,
  and stop when no model is available.
- Removed automatic Sol/Terra selection and the automatic Seawork Sol fallback;
  legacy IDs remain only as compatibility constants and test fixtures.
- Added model catalog regression coverage and configuration documentation.

## Applied Batch 3

- Added `scripts/runtime_limits.py` as the canonical owner for operational
  defaults repeated across runtime entry points.
- Updated direct execution, interactive requests, evaluation scenarios, and
  evaluation portfolios to import those defaults without changing values or
  override behavior.
- Preserved distinct revision budgets because their workflow safety semantics
  differ; the distinction is now named and regression-tested.
- Added `docs/repository-cleanup/2026-08-22-hardcoded-values-inventory.md` as
  the classification record for remaining literals and deferred families.

## Applied Batch 3

- Added `scripts/runtime_limits.py` as the canonical owner for operational
  defaults repeated across runtime entry points.
- Updated direct execution, interactive requests, evaluation scenarios, and
  evaluation portfolios to import those defaults without changing values or
  override behavior.
- Preserved distinct revision budgets because their workflow safety semantics
  differ; the distinction is now named and regression-tested.
- Added `docs/repository-cleanup/2026-08-22-hardcoded-values-inventory.md` as
  the classification record for remaining literals and deferred families.

## Deferred Items

- Timeout values, retry budgets, and worker limits have different safety
  semantics by operation; they require a separate contract-level decision and
  are not blindly merged.
- External duplicate skills require runtime-owner confirmation before removal.
- Static search alone cannot prove a script is unused; no source entry point was
  deleted without dynamic-import/CLI evidence.

## Validation

- Targeted runtime-policy, Agent runtime, and adaptive-routing tests passed.
- `py_compile` passed for all changed Python modules.
- Targeted portfolio tests and `python3 -m py_compile scripts/*.py` passed.
- Full repository validation remains required after the next governance batch.
