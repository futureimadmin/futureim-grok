# Business Scenario: Current Account Facility Operations

**Primary domain:** Current Account (CR: CurrentAccountFacility).

## Control Record + Business Qualifiers

| Element | Role |
|---------|------|
| CurrentAccountFacility (CR) | Aggregate root |
| Deposits (BQ) | Credit movements |
| Withdrawals (BQ) | Debit movements |
| AccountLien (BQ) | Holds reducing available balance |
| Payments (BQ) | Payment-related postings |

## Sequence: Initiate lien

```mermaid
sequenceDiagram
    participant EXT as External / Ops
    participant CA as CurrentAccountFacility
    participant LIEN as AccountLien BQ
    participant PK as Position Keeping

    EXT->>CA: AccountLien/Initiate
    CA->>LIEN: Create lien (type, amount)
    LIEN->>PK: Reduce available balance
    LIEN-->>CA: LienInstanceReference
    CA-->>EXT: Lien established
```

## Coding hints

- Available balance = ledger position − active liens/holds.
- Standing Order Initiate creates recurring instructions that drive Payment Order/Execution.
