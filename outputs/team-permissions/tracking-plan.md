# Tracking Plan

## Event Table

| event_name | description | trigger | platform | actor | required_properties | optional_properties | success_criteria | validation_notes | privacy_notes |
|---|---|---|---|---|---|---|---|---|---|
| permission_page_viewed | Admin views team permission page | Page load | Web | admin | user_id, workspace_id, platform, timestamp, role | team_size, filter_role | Page view can be measured | Compare with server page logs | Use workspace ID only if approved |
| permission_search_used | Admin searches or filters members | Search input or filter applied | Web | admin | user_id, workspace_id, platform, timestamp, filter_type | query_length | Search usage can be measured | Do not log raw search query unless approved | Avoid raw email search terms |
| permission_role_selected | Admin selects a new role | Role dropdown change | Web | admin | user_id, workspace_id, platform, timestamp, target_user_role, new_role | source_role | Selection funnel can be measured | Validate role values | Do not include target email |
| permission_change_reviewed | Admin opens confirmation panel | Confirmation panel appears | Web | admin | user_id, workspace_id, platform, timestamp, old_role, new_role | affected_permission_count | Review step can be measured | Check event fires once per panel open | No sensitive permission details beyond role labels |
| permission_change_submitted | Admin confirms permission change | Confirm button clicked | Web | admin | user_id, workspace_id, platform, timestamp, old_role, new_role | affected_permission_count | Submit conversion can be measured | Validate before API call | No target email |
| permission_change_succeeded | Permission change succeeds | API returns success | Web | system | user_id, workspace_id, platform, timestamp, old_role, new_role | audit_log_id | Success rate can be measured | Validate server success response | Audit log ID only if approved |
| permission_change_failed | Permission change fails | API returns failure | Web | system | user_id, workspace_id, platform, timestamp, error_category | old_role, new_role | Failure rate can be measured | Use mapped categories only | Do not log raw error payload |
| permission_audit_link_clicked | Admin opens audit log from success state | Audit link click | Web | admin | user_id, workspace_id, platform, timestamp | audit_log_id | Audit engagement can be measured | Validate link path | Audit log ID only if approved |

## Property Dictionary

| property_name | type | required | example | description | allowed_values | privacy_level | source |
|---|---|---|---|---|---|---|---|
| user_id | string | yes | u_123 | Approved internal user identifier | approved user id format | internal identifier | Auth system |
| workspace_id | string | yes | ws_123 | Workspace where permission change occurs | approved workspace id format | internal identifier | Workspace service |
| platform | string | yes | web | Client platform | web | non-sensitive | Client |
| timestamp | datetime | yes | 2026-05-18T10:00:00Z | Event time | ISO 8601 | non-sensitive | Client or server |
| role | string | yes | admin | Acting user's current role | owner, admin, member, viewer | low sensitivity | Permission service |
| filter_type | string | yes | role | Search or filter type | role, status, keyword | non-sensitive | Client |
| target_user_role | string | yes | member | Target user's current role | owner, admin, member, viewer | low sensitivity | Permission service |
| old_role | string | yes | member | Role before change | owner, admin, member, viewer | low sensitivity | Permission service |
| new_role | string | yes | admin | Role after change | owner, admin, member, viewer | low sensitivity | Permission service |
| source_role | string | no | member | Source role shown before selection | owner, admin, member, viewer | low sensitivity | Client |
| affected_permission_count | integer | no | 6 | Count of permission differences shown in review | integer >= 0 | non-sensitive | Permission service |
| error_category | string | yes | last_owner_blocked | Mapped failure category | validation, permission, conflict, server, last_owner_blocked | non-sensitive | API |
| audit_log_id | string | no | audit_123 | Audit log reference | approved audit id format | internal identifier | Audit service |
| team_size | integer | no | 42 | Workspace member count bucket or count | integer or bucket | aggregate | Workspace service |
| filter_role | string | no | admin | Selected role filter | owner, admin, member, viewer | low sensitivity | Client |
| query_length | integer | no | 8 | Length of search query, not raw query | integer >= 0 | non-sensitive | Client |

## Validation Checklist

- Confirm client events fire once per trigger.
- Confirm success and failure events match API outcomes.
- Confirm raw email, raw search query, and target user email are not collected.
- Confirm audit_log_id usage is approved by analytics and security owners.
