"""
Hybrid retrieval: dense ANN (Vertex AI Vector Search) + BM25 + RRF fusion.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

from rank_bm25 import BM25Okapi

from src.common.config import RAGConfig, get_config
from src.common.models import ChunkMetadata, RetrievedChunk
from src.ingestion.embedder import Embedder
from src.query.vector_store import VectorStore

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[str]],
    k: int = 60,
) -> List[Tuple[str, float]]:
    scores: Dict[str, float] = defaultdict(float)
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked, start=1):
            scores[doc_id] += 1.0 / (rank + k)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class HybridRetriever:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.cfg = config or get_config()
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self._bm25: Optional[BM25Okapi] = None
        self._bm25_ids: List[str] = []
        self._bm25_texts: List[str] = []
        self._doc_store: Dict[str, dict] = {}

    def add_documents(self, records: List[dict]) -> None:
        for r in records:
            cid = r["id"]
            text = r.get("text", "")
            self._doc_store[cid] = {"text": text, "metadata": r.get("metadata", {})}
            if cid not in self._bm25_ids:
                self._bm25_ids.append(cid)
                self._bm25_texts.append(text)
        tokenized = [t.lower().split() for t in self._bm25_texts]
        if tokenized:
            self._bm25 = BM25Okapi(tokenized)

    def dense_search(
        self,
        query_vector: List[float],
        top_k: int = 50,
        filters: Optional[Dict] = None,
    ) -> List[Tuple[str, float]]:
        hits = self.vector_store.search(query_vector, top_k=top_k, filters=filters)
        logger.info("Dense search top_k=%d filters=%s hits=%d", top_k, filters, len(hits))
        return hits

    def bm25_search(
        self,
        query: str,
        top_k: int = 50,
        filters: Optional[Dict] = None,
    ) -> List[Tuple[str, float]]:
        if not self._bm25 or not self._bm25_ids:
            return []
        tokens = query.lower().split()
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(zip(self._bm25_ids, scores), key=lambda x: x[1], reverse=True)
        out: List[Tuple[str, float]] = []
        for cid, s in ranked:
            if s <= 0:
                continue
            if filters:
                doc = self._doc_store.get(cid, {})
                meta = doc.get("metadata") or {}
                if filters.get("fleet_id") and meta.get("fleet_id") not in (None, filters["fleet_id"]):
                    continue
                if filters.get("rack_id") and meta.get("rack_id") not in (None, filters["rack_id"]):
                    continue
                if filters.get("tenant_id") and meta.get("tenant_id") not in (None, filters["tenant_id"]):
                    continue
            out.append((cid, float(s)))
            if len(out) >= top_k:
                break
        return out

    def retrieve(
        self,
        query: str,
        top_k_ann: Optional[int] = None,
        top_k_final: Optional[int] = None,
        filters: Optional[Dict] = None,
    ) -> List[RetrievedChunk]:
        top_k_ann = top_k_ann or self.cfg.retrieval.top_k_ann
        top_k_final = top_k_final or self.cfg.retrieval.top_k_prompt
        qvec = self.embedder.embed_query(query)
        dense_hits = self.dense_search(qvec, top_k=top_k_ann, filters=filters)
        bm25_hits = self.bm25_search(query, top_k=top_k_ann, filters=filters)
        dense_ids = [cid for cid, _ in dense_hits]
        bm25_ids = [cid for cid, _ in bm25_hits]
        fused = reciprocal_rank_fusion([dense_ids, bm25_ids], k=self.cfg.retrieval.rrf_k)[:top_k_ann]
        results: List[RetrievedChunk] = []
        for cid, score in fused[:top_k_final]:
            doc = self._doc_store.get(cid, {})
            meta_raw = doc.get("metadata", {})
            try:
                meta = ChunkMetadata(**meta_raw) if meta_raw else ChunkMetadata(source_path="unknown")
            except Exception:
                meta = ChunkMetadata(source_path=str(meta_raw.get("source_path", "unknown")))
            results.append(
                RetrievedChunk(
                    chunk_id=cid,
                    text=doc.get("text", ""),
                    score=score,
                    source="hybrid",
                    metadata=meta,
                )
            )
        logger.info(
            "Hybrid retrieve: dense=%d bm25=%d fused=%d returned=%d",
            len(dense_ids), len(bm25_ids), len(fused), len(results),
        )
        return results
