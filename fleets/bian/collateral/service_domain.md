# BIAN Service Domain: Collateral Asset Administration

**BIAN version:** 12 (reference)

## Purpose

Administer assets pledged as security for credit facilities: registration, valuation reference, allocation to facilities, release, and realisation support.

## Core business objects

| Object | Role |
|--------|------|
| Collateral Asset | The pledged asset record |
| Collateral Allocation | Link between asset and loan facility |
| Valuation Snapshot | Point-in-time value used for LTV |
| Charge / Lien Record | Legal interest metadata (jurisdiction-specific) |

## Boundaries

- **Loan** consumes allocation and LTV inputs; it does not own asset master data.
- Property valuation sources are external; this domain stores results and validity.

## Coding guidance

- Mortgage racks must model collateral allocation as a first-class API, not a free-text field on the loan.
- Enforce referential integrity: cannot fully release collateral while facility is live without credit override.
