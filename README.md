# futureim-grok

**Production-grade Retrieval-Augmented Generation (RAG) system** implementing the complete architecture described in *RAG Architecture Complete*.

The system is designed with **strict layer boundaries**:

| Layer | Responsibility | Network plane |
|-------|----------------|---------------|
| **Ingestion** | Offline write pipeline (Chunker → Embedder → Vector + Doc store) | `private-ingestion` subnet |
| **Query Path** | Online read pipeline (Orchestrator → Retrieval → Rerank → Generate) | `private-serving` subnet |
| **Shared State** | Vector store + semantic cache (the *only* interface between layers) | `private-data` subnet |
| **Edge** | Public API / Load Balancer | `public-ingress` subnet |

Ingestion and query path **never communicate directly**. The vector store is the sole shared boundary.

---

## Architecture Highlights

- **Semantic chunking** with configurable overlap and rich metadata (tenant, product, access level, language, section heading …)
- **Same embedding model** at ingest and query time (non-negotiable)
- **Hybrid retrieval** (dense ANN + BM25) fused with **Reciprocal Rank Fusion (RRF)**
- **Cross-encoder reranking** before prompt assembly
- **Four-slot prompt structure** (system → context → grounding guardrail → query)
- **Semantic cache** (Redis) with cosine similarity threshold
- **Faithfulness / citation resolution / safety** post-processing pipeline
- **GCP-native**: Vertex AI embeddings + Gemini, Cloud Run, Memorystore, Eventarc, Terraform

---

## Repository Layout

```
futureim-grok/
├── infra/terraform/
│   ├── modules/
│   │   ├── vpc/          # Custom VPC + 4 subnets + firewall boundaries
│   │   ├── services/     # GCS, Redis, Pub/Sub, Artifact Registry, private services
│   │   └── iam/          # Plane-specific service accounts
│   └── environments/dev/ # Ready-to-apply root module
├── src/
│   ├── common/           # Config, models
│   ├── ingestion/        # Chunker, Embedder
│   ├── orchestrator/     # 5-stage decision engine
│   └── query/            # (retrieval, cache, prompt, post-process – extend here)
├── apps/api/             # FastAPI Cloud Run service
├── Dockerfile
├── requirements.txt
└── docs/
```

---

## Infrastructure (GCP)

### Network boundaries

Terraform creates a custom VPC (`rag-vpc`) with four subnets:

| Subnet | CIDR (default) | Purpose |
|--------|----------------|---------|
| `rag-vpc-public-ingress` | 10.10.0.0/24 | Cloud Run ingress / LB |
| `rag-vpc-private-ingestion` | 10.10.1.0/24 | Document processors (offline) |
| `rag-vpc-private-serving` | 10.10.2.0/24 | Query orchestrator + retrieval |
| `rag-vpc-private-data` | 10.10.3.0/24 | Memorystore Redis, private endpoints |

Firewall rules enforce the architectural invariant:

- Ingestion ↔ Serving traffic is **denied**
- Both planes may reach the data plane (Redis, private services)
- Private Google Access + Cloud NAT for controlled egress
- Serverless VPC Access connector for Cloud Run → Redis

### Quick start (Terraform)

```bash
cd infra/terraform/environments/dev
cp terraform.tfvars.example terraform.tfvars
# edit project_id
terraform init
terraform plan
terraform apply
```

Required IAM for the applying principal:

- `roles/owner` or a combination of Compute Network Admin, Redis Admin, Storage Admin, IAM Admin, Service Usage Admin, etc.

---

## Application

### Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GCP_PROJECT=your-project
export GCP_REGION=us-central1
uvicorn apps.api.main:app --reload --port 8080
```

### Deploy to Cloud Run

```bash
# after terraform apply (Artifact Registry exists)
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT}/rag/query:latest
gcloud run deploy rag-query \
  --image ${REGION}-docker.pkg.dev/${PROJECT}/rag/query:latest \
  --region ${REGION} \
  --service-account rag-serving@${PROJECT}.iam.gserviceaccount.com \
  --vpc-connector rag-connector \
  --set-env-vars GCP_PROJECT=${PROJECT},REDIS_HOST=... \
  --allow-unauthenticated   # or protect with IAP / API key
```

---

## Mapping to the Architecture Document

| Document section | Implementation |
|------------------|----------------|
| 2.2 Chunker | `src/ingestion/chunker.py` – semantic / fixed / sentence |
| 2.3 Embedder | `src/ingestion/embedder.py` – Vertex AI dual-write pattern |
| 2.4 Vector Store | Vertex AI Vector Search (or AlloyDB pgvector) – configure via env |
| 3. Orchestrator | `src/orchestrator/orchestrator.py` – 5 stages |
| 4. Query Expansion / HyDE | Extend `src/query/` |
| 5. Hybrid Retrieval + RRF | Extend `src/query/retrieval.py` |
| 6. Cross-encoder rerank | Cohere Rerank or Vertex ranking API |
| 8. Prompt Builder | Four-slot structure (system / context / guardrail / query) |
| 10. Post-processing | Citation resolution, faithfulness, safety, cache write-back |
| 12. Scalability | Stateless Cloud Run + managed Redis + Vertex Vector Search |

---

## Next steps

1. Wire Vertex AI Vector Search index + endpoint (or AlloyDB + pgvector).
2. Implement full hybrid retriever + RRF + cross-encoder.
3. Add Eventarc trigger from GCS → Cloud Run ingestion job.
4. Complete semantic cache with Redis + embedding similarity.
5. Add Ragas / LangSmith evaluation harness.
6. Promote Terraform to a remote state backend and add a `prod` environment.

---

## Licence

Proprietary – FutureIM. All rights reserved.
