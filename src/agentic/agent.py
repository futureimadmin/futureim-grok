"""
Agentic RAG — multi-step reasoning loop with BIAN dual-pull and codegen mode.

Flow (architecture diagram):
  Planner → Reasoning LLM (ReAct/CoT) → Memory → Self-Reflection
       ↑                                              |
       └──────── Feedback + Retry (if score < threshold)
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
from src.query.codegen import build_codegen_system_prompt, build_codegen_user_prompt
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
        try:
            self.generator = Generator(self.cfg)
        except Exception as e:
            logger.warning("Generator unavailable: %s", e)
            self.generator = None

    def run(
        self,
        query: str,
        *,
        fleet_id: Optional[str] = None,
        rack_id: Optional[str] = None,
        tenant_id: str = "default",
        access_level: str = "public",
        user_id: Optional[str] = None,
        mode: str = "ask",
        language: str = "python",
        tier_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        memory = AgentMemory()

        if not query or not query.strip():
            raise ValueError("Empty query")
        clean = query.strip()
        mode = (mode or "ask").lower()
        if mode not in ("ask", "codegen", "agentic"):
            mode = "ask"

        fleet = get_fleet(fleet_id) if fleet_id else None
        rack = fleet.rack(rack_id) if fleet and rack_id else None
        tier = fleet.tier(tier_id) if fleet and tier_id else None
        if tier is None and rack and rack.tier_ids and fleet:
            tier = fleet.tier(rack.tier_ids[0])
        namespace = fleet.namespace(rack_id) if fleet else "default"

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
            tier_id=tier.tier_id if tier else None,
            tenant_id=tenant_id,
            access_level=access_level,
            namespace=namespace,
        )
        dual = should_dual_pull(fleet)
        domains = resolve_bian_domains(fleet, rack, tier.tier_id if tier else None) if dual else []
        if fleet and fleet.is_reference and not domains:
            domains = resolve_bian_domains(fleet, rack, tier.tier_id if tier else None)
            if not domains and rack and rack.bian_service_domains:
                domains = list(rack.bian_service_domains)

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
        memory.think(f"Scope: {describe_scope(fleet, rack, tier.tier_id if tier else None)} dual_pull={dual} mode={mode}")

        goals = self.planner.decompose(
            clean,
            bian_domains=domains,
            dual_pull=dual or bool(domains),
            mode=mode if mode != "agentic" else ("codegen" if self.planner.is_codegen_intent(clean) else "ask"),
        )
        memory.plan(goals)
        memory.think(f"User query: {clean}")

        answer = ""
        citations: List[Citation] = []
        chunks: List[RetrievedChunk] = []
        metrics = AccuracyMetrics(threshold=self.threshold)
        attempt = 0
        codegen_payload: Optional[str] = None
        effective_mode = mode
        if mode == "agentic" and self.planner.is_codegen_intent(clean):
            effective_mode = "codegen"
        elif mode == "agentic":
            effective_mode = "ask"

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
                elif tool_name == "bian_codegen":
                    result = self.tools.call(
                        "bian_codegen",
                        domains=domains,
                        language=language,
                        fleet_id=fleet_id,
                        rack_id=rack_id,
                        query=clean,
                    )
                    if result.success and result.data:
                        codegen_payload = result.data
                        memory.observe(
                            f"Generated stubs for {len(domains)} BIAN domains",
                            tool=tool_name,
                        )
                    else:
                        memory.observe(
                            f"Codegen failed: {result.error}",
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

            if effective_mode == "codegen" or codegen_payload is not None:
                if codegen_payload is None:
                    result = self.tools.call(
                        "bian_codegen",
                        domains=domains,
                        language=language,
                        fleet_id=fleet_id,
                        rack_id=rack_id,
                        query=clean,
                    )
                    codegen_payload = result.data if result.success else "# codegen failed\n"
                if self.generator is not None:
                    try:
                        sys_p = build_codegen_system_prompt(
                            fleet=fleet, rack=rack, tier=tier, domains=domains, language=language
                        )
                        user_p = build_codegen_user_prompt(clean, chunks, domains)
                        raw = self.generator.generate(f"{sys_p}\n\n{user_p}")
                        if (
                            raw
                            and len(raw) > 80
                            and "don't have enough" not in raw.lower()
                            and "[Generator fallback]" not in raw
                            and "Vertex AI not configured" not in raw
                        ):
                            answer = raw
                        else:
                            answer = codegen_payload
                    except Exception as e:
                        logger.info("LLM codegen unavailable, using deterministic stubs: %s", e)
                        answer = codegen_payload
                else:
                    answer = codegen_payload
                citations = []
                for i, c in enumerate(chunks[:6], start=1):
                    citations.append(
                        Citation(
                            source_id=i,
                            path=c.metadata.source_path if c.metadata else "bian",
                            section=getattr(c.metadata, "section_heading", None) if c.metadata else None,
                        )
                    )
            else:
                prompt = build_prompt(
                    clean,
                    chunks,
                    fleet=fleet,
                    rack=rack,
                    tier=tier,
                    bian_domains=domains or None,
                )
                if self.generator is not None:
                    try:
                        raw = self.generator.generate(prompt)
                        answer, citations, _ = post_process(raw, chunks)
                    except Exception as e:
                        logger.info("Generator failed: %s", e)
                        answer = (
                            f"(Preview) Grounded structure for scope with BIAN domains: "
                            f"{', '.join(domains) or 'none'}.\n\nQuery: {clean}\n\n"
                            f"Sources retrieved: {len(chunks)}. Enable Vertex for full generation."
                        )
                        citations = []
                else:
                    answer = (
                        f"(Preview) Grounded structure for scope with BIAN domains: "
                        f"{', '.join(domains) or 'none'}.\n\nQuery: {clean}\n\n"
                        f"Sources retrieved: {len(chunks)}. Enable Vertex for full generation."
                    )
                    citations = []

            memory.observe(f"Generated answer ({len(answer)} chars) mode={effective_mode}")

            eval_result = self.tools.call(
                "accuracy_evaluator",
                query=clean,
                answer=answer,
                chunks=chunks,
                threshold=self.threshold,
            )
            if eval_result.success and isinstance(eval_result.data, AccuracyMetrics):
                metrics = eval_result.data
            memory.critique(
                f"RAGAS={metrics.ragas_score:.3f} "
                f"faith={metrics.faithfulness:.3f} "
                f"rel={metrics.answer_relevance:.3f} "
                f"prec={metrics.context_precision:.3f} "
                f"recall={metrics.context_recall:.3f} "
                f"passed={metrics.passed}",
                meta=metrics.to_dict(),
            )

            if metrics.passed or effective_mode == "codegen":
                memory.think("Emitting final answer")
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
            "tier_id": tier.tier_id if tier else None,
            "mode": effective_mode,
            "bian_domains": domains,
            "platform": fleet.platform if fleet else None,
            "confidence_score": metrics.ragas_score,
            "ragas": metrics.to_dict(),
            "reasoning_trace": memory.reasoning_trace(),
            "tool_calls": memory.tool_calls,
            "attempts": attempt,
            "threshold_met": metrics.passed if effective_mode != "codegen" else True,
            "sub_goals": memory.sub_goals,
            "language": language if effective_mode == "codegen" else None,
        }
