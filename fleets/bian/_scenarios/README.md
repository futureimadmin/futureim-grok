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
| `customer_onboarding.md` | Party → CRM → Offer → facility |
| `card_authorization_flow.md` | Auth → capture → clearing separation |

Also see `fleets/bian/_patterns/service_operations.md` for CR/BQ operation taxonomy.
