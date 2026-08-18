# BIAN Service Domain: Credit Management

**BIAN version:** 12 (reference)

## Purpose

**Credit Management** covers credit assessment, limit setting, ongoing credit monitoring, and credit policy application for counterparties and facilities.

## Core business objects

| Object | Role |
|--------|------|
| Credit Assessment | Underwriting outcome for an application or review |
| Credit Limit | Authorised exposure ceiling |
| Credit Position | Utilised vs available exposure |
| Credit Policy Rule | Policy constraints applied during assessment |

## Representative operations

- Initiate credit assessment
- Decide / recommend credit outcome
- Establish or revise credit limit
- Monitor credit position
- Trigger periodic review

## Boundaries

- Does **not** book the loan facility (that is **Loan**).
- Does **not** own party identity (that is **Party Reference Data Management**).
- Fraud signals may feed assessment but case management sits with **Fraud Evaluation**.

## Coding guidance

- Expose assessment as a decision service with explicit inputs and outputs (decision, limit, conditions).
- Keep policy rules data-driven; version policies alongside `bian_version` and bank policy packs.
- Lending racks under tier `originations` should retrieve this domain together with Loan and Customer Offer.
