# Clarifying Questions

## Must Answer Before Launch

1. What roles are supported in v1, and what permissions does each role include?
2. Can admins edit roles controlled by directory sync or identity provider groups?
3. What audit log fields are available today?
4. Which unsafe role changes must be blocked: self-demotion, last-owner removal, owner transfer, or all?
5. What support ticket categories should be used to measure access-related issues?

## Can Proceed With Assumptions for Draft

1. V1 uses existing roles only.
2. Admins can change roles for regular members.
3. Last-owner removal and self-demotion are blocked.
4. Directory-synced roles may be read-only.
5. Raw emails and search query text are not logged in analytics.

## Can Decide Later

1. Custom roles.
2. Approval workflow for high-risk changes.
3. Bulk permission updates.
4. Advanced audit log filtering.
