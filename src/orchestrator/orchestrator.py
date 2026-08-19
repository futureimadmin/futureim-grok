"""
Orchestrator – Tier 3 query entry (architecture diagram).

Stages:
  auth · rate-limit · sanitise · classify · route · fan-out
  → Semantic Cache → (on miss) Tier 4–7 pipeline

Supports Fleet + Rack scoping for multi-domain RAG fleets.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

from src.common.config import RAGConfig, get_config
from src.common.models import ExecutionPlan, QueryType, RAGResponse
from src.fleet.registry import get_fleet
from src.query.cache import SemanticCache
from src.query.generator import Generator
from src.query.postprocess import post_process
from src.query.prompt import build_prompt
from src.query.reranker import CrossEncoderReranker
from src.query.retrieval import HybridRetriever
from src.query.expansion import QueryExpander, HyDE
from src.query.topk import TopKSelector

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, max_per_minute: int = 60):
        self.max_per_minute = max_per_minute
        self._hits: Dict[str, list] = defaultdict(list)

    def check(self, key: str) -> Tuple[bool, int]:
        now = time.time()
        window = self._hits[key]
        self._hits[key] = [t for t in window if now - t < 60.0]
        if len(self._hits[key]) >= self.max_per_minute:
            return False, self.max_per_minute
        self._hits[key].append(now)
        return True, self.max_per_minute - len(self._hits[key])


class Orchestrator:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.cfg = config or get_config()
        self.cache = SemanticCache(self.cfg)
        self.retriever = HybridRetriever(self.cfg)
        self.reranker = CrossEncoderReranker(self.cfg)
        self.topk = TopKSelector(self.cfg)
        self.generator = Generator(self.cfg)
        self.expander = QueryExpander(self.cfg)
        self.hyde = HyDE(self.cfg)
        self.rate_limiter = RateLimiter(
            max_per_minute=int(__import__("os").getenv("RAG_RATE_LIMIT_RPM", "60"))
        )

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

    def classify(
        self,
        query: str,
        default_k: int = 6,
        *,
        fleet_id: Optional[str] = None,
        rack_id: Optional[str] = None,
        tenant_id: str = "default",
        access_level: str = "public",
    ) -> ExecutionPlan:
        q = query.lower()
        if any(w in q for w in ["compare", "difference", "vs", "versus"]):
            return ExecutionPlan(
                query_type=QueryType.COMPARATIVE, k=max(12, default_k),
                retrieval_strategy="hybrid", use_reranker=True,
                max_tokens=768, model_tier="pro",
                fleet_id=fleet_id, rack_id=rack_id,
                tenant_id=tenant_id, access_level=access_level,
            )
        if any(w in q for w in ["summarise", "summarize", "all", "list every"]):
            return ExecutionPlan(
                query_type=QueryType.ANALYTICAL, k=max(20, default_k),
                retrieval_strategy="hybrid", use_reranker=True,
                max_tokens=1024, model_tier="pro",
                fleet_id=fleet_id, rack_id=rack_id,
                tenant_id=tenant_id, access_level=access_level,
            )
        if any(w in q for w in ["status", "current", "live", "now"]):
            return ExecutionPlan(
                query_type=QueryType.REAL_TIME, k=0,
                retrieval_strategy="none", use_reranker=False,
                max_tokens=256, model_tier="flash",
                tool_calls=["status_api"],
                fleet_id=fleet_id, rack_id=rack_id,
                tenant_id=tenant_id, access_level=access_level,
            )
        return ExecutionPlan(
            query_type=QueryType.SIMPLE_FACTUAL, k=default_k,
            retrieval_strategy="hybrid", use_reranker=True,
            max_tokens=512, model_tier="flash",
            fleet_id=fleet_id, rack_id=rack_id,
            tenant_id=tenant_id, access_level=access_level,
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
        product: Optional[str] = None,
    ) -> RAGResponse:
        t0 = time.perf_counter()

        rl_key = user_id or tenant_id or "anonymous"
        allowed, remaining = self.rate_limiter.check(rl_key)
        if not allowed:
            raise ValueError(
                f"Rate limit exceeded ({self.rate_limiter.max_per_minute}/min). "
                "Retry after a short pause."
            )

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

        plan = self.classify(
            clean,
            default_k=default_k,
            fleet_id=fleet_id,
            rack_id=rack_id,
            tenant_id=tenant_id,
            access_level=access_level,
        )
        logger.info(
            "plan=%s fleet=%s rack=%s ns=%s rate_remaining=%d",
            plan.query_type.value, fleet_id, rack_id, namespace, remaining,
        )

        if plan.retrieval_strategy == "none":
            return RAGResponse(
                answer="This query requires real-time data that is not in the knowledge base.",
                citations=[],
                query_type=plan.query_type,
                latency_ms=(time.perf_counter() - t0) * 1000,
                cache_hit=False,
                sources_used=0,
            )

        from src.query.bian_context import (
            bian_reference_filters,
            describe_scope,
            product_filters,
            resolve_bian_domains,
            should_dual_pull,
        )

        filters = product_filters(
            fleet_id=fleet_id,
            rack_id=rack_id,
            tenant_id=tenant_id,
            access_level=access_level,
            namespace=namespace,
        )
        if product:
            filters["product"] = product

        variants = self.expander.expand(clean, max_variants=2)
        logger.info("query variants=%d", len(variants))
        use_hyde = plan.query_type.value in ("analytical", "comparative", "multi_part")
        hyde_vec = self.hyde.embed_hypothesis(clean) if use_hyde else None

        top_final = max(plan.k * 2, 20)
        if should_dual_pull(fleet):
            domains = resolve_bian_domains(fleet, rack)
            bian_filters = bian_reference_filters(
                domains,
                tenant_id=tenant_id,
                access_level=access_level,
                bian_version=fleet.bian_version if fleet else None,
            )
            logger.info(
                "BIAN dual-pull scope=%s domains=%s",
                describe_scope(fleet, rack),
                domains,
            )
            candidates = self.retriever.retrieve_dual(
                clean,
                product_filters=filters,
                bian_filter_list=bian_filters,
                top_k_ann=self.cfg.retrieval.top_k_ann,
                top_k_final=top_final,
                query_variants=variants,
                dense_vector_override=hyde_vec,
            )
            plan.bian_service_domains = domains
        else:
            candidates = self.retriever.retrieve(
                clean,
                top_k_ann=self.cfg.retrieval.top_k_ann,
                top_k_final=top_final,
                filters=filters,
                query_variants=variants,
                dense_vector_override=hyde_vec,
            )

        if plan.use_reranker and candidates:
            reranked = self.reranker.rerank(clean, candidates, top_k=max(plan.k * 2, 20))
        else:
            reranked = candidates

        top_chunks = self.topk.select(reranked, k=plan.k)

        tier = None
        bian_domains = getattr(plan, "bian_service_domains", None) or []
        if rack and rack.tier_ids:
            tier = fleet.tier(rack.tier_ids[0]) if fleet else None
        prompt = build_prompt(
            clean,
            top_chunks,
            fleet=fleet,
            rack=rack,
            tier=tier,
            bian_domains=bian_domains or None,
        )
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
