# BIAN Service Domain: Customer Offer

**BIAN version:** 12 (reference)

## Purpose

Create, configure, and manage product offers presented to a party — including eligibility, pricing options, and acceptance state — before a lasting customer agreement or facility is booked.

## Core business objects

| Object | Role |
|--------|------|
| Customer Offer | The commercial proposal instance |
| Offer Item | Product / term line within the offer |
| Eligibility Result | Outcome of eligibility checks |
| Offer Acceptance | Customer decision capture |

## Boundaries

- **Sales Product** defines catalogue products; Customer Offer instantiates a proposal for a party.
- Accepted offers flow into **Customer Agreement** and/or **Loan** facility booking.
- Does not perform final credit decision (Credit Management) though it may carry indicative terms.

## Coding guidance

- Originations tier services should start with Offer → Assessment → Agreement/Facility, not a single monolithic "create loan" API.
- Persist offer state machine: draft, presented, accepted, expired, withdrawn.
