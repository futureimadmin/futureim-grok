# BIAN Business Object Model (BOM) — core entities

**Purpose:** Shared semantic foundation across service domains. APIs and CRs specialize these objects; they are not a shared database.

## Backbone chain

```text
Party → enters → Agreement → defines → Arrangement → manages → Account → records → Transaction
```

| Object | Meaning |
|--------|--------|
| **Party** | Legal/identity entity |
| **Agreement** | Formal understanding between parties |
| **Arrangement** | Commitment to perform actions |
| **Account** | Log of value/obligation movements |
| **Transaction** | Planned or performed action |

## Supporting objects

PartyRole · BankingProduct · Service · Event · Feature

## ISO 20022 alignment

BIAN Semantic APIs offer BOM-extended and ISO20022+DDD-annotated OAS 3.x variants. Prefer ISO20022 field names for payments/securities interoperability.

## Coding / RAG rules

1. Do not collapse Party and Account across domains.
2. Loan CR vs Payment Execution own different concerns.
3. Codegen accepts references (`partyReference`, `arrangementReference`), not full masters.
