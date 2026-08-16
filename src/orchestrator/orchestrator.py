"""
Orchestrator – the central nervous system of the query path.

Implements the five decision stages from the architecture document:

  1. Receive & validate
  2. Semantic cache check
  3. Classify & route
  4. Fan-out in parallel
  5. Aggregate & respond

All expensive work is gated behind cache miss + classification.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from src.common.config import RAGConfig, get_config
from src.common.models import ExecutionPlan, QueryType, RAGResponse

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.cfg = config or get_config()
        # Lazy imports keep cold-start light
        self._cache = None
        self._classifier = None
        self._retriever = None
        self._generator = None

    # ------------------------------------------------------------------
    # Stage 1 – Receive & Validate
    # ------------------------------------------------------------------
    def validate(self, query: str, tenant_id: str, access_level: str) -> str:
        if not query or not query.strip():
            raise ValueError("Empty query")
        q = query.strip()
        # crude length guard (token estimate)
        if len(q.split()) > self.cfg.max_query_tokens:
            raise ValueError("Query too long")
        # basic injection heuristics – production would use a proper classifier
        forbidden = ["ignore previous", "system prompt", "jailbreak"]
        lower = q.lower()
        if any(f in lower for f in forbidden):
            raise ValueError("Query rejected by safety policy")
        return q

    # ------------------------------------------------------------------
    # Stage 2 – Semantic Cache
    # ------------------------------------------------------------------
    def check_cache(self, query: str, tenant_id: str) -> Optional[RAGResponse]:
        if not self.cfg.cache.enabled:
            return None
        # Placeholder – real implementation uses Redis + embedding similarity
        # See src/query/cache.py
        return None

    # ------------------------------------------------------------------
    # Stage 3 – Classify & Route
    # ------------------------------------------------------------------
    def classify(self, query: str) -> ExecutionPlan:
        """
        Fast heuristic classifier. In production replace with a small LLM
        or fine-tuned classifier that returns structured ExecutionPlan.
        """
        q = query.lower()
        if any(w in q for w in ["compare", "difference", "vs", "versus"]):
            return ExecutionPlan(
                query_type=QueryType.COMPARATIVE,
                k=12,
                retrieval_strategy="hybrid",
                use_reranker=True,
                max_tokens=768,
                model_tier="pro",
            )
        if any(w in q for w in ["summarise", "summarize", "all", "list every"]):
            return ExecutionPlan(
                query_type=QueryType.ANALYTICAL,
                k=20,
                retrieval_strategy="hybrid",
                use_reranker=True,
                max_tokens=1024,
                model_tier="pro",
            )
        if any(w in q for w in ["status", "current", "live", "now"]):
            return ExecutionPlan(
                query_type=QueryType.REAL_TIME,
                k=0,
                retrieval_strategy="none",
                use_reranker=False,
                max_tokens=256,
                model_tier="flash",
                tool_calls=["status_api"],
            )
        # default – simple factual
        return ExecutionPlan(
            query_type=QueryType.SIMPLE_FACTUAL,
            k=6,
            retrieval_strategy="hybrid",
            use_reranker=True,
            max_tokens=512,
            model_tier="flash",
        )

    # ------------------------------------------------------------------
    # Stages 4 + 5 – Fan-out, retrieve, generate, post-process
    # ------------------------------------------------------------------
    def run(
        self,
        query: str,
        *,
        tenant_id: str = "default",
        access_level: str = "public",
        user_id: Optional[str] = None,
    ) -> RAGResponse:
        t0 = time.perf_counter()

        clean = self.validate(query, tenant_id, access_level)

        cached = self.check_cache(clean, tenant_id)
        if cached:
            cached.cache_hit = True
            cached.latency_ms = (time.perf_counter() - t0) * 1000
            return cached

        plan = self.classify(clean)
        logger.info("Execution plan: %s", plan.model_dump())

        # Placeholder for the full pipeline – real code lives in query/
        # 1. Query expansion / HyDE
        # 2. Parallel dense + BM25 + metadata filter
        # 3. RRF fusion
        # 4. Cross-encoder rerank → top-K
        # 5. Prompt assembly (4-slot structure)
        # 6. LLM generate (streaming)
        # 7. Post-process (citations, faithfulness, safety)
        # 8. Cache write-back

        # Minimal stub response so the service can start
        answer = (
            f"[Orchestrator stub] Received query of type {plan.query_type.value}. "
            f"Full retrieval + generation pipeline will be wired in subsequent commits. "
            f"K={plan.k}, strategy={plan.retrieval_strategy}."
        )

        return RAGResponse(
            answer=answer,
            citations=[],
            query_type=plan.query_type,
            latency_ms=(time.perf_counter() - t0) * 1000,
            cache_hit=False,
            sources_used=0,
        )
