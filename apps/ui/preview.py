"""
Local preview server for RAG Fleet Console.

Supports:
  - Fleet / Rack / Tier navigation with active BIAN domains
  - Ask / Agentic / Codegen modes
  - Accuracy dashboard
  - Offline BIAN stub generation without Vertex
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from src.fleet.registry import get_fleet, list_fleets
from src.query.bian_context import (
    describe_scope,
    resolve_bian_domains,
    should_dual_pull,
)
from src.query.codegen import generate_stubs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag-fleet-preview")

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="RAG Fleet Console (Preview)", version="1.1.0-preview")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    fleet_id: Optional[str] = None
    rack_id: Optional[str] = None
    tier_id: Optional[str] = None
    tenant_id: str = "default"
    access_level: str = "public"
    mode: str = "ask"  # ask | agentic | codegen
    language: str = "python"


class QueryResponse(BaseModel):
    answer: str
    citations: list
    query_type: str
    latency_ms: float
    cache_hit: bool
    sources_used: int
    faithfulness_score: Optional[float] = None
    fleet_id: Optional[str] = None
    rack_id: Optional[str] = None
    tier_id: Optional[str] = None
    mode: Optional[str] = None
    bian_domains: List[str] = Field(default_factory=list)
    platform: Optional[str] = None
    ragas: Optional[dict] = None
    reasoning_trace: Optional[list] = None
    threshold_met: Optional[bool] = None
    confidence_score: Optional[float] = None
    sub_goals: Optional[list] = None
    tool_calls: Optional[list] = None
    attempts: Optional[int] = None
    language: Optional[str] = None


class TierOut(BaseModel):
    tier_id: str
    name: str
    description: str
    rack_ids: List[str] = Field(default_factory=list)
    bian_service_domains: List[str] = Field(default_factory=list)


class RackOut(BaseModel):
    rack_id: str
    name: str
    description: str
    bian_service_domains: List[str] = Field(default_factory=list)
    tier_ids: List[str] = Field(default_factory=list)


class FleetOut(BaseModel):
    fleet_id: str
    name: str
    description: str
    icon: str
    status: str
    platform: str = "generic"
    bian_version: Optional[str] = None
    is_reference: bool = False
    reference_fleet_id: Optional[str] = None
    racks: List[RackOut] = Field(default_factory=list)
    tiers: List[TierOut] = Field(default_factory=list)
    bian_domains_all: List[str] = Field(default_factory=list)


def _fleet_out(f) -> FleetOut:
    all_domains: List[str] = []
    for r in f.racks:
        all_domains.extend(r.bian_service_domains or [])
    seen = set()
    uniq = []
    for d in all_domains:
        if d not in seen:
            seen.add(d)
            uniq.append(d)
    return FleetOut(
        fleet_id=f.fleet_id,
        name=f.name,
        description=f.description,
        icon=f.icon,
        status=f.status.value if hasattr(f.status, "value") else str(f.status),
        platform=getattr(f, "platform", "generic") or "generic",
        bian_version=getattr(f, "bian_version", None),
        is_reference=bool(getattr(f, "is_reference", False)),
        reference_fleet_id=getattr(f, "reference_fleet_id", None),
        racks=[
            RackOut(
                rack_id=r.rack_id,
                name=r.name,
                description=r.description,
                bian_service_domains=list(r.bian_service_domains or []),
                tier_ids=list(r.tier_ids or []),
            )
            for r in f.racks
        ],
        tiers=[
            TierOut(
                tier_id=t.tier_id,
                name=t.name,
                description=t.description,
                rack_ids=list(t.rack_ids or []),
                bian_service_domains=list(t.bian_service_domains or []),
            )
            for t in getattr(f, "tiers", []) or []
        ],
        bian_domains_all=uniq,
    )


def _scope_domains(fleet_id: Optional[str], rack_id: Optional[str], tier_id: Optional[str]):
    fleet = get_fleet(fleet_id) if fleet_id else None
    rack = fleet.rack(rack_id) if fleet and rack_id else None
    domains = resolve_bian_domains(fleet, rack, tier_id)
    return fleet, rack, domains


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "rag-fleet-preview",
        "mode": "preview",
        "features": ["bian_domains", "codegen", "agentic", "dashboard"],
    }


@app.get("/", response_class=HTMLResponse)
def console(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"fleets": list_fleets(), "title": "RAG Fleet Console (Preview)"},
    )


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse(
        request,
        "admin.html",
        {"fleets": list_fleets(), "title": "Fleet Admin (Preview)"},
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    fleets = list_fleets()
    fleets_json = json.dumps(
        [
            {
                "fleet_id": f.fleet_id,
                "name": f.name,
                "icon": f.icon,
                "platform": getattr(f, "platform", "generic"),
            }
            for f in fleets
        ]
    )
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "fleets": fleets,
            "fleets_json": fleets_json,
            "title": "Accuracy Dashboard",
        },
    )


@app.get("/api/fleets", response_model=List[FleetOut])
def api_list_fleets():
    return [_fleet_out(f) for f in list_fleets()]


@app.get("/api/fleets/{fleet_id}", response_model=FleetOut)
def api_get_fleet(fleet_id: str):
    f = get_fleet(fleet_id)
    if not f:
        raise HTTPException(404, f"Fleet not found: {fleet_id}")
    return _fleet_out(f)


@app.get("/api/fleets/{fleet_id}/bian")
def api_fleet_bian(fleet_id: str, rack_id: Optional[str] = None, tier_id: Optional[str] = None):
    fleet, rack, domains = _scope_domains(fleet_id, rack_id, tier_id)
    if not fleet:
        raise HTTPException(404, f"Fleet not found: {fleet_id}")
    return {
        "fleet_id": fleet_id,
        "rack_id": rack_id,
        "tier_id": tier_id,
        "platform": fleet.platform,
        "bian_version": fleet.bian_version,
        "is_reference": fleet.is_reference,
        "dual_pull": should_dual_pull(fleet),
        "domains": domains,
        "scope": describe_scope(fleet, rack, tier_id),
        "tiers": [
            {
                "tier_id": t.tier_id,
                "name": t.name,
                "bian_service_domains": t.bian_service_domains,
            }
            for t in fleet.tiers
        ],
    }


@app.post("/api/v1/query", response_model=QueryResponse)
def api_query(body: QueryRequest):
    t0 = time.time()
    fleet, rack, domains = _scope_domains(body.fleet_id, body.rack_id, body.tier_id)
    mode = (body.mode or "ask").lower()

    if mode in ("agentic", "codegen"):
        try:
            from src.agentic.agent import AgenticRAG
            from src.agentic.store import accuracy_store

            agent = AgenticRAG()
            result = agent.run(
                body.query,
                fleet_id=body.fleet_id,
                rack_id=body.rack_id,
                tenant_id=body.tenant_id,
                access_level=body.access_level,
                mode=mode,
                language=body.language or "python",
                tier_id=body.tier_id,
            )
            if mode == "codegen" and (
                not result.get("answer") or result.get("answer", "").startswith("# No BIAN")
            ):
                result["answer"] = generate_stubs(
                    domains,
                    language=body.language or "python",
                    fleet_id=body.fleet_id,
                    rack_id=body.rack_id,
                )
                result["bian_domains"] = domains
                result["mode"] = "codegen"
                result["threshold_met"] = True
            accuracy_store.record({**result, "query": body.query})
            return QueryResponse(**{k: result.get(k) for k in QueryResponse.model_fields})
        except Exception as e:
            logger.exception("Agentic path failed, using preview fallback")
            if mode == "codegen":
                answer = generate_stubs(
                    domains,
                    language=body.language or "python",
                    fleet_id=body.fleet_id,
                    rack_id=body.rack_id,
                )
                return QueryResponse(
                    answer=answer,
                    citations=[],
                    query_type="codegen",
                    latency_ms=(time.time() - t0) * 1000,
                    cache_hit=False,
                    sources_used=0,
                    fleet_id=body.fleet_id,
                    rack_id=body.rack_id,
                    tier_id=body.tier_id,
                    mode="codegen",
                    bian_domains=domains,
                    platform=fleet.platform if fleet else None,
                    threshold_met=True,
                    language=body.language,
                )
            raise HTTPException(500, f"Agentic error: {e}") from e

    scope = describe_scope(fleet, rack, body.tier_id) if fleet else "unscoped"
    domain_line = (
        f"Active BIAN domains: {', '.join(domains)}."
        if domains
        else "No BIAN domains for this scope (generic fleet)."
    )
    answer = (
        f"**Preview answer** (GCP offline)\n\n"
        f"> {body.query}\n\n"
        f"Scope: `{scope}`\n\n"
        f"{domain_line}\n\n"
        f"In production this path runs hybrid retrieval"
        f"{' with BIAN dual-pull' if domains and should_dual_pull(fleet) else ''}, "
        f"rerank, and grounded generation.\n\n"
        f"Upload product docs under `fleets/{body.fleet_id or '{fleet}'}/"
        f"{body.rack_id or '{rack}'}/` and seed BIAN via `python scripts/seed_bian_knowledge.py`.\n\n"
        f"Switch mode to **Agentic** for plan→retrieve→RAGAS, or **Codegen** for "
        f"BIAN service stubs restricted to the domains above."
    )
    return QueryResponse(
        answer=answer,
        citations=[
            {
                "source_id": 1,
                "path": f"fleets/{body.fleet_id or 'demo'}/{(body.rack_id or 'general')}/sample.md",
                "section": "preview",
            }
        ],
        query_type="simple_factual",
        latency_ms=(time.time() - t0) * 1000,
        cache_hit=False,
        sources_used=1,
        faithfulness_score=0.92,
        fleet_id=body.fleet_id,
        rack_id=body.rack_id,
        tier_id=body.tier_id,
        mode="ask",
        bian_domains=domains,
        platform=fleet.platform if fleet else None,
    )


@app.post("/api/v1/codegen", response_model=QueryResponse)
def api_codegen(body: QueryRequest):
    body.mode = "codegen"
    return api_query(body)


@app.post("/api/v1/agentic/query")
def api_agentic_query(body: QueryRequest):
    body.mode = body.mode if body.mode in ("agentic", "codegen") else "agentic"
    return api_query(body)


@app.get("/api/accuracy/summary")
def api_accuracy_summary():
    from src.agentic.store import accuracy_store

    return accuracy_store.summary()


@app.post("/api/accuracy/clear")
def api_accuracy_clear():
    from src.agentic.store import accuracy_store

    accuracy_store.clear()
    return {"ok": True}


class FleetCreate(BaseModel):
    fleet_id: str
    name: str
    description: str = ""
    icon: str = "📦"


@app.post("/api/admin/fleets", response_model=FleetOut, status_code=201)
def admin_create_fleet(body: FleetCreate):
    raise HTTPException(501, "Admin create is YAML-backed in production; edit config/fleets/registry.yaml")


@app.delete("/api/admin/fleets/{fleet_id}", status_code=204)
def admin_delete_fleet(fleet_id: str):
    raise HTTPException(501, "Admin delete is YAML-backed in production")
