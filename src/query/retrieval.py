"""
Hybrid retrieval: dense ANN (Vertex AI Vector Search) + BM25 + RRF fusion.

Implements sections 5 and 6.1 of the architecture guide.
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
from src.query.doc_store import DocStore

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
        self.doc_store = DocStore()
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
                skip = False
                for key in (
                    "fleet_id", "rack_id", "tenant_id", "access_level",
                    "product", "doc_type", "namespace",
                ):
                    if filters.get(key) and meta.get(key) not in (None, filters[key]):
                        skip = True
                        break
                if skip:
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
        query_variants: Optional[List[str]] = None,
        dense_vector_override: Optional[List[float]] = None,
    ) -> List[RetrievedChunk]:
        top_k_ann = top_k_ann or self.cfg.retrieval.top_k_ann
        top_k_final = top_k_final or self.cfg.retrieval.top_k_prompt

        qvec = dense_vector_override or self.embedder.embed_query(query)
        dense_hits = self.dense_search(qvec, top_k=top_k_ann, filters=filters)
        variants = query_variants or [query]
        bm25_lists = [self.bm25_search(v, top_k=top_k_ann, filters=filters) for v in variants]
        bm25_best: Dict[str, float] = {}
        for hits in bm25_lists:
            for cid, sc in hits:
                bm25_best[cid] = max(sc, bm25_best.get(cid, 0.0))
        bm25_hits = sorted(bm25_best.items(), key=lambda x: x[1], reverse=True)[:top_k_ann]

        dense_ids = [cid for cid, _ in dense_hits]
        bm25_ids = [cid for cid, _ in bm25_hits]
        fused = reciprocal_rank_fusion([dense_ids, bm25_ids], k=self.cfg.retrieval.rrf_k)[:top_k_ann]

        results: List[RetrievedChunk] = []
        for cid, score in fused[:top_k_final]:
            doc = self._doc_store.get(cid) or self.doc_store.get(cid) or {}
            meta_raw = doc.get("metadata", {}) if isinstance(doc, dict) else {}
            if not isinstance(doc, dict):
                doc = {}
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

    def retrieve_dual(
        self,
        query: str,
        *,
        product_filters: Optional[Dict] = None,
        bian_filter_list: Optional[List[Dict]] = None,
        top_k_ann: Optional[int] = None,
        top_k_final: Optional[int] = None,
        query_variants: Optional[List[str]] = None,
        dense_vector_override: Optional[List[float]] = None,
        bian_share: float = 0.35,
    ) -> List[RetrievedChunk]:
        """Dual-pull: product fleet + BIAN reference domains, merge by score."""
        top_k_final = top_k_final or self.cfg.retrieval.top_k_prompt
        product = self.retrieve(
            query,
            top_k_ann=top_k_ann,
            top_k_final=top_k_final,
            filters=product_filters,
            query_variants=query_variants,
            dense_vector_override=dense_vector_override,
        )

        bian_chunks: List[RetrievedChunk] = []
        for bf in bian_filter_list or []:
            part = self.retrieve(
                query,
                top_k_ann=top_k_ann,
                top_k_final=max(4, top_k_final // 2),
                filters=bf,
                query_variants=query_variants,
                dense_vector_override=dense_vector_override,
            )
            bian_chunks.extend(part)

        by_id: Dict[str, RetrievedChunk] = {}
        for c in product + bian_chunks:
            prev = by_id.get(c.chunk_id)
            if prev is None or c.score > prev.score:
                by_id[c.chunk_id] = c
        merged = sorted(by_id.values(), key=lambda x: x.score, reverse=True)

        if not bian_chunks or not product:
            return merged[:top_k_final]

        n_bian = max(1, int(top_k_final * bian_share))
        bian_ids = {c.chunk_id for c in bian_chunks}
        bian_picked = [c for c in merged if c.chunk_id in bian_ids][:n_bian]
        rest = [c for c in merged if c.chunk_id not in {x.chunk_id for x in bian_picked}]
        out = (bian_picked + rest)[:top_k_final]
        logger.info(
            "Dual retrieve: product=%d bian=%d merged=%d returned=%d (bian_slots=%d)",
            len(product), len(bian_chunks), len(merged), len(out), n_bian,
        )
        return out
