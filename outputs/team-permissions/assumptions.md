# Assumptions

| ID | Assumption | Reason | Risk |
|---|---|---|---|
| A1 | V1 uses existing role taxonomy. | The task asks for safer management, not role redesign. | If roles are unclear, confirmation copy may be inaccurate. |
| A2 | Web desktop is the primary admin surface. | Permission management is table-heavy and admin-oriented. | Mobile admin use may need a separate responsive review. |
| A3 | Directory-synced roles may be locked. | Many workspace products use external identity providers. | Incorrect locking rules may confuse admins. |
| A4 | Audit log can record actor, target, old role, new role, and timestamp. | Safe permission changes require traceability. | If audit fields are missing, review confidence is lower. |
| A5 | Analytics should not log raw emails or raw search terms. | Search and target users can expose personal data. | Diagnostics may be less detailed. |
