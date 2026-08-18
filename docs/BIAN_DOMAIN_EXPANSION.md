# BIAN 3D Architecture — Extended Service & Data Domains

## Model reminder

| Dimension | Role | Example |
|-----------|------|---------|
| **Fleet** | Domain product line | `corporate_lending`, `investments`, `core_banking` |
| **Rack** | Sub-domain specialty | `syndicated`, `portfolio_management`, `current_accounts` |
| **Tier** | Logical group of racks | `origination`, `portfolio_mgmt`, `accounts` |
| **BIAN reference** | Base platform knowledge | fleet `bian` |

All banking fleets use `platform: bian` and dual-pull product + reference domains.

## Banking fleets (product)

| Fleet | Focus | Primary BIAN service domains |
|-------|--------|------------------------------|
| **consumer_lending** | Retail credit | Loan, Collateral, Credit Management, Customer Offer |
| **corporate_lending** | Commercial credit | Corporate Loan, Syndicated Loan, Credit Facility, Project Finance, Limit And Exposure Management |
| **investments** | Wealth / AM | Investment Portfolio Planning/Analysis/Management, Investment Account, eTrading Workbench |
| **core_banking** | Deposits & CASA | Current Account, Savings Account, Term Deposit, Virtual Account, Standing Order |
| **payments** | Rails | Payment Order, Payment Execution, Card Transaction |
| **trade_finance** | Documentary trade | Letter of Credit, Bank Guarantee, Trade Finance |
| **customer_relationship** | CRM | Party Reference, Customer Offer, Customer Agreement |
| **insurance** | Protection | (product-specific; extend BIAN as needed) |

## Reference fleet racks (structural knowledge)

Under `fleets/bian/` — seed with `scripts/seed_bian_knowledge.py`. Volume is not capped.

## Data domains (BOM-aligned)

Cross-cutting business objects used across fleets:

- **Party** — customer, obligor, counterparty
- **Facility / Arrangement** — control records for loans, accounts, LCs
- **Limit / Exposure** — group and product buckets
- **Payment / Settlement** — order and execution
- **Collateral** — security interests
- **Portfolio / Holding** — investment positions
- **Product / Offer / Agreement** — commercial packaging

## Codegen

`src/query/codegen.py` maps each active domain to Initiate/Update/Control/Retrieve/Execute-style stubs.
Codegen mode only emits domains resolved for the selected rack/tier.

## How to extend further

1. Add racks under fleet `bian` with `bian_service_domains`.
2. Map product fleet racks → those domains.
3. Drop markdown under `fleets/bian/{rack}/` and re-seed.
4. Optional: add operations to `DOMAIN_OPERATIONS` in codegen.py.
