---
artifact_type: structured_catalog
catalog_type: "<model_integration_matrix | api_capability_catalog | vendor_matrix | data_dictionary | other>"
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

## <localized validation results>

| Command | Status | Notes |
|---|---|---|
| `python3 scripts/run_delivery_checks.py outputs/<run-id> --language <zh|en>` | <passed / failed / skipped> | <observed result or limitation> |
