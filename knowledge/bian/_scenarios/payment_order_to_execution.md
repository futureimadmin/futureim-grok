# Business Scenario: Payment Order → Payment Execution

**Primary domains:** Payment Order, Payment Execution, Current Account.

## Sequence

```text
1. Payment Order.Initiate — validate instruction
2. Current Account.Retrieve — funds / holds
3. Payment Execution.Initiate/Execute — clearing lifecycle
4. Current Account.Update — post settlement outcome
```

## Mermaid

```mermaid
sequenceDiagram
    participant Client
    participant PO as Payment Order
    participant CA as Current Account
    participant PE as Payment Execution

    Client->>PO: Initiate (instruction)
    PO->>PO: Validate parties, amount, rail
    PO->>CA: Retrieve (funds / holds)
    alt Sufficient funds
        PO->>PE: Initiate (handoff validated order)
        PE->>PE: Execute (clearing)
        PE-->>CA: Settlement outcome
        CA->>CA: Update position
        PE-->>Client: Notify settled
    else Insufficient / blocked
        PO->>PO: Control (reject/hold)
        PO-->>Client: Notify failed
    end
```

## State machine (Payment Execution)

```text
accepted → in_clearing → settled
                ↘ failed
                ↘ returned
```
