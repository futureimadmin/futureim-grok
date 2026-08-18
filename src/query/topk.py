"""
Top-K selection with optional token budget (Tier 6 prompt assembly).

Selects highest-scoring chunks that fit within max_tokens for the context slot.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.common.config import RAGConfig, get_config
from src.common.models import RetrievedChunk

logger = logging.getLogger(__name__)


def _approx_tokens(text: str) -> int:
    # ~4 chars per token heuristic
    return max(1, len(text) // 4)


class TopKSelector:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.cfg = config or get_config()

    def select(
        self,
        chunks: List[RetrievedChunk],
        k: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        if not chunks:
            return []
        k = k if k is not None else self.cfg.retrieval.top_k_prompt
        budget = max_tokens
        if budget is None:
            # leave headroom for system + query slots
            budget = max(256, self.cfg.max_query_tokens - 400)

        ranked = sorted(chunks, key=lambda c: c.score, reverse=True)
        selected: List[RetrievedChunk] = []
        used = 0
        for ch in ranked:
            if len(selected) >= k:
                break
            t = _approx_tokens(ch.text or "")
            if selected and used + t > budget:
                continue
            selected.append(ch)
            used += t
        logger.debug("TopK selected=%d tokens~%d budget=%d", len(selected), used, budget)
        return selected
