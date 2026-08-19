"""
Accuracy Measurement Layer (Agentic RAG architecture).

Implements the four RAGAS-style metrics + composite score:
  - Faithfulness Score
  - Answer Relevance
  - Context Precision
  - Context Recall
  - RAGAS Score (target > 0.80)
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from src.common.models import RetrievedChunk

logger = logging.getLogger(__name__)

_STOP = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "and", "in",
    "for", "on", "with", "that", "this", "it", "as", "at", "by", "from",
    "or", "be", "not", "have", "has", "had", "but", "if", "can", "will",
}


def _tokens(text: str) -> set:
    words = re.findall(r"[a-z0-9]{3,}", (text or "").lower())
    return {w for w in words if w not in _STOP}


def _sentences(text: str) -> List[str]:
    parts = re.split(r"[.!?]+", text or "")
    return [s.strip() for s in parts if s.strip() and len(s.split()) > 2]


@dataclass
class AccuracyMetrics:
    faithfulness: float = 0.0
    answer_relevance: float = 0.0
    context_precision: float = 0.0
    context_recall: float = 0.0
    ragas_score: float = 0.0
    threshold: float = 0.80
    passed: bool = False
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def faithfulness_score(answer: str, chunks: List[RetrievedChunk]) -> float:
    if not answer or not chunks:
        return 0.0
    corpus = " ".join(c.text.lower() for c in chunks)
    corpus_toks = _tokens(corpus)
    if not corpus_toks:
        return 0.0
    grounded = 0
    total = 0
    for s in _sentences(answer):
        st = _tokens(s)
        if not st:
            continue
        total += 1
        if st & corpus_toks:
            grounded += 1
    return grounded / total if total else 1.0


def answer_relevance_score(query: str, answer: str) -> float:
    qt = _tokens(query)
    at = _tokens(answer)
    if not qt or not at:
        return 0.0
    overlap = len(qt & at) / len(qt)
    if "don't have enough information" in (answer or "").lower():
        return max(0.3, overlap * 0.5)
    return min(1.0, overlap * 1.4)


def context_precision_score(query: str, chunks: List[RetrievedChunk]) -> float:
    if not chunks:
        return 0.0
    qt = _tokens(query)
    if not qt:
        return 0.0
    useful = sum(1 for c in chunks if _tokens(c.text) & qt)
    return useful / len(chunks)


def context_recall_score(query: str, chunks: List[RetrievedChunk], answer: str) -> float:
    if not chunks:
        return 0.0
    answer_toks = _tokens(answer)
    if not answer_toks:
        return 0.5
    corpus_toks = _tokens(" ".join(c.text for c in chunks))
    if not corpus_toks:
        return 0.0
    return len(answer_toks & corpus_toks) / len(answer_toks)


def ragas_composite(
    faithfulness: float,
    answer_relevance: float,
    context_precision: float,
    context_recall: float,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    w = weights or {
        "faithfulness": 0.35,
        "answer_relevance": 0.25,
        "context_precision": 0.20,
        "context_recall": 0.20,
    }
    total_w = sum(w.values()) or 1.0
    score = (
        w["faithfulness"] * faithfulness
        + w["answer_relevance"] * answer_relevance
        + w["context_precision"] * context_precision
        + w["context_recall"] * context_recall
    ) / total_w
    return round(min(1.0, max(0.0, score)), 4)


def evaluate_accuracy(
    query: str,
    answer: str,
    chunks: List[RetrievedChunk],
    *,
    threshold: float = 0.80,
) -> AccuracyMetrics:
    t0 = time.perf_counter()
    faith = faithfulness_score(answer, chunks)
    relevance = answer_relevance_score(query, answer)
    precision = context_precision_score(query, chunks)
    recall = context_recall_score(query, chunks, answer)
    composite = ragas_composite(faith, relevance, precision, recall)
    metrics = AccuracyMetrics(
        faithfulness=round(faith, 4),
        answer_relevance=round(relevance, 4),
        context_precision=round(precision, 4),
        context_recall=round(recall, 4),
        ragas_score=composite,
        threshold=threshold,
        passed=composite >= threshold,
        detail={
            "chunks_evaluated": len(chunks),
            "answer_sentences": len(_sentences(answer)),
            "eval_ms": round((time.perf_counter() - t0) * 1000, 2),
        },
    )
    logger.info(
        "RAGAS=%.3f faith=%.3f rel=%.3f prec=%.3f recall=%.3f passed=%s",
        metrics.ragas_score,
        metrics.faithfulness,
        metrics.answer_relevance,
        metrics.context_precision,
        metrics.context_recall,
        metrics.passed,
    )
    return metrics
