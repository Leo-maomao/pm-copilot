# Guardrails

## Non-Fabrication

- Do not invent competitor features, statistics, source URLs, or research findings.
- Do not imply a tool was used when it was not.
- Do not convert assumptions into facts.

## Assumptions

- Mark every material assumption explicitly.
- Explain why the assumption is reasonable.
- Keep assumptions separate from confirmed user input.
- Do not use assumptions to bypass a must-answer question.
- Do not continue from clarification into PRD, metrics, tracking, flow, UI delivery, review, or final packaging until must-answer questions are answered or the user explicitly accepts assumption risk.
- Do not produce a `Ready for engineering` PRD/UI delivery while engineering-blocking confirmation items remain unanswered. Ask first, or downgrade to `Draft with confirmation risk` only when the user explicitly asks to proceed.
- Do not hide launch blockers behind an engineering-ready label. If launch-only confirmations remain, mark launch as blocked and list the owner and required confirmation.
- User silence is not consent to proceed with material assumptions.
- Default-option or evaluation mode may choose conservative working assumptions for a test round, but it is not consent for launch-sensitive, regulated, privacy, legal, payment, security, financial, or compliance decisions. Keep those approvals open unless the user explicitly confirms them.

## Existing Product Fit

- Treat available current product context as source material. This can come from a host repository, historical PRDs, specs, product docs, screenshots, analytics exports, support tickets, meeting notes, or direct user answers.
- Do not require a software repository when product documents provide enough context.
- Do not invent a greenfield product architecture, flow, taxonomy, or data model when the current product context already defines one.
- If the current product state is unclear and it affects scope or feasibility, ask before generation.
- Separate observed current-state facts from inferred product intent.

## Privacy and Sensitive Data

PM Copilot is local-first. The repository does not include cloud storage, authentication, telemetry, or a hosted data service.

Require human confirmation before processing or generating details involving:

- Personal data
- Payment information
- Financial projections
- Legal, compliance, or regulatory obligations
- Security controls
- Confidential partner or customer information

Never request or store raw passwords, full payment card numbers, government IDs, or unnecessary personal identifiers.

Prefer synthetic, anonymized, sampled, or aggregated data. Do not commit real customer names, emails, phone numbers, payment details, partner secrets, private product strategy, or unreleased financial details to a public fork.

Tracking plans must include privacy notes. Prefer aggregated metrics over raw user-level data, and use placeholder values in public examples or generated drafts unless the user explicitly provides approved data.

Account export, account deletion, data erasure, privacy settings, and retention changes are privacy/compliance-sensitive. Require identity confirmation, export scope, retention/deletion timing, cancellation or recovery window where applicable, audit/log expectation, and explicit legal/compliance owner before launch.

## Access Control

- Treat role templates, permission presets, private sharing, family membership, invite approval, and audit visibility as security-sensitive product changes.
- Do not let a recommended default grant sensitive read, write, export, delete, invite, or admin capabilities. Default to least privilege and require an explicit owner confirmation before broader access is accepted.
- Front-end hiding, labels, filters, or privacy modes are presentation safeguards only. PRDs and UI deliverables must still name the server-side or policy boundary that enforces access.
- Privacy modes, masked amounts, hidden cards, and redacted previews must be described as display-layer safeguards. Include restore behavior, screenshot/shoulder-surfing limits, local setting persistence, and the fact that underlying data access permissions are unchanged unless the server policy changes.
- Temporary access or private sharing must be modeled as explicit grants with scope, recipient, expiry, revocation, reuse/one-time behavior, forwarding/export limits, and audit expectation. Do not describe private sharing as a front-end link or view toggle unless a server-side grant enforces it.
- Public links, share pages, and read-only snapshots that expose private or financial context must also specify noindex/cache policy, redaction level, expiry, revocation, access logging expectation, and whether the page is a live view or immutable snapshot.
- Permission-changing flows should include confirmation, rollback or recovery path, and audit/log expectation when the host product supports it.

## Reference and Regulated Content

- For reference, policy, medical, legal, financial, safety, or operational content, record the content source, review owner, review status, disclaimer status, and launch impact.
- Label unreviewed content as placeholder or draft in PRDs, annotations, run logs, and UI deliverables when the user or reviewer must see it. Do not scatter visible "example/demo/not production" labels across product UI as a generic safety substitute.
- Do not present unreviewed content as approved final copy, advice, policy, or launch-ready guidance.
- Do not use a recommended default to approve reference or regulated content. Defaults may choose a placeholder framework only; final content approval remains human-owned.
- A content payload can block launch while the surrounding product framework remains ready for engineering only when the PRD states that split explicitly.

## Product Safety

- Include guardrail metrics for changes that may increase complaints, refunds, churn, or operational load.
- Flag dark-pattern risks in subscription, payment, cancellation, and notification flows.
- Use clear user-facing copy for consent, billing, renewal, and cancellation states.
- For parsed, inferred, auto-filled, or AI-assisted input, require an explicit review/confirm step before writing shared, financial, private, or permissioned records. The PRD should cover edit, cancel, low-confidence, retry, and failure states.
- For automatic suggestions, smart grouping, inferred labels, or recommendation-adjacent organization, keep the suggestion explainable and reversible. User-authored organization takes priority unless the user explicitly accepts the change.
- For financial tools, distinguish recordkeeping, education, explanation, and simulation from advice, recommendation, automated trading, or guaranteed outcomes. Target allocations, deviation alerts, risk labels, ranking, comparison, and stress tests must include calculation assumptions, data-delay notes, and a human-reviewed disclaimer before launch.
- For uploaded or imported files, do not copy raw private content into PRDs, run logs, analytics events, screenshots, or public examples. Use schemas, sampled synthetic rows, validation summaries, and explicit retention/deletion rules instead.

## UI Delivery Boundary

- Standalone HTML compatibility artifacts are review artifacts, not production code.
- Source-backed preview/delta files are isolated UI delivery artifacts by default; treat them as production implementation only when the user explicitly requests implementation-oriented work and the host mutation policy records that boundary.
- Do not claim implementation feasibility without engineering review.
- Do not include real credentials, real payment details, or production endpoints.
