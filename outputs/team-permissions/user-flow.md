# User Flow

```mermaid
flowchart TD
  A[Admin opens Team Settings] --> B{Has admin permission?}
  B -- No --> C[Show read-only state]
  B -- Yes --> D[Show member role table]
  D --> E[Search or filter members]
  E --> F[Select member]
  F --> G{Role editable?}
  G -- No --> H[Show locked by directory sync]
  G -- Yes --> I[Choose new role]
  I --> J[Open confirmation panel]
  J --> K{Unsafe change?}
  K -- Last owner or self-demotion --> L[Block and explain]
  K -- Safe --> M[Confirm change]
  M --> N{API success?}
  N -- Yes --> O[Show success and audit log link]
  N -- No --> P[Show error and keep old role]
  O --> Q[End]
  P --> I
```

## Legend

| Shape | Meaning |
|---|---|
| Rectangle | Screen, state, or user action |
| Diamond | Permission, safety, or API decision |
| Labeled arrow | Branch condition |

## Notes

- Last owner and self-demotion states block submission.
- Directory-synced roles are visible but not editable.
- API failure keeps the previous role and returns the admin to role selection.
