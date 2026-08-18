"""Cloud Run entry-point for the RAG query API."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from src.common.models import QueryType, RAGResponse
from src.orchestrator.orchestrator import Orchestrator

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="FutureIM RAG Fleet API", version="1.0.1")
orch = Orchestrator()


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    fleet_id: Optional[str] = None
    rack_id: Optional[str] = None
    tier_id: Optional[str] = None
    tenant_id: str = "default"
    access_level: str = "public"
    product: Optional[str] = None
    user_id: Optional[str] = None


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/query")
def query(
    body: QueryRequest,
    x_api_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    expected = os.getenv("API_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
    try:
        resp: RAGResponse = orch.run(
            body.query,
            fleet_id=body.fleet_id,
            rack_id=body.rack_id,
            tenant_id=body.tenant_id,
            access_level=body.access_level,
            user_id=body.user_id,
            product=body.product,
        )
        return resp.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=429 if "Rate limit" in str(e) else 400, detail=str(e))
    except Exception as e:
        logger.exception("query failed")
        raise HTTPException(status_code=500, detail=str(e))
