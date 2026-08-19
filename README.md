# futureim-rag-fleet

Production-grade **RAG Fleet** on GCP with **BIAN 3D architecture** (Fleet → Rack → Tier), hybrid retrieval, Agentic RAG + RAGAS accuracy, and BIAN-aligned codegen.

## Highlights

| Capability | Detail |
|------------|--------|
| **3D model** | Fleet (domain) · Rack (sub-domain) · Tier (logical group) |
| **BIAN platform** | Banking fleets dual-pull product + reference BIAN domains |
| **Hybrid retrieval** | Dense ANN + BM25 + RRF + rerank + Top-K token budget |
| **Agentic RAG** | Planner → tools → generate → RAGAS → retry |
| **Codegen** | BIAN service stubs (Initiate/Update/Control/Execute/…) |
| **Accuracy dashboard** | Faithfulness, relevance, precision, recall, pass rate |
| **GCP** | Vertex AI, Cloud Run, Eventarc, Memorystore, Terraform |

## Quick start (preview)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set PYTHONPATH=.
python scripts\seed_bian_knowledge.py
python -m uvicorn apps.ui.preview:app --reload --port 8081
```

Open http://127.0.0.1:8081

- **Console** `/` — fleets, racks, tiers, BIAN domain chips, Ask / Agentic / Codegen
- **Dashboard** `/dashboard` — RAGAS metrics
- **Admin** `/admin` — fleet admin UI

## Key paths

```
apps/ui/preview.py          # Local preview API + UI
src/agentic/                # AgenticRAG + metrics + store
src/query/retrieval.py      # Hybrid + retrieve_dual
src/query/codegen.py        # BIAN stubs
src/query/bian_context.py   # Dual-pull filters
config/fleets/registry.yaml # Fleet / rack / tier registry
fleets/bian/                # BIAN knowledge (seed → vector/doc store)
scripts/seed_bian_knowledge.py
scripts/upload_bian_to_gcs.py
infra/terraform/            # VPC, services, IAM, Eventarc, vector search
```

## GCP placeholders

Set in `.env` or Cloud Run env (see `.env.example` / `docs/GCP_CONFIG.md`):

- `GCP_PROJECT` / `GCP_REGION`
- `DOCUMENTS_BUCKET` / `PROCESSED_BUCKET`
- `VECTOR_INDEX_ID` / `VECTOR_ENDPOINT_ID`
- `REDIS_HOST` / `REDIS_PORT`

## Licence

Proprietary – FutureIM. All rights reserved.
