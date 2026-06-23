# PRD Contract

Use this contract when generating or reviewing `outputs/<run-id>/prd.md`.

The PRD is the primary product-manager handoff artifact. It contains the requirement, external product research, goals, requirement details, tracking plan, flow diagrams when useful, UI delivery reference, risks, open confirmations, acceptance criteria, and validation results.

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
## <localized implementation evidence and coverage map>
## <localized requirement list>
## <localized requirement details>
## <localized flow diagrams>
## <localized tracking plan>
## <localized UI delivery reference>
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

For AI assistants, automations, admin exports, workflow agents, or tool-enabled features, include trusted trigger, untrusted input boundary, tool allowlist/denylist, data scope, mutation permissions, redaction, audit logging, abuse tests, and human approval gates.

For accessibility-critical surfaces such as checkout, payment, account recovery, public service, support, consent, or cancellation flows, include visible labels, accessible names, keyboard/focus behavior, screen-reader expectations, error recovery, consent/price clarity, localization, and non-dark-pattern guardrails.

## Repo-Backed Engineering Map

For repo-backed product changes, include a localized engineering implementation map in the PRD. It should name likely routes, pages, services, components, data/config files, analytics integration points, permission boundaries, and validation entry points. This is not production code, but it must be specific enough for engineering to estimate and plan the change.

## Implemented Feature Evidence

When the PRD is reconstructed from an implemented branch or current diff, include a localized implementation evidence and coverage map. This section must separate observed implementation behavior from inferred product intent.

Include the relevant subset of:

| Field | Purpose |
|---|---|
| Evidence ID | Stable ID such as `EV1` |
| Source | Branch, diff, file path, screenshot, asset, test, or user-provided note |
| Observed behavior | What the implementation proves |
| Related requirement IDs | Requirement or function IDs supported by this evidence |
| Coverage status | Covered, partial, unverified, or conflict |
| Gap or risk | Product intent, rollout, metric, permission, copy, or launch gap still requiring confirmation |

If the implementation includes UI screenshots or image placeholders, place them inline at the related requirement detail, operation step, or evidence row. Do not put them into a separate image appendix unless the user explicitly asks for a screenshot inventory.

Screenshot coverage should be page-level rather than micro-state inflated: every independent changed page, window, panel, or dialog must be represented, but states that are visible together in one window should stay in one screenshot or placeholder.

For Chinese implemented-feature PRDs, missing screenshots must use only the exact inline block:

```markdown
> 占位图：文件上传-上传中.png
> 用途：展示文件上传过程中的进度、按钮状态和不可重复提交规则。
```

State screenshots must be named with the screenshot object plus the concrete state, such as `文件上传-上传中.png`, `文件上传-上传失败.png`, or `目标文件夹弹窗-非法目标.png`; do not use generic names such as `文件上传-状态.png` or `asset-upload-state.png`.

In Chinese PRDs, missing screenshots are called `占位图`; do not use labels such as `待补真实图`.

The PRD must be complete enough to review without manually inspecting the branch. Any behavior visible in the diff should either be represented in scope, requirement details, acceptance criteria, or risks, or explicitly excluded with rationale.

## Rules

- Use tables for version history, confirmations, goals, scope, requirement list, requirement details, tracking, risks, and acceptance criteria when there are multiple items.
- Put source-backed competitor, benchmark, comparable feature, user research, public product docs, screenshots, and technical solution references under `Research and reference findings`.
- For common product flows, include a competitor/comparable flow table that names the product, entry point, required input, primary path, fallback path, platform difference, observed fact, and implication. Generic policy, security, or implementation references are supporting evidence, not a substitute.
- Do not use repository file reading as the only content in `Research and reference findings`. Repo facts are current-product context and should appear in background, current-state notes, product-fit decisions, or the repo-backed engineering map.
- If external research is skipped or degraded, the research section must say why, identify the confidence impact, and avoid claiming a market-informed recommendation.
- Keep project goals and metrics near the top so the rest of the PRD can be judged against them.
- Include PRD status, engineering handoff status, and launch status as separate readiness fields.
- Keep confirmed MVP scope separate from optional, conditional, future scope, and non-goals.
- Do not put unconfirmed optional capabilities into MVP requirements or acceptance criteria.
- Specify entry point, navigation visibility, permission or eligibility states, and fallback behavior for existing-product surfaces.
- For aggregation features, specify per-source permissions, redaction, empty-result behavior, partial failure behavior, and performance limits.
- For algorithmic labels or scores, specify explainability, missing-data handling, and the boundary between calculation output and product recommendation.
- For simulations or forecasts, specify assumptions and limitations prominently enough for reviewers to see them in both PRD and UI deliverable.
- For SEO or public Web pages, specify index/noindex rules, metadata ownership, structured data, and private-data exclusion.
- For data reliability surfaces, specify freshness, staleness, partial failure, and degradation behavior in user-visible terms.
- For reference, policy, medical, legal, financial, tax, public-benefit, safety, or operational content, record source status, source currentness, review owner, review status, disclaimer status, and launch impact. If current authoritative sources are missing, keep launch blocked and do not present definitive guidance.
- For AI/tool-enabled features, do not treat untrusted content as user instruction or tool permission. Permission-sensitive actions must have owner-approved boundaries and abuse tests.
- Put tracking events and property definitions in the PRD by default; create a CSV export only when useful.
- Put functional or operation flow diagrams in the PRD when they help review; use Mermaid `flowchart` blocks as the primary diagram format and create Mermaid source exports only when useful. Do not replace the primary flow with a Markdown table or PNG.
- Put newly added or changed UI copy in the copy/i18n section as pure text that a product manager can copy for localization submission. If there is no new copy, state that explicitly.
- For implemented-feature PRD delivery, inspect current branch evidence before asking clarification questions that the code can answer. Use the evidence map to prove coverage and call out implementation/product-intent gaps.
- When `prd.html` is generated from `prd.md`, render it as a normal readable document with optional table of contents, reading-position TOC sync, full-width content flow, complete readable tables, rendered Mermaid diagrams through local assets, and inline images/placeholders at their relevant positions. Do not use `prototype-<platform>.html` naming for PRD document HTML.
- Images in PRD Markdown or HTML must appear where the reader needs them. If real screenshots are missing, insert an inline placeholder in that exact position and describe what should replace it. Do not create a detached screenshot list by default.
- PRD Markdown should contain exactly one top-level title. PRD HTML must not create a second visible document title or leave a large unused content column.
- For implemented-feature PRD HTML, prefer `scripts/render_prd_html.py`, which sets `pagetitle`, preserves the Markdown H1 as the single body title, keeps wide content readable, and enables an image lightbox.
- UI delivery details belong in the UI artifact and its annotations. The PRD should only link the source-backed preview/delta or compatibility HTML file, summarize covered screens/states, and state that page-level logic and interaction notes live in the UI delivery annotations.
- UI delivery references in the PRD should point to local generated files or local host preview surfaces. Do not require reviewers to load external assets, scripts, or remote UI preview URLs unless the user explicitly requests that workflow.
- Mark assumptions explicitly.
- Do not bury unresolved decisions in the requirements.
- Include structured delivery review findings with artifact, evidence, owner, required-before phase, and status.
- Localize headings and table labels into the user's language. Keep requirement IDs, event names, property names, and other machine-readable identifiers ASCII.
