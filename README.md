# futureim-rag-fleet

Production-oriented **Agentic RAG** on GCP with a **3D logical model** (Fleet → Rack → Tier) and **BIAN** as the banking base platform.

---

## Architecture diagram

![futureim-rag-fleet — Agentic RAG Architecture (BIAN 3D)](docs/architecture-agentic-rag-bian-3d.jpg)

> Image path: `docs/architecture-agentic-rag-bian-3d.jpg`  
> If the image is missing on a shallow clone, add it from the product docs package (same diagram as above).

**Subtitle:** *3D Logical Isolation — Fleet (domain) → Rack (sub-domain) → Tier (logical group) | BIAN base platform for banking*

```text
┌──────────────────┐  ┌──────────────┐  ┌─────────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│ LAYER 1 OFFLINE  │  │ SHARED       │  │ LAYER 2 ONLINE      │  │ LAYER 3 AGENTIC  │  │ LAYER 4         │
│ INGESTION        │→ │ STORES       │→ │ QUERY / HYBRID      │→ │ RAG LOOP         │→ │ ACCURACY & UI   │
│ GCS→Eventarc→    │  │ Vector+Doc+  │  │ Retriever + Dual-   │  │ Plan→Act→Reflect │  │ RAGAS + Console │
│ Chunk→Embed      │  │ Redis cache  │  │ Pull + Prompt       │  │ + tools + retry  │  │ Dashboard       │
└──────────────────┘  └──────────────┘  └─────────────────────┘  └──────────────────┘  └─────────────────┘
```

---

## Layer-by-layer walkthrough

### Layer 1 — Offline ingestion

| Component | Role |
|-----------|------|
| **Cloud Storage** | Documents bucket holds product + BIAN markdown under `fleets/{fleet}/{rack}/…` |
| **Eventarc** | On object finalize, triggers the ingestion Cloud Run job |
| **Cloud Run ingestion** | Semantic chunk (default 256 tokens / 32 overlap) → Vertex embeddings → **dual-write** |

**Dual-write** means each chunk is stored twice:

1. **Vector Search** — embedding + metadata restricts (`fleet_id`, `rack_id`, `tier_id`, `bian_service_domain`, …) — *no raw text*
2. **DocStore** — `chunk_id` → raw text + full metadata

Ingestion never runs on the live user path. Query only *reads* shared stores.

### Shared stores

| Store | Role |
|-------|------|
| **Vertex AI Vector Search** | ANN dense search with fleet/rack/tier/BIAN restricts |
| **DocStore** | Hydrate text after ANN/BM25 return chunk IDs |
| **Memorystore Redis** | Semantic cache (query embedding cosine ≥ ~0.92) |

### Layer 2 — Online query / hybrid retrieval

| Component | Role |
|-----------|------|
| **API Gateway / Fleet Console UI** | Entry for humans and services |
| **Modes** | **Ask** · **Agentic** · **Codegen** (BIAN stubs) |
| **Hybrid Retriever** | Dense ANN + BM25 → **RRF** → cross-encoder **rerank** → **Top-K token budget** |

#### BIAN dual-pull (banking fleets)

For fleets with `platform: bian`:

1. **Product pull** — filter by `fleet_id` / `rack_id` / `tier_id` (bank policy, rates, journeys)
2. **BIAN reference pull** — `fleet_id=bian` + active `bian_service_domain` list (structure + sequences)
3. **Merge** by `chunk_id` / score, reserve a share of slots for BIAN hits
4. **Four-slot prompt** — system + context + grounding guardrail + query, with BIAN domain hints

### Layer 3 — Agentic RAG loop

| Component | Role |
|-----------|------|
| **Planner** | Decompose goals; detect **codegen intent** |
| **ReAct / CoT + Tool Registry** | Tools: `rag_retrieval`, `bian_codegen`, `accuracy_evaluator` |
| **Agent Memory** | plan → act → observe → critique |
| **Self-Reflection + Retry** | If RAGAS &lt; threshold, widen retrieval / re-plan and retry |

### Layer 4 — Accuracy & UI

| Component | Role |
|-----------|------|
| **RAGAS metrics** | Faithfulness, Answer Relevance, Context Precision, Context Recall, composite |
| **Accuracy Dashboard** | Live aggregates, pass rate, latency, by-fleet stats |
| **Fleet Console** | Active BIAN domain chips, rack/tier scope, Ask / Agentic / Codegen |

---

## What is RAG?

**Retrieval-Augmented Generation** grounds an LLM answer in *your* documents instead of model memory alone.

```text
User question
    → embed / expand query
    → retrieve top chunks (hybrid)
    → build prompt with only those chunks
    → LLM generates answer + [Source N] citations
    → post-process (citations, light faithfulness, PII redaction)
```

**Why it matters for banking:** product rules and BIAN structure change; RAG keeps answers tied to versioned knowledge with metadata isolation (tenant, fleet, rack, access level).

---

## What is RAGAS and how is it integrated?

**RAGAS** (here: RAG Assessment–style scores) measures answer quality against retrieved context:

| Metric | Meaning |
|--------|---------|
| **Faithfulness** | Are answer claims supported by retrieved chunks? |
| **Answer relevance** | Does the answer address the question? |
| **Context precision** | Are retrieved chunks useful for the query? |
| **Context recall** | Did context cover what the answer needed? |
| **Composite (RAGAS score)** | Weighted blend (faithfulness weighted highest); target **≥ 0.80** |

**Integration path:**

1. Agent (or Ask path) produces `answer` + `chunks`
2. Tool `accuracy_evaluator` runs `evaluate_accuracy()` in `src/agentic/metrics.py`
3. Offline heuristics (token overlap / sentence grounding); can upgrade to LLM-as-judge when Vertex is configured
4. Result stored in `accuracy_store` for `/dashboard`
5. If composite &lt; threshold and mode is agentic Q&A → **retry loop** (drop rack filter, re-retrieve, regenerate)

Codegen mode is **structural**; threshold is treated as soft-pass after one eval.

---

## How the LLM is integrated

| Stage | Model use |
|-------|-----------|
| **Embed** | Vertex `text-embedding-004` (same model at ingest and query) |
| **Optional HyDE** | Gemini writes a short hypothetical answer; its embedding is used for dense ANN |
| **Generate** | Gemini (`gemini-2.0-flash-001` by default) with four-slot grounded prompt |
| **Codegen enrich** | Optional: same LLM polishes deterministic BIAN stubs |
| **RAGAS judge** | Optional LLM-as-judge; default is heuristic so preview works offline |

If Vertex is not configured, preview still runs: mock grounded answers, deterministic stubs, heuristic RAGAS.

---

## How code is generated (Codegen mode)

1. User selects a **banking fleet + rack** (and optional tier).
2. System resolves **active BIAN service domains** for that scope (`resolve_bian_domains`).
3. Tool `bian_codegen` / `generate_stubs()` emits **one stub module per domain**.
4. Operations follow the BIAN-style taxonomy: **Initiate → Update → Control → Execute → Retrieve → Request → Exchange** (domain-specific subset).
5. Languages: **Python** (default), TypeScript, Java.
6. Markers: `# EXTENSION: bank-specific policy` — never silent forks of BIAN semantics.
7. Optional LLM pass can enrich stubs using dual-pulled BIAN + product context.

Stubs are **scaffolding only** — authZ, audit, and human review are required before production.

---

## Fleet vs Rack vs Tier (3D logical model)

| Axis | Meaning | Example |
|------|---------|---------|
| **Fleet** | Domain boundary | Consumer Lending, Core Banking, Investments |
| **Rack** | Sub-domain specialty | Mortgages, Current Accounts, Letters of Credit |
| **Tier** | Logical group of racks / capabilities | Originations, Servicing, Documentary Trade |

All three are **logical**, not physical capacity units. Isolation is **metadata** on one (or sharded) Vector Search index:

`fleet_id` · `rack_id` · `tier_id` · `bian_service_domain` · `bian_version` · `tenant_id` · `access_level`

**Volume is not a design limit** — scale index shards; filter for relevance.

---

## What is BIAN?

**BIAN (Banking Industry Architecture Network)** is an industry standard for *service domains*, *business objects*, and *service operations* in banks.

In this system:

| Concept | Role |
|---------|------|
| **Reference fleet `bian`** | `is_reference: true` — canonical service-domain docs, scenarios, patterns |
| **Banking product fleets** | `platform: bian`, `reference_fleet_id: bian` — dual-pull product + reference |
| **Service domains** | e.g. Loan, Credit Management, Payment Order, Current Account |
| **Scenarios / sequences** | Cross-domain order (offer → credit → collateral → loan → payment) |
| **Operations taxonomy** | Initiate, Update, Control, Execute, Retrieve, Request, Exchange |

Product docs stay under `fleets/{product_fleet}/…`. BIAN structure stays under `fleets/bian/…`. Agents and codegen **prefer BIAN names for boundaries** and product docs for policy and rates.

---

## Fleets in the diagram (examples)

| Fleet | Platform |
|-------|----------|
| Consumer Lending | bian |
| Corporate Lending | bian |
| Core Banking | bian |
| Investments | bian |
| Trade Finance | bian |
| **bian** (reference) | bian, `is_reference` |

Knowledge layout: `service domains` · `_scenarios` sequences · `_patterns` operations taxonomy.

---

## Quick start (preview)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set PYTHONPATH=.
python scripts\seed_bian_knowledge.py
python -m uvicorn apps.ui.preview:app --reload --port 8081
```

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8081/ | Fleet Console (Ask / Agentic / Codegen) |
| http://127.0.0.1:8081/dashboard | RAGAS accuracy dashboard |
| http://127.0.0.1:8081/admin | Fleet admin UI |

GCP placeholders: `.env.example` / `docs/GCP_CONFIG.md` (`GCP_PROJECT`, buckets, Vector Search, Redis).

Upload BIAN docs to GCS (when ready for Eventarc): `python scripts/upload_bian_to_gcs.py --dry-run`

---

## Key source paths

```text
apps/ui/preview.py              Preview API + UI
src/agentic/                    AgenticRAG, metrics, tools, memory
src/query/retrieval.py          Hybrid + retrieve_dual
src/query/codegen.py            BIAN stubs
src/query/bian_context.py       Dual-pull filters
src/orchestrator/orchestrator.py  Standard Ask path
config/fleets/registry.yaml     Fleet / rack / tier registry
config/fleets/banking_extensions.yaml  Extra banking fleets (merged at load)
fleets/bian/                    BIAN knowledge tree
scripts/seed_bian_knowledge.py
scripts/upload_bian_to_gcs.py
infra/terraform/                VPC, services, IAM, Eventarc, vector search
docs/architecture-agentic-rag-bian-3d.jpg
```

---

## Licence

Proprietary – FutureIM. All rights reserved.
