# BIAN 3D Architecture — Fleet · Rack · Tier

## Model

| Axis | Role | Example |
|------|------|---------|
| **Fleet** | Domain | `consumer_lending`, `payments`, `bian` (reference) |
| **Rack** | Sub-domain | `mortgages`, `loan`, `payment_order` |
| **Tier** | Logical group of sub-domains | `originations`, `servicing`, `lending_credit` |

All axes are **logical** (not physical infra). Tiers extend on need.

## BIAN as base platform

- Banking fleets set `platform: bian` and `reference_fleet_id: bian`.
- The `bian` fleet is the **canonical reference** knowledge in the vector store.
- Product fleets **extend** BIAN; they do not fork service-domain semantics without marking bank extensions in metadata.

## Dual-pull retrieval

For `platform: bian` product fleets:

1. Retrieve product fleet / rack content.
2. Also retrieve matching BIAN service domains from the reference fleet.
3. Merge with a reserved share of context slots for BIAN structure.

Filters constrain **relevance**, not **volume**. Scale Vector Search shards operationally.

## Coding guidance

RAG-scoped coding for banking racks should emit service and data shapes aligned to retrieved BIAN domains (Loan, Credit Management, Customer Offer, Payment Order, etc.).

See `config/fleets/registry.yaml` and `scripts/seed_bian_knowledge.py`.
