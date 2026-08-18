# BIAN Service Domain: Payment Order

**BIAN version:** 12 (reference)

## Purpose

Capture and validate a customer's or system's instruction to move value — prior to clearing and settlement execution.

## Core business objects

| Object | Role |
|--------|------|
| Payment Order | The instruction to pay |
| Payment Party | Debtor / creditor references |
| Payment Rail Preference | Preferred network or scheme |
| Order Status | Initiation lifecycle state |

## Boundaries

- **Payment Execution** performs clearing/settlement; Payment Order stops at a validated instruction.
- Card authorisations may start in **Card Transaction** and later relate to execution.

## Coding guidance

- Separate initiation APIs (Order) from execution APIs (Execution).
- Idempotency keys belong on order creation; never double-post execution from retries without checks.
