# Business Scenario: Investment Portfolio Planning → Management

```text
1. Party Reference / Customer Offer — suitability, IPS intake
2. Investment Portfolio Planning.Initiate/Evaluate — goals, allocation model
3. Investment Portfolio Analysis.Retrieve/Evaluate — risk, performance inputs
4. Investment Account.Initiate — custody/cash structure
5. Investment Portfolio Management.Initiate/Execute — rebalance, corporate actions
6. eTrading Workbench.Execute — order routing (markets tier)
7. Investment Account.Update — holdings and cash sweeps
```

```mermaid
sequenceDiagram
    participant Plan as Portfolio Planning
    participant Anal as Portfolio Analysis
    participant Acct as Investment Account
    participant Mgmt as Portfolio Management
    participant Trade as eTrading Workbench

    Plan->>Plan: Initiate/Evaluate (IPS)
    Anal->>Anal: Retrieve/Evaluate
    Acct->>Acct: Initiate (account structure)
    Mgmt->>Mgmt: Execute (rebalance)
    Mgmt->>Trade: Execute (orders)
    Trade-->>Acct: Fills / settlements
    Acct->>Acct: Update holdings
```
