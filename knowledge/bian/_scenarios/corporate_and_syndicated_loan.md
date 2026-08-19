# Business Scenario: Corporate Loan and Syndicated Loan

## Corporate Loan (bilateral)

```text
Customer Offer.Initiate/Retrieve
Credit Management.Evaluate
Limit And Exposure Management.Retrieve/Evaluate  — headroom check
Credit Facility.Initiate/Update                 — commitment
Corporate Loan.Initiate                         — facility CR
Payment Order/Execution                         — drawdown
Limit And Exposure Management.Update            — utilisation
```

## Syndicated Loan

```text
Syndicated Loan.Initiate — syndicate structure, agent role, participations
Credit Facility.Update   — multi-lender commitment view
Limit And Exposure Management.Evaluate — each participant / group
Syndicated Loan.Notify   — transfer notices, agent events
Payment Execution        — agent distribution of drawdowns/repayments
```

## Boundaries

| Domain | Owns |
|--------|------|
| Corporate Loan | Bilateral facility lifecycle |
| Syndicated Loan | Multi-lender coordination, participations |
| Credit Facility | Commitment / availability independent of a single loan instance |
| Limit And Exposure | Enterprise aggregation across products and obligors |

## Coding

- Agent bank role is behaviour on Syndicated Loan + Payment Execution.
- Participation transfer = Update/Notify on Syndicated Loan, then exposure re-Evaluate.
