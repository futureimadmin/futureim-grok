"""
Tier 6 Top-K Selector — token-budget aware packing (diagram: pick top 6–12).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.common.config import RAGConfig, get_config
from src.common.models import RetrievedChunk

logger = logging.getLogger(__name__)


class TopKSelector:
    """Select chunks by score under a soft token budget; clamp to 6–12."""

    def __init__(self, config: Optional[RAGConfig] = None):
        self.cfg = config or get_config()

    def select(
        self,
        chunks: List[RetrievedChunk],
        k: Optional[int] = None,
        token_budget: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        if not chunks:
            return []
        k = k or self.cfg.retrieval.top_k_prompt
        k = max(6, min(12, k))
        budget = token_budget or getattr(self.cfg, "answer_budget_tokens", 1024)
        # leave headroom for system + question
        budget = int(budget * 0.75)

        selected: List[RetrievedChunk] = []
        used = 0
        for c in sorted(chunks, key=lambda x: x.score, reverse=True):
            # rough token estimate
            t = max(1, len((c.text or "").split()) * 4 // 3)
            if selected and used + t > budget and len(selected) >= 6:
                break
            selected.append(c)
            used += t
            if len(selected) >= k:
                break
        if len(selected) < 6:
            for c in sorted(chunks, key=lambda x: x.score, reverse=True):
                if c.chunk_id in {s.chunk_id for s in selected}:
                    continue
                selected.append(c)
                if len(selected) >= 6:
                    break
        logger.info("TopKSelector: in=%d out=%d tokens~%d budget=%d", len(chunks), len(selected), used, budget)
        return selected[:k]
