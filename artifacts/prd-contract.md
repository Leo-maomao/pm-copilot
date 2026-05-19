# PRD Contract

Use this contract when generating or reviewing `outputs/<run-id>/prd.md`.

The PRD is the primary product-manager handoff artifact. It contains the requirement, research, goals, requirement details, tracking plan, flow diagrams when useful, prototype reference, risks, open confirmations, acceptance criteria, and validation results.

## Required Output

The following outline defines semantic sections, not literal English headings. Localize human-facing headings and table labels into the user's language.

```markdown
# <localized feature name> PRD

## <localized version history>
## <localized requirement input and confirmation record>
## <localized readiness summary>
## <localized background>
## <localized research and reference findings>
## <localized project goals and metrics>
## <localized requirement scope>
## <localized surface and permission states>
## <localized content source and review status>
## <localized requirement list>
## <localized requirement details>
## <localized flow diagrams>
## <localized tracking plan>
## <localized prototype reference>
## <localized risks and open confirmations>
## <localized acceptance criteria>
## <localized delivery review findings>
## <localized validation results>
```

## Requirement Details

`Requirement details` must be detailed enough for design, engineering, QA, and analytics to work from. For each functional item, include the relevant subset of:

| Field | Purpose |
|---|---|
| Function ID | Stable ID such as `F1` |
| Function name | Concrete capability being delivered |
| User scenario | Who uses it and in what situation |
| Entry point / trigger | Where the user starts or what system event starts it |
| Page / content requirements | Copy, fields, states, and content source requirements |
| Business logic | Conditions, branches, limits, priority, and decision rules |
| Interaction rules | Tap, hover, long-press, disabled, loading, success, and failure behavior |
| Data rules | Source, save, refresh, sorting, dedupe, and retention behavior |
| Permission rules | Who can view, operate, or be blocked |
| Edge states | Empty, error, no permission, offline, rollback, and fallback behavior |
| Tracking links | Related event IDs |
| Acceptance links | Related acceptance criteria IDs |

For cross-module, search, feed, dashboard, or aggregation features, add source-by-source rows or a companion matrix covering source module, source permission rule, result redaction rule, ranking/sorting assumption, partial-failure behavior, and performance boundary. A single generic data rule is not enough when different sources have different permissions, privacy levels, or failure modes.

For algorithmic labels, scores, rankings, risk bands, recommendations, or simulation outputs, include source data, calculation window, refresh cadence, missing-data behavior, explanation copy, reviewer/approval owner, and user-facing limitations. Do not allow an unexplained score or label to imply a recommendation, rating, or guaranteed outcome.

For simulations, forecasts, stress tests, or scenario analysis, include assumptions, historical data window, scenario inputs, confidence/limitation language, extreme-case handling, and an explicit statement that the result is not a prediction or investment instruction.

For public Web or SEO surfaces, include indexability, canonical URL, sitemap/robots behavior, metadata/structured-data requirements, cache behavior, public-data boundary, and proof that signed-in or private user data cannot appear in indexable HTML.

For data freshness, source-status, health, or reliability indicators, include source owner, refresh cadence, cache/staleness rule, partial-failure behavior, stale-data display, user-facing trust copy, and what actions remain enabled or disabled while data is degraded.

## Repo-Backed Engineering Map

For repo-backed product changes, include a localized engineering implementation map in the PRD. It should name likely routes, pages, services, components, data/config files, analytics integration points, permission boundaries, and validation entry points. This is not production code, but it must be specific enough for engineering to estimate and plan the change.

## Rules

- Use tables for version history, confirmations, goals, scope, requirement list, requirement details, tracking, risks, and acceptance criteria when there are multiple items.
- Put competitor research, user research, historical PRD findings, screenshots, existing implementation findings, and technical solution references under `Research and reference findings`.
- Keep project goals and metrics near the top so the rest of the PRD can be judged against them.
- Include PRD status, engineering handoff status, and launch status as separate readiness fields.
- Keep confirmed MVP scope separate from optional, conditional, future scope, and non-goals.
- Do not put unconfirmed optional capabilities into MVP requirements or acceptance criteria.
- Specify entry point, navigation visibility, permission or eligibility states, and fallback behavior for existing-product surfaces.
- For aggregation features, specify per-source permissions, redaction, empty-result behavior, partial failure behavior, and performance limits.
- For algorithmic labels or scores, specify explainability, missing-data handling, and the boundary between calculation output and product recommendation.
- For simulations or forecasts, specify assumptions and limitations prominently enough for reviewers to see them in both PRD and prototype.
- For SEO or public Web pages, specify index/noindex rules, metadata ownership, structured data, and private-data exclusion.
- For data reliability surfaces, specify freshness, staleness, partial failure, and degradation behavior in user-visible terms.
- For reference, policy, medical, legal, financial, safety, or operational content, record source status, review owner, review status, disclaimer status, and launch impact.
- Put tracking events and property definitions in the PRD by default; create a CSV export only when useful.
- Put functional or operation flow diagrams in the PRD when they help review; create Mermaid source exports only when useful.
- Prototype details belong in the HTML prototype. The PRD should only link the prototype, summarize covered screens/states, and state that page-level logic and interaction notes live in the prototype annotations.
- Prototype references in the PRD should point to local generated files. Do not require reviewers to load external assets, scripts, or remote prototype URLs unless the user explicitly requests that workflow.
- Mark assumptions explicitly.
- Do not bury unresolved decisions in the requirements.
- Include structured delivery review findings with artifact, evidence, owner, required-before phase, and status.
- Localize headings and table labels into the user's language. Keep requirement IDs, event names, property names, and other machine-readable identifiers ASCII.
