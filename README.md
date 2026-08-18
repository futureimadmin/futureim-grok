# futureim-rag-fleet

**Production-grade Retrieval-Augmented Generation (RAG) Fleet** with BIAN platform, Agentic RAG, and 3D Fleet/Rack/Tier isolation.

See `docs/BIAN_AGENTIC_E2E.md` and `docs/BIAN_3D_ARCHITECTURE.md` for BIAN dual-pull, codegen, and agent loop.

## Quick start (preview)

```bat
set PYTHONPATH=.
pip install -r requirements-preview.txt
python scripts\seed_bian_knowledge.py
python -m uvicorn apps.ui.preview:app --reload --port 8081
```

Open http://127.0.0.1:8081 — select a banking fleet, view active BIAN domains, use Ask / Agentic / Codegen modes.

## Layout

- `src/` — ingestion, query, orchestrator, agentic, fleet
- `apps/ui` — Fleet Console + Accuracy Dashboard
- `config/fleets/registry.yaml` — 3D registry (BIAN platform)
- `fleets/bian/` / `knowledge/bian/` — BIAN reference docs
- `infra/terraform/` — VPC, Eventarc, Vector Search, IAM
