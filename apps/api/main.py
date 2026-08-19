"""
Cloud Run entry-point for the RAG query API.
Exposes a simple FastAPI surface that the orchestrator drives.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from src.common.models import RAGResponse
from src.orchestrator.orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag-api")

app = FastAPI(
    title="FutureIM RAG API",
    description="Production RAG system following the complete architecture guide",
    version="0.1.0",
)

orchestrator = Orchestrator()


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    tenant_id: str = "default"
    access_level: str = "public"
    fleet_id: Optional[str] = None
    rack_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    citations: list
    query_type: str
    latency_ms: float
    cache_hit: bool
    sources_used: int
    faithfulness_score: Optional[float] = None


@app.get("/health")
def health():
    return {"status": "ok", "service": "rag-query"}


@app.post("/v1/query", response_model=QueryResponse)
def query(
    body: QueryRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    expected_key = os.getenv("RAG_API_KEY")
    if expected_key and x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    try:
        result: RAGResponse = orchestrator.run(
            body.query,
            tenant_id=body.tenant_id,
            access_level=body.access_level,
            fleet_id=body.fleet_id,
            rack_id=body.rack_id,
            user_id=x_user_id,
        )
        return QueryResponse(
            answer=result.answer,
            citations=[c.model_dump() for c in result.citations],
            query_type=result.query_type.value,
            latency_ms=result.latency_ms,
            cache_hit=result.cache_hit,
            sources_used=result.sources_used,
            faithfulness_score=result.faithfulness_score,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unhandled error")
        raise HTTPException(status_code=500, detail="Internal error")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
