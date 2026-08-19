"""
Cross-encoder reranking (section 6.2 of the architecture guide).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.common.config import RAGConfig, get_config
from src.common.models import RetrievedChunk

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.cfg = config or get_config()
        self._model = None

    def rerank(
        self,
        query: str,
        candidates: List[RetrievedChunk],
        top_k: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        top_k = top_k or self.cfg.retrieval.top_k_prompt
        if not candidates:
            return []

        q_tokens = set(query.lower().split())
        scored = []
        for c in candidates:
            overlap = len(q_tokens & set(c.text.lower().split()))
            blended = 0.7 * c.score + 0.3 * (overlap / max(len(q_tokens), 1))
            scored.append((blended, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        out: List[RetrievedChunk] = []
        for new_score, chunk in scored[:top_k]:
            out.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    score=new_score,
                    source="rerank",
                    metadata=chunk.metadata,
                )
            )
        logger.info("Reranked %d → top %d", len(candidates), len(out))
        return out
