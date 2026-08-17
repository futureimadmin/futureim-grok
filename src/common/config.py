"""
Central configuration for the RAG system.
All values can be overridden via environment variables (Cloud Run friendly).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class EmbeddingConfig:
    # GCP Vertex default; diagram shows text-embedding-3-large/1536 for OpenAI-style stacks
    model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
    dimensions: int = int(os.getenv("EMBEDDING_DIMS", "768"))
    batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))


@dataclass
class ChunkConfig:
    strategy: str = os.getenv("CHUNK_STRATEGY", "semantic")  # fixed | sentence | semantic
    # Architecture diagram: size=256 tok, overlap=32
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "256"))
    overlap: int = int(os.getenv("CHUNK_OVERLAP", "32"))
    min_chunk_size: int = 50


@dataclass
class RetrievalConfig:
    top_k_ann: int = int(os.getenv("TOP_K_ANN", "50"))
    top_k_prompt: int = int(os.getenv("TOP_K_PROMPT", "8"))
    hybrid_alpha: float = float(os.getenv("HYBRID_ALPHA", "0.6"))
    rrf_k: int = 60
    similarity_threshold: float = 0.75


@dataclass
class CacheConfig:
    enabled: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    # Architecture diagram: similarity > 0.92
    similarity_threshold: float = float(os.getenv("CACHE_SIM_THRESHOLD", "0.92"))
    ttl_seconds: int = int(os.getenv("CACHE_TTL", "86400"))
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_auth: str = os.getenv("REDIS_AUTH", "")


@dataclass
class LLMConfig:
    model: str = os.getenv("LLM_MODEL", "gemini-2.0-flash-001")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    max_output_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))
    top_p: float = 0.9


@dataclass
class RAGConfig:
    project_id: str = os.getenv("GCP_PROJECT", "")
    region: str = os.getenv("GCP_REGION", "us-central1")
    documents_bucket: str = os.getenv("DOCUMENTS_BUCKET", "")
    processed_bucket: str = os.getenv("PROCESSED_BUCKET", "")
    vector_index_id: str = os.getenv("VECTOR_INDEX_ID", "")
    vector_endpoint_id: str = os.getenv("VECTOR_ENDPOINT_ID", "")

    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    chunk: ChunkConfig = field(default_factory=ChunkConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)

    temperature_rag: float = 0.1
    max_query_tokens: int = 2000
    answer_budget_tokens: int = 1024
    safety_buffer_pct: float = 0.25


def get_config() -> RAGConfig:
    return RAGConfig()
