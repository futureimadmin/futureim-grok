# End-to-End BIAN + Agentic RAG

## Architecture (3D + agent loop)

```
Fleet (domain, platform=bian|generic)
  └── Rack (sub-domain) ──► bian_service_domains[]
  └── Tier (logical group) ──► bian_service_domains[] + rack_ids[]

Reference fleet: bian (is_reference=true)
Banking fleets: dual-pull product + BIAN reference domains
```

Agent loop (Agentic RAG diagram):

1. **Planner** — sub-goals; BIAN dual-retrieve + optional codegen
2. **Tools** — `rag_retrieval` (dual), `bian_codegen`, `accuracy_evaluator`
3. **Memory** — plan / act / observe / critique
4. **Generate** — grounded answer or BIAN service stubs
5. **RAGAS** — faithfulness, relevance, precision, recall; retry if below threshold

## Console UI

- Select fleet → racks show mapped BIAN domains
- **Active BIAN service domains** panel (version, dual-pull hint)
- Modes:
  - **Ask** — scoped Q&A
  - **Agentic RAG** — full loop + reasoning trace + RAGAS
  - **Codegen** — stubs only for *active* domains (Python / TypeScript / Java)

## APIs

| Endpoint | Purpose |
|----------|---------|
| `GET /api/fleets` | Fleets with tiers, racks, BIAN fields |
| `GET /api/fleets/{id}/bian?rack_id=&tier_id=` | Active domains for scope |
| `POST /api/v1/query` | `mode=ask\|agentic\|codegen` |
| `POST /api/v1/codegen` | Shortcut for codegen |
| `POST /api/v1/agentic/query` | Agentic path |
| `GET /api/accuracy/summary` | Dashboard metrics |

## Codegen policy

- Only domains resolved for the selected rack/tier
- Operations: Initiate, Update, Control, Retrieve, Execute, … (per domain)
- `# EXTENSION: bank-specific policy` markers — never silent BIAN forks
- Deterministic stubs offline; LLM enrichment when Vertex is configured

## Seed & run (preview)

```bat
set PYTHONPATH=.
python scripts\seed_bian_knowledge.py
python -m uvicorn apps.ui.preview:app --reload --port 8081
```

Open http://127.0.0.1:8081 — pick **Consumer Lending → Mortgages**, switch to **Codegen**, submit.

## Production

- Same agent path via `AgenticRAG` with Vertex embeddings + Gemini
- Dual-pull filters enforced on Vector Search restricts
- Volume unconstrained by design; scale index shards operationally
