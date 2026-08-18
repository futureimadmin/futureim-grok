# BIAN Service Domain: Loan

**BIAN version:** 12 (reference)
**Platform role:** Base platform service domain for lending facilities.

## Purpose

The **Loan** service domain manages the lifecycle of a credit facility extended to a customer: arrangement, drawdown, interest application, repayment, restructuring, and closure.

## Core business objects (conceptual)

| Object | Role |
|--------|------|
| Loan Facility | Master agreement for the credit line or term loan |
| Drawdown / Disbursement | Funds advanced against the facility |
| Repayment Schedule | Planned principal and interest obligations |
| Outstanding Balance | Current principal, interest, fees |
| Loan Transaction | Accounting events (disburse, repay, write-off) |

## Coding guidance (RAG-scoped)

1. Name public APIs and aggregates using Loan facility language.
2. Separate **origination** from **servicing**.
3. Emit domain events: `FacilityBooked`, `DrawdownExecuted`, `RepaymentApplied`, `FacilityClosed`.
4. Do not embed credit decision logic inside Loan — call Credit Management.
