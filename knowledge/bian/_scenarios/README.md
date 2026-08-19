# BIAN Business Scenarios (sequence knowledge)

These documents encode **cross-domain sequences** in the style of BIAN business scenarios / sequence diagrams.
They are seeded into the `bian` reference fleet so Agentic RAG and Codegen can respect interaction order.

| File | Scenario |
|------|----------|
| `mortgage_loan_application.md` | Mortgage/loan origination chain |
| `payment_order_to_execution.md` | Payment instruction → settlement |
| `current_account_operations.md` | CA deposits, withdrawals, liens |
| `loan_lifecycle_and_delinquency.md` | Loan servicing + delinquency handoff |
| `corporate_and_syndicated_loan.md` | Corporate + syndicated flows |
| `investment_portfolio_flow.md` | Wealth planning → trading |

Also see `fleets/bian/_patterns/service_operations.md` for the CR/BQ operation taxonomy.

**Seed:** `python scripts/seed_bian_knowledge.py`
**GCS:** `python scripts/upload_bian_to_gcs.py`
