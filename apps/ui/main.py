"""
RAG Fleet Console – unified API + user-friendly web UI + admin.

GET  /                     Fleet console UI
GET  /admin                Fleet admin UI
GET  /health
GET  /api/fleets           List fleets
GET  /api/fleets/{id}      Fleet detail + racks
POST /api/v1/query         Scoped query
POST /api/admin/fleets     Create fleet
PATCH/DELETE admin routes  Manage fleets & racks
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


class FleetCreate(BaseModel):
    fleet_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]{1,63}$")
    name: str
    description: str = ""
    icon: str = "📚"
    default_top_k: int = 8
    system_prompt_hint: str = ""


class FleetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    default_top_k: Optional[int] = None
    system_prompt_hint: Optional[str] = None
    status: Optional[str] = None


class RackCreate(BaseModel):
    rack_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]{1,63}$")
    name: str
    description: str = ""
    top_k: Optional[int] = None


@app.get("/health")
def health():
    return {"status": "ok", "service": "rag-fleet", "version": "1.0.0"}


@app.get("/", response_class=HTMLResponse)
def console(request: Request):
    fleets = list_fleets()
    # Starlette 1.x: TemplateResponse(request, name, context)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"fleets": fleets, "title": "RAG Fleet Console"},
    )


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    fleets = list_fleets()
    return templates.TemplateResponse(
        request,
        "admin.html",
        {"fleets": fleets, "title": "Fleet Admin"},
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
    return FleetOut(
        fleet_id=f.fleet_id, name=f.name, description=f.description,
        icon=f.icon, status=f.status.value, racks=[],
    )


@app.patch("/api/admin/fleets/{fleet_id}", response_model=FleetOut)
def admin_update_fleet(fleet_id: str, body: FleetUpdate):
    from src.fleet import admin as fleet_admin
    try:
        f = fleet_admin.update_fleet(fleet_id, **body.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return FleetOut(
        fleet_id=f.fleet_id, name=f.name, description=f.description,
        icon=f.icon, status=f.status.value,
        racks=[RackOut(rack_id=r.rack_id, name=r.name, description=r.description) for r in f.racks],
    )


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
        r = fleet_admin.add_rack(
            fleet_id, body.rack_id, body.name, body.description, body.top_k,
        )
    except ValueError as e:
        code = 404 if "not found" in str(e).lower() else 409
        raise HTTPException(status_code=code, detail=str(e))
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
