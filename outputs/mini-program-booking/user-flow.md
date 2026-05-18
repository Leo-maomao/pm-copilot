# User Flow

```mermaid
flowchart TD
  A[User opens mini program booking] --> B{Authorized?}
  B -- No --> C[Explain value and request authorization]
  C --> D{Authorization granted?}
  D -- No --> E[Show limited state and retry option]
  D -- Yes --> F[Show service list]
  B -- Yes --> F
  F --> G[Select service]
  G --> H[Choose date]
  H --> I{Slots available?}
  I -- No --> J[Show no slots and next date option]
  I -- Yes --> K[Select time slot]
  K --> L[Fill required contact fields]
  L --> M{Form valid?}
  M -- No --> N[Show inline validation]
  N --> L
  M -- Yes --> O[Submit booking]
  O --> P{Slot still available?}
  P -- No --> Q[Ask user to choose another slot]
  P -- Yes --> R[Show confirmation]
  Q --> H
  R --> S[End]
```

## Legend

| Shape | Meaning |
|---|---|
| Rectangle | Mini Program page, form state, or action |
| Diamond | Authorization, availability, validation, or API decision |

## Notes

- Authorization denial leads to a limited retry state.
- Slot availability must be checked again on submit.
