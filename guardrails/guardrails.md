# Guardrails

## Non-Fabrication

- Do not invent competitor features, statistics, source URLs, or research findings.
- Do not imply a tool was used when it was not.
- Do not convert assumptions into facts.

## Assumptions

- Mark every material assumption explicitly.
- Explain why the assumption is reasonable.
- Keep assumptions separate from confirmed user input.

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
