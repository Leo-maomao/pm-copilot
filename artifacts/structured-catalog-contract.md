# Structured Reference Contract

Use this contract when the requested deliverable is primarily a structured document, reference, or table artifact rather than a product requirement or user-facing product flow. Typical examples include model integration matrices, API capability catalogs, vendor comparison tables, parameter dictionaries, migration inventories, data dictionaries, feature flags, payment rules, risk rules, SOPs, runbooks, and engineering reference lists.

The default file remains `outputs/<run-id>/catalog.md` for backward compatibility. `outputs/<run-id>/reference.md` is also valid when the run is a broader document-reference handoff. Generate `outputs/<run-id>/catalog.html`, `outputs/<run-id>/reference.html`, or a `document_prototype` compatibility HTML only when the user asks for HTML, a browser-readable review artifact, or a richer document review view.

## Required Metadata

Markdown reference files must start with YAML frontmatter:

```yaml
---
artifact_type: structured_catalog # or structured_reference
catalog_type: ""
language: ""
source_status: "" # source_backed | user_supplied | mixed | draft | blocked
review_status: "" # unreviewed | pm_reviewed | engineering_reviewed | approved | blocked
owner: ""
last_updated: ""
---
```

HTML reference files must include:

```html
<meta name="pm-copilot-artifact" content="structured_catalog">
```

Document prototype HTML must instead include:

```html
<meta name="pm-copilot-artifact" content="document_prototype">
```

## Required Sections

`catalog.md` must include these semantic sections. Localize human-facing headings, but keep the machine field names visible in code formatting.

- Catalog summary: what is being cataloged, target audience, intended use, and what is out of scope.
- Source and review status: source URLs or documents, access date, source owner, review owner, review status, and freshness limits.
- Field dictionary: every table column, type, allowed values, source, required/optional status, and implementation meaning.
- Catalog table: one row per item and stable IDs.
- Engineering handoff notes: integration implications, blockers, required decisions, validation or test expectations, and version/deprecation notes.
- Validation results: exact command results or explicit not-run reason.

For `structured_reference` or document prototype runs, also include:

- Structured source facts: extracted facts before PM decisions, with source and confidence.
- Product decisions: final PM/product-approved position, including overrides of source defaults.
- Attention points: document-specific points reviewers must notice.
- Change log: object-level changes across multi-turn calibration.
- Completeness check: object count, field coverage, defaults, enums, limits, sources, pending confirmations, and conflicts.

## Required Catalog Columns

Every structured catalog table must include the following machine-readable columns, even when the visible label is localized:

- `item_id`
- `display_name`
- `source_status`
- `review_status`
- `owner`
- `access_date`
- `implementation_notes`

For model-integration catalogs, also include:

- `provider`
- `model_id`
- `version_or_release`
- `input_modalities`
- `output_modalities`
- `context_window`
- `required_parameters`
- `optional_parameters`
- `rate_limits`
- `pricing_source`
- `deprecation_status`

## Structured Reference Schema

When a request is broader than a flat table, maintain one structured source of truth before rendering Markdown or HTML. The run log or working reference may use this shape:

```yaml
structured_reference:
  catalog_type: "" # parameter_reference | capability_catalog | rule_reference | data_dictionary | migration_inventory | sop_runbook | vendor_matrix | other
  primary_artifact: ""
  html_artifact: ""
  source_status: ""
  review_status: ""
  owner: ""
  entities:
    - entity_id: ""
      display_name: ""
      entity_type: "" # model | api | rule | policy | data_object | sop_step | vendor | other
      source_status: ""
      review_status: ""
      owner: ""
      fields:
        - field_id: ""
          name: ""
          type: ""
          required: null
          default: ""
          enum: []
          limits: []
          children: []
          conditions: []
          source_facts: []
          product_decisions: []
          attention_points: []
  rules: []
  decisions: []
  attention_points: []
  change_log: []
  completeness_check:
    entity_count: 0
    fields_checked: []
    defaults_checked: []
    enums_checked: []
    limits_checked: []
    sources_checked: []
    pending_confirmations: []
    conflicts: []
```

Use object-level patching for multi-turn calibration. If a user updates one entity, only that entity's fields, rules, decisions, attention points, and change log entries should change unless the user explicitly asks for a global rewrite.

Use presentation-only mode when the user asks to change layout, HTML styling, expansion, ordering, or readability without changing content. In that mode, the structured reference data must not change.

## Attention Points

Document artifacts should not copy UI annotation behavior blindly. Traditional UI annotations explain product logic and interaction. Document attention points explain information quality, decisions, and delivery risk. Supported attention types are:

- `source_gap`: missing, stale, unofficial, or unverifiable source.
- `pm_override`: product decision overrides vendor/source/default behavior.
- `conflict`: source, user, or previous-round statements conflict.
- `engineering_must_read`: implementation-critical parameter, compatibility, or integration note.
- `launch_blocker`: confirmation required before release.
- `cost_or_quota_risk`: pricing, quota, rate-limit, or operational cost risk.
- `security_or_compliance`: permission, privacy, safety, or compliance risk.
- `change_marker`: key addition, deletion, or modification in the current turn.

Each attention point must include a `target_ref` that points to a document, entity, field, rule, or decision. Do not add generic notes that cannot change a reviewer or engineer's behavior.

## Rules

- Do not invent parameters, limits, pricing, region support, availability, or deprecation status.
- For fast-changing catalog content such as AI models, APIs, pricing, policies, quota limits, SDK versions, or regions, use current official or user-supplied sources. If current sources are unavailable, mark rows as `source_status: blocked` or `source_status: draft` and keep launch or engineering decisions blocked.
- Preserve uncertainty per row. Do not hide unknown values behind blank cells; use `Unknown`, `Not supplied`, `Not applicable`, or `Needs owner confirmation`.
- Separate model/provider facts from PM Copilot recommendations. The catalog can include implementation notes, but it must not imply legal, privacy, security, cost, or launch approval.
- Parameter names, event names, model IDs, API fields, and enum values should stay ASCII and copy-paste-safe.
- HTML catalogs and document prototypes must be self-contained. Do not load external scripts, fonts, stylesheets, images, or CDNs.
- Markdown, HTML, and run-log summaries must be rendered from the same structured reference data or checked for object/field/count consistency before delivery.
- Do not force PRD generation when the user explicitly asks for a structured reference or document prototype and says no PRD is needed.
- Document prototype HTML must provide document-specific attention points through badges, inline markers, change highlights, source/risk summaries, or filters. It does not need UI `annotation-marker` controls unless the artifact is also a user-facing product UI.

## Quality Bar

- Engineering can use the catalog without rereading the conversation.
- Every row has source and review status.
- Every important unknown has an owner or required confirmation.
- Fast-changing facts have access dates and source freshness limitations.
- The output distinguishes reference facts from implementation recommendations.
- Attention points are specific, typed, and target a concrete object, field, rule, or decision.
- Multi-turn changes are object-level and traceable.
