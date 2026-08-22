# Hardcoded Values Inventory

Date: 2026-08-22
Scope: repository-owned source, tests, tools, templates, and runtime documents.

## Classification

| Classification | Examples | Decision |
|---|---|---|
| Code-owned policy | Execution timeout, revision budgets, worker limits, loop budgets, SeaWork restart acknowledgement | Canonicalized in `scripts/runtime_limits.py`; workflow-specific values remain distinct and tested |
| User/provider model capability | Model IDs and `standard`/`judgment` capabilities | Discovered by `scripts/model_catalog.py`; legacy Sol/Terra IDs are compatibility-only and never automatic choices |
| Stable protocol contract | Artifact names, CLI flags, schema keys, provider names, trace states, Mermaid identifiers | Keep in code/contracts; changing these would change interoperability |
| Project configuration | Product context, user preferences, decision log, external tool catalog | Keep in `context/` or `tools/`; load through existing project/config resolution |
| Environment/session input | Active provider, executable, workspace, credentials, host runtime | Discover at runtime; do not replace with static values |
| User input | Request text, answers, explicit model/provider/timeout overrides, output folder | Keep as CLI/API input and persist in the run trace where applicable |
| Test-only fixture | Synthetic requests, temporary paths, short timeouts, expected protocol literals | Keep local to tests; never use as production defaults |
| Visual/network validator defaults | Viewports, wait intervals, navigation timeout, diff/nonblank thresholds, preflight timeout | Deferred: different tools have different evidence and safety semantics |
| Local tool contract | PRD manager port `57391` | Keep fixed; it is a local tool protocol, not deployment configuration |

## Applied Governance

- Model names and adaptive routing are canonical in `scripts/runtime_policy.py`.
- Portfolio plan hashing is canonical in `scripts/portfolio_contract.py`.
- Operational defaults are canonical in `scripts/runtime_limits.py`.
- Existing default behavior is preserved: 15-minute execution, interactive/evaluation/portfolio revision budgets of 3/2/1, one default worker, three-case Codex cap, 30-minute loop, two loop iterations, and 90-second SeaWork restart acknowledgement.

## Deferred Items

Visual/network wait and threshold values require tool-specific contract review;
they are not interchangeable merely because they are numeric. Process-level
polling values in `agent_runtime.py` likewise remain local implementation
budgets until their failure semantics are reviewed together.

Concrete deferred values found during the repository scan:

| Owner | Values | Classification/reason |
|---|---|---|
| `scripts/agent_runtime.py` | `FIRST_ARTIFACT_SECONDS=30`, process waits `2/8/15/30` seconds, control-plane failure limit `2` | Runtime safety/watchdog budgets with different failure meanings |
| `scripts/validate_ui_preview.py` | wait `500ms`, navigation `15000ms`, nonblank ratio `0.01`, viewports `1440x1000` and `390x844` | Validator-specific evidence thresholds and fixture-like viewport contracts |
| `scripts/validate_prototype_visual.py` | launch `15000ms`, wait `300ms`, diff/nonblank ratio `0.01`, same viewports | Visual QA contract; must be reviewed with screenshot acceptance rules |
| `scripts/extract_ui_region.py` | wait `500ms`, navigation `15000ms`, web platform, `1440x1000` viewport | Browser extraction defaults; not interchangeable with visual validator defaults without evidence |
| `scripts/preflight_tools.py` | network timeout `3.0s` | Local preflight responsiveness budget |
| `scripts/preflight_integrations.py` | remote check timeout `4.0s` | Integration availability probe budget |
| `scripts/validate_outputs.py` | validator subprocess timeout `10s`, review score threshold `15/20` | Artifact contract and quality rubric values |
| `scripts/inspect_host_frontend.py` | inventory limit `30` | Output-size bound for discovery, not runtime execution policy |
| `scripts/run_agent_delegation.py` | max attempts `2` | Delegation retry budget; requires agent-control-plane review |
| `scripts/prd_manager.py` | local port `57391` | Fixed local tool protocol |

Static literal search cannot prove that a low-reference CLI script is unused,
so no entry point was removed on that basis.

## Validation Evidence

Run `python3 -m unittest discover -s scripts -p 'test_*.py'`,
`python3 scripts/validate_runtime_routing.py`, `python3 scripts/validate_repo.py`,
`python3 -m py_compile scripts/*.py`, and `git diff --check` after changes.
