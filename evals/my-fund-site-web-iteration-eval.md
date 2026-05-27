# My Fund Site Web Iteration Eval

## Metadata

| Field | Value |
|---|---|
| Case ID | my-fund-site-web-iteration |
| Scenario | financial-tool-web-iteration-portfolio |
| Platform | Web |
| Product Area | Financial tool and portfolio workflows |
| Fixture Scope | Fixture-scoped |
| PM User Type | Data PM / AI product manager |
| Risk Profile | Privacy / Compliance / Data quality |
| Created | 2026-05-21 |
| Last Updated | 2026-05-26 |

## Fixture Isolation Terms

- `my-fund-site`
- `apps/my-fund-site`
- `fund-bff`
- `fund-api`

Use this eval when PM Copilot is validated inside `my-fund-site`, a Web financial-tool monorepo with:

- `apps/my-fund-site` as the only user frontend.
- `apps/fund-bff` as the only business API boundary.
- `apps/fund-api` as the public fund-data capability layer.
- Supabase for authentication, user business data, and RLS.

## Required Round Artifacts

Each Web evaluation round must create:

- `outputs/<run-id>/prd.md`
- A Web UI deliverable that is source-backed when `apps/my-fund-site` frontend source is present: record the preview route/story/demo or `source_delta_patch` files in `run-log.yaml`; use `outputs/<run-id>/prototype-web.html` only for explicit portable HTML or concrete source-rendering blockers
- `outputs/<run-id>/run-log.yaml`

Validation commands:

```bash
python3 scripts/validate_repo.py
python3 scripts/validate_outputs.py outputs/<run-id> --language zh
python3 scripts/run_delivery_checks.py outputs/<run-id> --language zh
```

If compatibility HTML is explicitly selected, `run_delivery_checks.py` runs the HTML parser checks and records optional `tidy` evidence when available. If source-backed preview files are selected, run the host dev/preview path and record equivalent browser or screenshot evidence under `visual_validation`.

## Rubric Thresholds

| Area | Minimum Score |
|---|---|
| Web platform and container fit | 5 / 5 |
| Financial risk boundary | 5 / 5 |
| Privacy and compliance handling | 5 / 5 |
| Source-backed UI delivery | 4 / 5 |
| Validation evidence | 5 / 5 |

## Failure History

| Date | Failure Code | Severity | Symptom | Fix |
|---|---|---|---|---|
| 2026-05-21 | platform-assumption-regression | High | Prior self-iteration could carry Mini Program assumptions into Web financial-tool scenarios. | Add Web-specific scenario portfolio and source-backed Web validation expectations. |

## Scenario Set

| Round | Scenario | Regression Risk | Expected Coverage |
|---|---|---|---|
| R61 | Fund detail page | Mini Program state assumptions reject Web outputs | Web validator accepts visitor/signed-in states and checks Web shell markers |
| R62 | Portfolio target allocation | Target/deviation becomes investment advice | Calculation source, stale data, disclaimer, and no buy/sell instruction |
| R63 | DIP plan reminder | Reminder implies automatic trading | Trading-day adjustment, missed reminder, quiet state, and non-execution boundary |
| R64 | Watchlist alerts | Analytics leaks thresholds or investment preference | Coarse alert properties and sensitive financial exclusions |
| R65 | Risk labels and drawdown | Risk labels become ratings | Algorithm window, missing data, explanation, and non-rating boundary |
| R66 | Portfolio CSV import | Raw file content leaks into artifacts or logs | Parse/preview/confirm/write separation and privacy-safe samples |
| R67 | Dividend/reinvestment records | New transaction types break calculations | Migration, backfill, calculation impact, and regression tests |
| R68 | Fund comparison | Comparison implies a recommended winner | Neutral ordering, methodology, fee/risk definitions, and disclaimer |
| R69 | Performance attribution | Attribution hides residual/missing data | Attribution window, denominator, residual bucket, and missing-data behavior |
| R70 | Public fund SEO pages | Indexable HTML leaks private data | Canonical, sitemap, robots/noindex, structured data, and public-data boundary |
| R71 | Notification center | Public announcements and private alerts mix | Source separation, read sync, priority, frequency cap, redaction |
| R72 | Data source status | Users over-trust stale market data | Freshness, cache/staleness, partial failure, degradation copy |
| R73 | Account export/delete | Privacy workflow treated as ordinary settings | Identity confirmation, export scope, retention/deletion, audit, compliance owner |
| R74 | Read-only portfolio share | Private financial data exposed through public link | Grant scope, snapshot/live choice, noindex/cache, redaction, expiry, revocation |
| R75 | Portfolio stress test | Simulation presented as prediction | Assumptions, historical window, limitations, extreme-case handling |
| R76 | Smart watchlist groups | Automatic grouping overwrites user intent | Explainable suggestions, manual priority, confirmation, undo |
| R77 | Extension watchlist sync | Extension treated as ordinary Web page | Manifest permissions, popup constraints, auth/session handoff, cache and logout |
| R78 | Mobile responsive portfolio | Mobile changes regress desktop or create mistaps | Breakpoints, touch targets, content priority, desktop parity |
| R79 | Market open/close banner | Availability message implies trading capability | Timezone, holidays, exceptional closure, data delay, informational boundary |
| R80 | BFF data contract readiness | Contract checks replace tests or approval | Breaking changes, fixtures, compatibility, real-test boundary, rollback |

## Pass Criteria

- Every scenario passes repository and output validation after fixes are applied.
- Web UI deliverables use the current `apps/my-fund-site` frontend source as the baseline when available, show a Web shell or proper extension container, include responsive/access states, and record the isolated preview/delta boundary.
- Financial content includes source, calculation, delay, disclaimer, and non-advice boundaries.
- Generated host `outputs/` folders are removed after PM Copilot improvements and eval knowledge are captured.
