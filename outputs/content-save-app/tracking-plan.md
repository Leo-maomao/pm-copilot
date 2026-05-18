# Tracking Plan

## Event Table

| event_name | description | trigger | platform | actor | required_properties | optional_properties | success_criteria | validation_notes | privacy_notes |
|---|---|---|---|---|---|---|---|---|---|
| article_save_clicked | User taps save on article detail | Save button tap | App | user | user_id, platform, timestamp, content_id, content_type | source, subscription_status | Save intent can be measured | Validate one event per tap | Content ID must not expose private content |
| article_saved | Article save succeeds | Save API or local persistence succeeds | App | system | user_id, platform, timestamp, content_id, content_type | offline_eligible | Save success rate can be measured | Validate persistence result | No article body text |
| article_unsaved | User removes saved article | Unsave succeeds | App | user | user_id, platform, timestamp, content_id | source | Unsave rate can be measured | Validate state transition | No article body text |
| saved_tab_viewed | User opens Saved tab | Saved tab becomes active | App | user | user_id, platform, timestamp | saved_count | Saved usage can be measured | Compare tab views with app navigation logs | Do not include full saved list |
| saved_article_opened | User opens saved article | Saved item tap | App | user | user_id, platform, timestamp, content_id, network_status | offline_available | Return reading can be measured | Validate online and offline cases | No article body text |
| offline_article_opened | User opens cached article offline | Article opens while offline | App | user | user_id, platform, timestamp, content_id, cache_status | cache_age_bucket | Offline value can be measured | Test with network disabled | No raw device path |
| offline_access_failed | Offline access fails | User attempts to open unavailable offline article | App | system | user_id, platform, timestamp, content_id, failure_category | network_status | Failure rate can be measured | Use mapped categories only | No raw error payload |

## Property Dictionary

| property_name | type | required | example | description | allowed_values | privacy_level | source |
|---|---|---|---|---|---|---|---|
| user_id | string | yes | u_123 | Approved internal user identifier | approved user id format | internal identifier | Auth system |
| platform | string | yes | app | Client platform | app | non-sensitive | Client |
| timestamp | datetime | yes | 2026-05-18T10:00:00Z | Event time | ISO 8601 | non-sensitive | Client or server |
| content_id | string | yes | c_123 | Article identifier | approved content id format | internal identifier | Content service |
| content_type | string | yes | article | Content type | article, video, note | non-sensitive | Content service |
| source | string | no | article_detail | Entry source | article_detail, saved_tab, push, search | non-sensitive | Client |
| subscription_status | string | no | paid | User subscription state | free, trial, paid, expired | low sensitivity | Account service |
| offline_eligible | boolean | no | true | Whether content can be cached offline | true, false | non-sensitive | Content service |
| saved_count | integer | no | 12 | Count of saved items shown as aggregate | integer >= 0 | aggregate | Client |
| network_status | string | no | offline | Network state | online, offline, degraded | non-sensitive | Client |
| offline_available | boolean | no | true | Whether saved content can open offline | true, false | non-sensitive | Client |
| cache_status | string | yes | fresh | Cache availability state | fresh, stale, missing | non-sensitive | Local cache |
| cache_age_bucket | string | no | 1_7_days | Age bucket, not exact local path | lt_1_day, 1_7_days, gt_7_days | non-sensitive | Local cache |
| failure_category | string | yes | cache_missing | Mapped failure reason | cache_missing, permission, network, unknown | non-sensitive | Client |

## Validation Checklist

- Confirm no article body, raw local path, or private content text is logged.
- Confirm offline events can be tested with network disabled.
- Confirm save and unsave state transitions match persistence results.
