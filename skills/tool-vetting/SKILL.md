---
name: tool-vetting
description: Use when evaluating external MCP servers, APIs, SaaS tools, automation connectors, or paid services before PM Copilot recommends or depends on them.
---

# Tool Vetting

## Goal

Prevent PM Copilot from relying on unavailable, unverified, unsafe, or unexpectedly paid tools. A tool is usable only when its source, setup path, authentication, cost risk, data access, permissions, and fallback are explicit.

## Workflow

1. Define the job the tool must do and whether the job is required or optional.
2. Check `tools/external-tool-catalog.json` first. If the tool is absent, treat it as unvetted until source verification is completed.
3. Prefer official providers and mature open-source projects. Community wrappers can be used only with a visible maintenance and fallback note.
4. Verify the source before recommending the tool: official docs, official repo, package page, or inspected community repo.
5. Classify runtime status separately from candidate quality: `candidate` means promising but not configured, `setup_required` means an install/API key/OAuth/account/browser/permission is missing, `available` means locally configured or supplied by the active agent runtime, and `blocked` means the source, credentials, permission scope, cost, or account risk makes it unusable.
6. Classify cost risk: `free_local`, `open_source_self_hostable`, `byo_account`, `commercial_api`, `unknown`, or `paid_only`.
7. Classify data risk: public-only, workspace documents, product analytics, production database, customer data, CRM/support data, advertising spend, or write-capable operations.
8. Require least-privilege credentials. Prefer read-only scopes for research, analytics, project-management, support, CRM, and production-data tools.
9. Do not enable write operations such as creating issues, sending Slack messages, changing CRM records, editing ads, publishing pages, or modifying production databases unless the user explicitly approves that action.
10. Run `python3 scripts/preflight_integrations.py` when a cataloged integration may be used. Use `--check-remote` when source availability itself is part of the decision.
11. Record the decision in `run-log.yaml.external_integrations`, including tool id, candidate status, configured status, credential requirement, cost risk, permission boundary, source URL, fallback, and approval owner.
12. If a tool is unavailable, continue only with a fallback that does not pretend the tool result exists.

## Output

- Tool decision summary
- Approved, setup-required, rejected, and blocked tools
- Credential and permission requirements
- Cost and account risk
- Fallback plan
- Run-log `external_integrations` entries

## Quality Bar

- No third-party tool is described as available until the runtime, credentials, and permissions are checked or supplied by the active agent environment.
- No paid or account-gated tool is part of the default path.
- No source-backed claim relies on a tool that was not actually accessed.
- Sensitive integrations default to read-only, aggregated, or synthetic data.
- The user can tell which tools are local/free, which need an API key, which may cost money, and which are only candidates.
