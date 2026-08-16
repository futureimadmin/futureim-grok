# RAG System – GCP Deployment Architecture

This document maps the logical layers from *RAG Architecture Complete* onto concrete Google Cloud services and network boundaries.

## High-level diagram (logical)

```
┌──────────────────────────────────────────────────────────────────────┐
│                         PUBLIC INTERNET                              │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ HTTPS
                    ┌───────────▼───────────┐
                    │  public-ingress       │  Cloud Load Balancing /
                    │  (10.10.0.0/24)       │  Cloud Run (ingress)
                    └───────────┬───────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
┌─────────▼─────────┐  ┌────────▼────────┐  ┌─────────▼─────────┐
│ private-serving   │  │ private-data    │  │ private-ingestion │
│ (10.10.2.0/24)    │  │ (10.10.3.0/24)  │  │ (10.10.1.0/24)    │
│                   │  │                 │  │                   │
│ • Orchestrator    │  │ • Memorystore   │  │ • Chunker         │
│ • Hybrid Retriever│◄─┤   Redis         │◄─┤ • Embedder        │
│ • Reranker        │  │ • (future       │  │ • GCS processors  │
│ • Prompt Builder  │  │   AlloyDB)      │  │                   │
│ • LLM client      │  │                 │  │                   │
│ (Cloud Run)       │  │                 │  │ (Cloud Run Jobs)  │
└─────────┬─────────┘  └────────┬────────┘  └─────────┬─────────┘
          │                     │                     │
          │                     │                     │
          └──────────┬──────────┴──────────┬──────────┘
                     │                     │
              ┌──────▼──────┐       ┌──────▼──────┐
              │ Vertex AI   │       │ Cloud       │
              │ Vector      │       │ Storage     │
              │ Search /    │       │ (documents) │
              │ RAG Engine  │       └─────────────┘
              └─────────────┘
```

## Network policy summary

| Source plane     | Destination plane | Allowed? | Rationale |
|------------------|-------------------|----------|-----------|
| Ingestion        | Serving           | **No**   | Architectural boundary – only vector store is shared |
| Serving          | Ingestion         | **No**   | Same |
| Ingestion        | Data              | Yes      | Write semantic cache / private endpoints |
| Serving          | Data              | Yes      | Read semantic cache |
| Both             | Google APIs       | Yes      | Private Google Access |
| Internet         | Ingestion         | No       | Offline only |
| Internet         | Serving           | Via LB   | Controlled public surface |

## Service mapping

| Component (doc)          | GCP service                          | Notes |
|--------------------------|--------------------------------------|-------|
| Document source          | Cloud Storage + Eventarc             | Object finalize → Pub/Sub or direct Cloud Run |
| Chunker                  | Cloud Run Job / Function             | Runs in private-ingestion |
| Embedder                 | Vertex AI text-embedding-004         | Same model at query time |
| Vector store             | Vertex AI Vector Search **or** RAG Engine (RagManagedDb) **or** AlloyDB + pgvector | Managed preferred |
| Doc store                | Firestore / AlloyDB / Redis          | Point lookups by chunk_id |
| Semantic cache           | Memorystore Redis (HA)               | Cosine similarity on query embeddings |
| Orchestrator             | Cloud Run (private-serving)          | Stateless, auto-scales |
| BM25                     | Elasticsearch on GKE **or** OpenSearch **or** in-memory rank_bm25 for small corpora | |
| Cross-encoder            | Cohere Rerank API **or** self-hosted on GPU | |
| LLM                      | Vertex AI Gemini 2.0 Flash / Pro     | Temperature 0.0–0.3 |
| Observability            | Cloud Logging, Trace, Monitoring + LangSmith / Ragas | |

## Security boundaries

1. **Network** – VPC + firewall + Private Google Access + VPC Access connector.
2. **Identity** – Separate service accounts per plane (`rag-ingestion`, `rag-serving`, `rag-orchestrator`).
3. **Data** – Tenant-scoped metadata filters; cache keys always include `tenant_id`.
4. **Access control** – `access_level` metadata filter applied before ANN search.
5. **Secrets** – Secret Manager for Redis AUTH and any API keys.

## Scaling notes

- All application components are **stateless** → horizontal scaling via Cloud Run.
- Vector index and Redis are the only stateful pieces; both are managed and support sharding / HA.
- Ingestion is fully asynchronous; a spike in document uploads never affects query latency.
