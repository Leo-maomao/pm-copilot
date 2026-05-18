# Tracking Plan

## Event Table

| event_name | description | trigger | platform | actor | required_properties | optional_properties | success_criteria | validation_notes | privacy_notes |
|---|---|---|---|---|---|---|---|---|---|
| feature_viewed | User views the feature entry | Entry becomes visible | <platform> | user | user_id, platform, timestamp | source, experiment_id | Event fires once per qualified view | Compare event count with page or screen views | Do not include personal identifiers beyond approved user ID |

## Property Dictionary

| property_name | type | required | example | description | allowed_values | privacy_level | source |
|---|---|---|---|---|---|---|---|
| user_id | string | yes | u_123 | Approved internal user identifier | Existing approved ID format | internal identifier | Auth system |
| platform | string | yes | web | Client platform where event fires | web, h5, app, mini_program | non-sensitive | Client |
| timestamp | datetime | yes | 2026-05-18T10:00:00Z | Event time | ISO 8601 | non-sensitive | Client or server |

## Validation Checklist

- Confirm event fires exactly once per trigger.
- Confirm required properties are present and typed correctly.
- Confirm optional properties are omitted when unavailable.
- Compare client events with server logs or page views where possible.
- Confirm no forbidden sensitive properties are collected.

## Assumptions And Privacy Notes

- Mark inferred events and fields clearly.
- Confirm sensitive fields with product, legal, security, or analytics owners before development.
