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

## Representative service operations (control-record style)

- Initiate / Request loan facility
- Update facility terms (within policy)
- Execute drawdown
- Apply repayment
- Assess outstanding position
- Restructure facility
- Close / terminate facility

## Boundaries

- **Credit Management** decides risk appetite and limits; Loan executes the facility within those limits.
- **Collateral Asset Administration** links security assets; Loan does not value collateral itself.
- **Customer Offer** produces the commercial offer; Loan books the accepted facility.
- **Customer Agreement** may hold the legal agreement wrapper; Loan holds operational facility state.

## Coding guidance (RAG-scoped)

When generating services for a lending rack:

1. Name public APIs and aggregates using Loan facility language (not generic "Account" unless Current Account domain applies).
2. Separate **origination** (offer → agreement → facility create) from **servicing** (drawdown, repay, restructure).
3. Emit domain events: `FacilityBooked`, `DrawdownExecuted`, `RepaymentApplied`, `FacilityClosed`.
4. Do not embed credit decision logic inside Loan services — call Credit Management.

## Related product fleets

- `consumer_lending` racks: personal_loans, mortgages, credit_cards, collections
