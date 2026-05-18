# User Flow

```mermaid
flowchart TD
  A[User opens renewal H5 link] --> B{Logged in?}
  B -- No --> C[Prompt login]
  C --> D[Return to renewal page]
  B -- Yes --> D[Load membership and payment status]
  D --> E{Eligible for renewal flow?}
  E -- No --> F[Show not eligible state]
  F --> Z[Exit or go to membership center]
  E -- Yes --> G[Show renewal detail page]
  G --> H[Show billing date price plan and benefit recap]
  H --> I{Payment status}
  I -- Healthy --> J[Primary CTA: keep auto-renewal]
  I -- Expiring or failed --> K[Primary CTA: update payment]
  K --> L[Secure payment update]
  L --> M{Update successful?}
  M -- Yes --> N[Show payment updated confirmation]
  N --> O[Show next renewal date]
  M -- No --> P[Show failure category retry and support options]
  P --> K
  J --> Q[Show confirmation and policy links]
  G --> R[User opens cancellation terms or refund policy]
  R --> S[Show policy detail]
  S --> G
  O --> T[Track recovery success when renewal confirmed]
  Q --> U[End]
  T --> U
```

## Legend

| Shape | Meaning |
|---|---|
| Rectangle | H5 page, module, or state |
| Diamond | Login, eligibility, payment, or callback decision |

## Notes

- Payment update must happen through a secure payment handoff.
- Cancellation, terms, and refund policy links remain visible.
