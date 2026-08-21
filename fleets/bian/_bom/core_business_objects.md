# BIAN Business Object Model (BOM) — core entities

**Purpose:** Shared semantic foundation across service domains.

## Backbone chain

```text
Party → Agreement → Arrangement → Account → Transaction
```

## Party / KYC objects (enterprise)

PartyRelationship, QualificationCheck, LegalEntity, OwnershipStructure, CustomerProfile, Document, Entitlement, AuthorizationDecision

## Cards objects

Card, CardTransaction, CardCapture, ClearingBatch, CardCase, Statement

## Payments / accounts

PaymentInstruction, PaymentOrder, Mandate, VirtualAccount, StandingOrder

## Lending / trade

Facility, CollateralAsset, Guarantee, Project/SPV

## Supporting

PartyRole, BankingProduct, Service, Event, Feature, CreditRating, FraudCase/Alert

## Coding / RAG rules

1. Do not collapse Party and Account across domains.
2. KYC lives in Party Lifecycle Management — product domains use partyReference only.
3. Card domains own Card/CardTransaction; do not model card auth inside Payment Order.
4. Codegen stubs accept references, not full party masters.
