# External Tooling

PM Copilot can use external tools, but external tools are not automatically trusted or enabled. The default project must remain useful with local files, local validation scripts, and agent-native browsing.

Use this file with:

- `agents/integration-governance-agent.md`
- `skills/tool-vetting/SKILL.md`
- `tools/external-tool-catalog.json`
- `scripts/preflight_integrations.py`

## Availability Definitions

| Status | Meaning |
|---|---|
| `candidate` | The tool is worth considering, but it is not proven configured for the current run. |
| `setup_required` | The tool needs install steps, an API key, OAuth consent, account access, browser setup, or workspace permissions. |
| `available` | The current runtime can use it with the needed credentials and permissions. |
| `blocked` | The tool cannot be used safely or reliably for the current task. |
| `hold` | Keep in the catalog for future review but do not recommend by default. |

## Default Policy

- Default-on tools must be local, open-source, or already supplied by the active agent runtime.
- Account-gated SaaS, commercial APIs, and OAuth integrations are optional even when they are high quality.
- Community MCP servers are candidates, not defaults, unless the user explicitly accepts the maintenance risk.
- Write-capable tools require explicit user approval for the concrete action.
- Analytics, database, CRM, ads, support, and workspace tools should start read-only.

## Cost And Account Classes

| Class | Meaning |
|---|---|
| `free_local` | Runs locally without a paid service. |
| `open_source_self_hostable` | Can be self-hosted, but may need infrastructure. |
| `byo_account` | Needs an existing account, token, OAuth client, or workspace permission. |
| `commercial_api` | Cloud API usage may require a paid plan or metered billing. |
| `unknown` | Pricing or access terms were not verified. Do not use as a default. |

## Required Vetting Record

Record this in `run-log.yaml.external_integrations` before using an external tool:

```yaml
external_integrations:
  - tool_id: ""
    decision: "" # approved | setup_required | rejected | blocked | not_applicable
    candidate_status: "" # candidate | setup_required | available | blocked | hold
    source_type: "" # official_docs | official_repo | community_repo | marketplace | unknown
    source_url: ""
    cost_risk: "" # free_local | open_source_self_hostable | byo_account | commercial_api | unknown
    credentials_required: []
    permission_boundary: "" # read_only | write_requires_approval | write_approved | not_applicable
    data_risk: ""
    command_or_runtime: ""
    fallback: ""
    approval_owner: ""
    limitation: ""
```

## Use Cases

- Design and prototype: Figma, browser validation, v0 or Stitch only when API/account access is confirmed.
- Product research: Firecrawl, Exa, Tavily, or browser tools only when API keys/network access are available; otherwise cite manual browsing sources.
- Product operations analysis: prefer local CSV/Sheets/Jupyter/DuckDB first; connect live analytics or databases only with read-only credentials.
- Collaboration systems: Notion, Jira, Linear, Slack, Google Workspace, and CRM tools must be scoped to the task and may not write without approval.
- Automation: n8n, Activepieces, Pipedream, and Zapier-like tools should be execution backplanes, not hidden defaults.
