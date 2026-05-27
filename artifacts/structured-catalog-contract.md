# Structured Catalog Contract

Use this contract when the requested deliverable is primarily a structured text or table artifact rather than a product requirement or UI flow. Typical examples include model integration matrices, API capability catalogs, vendor comparison tables, parameter dictionaries, migration inventories, data dictionaries, feature flags, and engineering reference lists.

The default file is `outputs/<run-id>/catalog.md`. Generate `outputs/<run-id>/catalog.html` only when the user asks for an HTML handoff, a browser-readable review artifact, or a richer table view.

## Required Metadata

`catalog.md` must start with YAML frontmatter:

```yaml
---
artifact_type: structured_catalog
catalog_type: ""
language: ""
source_status: "" # source_backed | user_supplied | mixed | draft | blocked
review_status: "" # unreviewed | pm_reviewed | engineering_reviewed | approved | blocked
owner: ""
last_updated: ""
---
```

`catalog.html` must include:

```html
<meta name="pm-copilot-artifact" content="structured_catalog">
```

## Required Sections

`catalog.md` must include these semantic sections. Localize human-facing headings, but keep the machine field names visible in code formatting.

- Catalog summary: what is being cataloged, target audience, intended use, and what is out of scope.
- Source and review status: source URLs or documents, access date, source owner, review owner, review status, and freshness limits.
- Field dictionary: every table column, type, allowed values, source, required/optional status, and implementation meaning.
- Catalog table: one row per item and stable IDs.
- Engineering handoff notes: integration implications, blockers, required decisions, validation or test expectations, and version/deprecation notes.
- Validation results: exact command results or explicit not-run reason.

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

## Rules

- Do not invent parameters, limits, pricing, region support, availability, or deprecation status.
- For fast-changing catalog content such as AI models, APIs, pricing, policies, quota limits, SDK versions, or regions, use current official or user-supplied sources. If current sources are unavailable, mark rows as `source_status: blocked` or `source_status: draft` and keep launch or engineering decisions blocked.
- Preserve uncertainty per row. Do not hide unknown values behind blank cells; use `Unknown`, `Not supplied`, `Not applicable`, or `Needs owner confirmation`.
- Separate model/provider facts from PM Copilot recommendations. The catalog can include implementation notes, but it must not imply legal, privacy, security, cost, or launch approval.
- Parameter names, event names, model IDs, API fields, and enum values should stay ASCII and copy-paste-safe.
- HTML catalogs must be self-contained. Do not load external scripts, fonts, stylesheets, images, or CDNs.

## Quality Bar

- Engineering can use the catalog without rereading the conversation.
- Every row has source and review status.
- Every important unknown has an owner or required confirmation.
- Fast-changing facts have access dates and source freshness limitations.
- The output distinguishes reference facts from implementation recommendations.
