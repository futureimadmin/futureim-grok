"""
Tool Registry — agent selects tools dynamically based on sub-goal.

Tools:
  - rag_retrieval      product + optional BIAN dual-pull
  - accuracy_evaluator RAGAS metrics
  - web_search / code_executor / api_db stubs
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.agentic.metrics import AccuracyMetrics, evaluate_accuracy
from src.common.config import RAGConfig, get_config
from src.common.models import RetrievedChunk
from src.query.retrieval import HybridRetriever
from src.query.reranker import CrossEncoderReranker
from src.query.topk import TopKSelector

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    tool: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.cfg = config or get_config()
        self.retriever = HybridRetriever(self.cfg)
        self.reranker = CrossEncoderReranker(self.cfg)
        self.topk = TopKSelector(self.cfg)
        self._tools: Dict[str, Callable[..., ToolResult]] = {
            "rag_retrieval": self.rag_retrieval,
            "accuracy_evaluator": self.accuracy_evaluator,
            "web_search": self.web_search,
            "code_executor": self.code_executor,
            "api_db": self.api_db,
        }

    def available(self) -> List[str]:
        return list(self._tools.keys())

    def call(self, name: str, **kwargs) -> ToolResult:
        fn = self._tools.get(name)
        if not fn:
            return ToolResult(tool=name, success=False, error=f"Unknown tool: {name}")
        t0 = time.perf_counter()
        try:
            result = fn(**kwargs)
            result.latency_ms = (time.perf_counter() - t0) * 1000
            return result
        except Exception as e:
            logger.exception("Tool %s failed", name)
            return ToolResult(
                tool=name,
                success=False,
                error=str(e),
                latency_ms=(time.perf_counter() - t0) * 1000,
            )

    def rag_retrieval(
        self,
        query: str,
        filters: Optional[Dict] = None,
        top_k: int = 8,
        dual_pull: bool = False,
        bian_filter_list: Optional[List[Dict]] = None,
        **_kwargs,
    ) -> ToolResult:
        if dual_pull and bian_filter_list is not None:
            candidates = self.retriever.retrieve_dual(
                query,
                product_filters=filters or {},
                bian_filter_list=bian_filter_list,
                top_k_ann=self.cfg.retrieval.top_k_ann,
                top_k_final=max(top_k * 2, 16),
            )
        else:
            candidates = self.retriever.retrieve(
                query,
                top_k_ann=self.cfg.retrieval.top_k_ann,
                top_k_final=max(top_k * 2, 20),
                filters=filters or {},
            )
        if candidates:
            candidates = self.reranker.rerank(query, candidates, top_k=max(top_k * 2, 16))
            candidates = self.topk.select(candidates, k=top_k)
        return ToolResult(
            tool="rag_retrieval",
            success=True,
            data=candidates,
            meta={"n": len(candidates), "filters": filters or {}, "dual_pull": dual_pull},
        )

    def accuracy_evaluator(
        self,
        query: str,
        answer: str,
        chunks: Optional[List[RetrievedChunk]] = None,
        threshold: float = 0.80,
        **_kwargs,
    ) -> ToolResult:
        metrics: AccuracyMetrics = evaluate_accuracy(
            query, answer, chunks or [], threshold=threshold
        )
        return ToolResult(
            tool="accuracy_evaluator",
            success=True,
            data=metrics,
            meta={"passed": metrics.passed, "ragas": metrics.ragas_score},
        )

    def web_search(self, query: str, **_kwargs) -> ToolResult:
        return ToolResult(tool="web_search", success=True, data=[], meta={"note": "web_search stub"})

    def code_executor(self, code: str = "", **_kwargs) -> ToolResult:
        return ToolResult(tool="code_executor", success=True, data=None, meta={"note": "code_executor stub"})

    def api_db(self, query: str = "", **_kwargs) -> ToolResult:
        return ToolResult(tool="api_db", success=True, data=None, meta={"note": "api_db stub"})

    def select_for_goal(self, goal: str) -> str:
        g = goal.lower()
        if any(w in g for w in ("evaluate", "quality", "faithfulness", "accuracy", "ragas")):
            return "accuracy_evaluator"
        if any(w in g for w in ("web", "internet", "online")):
            return "web_search"
        if any(w in g for w in ("compute", "calculate", "sql", "code")):
            return "code_executor"
        if any(w in g for w in ("crm", "erp", "database", "api")):
            return "api_db"
        return "rag_retrieval"
