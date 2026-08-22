# Security and Privacy

<p align="center"><a href="../../SECURITY.md">简体中文</a> | <strong>English</strong></p>

<a id="english"></a>

PM Copilot is local-first and does not include a cloud service, database, account system, or telemetry.
The current supported runtime is `6.2.4`; users control provider configuration, and credentials must not be written to artifacts.

## Supported Versions

| Version | Supported |
|---|---|
| 6.x | Supported |
| 5.x | Best-effort |

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
- Never present Agent calls, model responses, or validation results as evidence when they did not occur.
- Review and redact `outputs/` or `pm-copilot-outputs/` before committing because they may contain business context.
