# Business Scenario: Card authorization (assess pattern)

```text
Card Authorization.Evaluate
  ├── Device / Authentication BQs
  ├── Credit / funds check
  └── Fraud check BQ
→ approved | declined
Later: Card Capture → Card Clearing (separate domains)
```

Do not collapse authorization, capture, and clearing into one service domain.
