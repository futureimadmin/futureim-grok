# BIAN Service Operations Taxonomy

**Source pattern:** BIAN Service Landscape (control-record style operations).
**Use:** Agents and codegen must map APIs to these verbs — never invent ad-hoc CRUD names for structural boundaries.

## Standard operations (Control Record / Business Qualifier)

| Operation | Typical HTTP | Lifecycle | Idempotent | Meaning |
|-----------|--------------|-----------|------------|---------|
| **Initiate** | POST | Creation | No | Create a new CR or BQ instance |
| **Register** | POST | Creation | No | Register in a directory/catalog |
| **Evaluate** | POST | Creation | No | Assessment / agreement establishment |
| **Update** | PUT | Modification | Yes | Change attributes of an existing instance |
| **Control** | PUT | Lifecycle | Yes | Suspend, resume, terminate processing |
| **Exchange** | PUT | Verification | Yes | Accept, verify, acknowledge external data |
| **Execute** | PUT | Execution | No | Trigger automated action |
| **Request** | PUT | Intervention | No | Request manual review or decision |
| **Retrieve** | GET | Query | Yes | Read state or history |
| **Notify** | GET | Subscription | Yes | Notification / event subscription status |
| **Capture** | PUT | Recording | No | Capture activity without full lifecycle change |

## CR + BQ structure

Service Domain → Control Record (aggregate root) → Business Qualifiers (sub-aggregates).
Domains exchange only through service operations — not shared databases.
