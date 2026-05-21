# Configuration Guide

The main configuration file is:

```text
context/product-context.example.yaml
```

Copy it to a local file before editing:

```text
context/product-context.local.yaml
```

Do not commit private product context to a public repository.

PM Copilot also supports local memory files:

```text
context/product-memory.example.yaml
context/user-preferences.example.yaml
context/decision-log.example.yaml
```

Copy them to `.local.yaml` files when you want PM Copilot to remember stable product facts, your working preferences, and durable decisions across runs. `.local.yaml` files are ignored by Git.

## Required Fields

| Field | Required | Purpose |
|---|---|---|
| `product.name` | Yes | Product name used in artifact titles and assumptions |
| `product.category` | Yes | Helps agents choose product patterns |
| `product.platforms` | Yes | Helps Prototype Agent choose Web, H5, App, or Mini Program |
| `users.primary_segments` | Yes | Grounds scenarios and user stories |
| `business_goals.north_star_metric` | Yes | Grounds metrics and PRD goals |
| `prd_preferences.default_style` | Yes | Controls output depth |
| `tracking_taxonomy.event_name_case` | Yes | Controls event naming |
| `privacy.default_mode` | Yes | Controls sensitive data handling |

## Product

```yaml
product:
  name: "Example Product"
  category: "Consumer internet product"
  platforms:
    - "Web"
    - "H5"
    - "App"
    - "Mini Program"
  business_model:
    - "Subscription"
```

Use this section to describe what the product is and where users experience it.

Platform guidance:

- Web: desktop or responsive browser product
- H5: mobile web page opened from links, notifications, or campaigns
- App: native mobile app flow
- Mini Program: mini-program container with authorization and lightweight tasks

## Users

```yaml
users:
  primary_segments:
    - name: "Paying users"
      goals:
        - "Use premium benefits with low friction"
      pain_points:
        - "Renewal and payment details are hard to find"
```

Keep each segment specific enough for scenario writing. Avoid adding every possible user type.

## Business Goals

```yaml
business_goals:
  north_star_metric: "Weekly active paying users"
  current_focus:
    - "Improve subscription retention"
  guardrail_metrics:
    - "Refund rate"
```

Guardrail metrics are important for preventing harmful optimizations.

## PRD Preferences

```yaml
prd_preferences:
  default_style: "Review-ready"
  audience:
    - "Product"
    - "Design"
    - "Engineering"
    - "QA"
    - "Analytics"
```

Use `Review-ready` when the output should be suitable for cross-functional review.

## Tracking Taxonomy

```yaml
tracking_taxonomy:
  event_name_case: "snake_case"
  property_name_case: "snake_case"
  required_event_fields:
    - "event_name"
    - "user_id"
    - "platform"
    - "timestamp"
```

Use this section to enforce event naming and property rules.

Forbidden properties should include fields that agents must not collect:

```yaml
forbidden_properties:
  - "raw_password"
  - "full_payment_card"
  - "government_id"
```

## Competitors

```yaml
competitors:
  known:
    - name: "Competitor A"
      url: "https://example.com"
      notes: "Replace with a real competitor."
  research_policy: "Use source-backed claims only."
```

If research tools are unavailable, agents must not fabricate competitor facts.

## Prototype Preferences

```yaml
prototype_preferences:
  fidelity: "Low"
  default_output: "Local HTML"
  repo_backed_ui_mode: "Isolated HTML from host code"
  host_mutation_policy: "Read-only unless implementation is explicitly requested"
  repo_backed_layers: "baseline_layer restores original UI; delta_layer contains new feature markers and dialogs"
  platform_selection: "Choose based on scenario; generate multiple only for cross-platform needs."
```

The default prototype mode produces local HTML prototypes instead of production code. In repo-backed UI work, the local HTML should be generated from inspected host frontend code, assets, styles, and state patterns while keeping host production files unchanged unless the user explicitly requests implementation.

## Privacy

```yaml
privacy:
  default_mode: "Local-first"
  sensitive_data_policy: "Use anonymized or synthetic data unless the environment is approved."
```

Use anonymized data in public examples.

## External Integrations

External tools are optional candidates, not default dependencies. Review:

```text
tools/external-tooling.md
tools/external-tool-catalog.json
```

Run:

```bash
python3 scripts/preflight_integrations.py --tier recommended
```

Use `--check-remote` when source availability matters. Use `--require-ready` only when an integration is required for the run; `candidate`, `hold`, `setup_required`, `unavailable`, and `blocked` are not ready states. Missing API keys, OAuth consent, paid accounts, workspace permissions, or production-data credentials should remain `setup_required` or `blocked` until the user explicitly configures and approves them.

## Good Configuration Habits

- Keep product context concise.
- Prefer stable product facts over temporary campaign details.
- Keep task-specific assumptions in the task folder, not long-term context.
- Do not commit private context to public repositories.
