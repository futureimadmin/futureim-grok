# BIAN Base Platform + 3D Logical Model

## Intent

Make banking RAG (and future rack-scoped coding) **structurally robust**:

1. **BIAN** is the **base platform** knowledge layer in the vector/doc store.
2. Product **Fleets** extend BIAN with bank-specific policy and product content.
3. **Racks** are logical sub-domains; **Tiers** are logical groups of sub-domains, extended on demand.
4. **Volume is not a design limit** — Vertex AI Vector Search scales with shards/indexes; we partition with metadata, not by refusing knowledge.

## 3D logical model

```text
                    ┌─────────────────────────────────────┐
                    │  Tier (logical group, extendable)   │
                    │  e.g. Originations, Servicing       │
                    └──────────────┬──────────────────────┘
                                   │ groups
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
         ┌────────┐          ┌────────┐          ┌────────┐
         │  Rack  │          │  Rack  │          │  Rack  │
         └────┬───┘          └────┬───┘          └────┬───┘
              └───────────────────┼───────────────────┘
                                  ▼
                         ┌────────────────┐
                         │ Fleet (domain) │
                         │ platform: bian │
                         └────────┬───────┘
                                  │ extends
                                  ▼
                         ┌────────────────┐
                         │ BIAN reference │
                         │ fleet (base)   │
                         └────────────────┘
```

| Axis | Meaning | Physical? |
|------|---------|-----------|
| **Fleet** | Domain boundary | Logical (metadata namespace) |
| **Rack** | Sub-domain | Logical |
| **Tier** | Cross-rack capability group | Logical — add when needed |

## BIAN as base platform

- Fleet `bian` with `is_reference: true` holds canonical service-domain write-ups under `fleets/bian/{rack}/`.
- Banking fleets set `platform: bian` and `reference_fleet_id: bian`.
- Each rack lists `bian_service_domains` it implements or extends.

### Retrieval policy

For `fleet=consumer_lending`, `rack=mortgages`:

1. Retrieve product chunks (fleet/rack/tier filters).
2. Also retrieve BIAN reference chunks for that rack’s `bian_service_domains`.
3. Prompt builder prefers BIAN names for service boundaries; product docs for rates/policy.

## Volume / scale

| Concern | Approach |
|---------|----------|
| Large corpus | Horizontal scale of Vector Search; streaming upsert |
| Noisy retrieval | Restricts + tier/rack filters + hybrid RRF + rerank |
| Version drift | `bian_version` on every BIAN chunk |

We do **not** omit BIAN domains because the corpus is large. We **shard, filter, and version**.

## Seed & run

```bat
python scripts\seed_bian_knowledge.py
python -m uvicorn apps.ui.preview:app --reload --port 8081
```
