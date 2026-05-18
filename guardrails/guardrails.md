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
- Do not continue from clarification into PRD, metrics, tracking, flow, prototype, review, or final packaging until must-answer questions are answered or the user explicitly accepts assumption risk.
- User silence is not consent to proceed with material assumptions.

## Existing Product Fit

- Treat available current product context as source material. This can come from a host repository, historical PRDs, specs, product docs, screenshots, analytics exports, support tickets, meeting notes, or direct user answers.
- Do not require a software repository when product documents provide enough context.
- Do not invent a greenfield product architecture, flow, taxonomy, or data model when the current product context already defines one.
- If the current product state is unclear and it affects scope or feasibility, ask before generation.
- Separate observed current-state facts from inferred product intent.

## Privacy and Sensitive Data

Require human confirmation before processing or generating details involving:

- Personal data
- Payment information
- Financial projections
- Legal, compliance, or regulatory obligations
- Security controls
- Confidential partner or customer information

Never request or store raw passwords, full payment card numbers, government IDs, or unnecessary personal identifiers.

## Product Safety

- Include guardrail metrics for changes that may increase complaints, refunds, churn, or operational load.
- Flag dark-pattern risks in subscription, payment, cancellation, and notification flows.
- Use clear user-facing copy for consent, billing, renewal, and cancellation states.

## Prototype Boundary

- HTML prototypes are review artifacts, not production code.
- Do not claim implementation feasibility without engineering review.
- Do not include real credentials, real payment details, or production endpoints.
