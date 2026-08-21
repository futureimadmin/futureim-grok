# BIAN Service Domain Catalog (RAG Fleet reference)

Curated for futureim-rag-fleet. Full BIAN Landscape (v12–v14) has 300+ domains;
this catalog prioritises dual-pull, enterprise common services, and codegen.

## Enterprise-shared (common to all Fleets / Racks / Tiers)

Party Lifecycle Management (KYC/KYB), Party Reference Data Management, Party Data Management,
Legal Entity Directory, Customer Profile, Party Authentication, Customer Access Entitlement,
Transaction Authorization, Document Services, Fraud Evaluation, Customer Credit Rating,
Regulatory Reporting, Customer Agreement, Customer Product And Service Eligibility,
Customer Position, Servicing Event History, Financial Gateway.

These map to fleet **enterprise** in the registry.

## Categories

| Category | Examples |
|----------|----------|
| Party / KYC | Party Lifecycle Management, Party Data Management, Legal Entity Directory |
| Customer | CRM, Offer, Agreement, Eligibility, Position |
| Cross Channel | Party Authentication, Transaction Authorization |
| Lending | Loan, Mortgage, Consumer/Corporate/Syndicated, Credit Facility, Project Finance |
| Accounts | Current, Savings, Term Deposit, Virtual Account, Standing Order |
| Payments | Payment Order, Execution, Initiation, Direct Debit, Financial Gateway |
| Cards | Card Transaction, Capture, Clearing, Billing, Case, Collections |
| Investments | Investment Account, Portfolio Planning/Analysis/Management, eTrading |
| Trade | Letter of Credit, Bank Guarantee, Trade Finance |
| Risk | Fraud Evaluation, Customer Credit Rating, Regulatory Reporting |
| Infrastructure | Document Services, Financial Gateway |

## Rule

1. Enterprise common always dual-pull from bian domains (or scope fleet enterprise).
2. Product fleets add product-specific domains only.
3. Codegen emits stubs only for resolved domains for the selected scope.
