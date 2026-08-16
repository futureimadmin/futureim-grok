"""
Shared data models that flow through the RAG pipeline.
Matches the object shapes described in the architecture document.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocType(str, Enum):
    REFERENCE = "reference"
    TUTORIAL = "tutorial"
    RELEASE_NOTES = "release-notes"
    FAQ = "faq"
    OTHER = "other"


class AccessLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"


class ChunkMetadata(BaseModel):
    source_path: str
    section_heading: Optional[str] = None
    page_number: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    doc_type: DocType = DocType.OTHER
    product: Optional[str] = None
    language: str = "en"
    tenant_id: str = "default"
    fleet_id: Optional[str] = None
    rack_id: Optional[str] = None
    access_level: AccessLevel = AccessLevel.PUBLIC
    extra: Dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    chunk_id: str
    text: str
    token_count: int
    metadata: ChunkMetadata


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    score: float
    source: str  # "dense" | "bm25" | "hybrid" | "rerank"
    metadata: ChunkMetadata


class QueryType(str, Enum):
    SIMPLE_FACTUAL = "simple_factual"
    MULTI_PART = "multi_part"
    COMPARATIVE = "comparative"
    ANALYTICAL = "analytical"
    REAL_TIME = "real_time"
    OFF_DOMAIN = "off_domain"


class ExecutionPlan(BaseModel):
    query_type: QueryType
    k: int
    retrieval_strategy: str  # "dense" | "hybrid" | "hyde"
    use_reranker: bool = True
    max_tokens: int = 512
    model_tier: str = "flash"  # flash | pro
    tool_calls: List[str] = Field(default_factory=list)


class Citation(BaseModel):
    source_id: int
    path: str
    section: Optional[str] = None
    url: Optional[str] = None
    date: Optional[str] = None


class RAGResponse(BaseModel):
    answer: str
    citations: List[Citation]
    query_type: QueryType
    latency_ms: float
    cache_hit: bool = False
    faithfulness_score: Optional[float] = None
    sources_used: int = 0
