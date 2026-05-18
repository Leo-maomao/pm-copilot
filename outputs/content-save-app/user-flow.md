# User Flow

```mermaid
flowchart TD
  A[User opens article in App] --> B{Logged in?}
  B -- No --> C[Prompt login]
  C --> A
  B -- Yes --> D[Tap save]
  D --> E{Save succeeds?}
  E -- No --> F[Show retry error]
  E -- Yes --> G[Show saved confirmation]
  G --> H[Article appears in Saved tab]
  H --> I[User opens Saved tab]
  I --> J{Network available?}
  J -- Yes --> K[Open article online]
  J -- No --> L{Offline cached and eligible?}
  L -- Yes --> M[Open cached article]
  L -- No --> N[Show offline unavailable state]
  K --> O[Track completion]
  M --> O
```

## Legend

| Shape | Meaning |
|---|---|
| Rectangle | App screen, state, or action |
| Diamond | Login, persistence, network, or cache decision |

## Notes

- Offline unavailable states should explain why the content cannot open.
- Login returns the user to the original article after completion.
