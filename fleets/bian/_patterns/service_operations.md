# BIAN Service Operations Taxonomy

**Source pattern:** BIAN Service Landscape (control-record style operations).
**Use:** Agents and codegen must map APIs to these verbs — never invent ad-hoc CRUD names for structural boundaries.

## Standard operations (Control Record / Business Qualifier)

| Operation | Typical HTTP | Lifecycle | Idempotent | Meaning |
|-----------|--------------|-----------|------------|---------|
| **Initiate** | POST | Creation | No | Create a new CR or BQ instance (facility, order, mandate) |
| **Register** | POST | Creation | No | Register in a directory/catalog |
| **Evaluate** | POST | Creation | No | Assessment / agreement establishment |
| **Update** | PUT | Modification | Yes | Change attributes of an existing instance |
| **Control** | PUT | Lifecycle | Yes | Suspend, resume, terminate processing |
| **Exchange** | PUT | Verification | Yes | Accept, verify, acknowledge external data |
| **Execute** | PUT | Execution | No | Trigger automated action (clearing, accrual, disbursement) |
| **Request** | PUT | Intervention | No | Request manual review or decision |
| **Retrieve** | GET | Query | Yes | Read state or history (CQRS-friendly) |
| **Notify** | GET | Subscription | Yes | Notification / event subscription status |
| **Capture** | PUT | Recording | No | Capture activity without full lifecycle change |

## CR + BQ structure (every service domain)

```
Service Domain (bounded context)
  └── Control Record (CR) — aggregate root, e.g. LoanFacility, CurrentAccountFacility
        ├── Initiate / Update / Control / Execute / Request / Retrieve / Exchange
        └── Business Qualifiers (BQ) — sub-aggregates
              e.g. Disbursement, Repayment, Interest, Fees, Collateral, Lien
```

- **CR** owns the facility lifecycle.
- **BQ** owns a specialized aspect; operations are scoped under the CR instance.
- Domains exchange **only** through service operations — not shared databases.

## Coding rule for RAG Fleet codegen

1. One module per BIAN service domain.
2. Methods named after operations above.
3. Mark bank policy with `# EXTENSION: bank-specific policy`.
4. Sequence scenarios (under `_scenarios/`) define cross-domain order of calls.
