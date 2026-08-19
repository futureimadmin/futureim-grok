# BIAN Service Domain Catalog (reference)

**Sources:** BIAN Service Landscape (v9–v14), bian-official/public Semantic APIs.
**Note:** Full landscape has 300+ domains historically; public OAS packs expose 98+ ISO20022-extended domains. Extend without volume limits.

## Hierarchy

```text
Business Area
  └── Business Domain
        └── Service Domain  ← unit of capability + Semantic API
```

**ArchiMate mapping:**
- Business Area / Business Domain → Grouping / Capability hierarchy
- Service Domain → Capability (discrete, non-overlapping)
- Service exchanges → serving / flow between capabilities
- Business Scenario → sequence of service operations

## Categories and representative service domains

| Category | Representative service domains | Purpose |
|----------|--------------------------------|---------|
| **Customer & relationship** | Customer Relationship Management, Customer Offer, Customer Position, Party Reference Data Directory, Party Authentication | Party lifecycle, offers |
| **Account management** | Current Account, Savings Account, Investment Account, Term Deposit, Position Keeping | Deposit/investment facilities |
| **Lending** | Loan, Mortgage Loan, Consumer Loan, Corporate Loan, Syndicated Loan, Credit Facility, Credit Management, Limit And Exposure, Collateral | Credit products |
| **Payments** | Payment Order, Payment Instruction, Payment Execution, Direct Debit Mandate, Standing Order | Instruction → settlement |
| **Cards** | Card Authorization, Card Capture, Card Clearing, Card Collections | Card lifecycle |
| **Markets & trading** | Program Trading, Trade Settlement, Trade Clearing, eTrading Workbench | Capital markets |
| **Trade finance** | Letter Of Credit, Bank Guarantee, Trade Finance | Documentary products |
| **Risk & compliance** | Credit Risk Operations, Account Reconciliation, Fraud Evaluation | Control & integrity |
| **Collections** | Delinquent Account Handling, Account Recovery, Collections | Arrears |
| **Channels** | Session Dialogue, Contact Routing, Branch/eBranch/ATM Operations | Channel execution |
| **Documents** | Document Services, Document Library, Correspondence | Content & evidence |
| **Infrastructure** | Service Directory, Enterprise Architecture, Product Directory | Cross-cutting |

## RAG Fleet rule

- Product fleets declare `bian_service_domains` per rack.
- Reference fleet `bian` holds canonical knowledge.
- Dual-pull merges product policy with reference domains.
