"""
RAG Fleet Console – unified API + user-friendly web UI.

GET  /                     Fleet console UI
GET  /health
GET  /api/fleets           List fleets
GET  /api/fleets/{id}      Fleet detail + racks
POST /api/v1/query         Scoped query (fleet_id, rack_id optional)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from src.common.models import RAGResponse
from src.fleet.registry import get_fleet, list_fleets
from src.orchestrator.orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag-fleet")

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(
    title="RAG Fleet Console",
    description="Multi-domain RAG fleets with racks for subdomain knowledge",
    version="1.0.0",
)

static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

orchestrator = Orchestrator()


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


@app.get("/health")
def health():
    return {"status": "ok", "service": "rag-fleet", "version": "1.0.0"}


@app.get("/", response_class=HTMLResponse)
def console(request: Request):
    fleets = list_fleets()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "fleets": fleets, "title": "RAG Fleet Console"},
    )


@app.get("/api/fleets", response_model=List[FleetOut])
def api_list_fleets():
    out = []
    for f in list_fleets():
        out.append(
            FleetOut(
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
        )
    return out


@app.get("/api/fleets/{fleet_id}", response_model=FleetOut)
def api_get_fleet(fleet_id: str):
    f = get_fleet(fleet_id)
    if not f:
        raise HTTPException(status_code=404, detail=f"Fleet '{fleet_id}' not found")
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


@app.post("/api/v1/query", response_model=QueryResponse)
def api_query(
    body: QueryRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    if body.fleet_id and not get_fleet(body.fleet_id):
        raise HTTPException(status_code=404, detail=f"Unknown fleet '{body.fleet_id}'")
    if body.fleet_id and body.rack_id:
        fleet = get_fleet(body.fleet_id)
        if fleet and not fleet.rack(body.rack_id):
            raise HTTPException(
                status_code=404,
                detail=f"Unknown rack '{body.rack_id}' in fleet '{body.fleet_id}'",
            )

    try:
        result: RAGResponse = orchestrator.run(
            body.query,
            fleet_id=body.fleet_id,
            rack_id=body.rack_id,
            tenant_id=body.tenant_id,
            access_level=body.access_level,
            user_id=x_user_id,
        )
        return QueryResponse(
            answer=result.answer,
            citations=[c.model_dump() if hasattr(c, "model_dump") else c for c in result.citations],
            query_type=result.query_type.value,
            latency_ms=result.latency_ms,
            cache_hit=result.cache_hit,
            sources_used=result.sources_used,
            faithfulness_score=result.faithfulness_score,
            fleet_id=body.fleet_id,
            rack_id=body.rack_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail="Internal error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
