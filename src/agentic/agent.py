"""
Agentic RAG — multi-step reasoning loop with BIAN dual-pull and RAGAS gate.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agentic.memory import AgentMemory
from src.agentic.metrics import AccuracyMetrics
from src.agentic.planner import Planner
from src.agentic.tools import ToolRegistry
from src.common.config import RAGConfig, get_config
from src.common.models import Citation, QueryType, RAGResponse, RetrievedChunk
from src.fleet.registry import get_fleet
from src.query.generator import Generator
from src.query.postprocess import post_process
from src.query.prompt import build_prompt

logger = logging.getLogger(__name__)


class AgenticRAG:
    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        *,
        ragas_threshold: float = 0.80,
        max_retries: int = 2,
    ):
        self.cfg = config or get_config()
        self.threshold = float(
            __import__("os").getenv("RAGAS_THRESHOLD", str(ragas_threshold))
        )
        self.max_retries = int(
            __import__("os").getenv("AGENT_MAX_RETRIES", str(max_retries))
        )
        self.planner = Planner(self.cfg)
        self.tools = ToolRegistry(self.cfg)
        self.generator = Generator(self.cfg)

    def run(
        self,
        query: str,
        *,
        fleet_id: Optional[str] = None,
        rack_id: Optional[str] = None,
        tenant_id: str = "default",
        access_level: str = "public",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        memory = AgentMemory()

        if not query or not query.strip():
            raise ValueError("Empty query")
        clean = query.strip()

        fleet = get_fleet(fleet_id) if fleet_id else None
        rack = fleet.rack(rack_id) if fleet and rack_id else None
        namespace = fleet.namespace(rack_id) if fleet else "default"
        from src.query.bian_context import (
            bian_reference_filters,
            product_filters,
            resolve_bian_domains,
            should_dual_pull,
            describe_scope,
        )

        filters = product_filters(
            fleet_id=fleet_id,
            rack_id=rack_id,
            tenant_id=tenant_id,
            access_level=access_level,
            namespace=namespace,
        )
        dual = should_dual_pull(fleet)
        domains = resolve_bian_domains(fleet, rack) if dual else []
        bian_filters = (
            bian_reference_filters(
                domains,
                tenant_id=tenant_id,
                access_level=access_level,
                bian_version=fleet.bian_version if fleet else None,
            )
            if dual
            else []
        )
        memory.think(f"Scope: {describe_scope(fleet, rack)} dual_pull={dual}")

        goals = self.planner.decompose(clean)
        memory.plan(goals)
        memory.think(f"User query: {clean}")

        answer = ""
        citations: List[Citation] = []
        chunks: List[RetrievedChunk] = []
        metrics = AccuracyMetrics(threshold=self.threshold)
        attempt = 0

        while attempt <= self.max_retries:
            attempt += 1
            memory.think(f"Attempt {attempt}/{self.max_retries + 1}")

            all_chunks: List[RetrievedChunk] = []
            for goal in goals:
                tool_name = self.tools.select_for_goal(goal)
                memory.act(tool_name, goal)

                if tool_name == "rag_retrieval":
                    focus = clean
                    for sep in (" for: ", " about: "):
                        if sep in goal:
                            focus = goal.split(sep, 1)[1].strip() or clean
                            break
                    result = self.tools.call(
                        "rag_retrieval",
                        query=focus,
                        filters=filters,
                        top_k=8,
                        dual_pull=dual,
                        bian_filter_list=bian_filters if dual else None,
                    )
                    if result.success and result.data:
                        all_chunks.extend(result.data)
                        memory.observe(
                            f"Retrieved {len(result.data)} chunks for goal",
                            tool=tool_name,
                        )
                    else:
                        memory.observe(
                            f"Retrieval empty: {result.error or 'no hits'}",
                            tool=tool_name,
                        )
                elif tool_name == "accuracy_evaluator":
                    continue
                else:
                    result = self.tools.call(tool_name, query=clean)
                    memory.observe(
                        result.meta.get("note", str(result.data))[:200],
                        tool=tool_name,
                    )

            by_id: Dict[str, RetrievedChunk] = {}
            for c in all_chunks:
                prev = by_id.get(c.chunk_id)
                if prev is None or c.score > prev.score:
                    by_id[c.chunk_id] = c
            chunks = sorted(by_id.values(), key=lambda x: x.score, reverse=True)[:12]

            prompt = build_prompt(
                clean,
                chunks,
                fleet=fleet,
                rack=rack,
                bian_domains=domains or None,
            )
            raw = self.generator.generate(prompt)
            answer, citations, _faith_legacy = post_process(raw, chunks)
            memory.observe(f"Generated answer ({len(answer)} chars)")

            eval_result = self.tools.call(
                "accuracy_evaluator",
                query=clean,
                answer=answer,
                chunks=chunks,
                threshold=self.threshold,
            )
            if eval_result.success and eval_result.data:
                metrics = eval_result.data
            memory.reflect(
                f"RAGAS={metrics.ragas_score:.3f} faith={metrics.faithfulness:.3f} "
                f"passed={metrics.passed}",
                meta=metrics.to_dict() if hasattr(metrics, "to_dict") else {},
            )

            if metrics.passed:
                memory.think("Accuracy threshold met — emitting final answer")
                break

            if attempt <= self.max_retries:
                memory.think(
                    f"Score {metrics.ragas_score:.3f} < {self.threshold} — re-planning"
                )
                if filters.get("rack_id"):
                    filters = {**filters, "rack_id": None}
                    memory.act("replan", "Dropped rack filter to widen retrieval")
                goals = [
                    f"retrieve broader context for: {clean}",
                    "synthesize improved answer",
                    "evaluate answer quality",
                ]
                memory.plan(goals)
            else:
                memory.think(
                    f"Max retries reached — best-effort (RAGAS={metrics.ragas_score:.3f})"
                )

        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "answer": answer,
            "citations": [
                c.model_dump() if hasattr(c, "model_dump") else c for c in citations
            ],
            "query_type": QueryType.SIMPLE_FACTUAL.value,
            "latency_ms": latency_ms,
            "cache_hit": False,
            "sources_used": len(chunks),
            "faithfulness_score": metrics.faithfulness,
            "fleet_id": fleet_id,
            "rack_id": rack_id,
            "confidence_score": metrics.ragas_score,
            "ragas": metrics.to_dict() if hasattr(metrics, "to_dict") else {},
            "reasoning_trace": memory.reasoning_trace(),
            "tool_calls": memory.tool_calls,
            "attempts": attempt,
            "threshold_met": metrics.passed,
            "sub_goals": memory.sub_goals,
        }
