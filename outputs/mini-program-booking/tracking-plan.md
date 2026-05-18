# Tracking Plan

## Event Table

| event_name | description | trigger | platform | actor | required_properties | optional_properties | success_criteria | validation_notes | privacy_notes |
|---|---|---|---|---|---|---|---|---|---|
| booking_entry_viewed | User opens booking entry | Booking page load | Mini Program | user | user_id, anonymous_id, platform, timestamp | source | Entry funnel can be measured | Compare page logs with event count | No personal contact data |
| booking_authorization_requested | Mini program requests authorization | Authorization prompt appears | Mini Program | user | anonymous_id, platform, timestamp, auth_scope | source | Authorization prompt exposure can be measured | Validate scope value | Use minimal auth scope |
| booking_authorization_completed | User completes authorization | Authorization succeeds | Mini Program | user | user_id, platform, timestamp, auth_scope | source | Authorization completion can be measured | Validate success callback | Do not store unnecessary profile fields |
| booking_service_selected | User selects service type | Service card tap | Mini Program | user | user_id, platform, timestamp, service_id | service_category | Service demand can be measured | Validate service IDs | No free-text service notes |
| booking_slot_selected | User selects available slot | Available slot tap | Mini Program | user | user_id, platform, timestamp, service_id, slot_id, date_bucket | location_id | Slot selection can be measured | Validate unavailable slots do not fire | Slot ID should not reveal staff identity unless approved |
| booking_form_submitted | User submits booking form | Submit button tap | Mini Program | user | user_id, platform, timestamp, service_id, slot_id | contact_method_type | Submit conversion can be measured | Validate before API call | Do not log raw phone or name |
| booking_succeeded | Booking succeeds | Booking API returns success | Mini Program | system | user_id, platform, timestamp, booking_id, service_id, slot_id | location_id | Completion rate can be measured | Validate server response | Booking ID only if approved |
| booking_failed | Booking fails | Booking API returns failure | Mini Program | system | user_id, platform, timestamp, failure_category | service_id, slot_id | Failure rate can be measured | Use mapped failure categories only | Do not log raw API error |

## Property Dictionary

| property_name | type | required | example | description | allowed_values | privacy_level | source |
|---|---|---|---|---|---|---|---|
| user_id | string | yes | u_123 | Approved internal user identifier | approved user id format | internal identifier | Auth system |
| anonymous_id | string | no | anon_123 | Anonymous visitor identifier before authorization | approved anonymous id format | pseudonymous | Analytics SDK |
| platform | string | yes | mini_program | Client platform | mini_program | non-sensitive | Client |
| timestamp | datetime | yes | 2026-05-18T10:00:00Z | Event time | ISO 8601 | non-sensitive | Client or server |
| source | string | no | home | Entry source | home, search, campaign, profile | non-sensitive | Client |
| auth_scope | string | yes | basic_profile | Authorization scope requested | basic_profile, phone, location | sensitive category | Mini Program API |
| service_id | string | yes | svc_123 | Service type identifier | approved service id format | non-sensitive | Booking service |
| service_category | string | no | consultation | Service category | consultation, repair, visit, other | non-sensitive | Booking service |
| slot_id | string | yes | slot_123 | Appointment slot identifier | approved slot id format | internal identifier | Booking service |
| date_bucket | string | yes | same_week | Bucketed appointment date | today, same_week, later | non-sensitive | Client |
| location_id | string | no | loc_123 | Location identifier | approved location id format | low sensitivity | Location service |
| contact_method_type | string | no | phone | Contact channel category | phone, wechat, email | sensitive category | Client |
| booking_id | string | yes | bk_123 | Booking identifier | approved booking id format | internal identifier | Booking service |
| failure_category | string | yes | slot_taken | Mapped failure category | validation, slot_taken, auth, server, unknown | non-sensitive | API |

## Validation Checklist

- Confirm raw phone, raw name, and free-text notes are not logged.
- Confirm unavailable slot taps do not fire selection events.
- Confirm authorization scope is minimal and mapped.
