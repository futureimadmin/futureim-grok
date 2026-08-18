# Business Scenario: Current Account Facility Operations

**Primary domain:** Current Account (CR: CurrentAccountFacility).
**Related:** Position Keeping, Standing Order, Payment Execution.

## Control Record + Business Qualifiers

| Element | Role |
|---------|------|
| CurrentAccountFacility (CR) | Aggregate root: status, currency, party reference |
| Deposits (BQ) | Credit movements |
| Withdrawals (BQ) | Debit movements |
| AccountLien (BQ) | Holds reducing available balance |
| Payments (BQ) | Payment-related postings |

## Sequence: Initiate lien (hold)

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

## Sequence: Deposit / withdrawal

```mermaid
sequenceDiagram
    participant Client
    participant CA as Current Account
    participant DEP as Deposits BQ
    participant WDR as Withdrawals BQ
    participant PK as Position Keeping

    Client->>CA: Deposits/Initiate or Withdrawals/Initiate
    alt Deposit
        CA->>DEP: Record credit
        DEP->>PK: Increase position
    else Withdrawal
        CA->>WDR: Record debit
        WDR->>PK: Decrease position (if available)
    end
    CA-->>Client: Retrieve updated status
```

## Standard CR operations

- **Initiate** — open account facility
- **Update** — fees, sweeps, product attributes
- **Control** — suspend, freeze, close
- **Execute** — scheduled interest, automated sweeps
- **Retrieve** — balances, statements, history
- **Request** — manual fee waiver / exception

## Coding hints

- Available balance = ledger position − active liens/holds.
- Standing Order **Initiate** creates recurring instructions that later drive Payment Order/Execution.
