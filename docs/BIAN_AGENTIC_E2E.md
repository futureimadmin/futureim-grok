# End-to-End BIAN + Agentic RAG

## Architecture (3D + agent loop)

```
Fleet (domain, platform=bian|generic)
  └── Rack (sub-domain) ──► bian_service_domains[]
  └── Tier (logical group) ──► bian_service_domains[] + rack_ids[]

Reference fleet: bian (is_reference=true)
Banking fleets: dual-pull product + BIAN reference domains
```

Agent loop:

1. **Planner** — sub-goals; BIAN dual-retrieve + optional codegen
2. **Tools** — `rag_retrieval` (dual), `bian_codegen`, `accuracy_evaluator`
3. **Memory** — plan / act / observe / critique
4. **Generate** — grounded answer or BIAN service stubs
5. **RAGAS** — faithfulness, relevance, precision, recall; retry if below threshold

## Console UI

- Select fleet → racks show mapped BIAN domains
- **Active BIAN service domains** panel
- Modes: **Ask** | **Agentic RAG** | **Codegen**

## Seed & run (preview)

```bat
set PYTHONPATH=.
python scripts\seed_bian_knowledge.py
python -m uvicorn apps.ui.preview:app --reload --port 8081
```

## Production

- Same agent path with Vertex embeddings + Gemini
- Dual-pull filters on Vector Search restricts
- Volume unconstrained; scale index shards operationally
