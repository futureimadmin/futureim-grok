# BIAN Service Domain: Corporate Loan

**Business Area:** Operations and Execution · **Business Domain:** Loans and Deposits

## Purpose
Manage the lifecycle of bilateral corporate loan facilities — initiation, drawdown,
repayment, covenant monitoring, and closure.

## Control record
Corporate Loan Facility (arrangement between bank and corporate obligor).

## Typical service operations
Initiate · Update · Control · Retrieve · Execute · Request

## Key business objects
Facility, Drawdown, Repayment Schedule, Covenant, Collateral Link, Party (Obligor)

## Notes for product fleets
Product policy lives in the bank's `corporate_lending` fleet racks; keep structural
boundaries aligned to this domain.
