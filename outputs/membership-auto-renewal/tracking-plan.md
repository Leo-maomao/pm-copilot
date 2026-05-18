# Tracking Plan

## Event Table

| event_name | description | trigger | platform | actor | required_properties | optional_properties | success_criteria | validation_notes | privacy_notes |
|---|---|---|---|---|---|---|---|---|---|
| renewal_page_viewed | User views the H5 renewal optimization page | Renewal page loads successfully | H5 | user | user_id, anonymous_id, platform, timestamp, plan_id, renewal_status, source | campaign_id, experiment_id, variant_id | Event count aligns with page analytics | Compare client event count with server page logs | Do not include raw payment details |
| renewal_benefit_viewed | User sees benefit recap module | Benefit module enters viewport | H5 | user | user_id, platform, timestamp, plan_id, renewal_status | benefit_count, experiment_id, variant_id | Benefit exposure can be compared to CTA behavior | Validate viewport trigger and duplicate suppression | No personal benefit usage details unless aggregated |
| renewal_primary_cta_clicked | User clicks primary renewal or payment update CTA | Primary CTA click | H5 | user | user_id, platform, timestamp, plan_id, renewal_status, cta_type | source, campaign_id, experiment_id, variant_id | CTA click-through can be calculated | Check one event per click and correct cta_type | No raw payment details |
| payment_update_started | User starts payment update from renewal flow | Payment update flow opens | H5 | user | user_id, platform, timestamp, plan_id, renewal_status, payment_status_category | payment_method_type | Start rate can be calculated | Confirm event fires before secure payment handoff | Payment method type only; no card number |
| payment_update_completed | User successfully updates payment method | Payment service returns successful update | H5 | user | user_id, platform, timestamp, plan_id, renewal_status, payment_status_category | payment_method_type | Completion rate can be calculated | Validate with payment service success callback | Payment method type only; no card number |
| payment_update_failed | Payment update attempt fails | Payment service returns failure or user cannot complete | H5 | user | user_id, platform, timestamp, plan_id, renewal_status, failure_category | payment_method_type | Failure categories can be monitored | Validate category mapping with payment service | Use non-sensitive failure category only |
| renewal_recovery_succeeded | User renews successfully after failure or risk state | Server confirms successful renewal after recovery flow | H5 | system | user_id, platform, timestamp, plan_id, previous_renewal_status, recovery_source | campaign_id, experiment_id, variant_id | Recovery rate can be calculated | Validate server-side renewal confirmation | No raw transaction or payment details |
| renewal_policy_link_clicked | User clicks terms cancellation or refund policy link | Policy or cancellation link click | H5 | user | user_id, platform, timestamp, plan_id, link_type | source, experiment_id | Transparency engagement can be measured | Check link_type values for terms cancellation refund | No sensitive data |
| renewal_error_viewed | User sees an error or ineligible state | Error or ineligible state appears | H5 | user | user_id, platform, timestamp, error_category, renewal_status | plan_id, source | Error rate can be monitored | Validate each state maps to allowed error_category | No raw processor error messages |

## Property Dictionary

| property_name | type | required | example | description | allowed_values | privacy_level | source |
|---|---|---|---|---|---|---|---|
| user_id | string | yes | u_123 | Approved internal user identifier | approved user id format | internal identifier | Auth system |
| anonymous_id | string | no | anon_123 | Anonymous visitor identifier before login | approved anonymous id format | pseudonymous | Analytics SDK |
| platform | string | yes | h5 | Client platform | h5 | non-sensitive | Client |
| timestamp | datetime | yes | 2026-05-18T10:00:00Z | Event time | ISO 8601 | non-sensitive | Client or server |
| plan_id | string | yes | plan_pro | Membership plan identifier | approved plan id format | non-sensitive | Membership service |
| renewal_status | string | yes | payment_failed | Renewal state | healthy, expiring, payment_failed, canceled, ineligible | low sensitivity | Membership service |
| source | string | yes | sms | Traffic or in-product source | app, email, sms, push, account_center | non-sensitive | Client |
| campaign_id | string | no | cmp_123 | Campaign identifier | approved campaign id format | non-sensitive | Campaign system |
| experiment_id | string | no | exp_123 | Experiment identifier | approved experiment id format | non-sensitive | Experiment system |
| variant_id | string | no | b | Experiment variant | a, b, control | non-sensitive | Experiment system |
| cta_type | string | yes | update_payment | CTA selected | keep_auto_renewal, update_payment, view_policy | non-sensitive | Client |
| payment_status_category | string | yes | expired | Mapped payment status | healthy, expiring, expired, failed, missing | sensitive category | Payment service |
| payment_method_type | string | no | card | Payment method category only | card, wallet, bank, other | sensitive category | Payment service |
| failure_category | string | yes | processor_declined | Mapped failure category | processor_declined, timeout, user_cancelled, validation, unknown | sensitive category | Payment service |
| recovery_source | string | yes | payment_update | Recovery path | payment_update, retry, support | non-sensitive | Server |
| link_type | string | yes | cancellation | Policy link clicked | terms, cancellation, refund | non-sensitive | Client |
| error_category | string | yes | ineligible | Mapped error state | ineligible, network, payment, server, unknown | non-sensitive | Client |
| benefit_count | integer | no | 4 | Count of benefits shown | integer >= 0 | aggregate | Client |

## Validation Checklist

- Confirm no card number, processor payload, or transaction detail is logged.
- Confirm payment success is validated through secure callback or server confirmation.
- Confirm policy link clicks include only link_type, not full policy text.
