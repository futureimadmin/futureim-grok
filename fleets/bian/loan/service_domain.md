# BIAN Service Domain: Loan

**BIAN version:** 12 (reference)

## Purpose

Lifecycle management of loan facilities — initiation, disbursement, repayment scheduling, interest application, restructuring, and closure.

## Control record

LoanFacility (or product-specific specialisations such as MortgageLoanFacility).

## Typical BQs

Disbursement · Repayment · Interest · Fees · Billing · Collateral / Lien · Restructuring

## Operations

Initiate · Update · Control · Execute · Request · Retrieve · Exchange

## Boundaries

| Domain | Owns | Does not own |
|--------|------|--------------|
| Loan | Facility CR, schedule, status | Credit decision (Credit Management) |
| Payment Order/Execution | Instruction and settlement | Facility accounting rules |
| Collateral | Asset master and allocation | Loan repayment plan |

## Coding guidance

- Model facility as aggregate root; do not collapse credit assessment into loan Initiate.
- Sequence: Offer → Credit Evaluate → Collateral Initiate → Loan Initiate → Payment Execute (disbursement).
