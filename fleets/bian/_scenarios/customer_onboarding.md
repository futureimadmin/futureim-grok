# Business Scenario: Customer onboarding

```text
1. Party Reference Data Directory — Register/Retrieve
2. Party Authentication — Evaluate
3. Customer Relationship Management — Initiate
4. Customer Offer — Initiate/Evaluate
5. Product facility (CA / Loan / …) — Initiate CR
6. Document Services — capture evidence
```

```mermaid
sequenceDiagram
    participant Party as Party Reference
    participant Auth as Party Authentication
    participant CRM as CRM
    participant Offer as Customer Offer
    participant Fac as Product Facility
    participant Doc as Document Services

    Party->>Party: Register/Retrieve
    Auth->>Auth: Evaluate
    CRM->>CRM: Initiate relationship
    Offer->>Offer: Initiate/Evaluate offer
    Fac->>Fac: Initiate facility CR
    Doc->>Doc: Capture/Retrieve evidence
```

Security: KYC retention; minimize PII in vector index.
