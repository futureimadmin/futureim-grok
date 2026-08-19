"""
Tier 6 — Top-K Selector with token budget.

Architecture diagram:
  Top-K Selector  ·  token budget → pick top 6–12 chunks

After RRF + cross-encoder rerank, select the highest-scoring chunks
that fit under a configurable context token budget so the prompt
stays within the LLM window.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.common.config import RAGConfig, get_config
from src.common.models import RetrievedChunk

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(len(text.split()), len(text) // 4)


class TopKSelector:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.cfg = config or get_config()
        answer = self.cfg.answer_budget_tokens
        buffer = int(self.cfg.max_query_tokens * self.cfg.safety_buffer_pct)
        self.default_budget = max(512, self.cfg.max_query_tokens - answer - buffer)
        self.min_k = 6
        self.max_k = 12

    def select(
        self,
        chunks: List[RetrievedChunk],
        *,
        k: Optional[int] = None,
        token_budget: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        if not chunks:
            return []

        target_k = k or self.cfg.retrieval.top_k_prompt
        target_k = max(self.min_k, min(self.max_k, target_k, len(chunks)))
        budget = token_budget if token_budget is not None else self.default_budget

        selected: List[RetrievedChunk] = []
        used = 0
        for c in chunks:
            t = _estimate_tokens(c.text)
            if selected and used + t > budget:
                if len(selected) < self.min_k and used + t <= int(budget * 1.25):
                    selected.append(c)
                    used += t
                    continue
                break
            selected.append(c)
            used += t
            if len(selected) >= target_k:
                break

        logger.info(
            "TopK selected %d/%d chunks (~%d tokens, budget=%d)",
            len(selected),
            len(chunks),
            used,
            budget,
        )
        return selected
