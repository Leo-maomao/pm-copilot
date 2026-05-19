# Security and Privacy

PM Copilot is local-first and does not include a cloud service, database, account system, or telemetry.

## Supported Versions

| Version | Supported |
|---|---|
| 2.x | Best-effort |
| 1.x | Best-effort |

## Reporting Issues

For now, report security or privacy issues through the repository issue tracker or maintainer contact listed by the project owner.

## Sensitive Data Rules

Do not commit:

- Real passwords or API keys
- Full payment card numbers
- Government IDs
- Raw personal identifiers
- Confidential partner agreements
- Private customer data
- Unreleased financial data

## Agent Safety Expectations

Agents using this repository should:

- Warn before processing sensitive data.
- Use synthetic or anonymized examples by default.
- Avoid collecting unnecessary personal properties in tracking plans.
- Mark assumptions and tool limitations clearly.
- Never fabricate source-backed claims.
