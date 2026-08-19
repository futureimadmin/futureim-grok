"""
Semantic cache backed by Redis (section 3.2 of the architecture guide).

Cache key = embedding of the query (not the string).
Hit when cosine similarity ≥ threshold and tenant_id matches.
"""

from __future__ import annotations

import json
import logging
import time
from typing import List, Optional

import numpy as np

from src.common.config import RAGConfig, get_config
from src.common.models import QueryType, RAGResponse
from src.ingestion.embedder import Embedder

logger = logging.getLogger(__name__)


def _cosine(a: List[float], b: List[float]) -> float:
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


class SemanticCache:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.cfg = config or get_config()
        self.embedder = Embedder()
        self._redis = None
        if self.cfg.cache.enabled:
            try:
                import redis

                self._redis = redis.Redis(
                    host=self.cfg.cache.redis_host,
                    port=self.cfg.cache.redis_port,
                    password=self.cfg.cache.redis_auth or None,
                    decode_responses=True,
                    socket_connect_timeout=2,
                )
                self._redis.ping()
                logger.info("Semantic cache connected to Redis %s:%s", self.cfg.cache.redis_host, self.cfg.cache.redis_port)
            except Exception as e:
                logger.warning("Redis unavailable (%s) – cache disabled for this process", e)
                self._redis = None

    def _key(self, tenant_id: str) -> str:
        return f"rag:cache:{tenant_id}"

    def get(self, query: str, tenant_id: str = "default") -> Optional[RAGResponse]:
        if not self._redis:
            return None
        try:
            qvec = self.embedder.embed_query(query)
            raw = self._redis.hgetall(self._key(tenant_id))
            if not raw:
                return None
            best_sim = 0.0
            best_payload = None
            for _entry_id, payload in raw.items():
                data = json.loads(payload)
                sim = _cosine(qvec, data["vector"])
                if sim > best_sim:
                    best_sim = sim
                    best_payload = data
            if best_sim >= self.cfg.cache.similarity_threshold and best_payload:
                logger.info("Semantic cache HIT (sim=%.4f)", best_sim)
                return RAGResponse(
                    answer=best_payload["answer"],
                    citations=best_payload.get("citations", []),
                    query_type=QueryType(best_payload.get("query_type", "simple_factual")),
                    latency_ms=0.0,
                    cache_hit=True,
                    sources_used=best_payload.get("sources_used", 0),
                )
        except Exception as e:
            logger.warning("Cache get failed: %s", e)
        return None

    def put(
        self,
        query: str,
        response: RAGResponse,
        tenant_id: str = "default",
    ) -> None:
        if not self._redis or response.cache_hit:
            return
        if "don't have enough information" in response.answer.lower():
            return
        try:
            qvec = self.embedder.embed_query(query)
            entry_id = str(int(time.time() * 1000))
            payload = {
                "vector": qvec,
                "answer": response.answer,
                "citations": [c.model_dump() if hasattr(c, "model_dump") else c for c in response.citations],
                "query_type": response.query_type.value,
                "sources_used": response.sources_used,
                "answered_at": time.time(),
            }
            pipe = self._redis.pipeline()
            pipe.hset(self._key(tenant_id), entry_id, json.dumps(payload))
            pipe.expire(self._key(tenant_id), self.cfg.cache.ttl_seconds)
            pipe.execute()
            logger.info("Semantic cache WRITE tenant=%s", tenant_id)
        except Exception as e:
            logger.warning("Cache put failed: %s", e)
