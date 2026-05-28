---
artifact_type: structured_catalog # use structured_reference for broader document-reference handoffs
catalog_type: "<parameter_reference | model_integration_matrix | api_capability_catalog | vendor_matrix | data_dictionary | rule_reference | sop_runbook | migration_inventory | other>"
language: "<zh | en>"
source_status: "<source_backed | user_supplied | mixed | draft | blocked>"
review_status: "<unreviewed | pm_reviewed | engineering_reviewed | approved | blocked>"
owner: "<owner or owner gap>"
last_updated: "<YYYY-MM-DD>"
---

# <localized catalog title>

## <localized catalog summary>

| Field | Value |
|---|---|
| Intended audience | <engineering / PM / QA / ops> |
| Intended use | <how this catalog should be used> |
| Out of scope | <what this catalog does not decide> |
| Engineering readiness | <ready / blocked / draft with source gaps> |
| Launch readiness | <ready / blocked / not applicable> |

## <localized source and review status>

| Source ID | Source Type | Source Reference | Access Date | Source Owner | Review Owner | Review Status | Freshness Limit |
|---|---|---|---|---|---|---|---|
| S1 | <official_docs / user_supplied / repo_file / unknown> | <URL or document path> | <YYYY-MM-DD> | <owner> | <owner> | <status> | <what may change> |

## <localized structured source facts>

Use this section for document-reference handoffs before final PM/product decisions are applied.

| `entity_id` | `target_ref` | Source Fact | Source | Confidence | Extracted At | Notes |
|---|---|---|---|---|---|---|
| <entity_1> | <entity_1.field> | <fact from source> | <S1> | <high / medium / low> | <YYYY-MM-DD> | <source limitation> |

## <localized product decisions>

Use this section to distinguish final product decisions from source/vendor defaults.

| `decision_id` | `target_ref` | Source Default | Product Decision | Owner | Review Status | Rationale |
|---|---|---|---|---|---|---|
| D1 | <entity_1.field> | <vendor/default value> | <final value used by product> | <owner> | <status> | <why this override or decision exists> |

## <localized field dictionary>

| Field Name | Type | Required | Allowed Values | Source | Implementation Meaning |
|---|---|---|---|---|---|
| `item_id` | string | yes | stable ASCII ID | catalog author | Stable row key for engineering references |
| `display_name` | string | yes | free text | source | Human-readable item name |
| `source_status` | enum | yes | `source_backed`, `user_supplied`, `mixed`, `draft`, `blocked` | source review | Reliability of row facts |
| `review_status` | enum | yes | `unreviewed`, `pm_reviewed`, `engineering_reviewed`, `approved`, `blocked` | reviewer | Whether row can be used downstream |
| `owner` | string | yes | owner name or owner gap | reviewer | Person or team responsible for confirmation |
| `access_date` | date | yes | `YYYY-MM-DD` | source review | Date source was inspected |
| `implementation_notes` | string | yes | free text | PM/engineering | Engineering handoff implications |

## <localized catalog table>

| `item_id` | `display_name` | `source_status` | `review_status` | `owner` | `access_date` | `implementation_notes` |
|---|---|---|---|---|---|---|
| <item_1> | <name> | <status> | <status> | <owner> | <YYYY-MM-DD> | <implementation note> |

## <localized structured fields and rules>

Use this section when the reference contains hierarchical fields, conditional rules, enums, defaults, or limits.

| `item_id` | `display_name` | `field_id` | `name` | `type` | Required | Default | Enum | Limits | Children | Conditions | Source | Product Decision | `source_status` | `review_status` | `owner` | `access_date` | `implementation_notes` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <item_1> | <name> | <field_1> | <field name> | <type> | <yes/no/conditional> | <default> | <values> | <limits> | <child refs> | <condition refs> | <S1> | <decision ref> | <status> | <status> | <owner> | <YYYY-MM-DD> | <note> |

## <localized model integration table>

Use this section only for model/provider catalogs.

| `item_id` | `provider` | `model_id` | `display_name` | `version_or_release` | `input_modalities` | `output_modalities` | `context_window` | `required_parameters` | `optional_parameters` | `rate_limits` | `pricing_source` | `deprecation_status` | `source_status` | `review_status` | `owner` | `access_date` | `implementation_notes` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <model_1> | <provider> | <model_id> | <name> | <version> | <modalities> | <modalities> | <value or Unknown> | <params> | <params> | <limits or Unknown> | <source or Unknown> | <active/deprecated/unknown> | <status> | <status> | <owner> | <YYYY-MM-DD> | <integration note> |

## <localized engineering handoff notes>

| Topic | Decision Or Gap | Owner | Required Before |
|---|---|---|---|
| Integration scope | <decision or gap> | <owner> | <review / engineering / launch> |
| Validation | <test or check expectation> | <owner> | <engineering> |

## <localized attention_points>

| `attention_id` | Type | `target_ref` | Finding | Impact | Owner | Required Before | Status |
|---|---|---|---|---|---|---|---|
| A1 | `source_gap` | <entity_1.field> | <missing or stale source> | <review or engineering impact> | <owner> | <review / engineering / launch> | <open / fixed / accepted> |
| A2 | `pm_override` | <entity_1.field> | <product decision overrides source default> | <implementation impact> | <owner> | <engineering> | <open / fixed / accepted> |
| A3 | `engineering_must_read` | <entity_1.rule> | <implementation-critical rule> | <handoff impact> | <owner> | <engineering> | <open / fixed / accepted> |

Supported types: `source_gap`, `pm_override`, `conflict`, `engineering_must_read`, `launch_blocker`, `cost_or_quota_risk`, `security_or_compliance`, `change_marker`.

## <localized change_log>

| Turn Or Version | Object | Change Type | Summary | Source | Owner |
|---|---|---|---|---|---|
| <turn> | <entity_id / field_id> | <added / changed / removed / presentation_only> | <change summary> | <user / source / agent> | <owner> |

## <localized completeness_check>

| Check | Status | Covered Items | Missing Or Conflicting Items | Owner |
|---|---|---|---|---|
| Entity count | <passed / needs_review> | <count/list> | <gaps> | <owner> |
| Field coverage | <passed / needs_review> | <fields> | <gaps> | <owner> |
| Defaults/enums/limits | <passed / needs_review> | <items> | <gaps> | <owner> |
| Sources and review | <passed / needs_review> | <sources> | <gaps> | <owner> |

## <localized validation results>

| Command | Status | Notes |
|---|---|---|
| `python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>` | <passed / failed / skipped> | <observed result or limitation> |
