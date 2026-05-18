# <localized tracking plan title>

<!-- Template note: tracking tables belong in prd.md by default. Use this split template only when a separate analytics handoff or CSV companion is requested. Localize human-facing headings and descriptions before generating a real artifact. Keep machine column names, event names, and property names in ASCII. Remove this note from generated artifacts. -->

## <localized taxonomy source>

| <localized field> | <localized value> |
|---|---|
| <localized source status> | <localized existing taxonomy followed / proposed taxonomy because no source was found / tracking omitted> |
| <localized approval needed> | <localized owner or not applicable> |

## <localized event table>

| event_name | description | trigger | platform | actor | required_properties | optional_properties | success_criteria | validation_notes | privacy_notes |
|---|---|---|---|---|---|---|---|---|---|
| feature_viewed | <localized event description> | <localized trigger timing> | <platform> | user | user_id, platform, timestamp | source, experiment_id | <localized success criteria> | <localized validation note> | <localized privacy note> |

## <localized property dictionary>

| property_name | type | required | example | description | allowed_values | privacy_level | source |
|---|---|---|---|---|---|---|---|
| user_id | string | yes | u_123 | <localized approved internal user identifier> | <localized approved ID format> | internal identifier | <localized auth system> |
| platform | string | yes | web | <localized client platform where event fires> | web, h5, app, mini_program | non-sensitive | <localized client> |
| timestamp | datetime | yes | 2026-05-18T10:00:00Z | <localized event time> | ISO 8601 | non-sensitive | <localized client or server> |

## <localized validation checklist>

- <localized confirm event fires exactly once per trigger>
- <localized confirm required properties are present and typed correctly>
- <localized confirm optional properties are omitted when unavailable>
- <localized compare client events with server logs or page views where possible>
- <localized confirm no forbidden sensitive properties are collected>

## <localized assumptions and privacy notes>

- <localized mark inferred events and fields clearly>
- <localized mark optional-scope events as conditional>
- <localized confirm sensitive fields with product, legal, security, or analytics owners before development>
