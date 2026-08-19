# Business Scenario: Customer Mortgage Application

**BIAN style:** End-to-end business scenario (service domain interaction sequence).
**Primary domains:** Party Reference, Customer Offer, Credit Management, Collateral Asset Administration, Loan/Mortgage, Current Account, Payment Order / Payment Execution.

## Sequence (logical order)

```text
1. Party Reference Data Management — Retrieve (known customer)
2. Customer Offer — Retrieve/Initiate (offer rules, eligibility)
3. Credit Management — Retrieve/Evaluate (credit assessment)
4. Collateral Asset Administration — Initiate (collateral + valuation)
5. Loan / Mortgage Loan — Initiate (facility CR)
6. Current Account — Initiate/Register (linked account optional)
7. Payment Order.Initiate → Payment Execution.Execute (disbursement)
```

## Mermaid

```mermaid
sequenceDiagram
    participant Party as Party Reference
    participant Offer as Customer Offer
    participant Credit as Credit Management
    participant Coll as Collateral Admin
    participant Loan as Loan / Mortgage
    participant CA as Current Account
    participant PO as Payment Order
    participant PE as Payment Execution

    Party->>Party: Retrieve (known customer)
    Offer->>Offer: Retrieve/Initiate (offer rules)
    Credit->>Credit: Retrieve/Evaluate (credit assessment)
    Coll->>Coll: Initiate (collateral + valuation)
    Loan->>Loan: Initiate (facility CR)
    CA->>CA: Initiate (linked account optional)
    PO->>PO: Initiate (disbursement instruction)
    PE->>PE: Execute (settle funds)
```

## Boundaries

| Domain | Owns | Does not own |
|--------|------|--------------|
| Customer Offer | Offer terms, acceptance | Facility balances |
| Credit Management | Assessment, limits advice | Collateral register |
| Collateral | Asset registration, valuation | Loan schedule |
| Loan | Facility CR, drawdown, repayment plan | Payment rail clearing |
| Payment Order | Instruction | Settlement finality |
| Payment Execution | Clearing/settlement | Facility accounting rules |
