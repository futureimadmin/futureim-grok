"""
Orchestrator – query path control plane (Tiers 3–7).

Flow: validate → semantic cache → classify → expand/HyDE → retrieve →
rerank → prompt → generate → post-process → cache write-back.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from src.common.config import RAGConfig, get_config
from src.common.models import ExecutionPlan, QueryType, RAGResponse
from src.fleet.registry import get_fleet
from src.query.cache import SemanticCache
from src.query.expansion import HyDE, QueryExpander
from src.query.generator import Generator
from src.query.postprocess import post_process
from src.query.prompt import build_prompt
from src.query.reranker import CrossEncoderReranker
from src.query.retrieval import HybridRetriever

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.cfg = config or get_config()
        self.cache = SemanticCache(self.cfg)
        self.retriever = HybridRetriever(self.cfg)
        self.reranker = CrossEncoderReranker(self.cfg)
        self.generator = Generator(self.cfg)
        self.expander = QueryExpander(self.cfg)
        self.hyde = HyDE(self.cfg)

    def validate(self, query: str) -> str:
        if not query or not query.strip():
            raise ValueError("Empty query")
        q = query.strip()
        if len(q.split()) > self.cfg.max_query_tokens:
            raise ValueError("Query too long")
        forbidden = ["ignore previous", "system prompt", "jailbreak"]
        if any(f in q.lower() for f in forbidden):
            raise ValueError("Query rejected by safety policy")
        return q

    def classify(self, query: str, default_k: int = 6) -> ExecutionPlan:
        q = query.lower()
        if any(w in q for w in ["compare", "difference", "vs", "versus"]):
            return ExecutionPlan(
                query_type=QueryType.COMPARATIVE, k=max(12, default_k),
                retrieval_strategy="hybrid", use_reranker=True,
                max_tokens=768, model_tier="pro",
            )
        if any(w in q for w in ["summarise", "summarize", "all", "list every"]):
            return ExecutionPlan(
                query_type=QueryType.ANALYTICAL, k=max(20, default_k),
                retrieval_strategy="hybrid", use_reranker=True,
                max_tokens=1024, model_tier="pro",
            )
        if any(w in q for w in ["status", "current", "live", "now"]):
            return ExecutionPlan(
                query_type=QueryType.REAL_TIME, k=0,
                retrieval_strategy="none", use_reranker=False,
                max_tokens=256, model_tier="flash",
                tool_calls=["status_api"],
            )
        return ExecutionPlan(
            query_type=QueryType.SIMPLE_FACTUAL, k=default_k,
            retrieval_strategy="hybrid", use_reranker=True,
            max_tokens=512, model_tier="flash",
        )

    def run(
        self,
        query: str,
        *,
        fleet_id: Optional[str] = None,
        rack_id: Optional[str] = None,
        tenant_id: str = "default",
        access_level: str = "public",
        user_id: Optional[str] = None,
    ) -> RAGResponse:
        t0 = time.perf_counter()
        clean = self.validate(query)

        fleet = get_fleet(fleet_id) if fleet_id else None
        rack = fleet.rack(rack_id) if fleet and rack_id else None
        default_k = (rack.top_k if rack and rack.top_k else None) or (
            fleet.default_top_k if fleet else 6
        )
        namespace = fleet.namespace(rack_id) if fleet else "default"
        cache_scope = f"{tenant_id}:{namespace}"

        cached = self.cache.get(clean, tenant_id=cache_scope)
        if cached:
            cached.latency_ms = (time.perf_counter() - t0) * 1000
            return cached

        plan = self.classify(clean, default_k=default_k)
        logger.info("plan=%s fleet=%s rack=%s ns=%s",
                    plan.query_type.value, fleet_id, rack_id, namespace)

        if plan.retrieval_strategy == "none":
            return RAGResponse(
                answer="This query requires real-time data that is not in the knowledge base.",
                citations=[],
                query_type=plan.query_type,
                latency_ms=(time.perf_counter() - t0) * 1000,
                cache_hit=False,
                sources_used=0,
            )

        filters = {
            "tenant_id": tenant_id,
            "access_level": access_level,
            "fleet_id": fleet_id,
            "rack_id": rack_id,
            "namespace": namespace,
        }

        # Tier 4 — Query Expansion + optional HyDE
        variants = self.expander.expand(clean, max_variants=2)
        use_hyde = plan.query_type.value in ("analytical", "comparative", "multi_part")
        hyde_vec = self.hyde.embed_hypothesis(clean) if use_hyde else None
        logger.info("variants=%d hyde=%s", len(variants), bool(hyde_vec))

        candidates = self.retriever.retrieve(
            clean,
            top_k_ann=self.cfg.retrieval.top_k_ann,
            top_k_final=max(plan.k * 2, 20),
            filters=filters,
            query_variants=variants,
            dense_vector_override=hyde_vec,
        )

        if plan.use_reranker and candidates:
            top_chunks = self.reranker.rerank(clean, candidates, top_k=plan.k)
        else:
            top_chunks = candidates[: plan.k]

        prompt = build_prompt(clean, top_chunks, fleet=fleet, rack=rack)
        raw_answer = self.generator.generate(prompt)
        answer, citations, faith = post_process(raw_answer, top_chunks)

        response = RAGResponse(
            answer=answer,
            citations=citations,
            query_type=plan.query_type,
            latency_ms=(time.perf_counter() - t0) * 1000,
            cache_hit=False,
            faithfulness_score=faith,
            sources_used=len(top_chunks),
        )

        if faith >= 0.5:
            self.cache.put(clean, response, tenant_id=cache_scope)

        return response
