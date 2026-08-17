"""
Local preview server for RAG Fleet Console (no GCP required).

  set PYTHONPATH=.
  python -m uvicorn apps.ui.preview:app --reload --port 8080
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from src.fleet.registry import get_fleet, list_fleets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag-fleet-preview")

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="RAG Fleet Console (Preview)", version="1.0.1-preview")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    fleet_id: Optional[str] = None
    rack_id: Optional[str] = None
    tenant_id: str = "default"
    access_level: str = "public"


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


class RackOut(BaseModel):
    rack_id: str
    name: str
    description: str


class FleetOut(BaseModel):
    fleet_id: str
    name: str
    description: str
    icon: str
    status: str
    racks: List[RackOut]


def _fleet_out(f) -> FleetOut:
    return FleetOut(
        fleet_id=f.fleet_id,
        name=f.name,
        description=f.description,
        icon=f.icon,
        status=f.status.value,
        racks=[
            RackOut(rack_id=r.rack_id, name=r.name, description=r.description)
            for r in f.racks
        ],
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "rag-fleet-preview", "mode": "preview"}


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


@app.get("/api/fleets", response_model=List[FleetOut])
def api_list_fleets():
    return [_fleet_out(f) for f in list_fleets()]


@app.get("/api/fleets/{fleet_id}", response_model=FleetOut)
def api_get_fleet(fleet_id: str):
    f = get_fleet(fleet_id)
    if not f:
        raise HTTPException(status_code=404, detail=f"Fleet '{fleet_id}' not found")
    return _fleet_out(f)


@app.post("/api/v1/query", response_model=QueryResponse)
def api_query(body: QueryRequest):
    t0 = time.perf_counter()
    if body.fleet_id and not get_fleet(body.fleet_id):
        raise HTTPException(status_code=404, detail=f"Unknown fleet '{body.fleet_id}'")

    fleet = get_fleet(body.fleet_id) if body.fleet_id else None
    rack = fleet.rack(body.rack_id) if fleet and body.rack_id else None
    scope = fleet.name if fleet else "general knowledge"
    if rack:
        scope = f"{fleet.name} › {rack.name}"

    answer = (
        f"[PREVIEW MODE]\n\n"
        f"You asked about **{scope}**:\n\n"
        f"> {body.query}\n\n"
        f"In production this would run hybrid retrieval (dense + BM25 + RRF), "
        f"cross-encoder rerank, Gemini generation, and faithfulness checks "
        f"scoped to namespace `{fleet.namespace(body.rack_id) if fleet else 'default'}`.\n\n"
        f"Upload docs under `fleets/{body.fleet_id or '{fleet}'}/{body.rack_id or '{rack}'}/` "
        f"to populate this fleet's knowledge."
    )

    return QueryResponse(
        answer=answer,
        citations=[{
            "source_id": 1,
            "path": f"fleets/{body.fleet_id or 'demo'}/{(body.rack_id or 'general')}/sample.md",
            "section": "Preview placeholder",
        }],
        query_type="simple_factual",
        latency_ms=(time.perf_counter() - t0) * 1000,
        cache_hit=False,
        sources_used=1,
        faithfulness_score=1.0,
        fleet_id=body.fleet_id,
        rack_id=body.rack_id,
    )


class FleetCreate(BaseModel):
    fleet_id: str
    name: str
    description: str = ""
    icon: str = "📚"
    default_top_k: int = 8
    system_prompt_hint: str = ""


class RackCreate(BaseModel):
    rack_id: str
    name: str
    description: str = ""
    top_k: Optional[int] = None


@app.post("/api/admin/fleets", response_model=FleetOut, status_code=201)
def admin_create_fleet(body: FleetCreate):
    from src.fleet import admin as fleet_admin
    try:
        f = fleet_admin.create_fleet(
            fleet_id=body.fleet_id,
            name=body.name,
            description=body.description,
            icon=body.icon,
            default_top_k=body.default_top_k,
            system_prompt_hint=body.system_prompt_hint,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _fleet_out(f)


@app.delete("/api/admin/fleets/{fleet_id}", status_code=204)
def admin_delete_fleet(fleet_id: str):
    from src.fleet import admin as fleet_admin
    try:
        fleet_admin.delete_fleet(fleet_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/admin/fleets/{fleet_id}/racks", response_model=RackOut, status_code=201)
def admin_add_rack(fleet_id: str, body: RackCreate):
    from src.fleet import admin as fleet_admin
    try:
        r = fleet_admin.add_rack(fleet_id, body.rack_id, body.name, body.description, body.top_k)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return RackOut(rack_id=r.rack_id, name=r.name, description=r.description)


@app.delete("/api/admin/fleets/{fleet_id}/racks/{rack_id}", status_code=204)
def admin_delete_rack(fleet_id: str, rack_id: str):
    from src.fleet import admin as fleet_admin
    try:
        fleet_admin.delete_rack(fleet_id, rack_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
