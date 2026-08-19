"""
Five-stage post-processing pipeline (section 10 of the architecture guide).
"""

from __future__ import annotations

import re
from typing import List, Tuple

from src.common.models import Citation, RetrievedChunk


def resolve_citations(
    answer: str,
    chunks: List[RetrievedChunk],
) -> Tuple[str, List[Citation]]:
    citations: List[Citation] = []
    pattern = re.compile(r"\[Source\s+(\d+)\]", re.IGNORECASE)

    def _replace(m: re.Match) -> str:
        n = int(m.group(1))
        if 1 <= n <= len(chunks):
            c = chunks[n - 1]
            citations.append(
                Citation(
                    source_id=n,
                    path=c.metadata.source_path if c.metadata else "unknown",
                    section=c.metadata.section_heading if c.metadata else None,
                    date=None,
                )
            )
            return f"[Source {n}]"
        return "[Source ?]"

    cleaned = pattern.sub(_replace, answer)
    seen = set()
    unique: List[Citation] = []
    for cit in citations:
        if cit.source_id not in seen:
            seen.add(cit.source_id)
            unique.append(cit)
    return cleaned, unique


def faithfulness_heuristic(answer: str, chunks: List[RetrievedChunk]) -> float:
    if not answer or not chunks:
        return 0.0
    stop = {"the", "a", "an", "is", "are", "to", "of", "and", "in", "for", "on", "with"}
    corpus = " ".join(c.text.lower() for c in chunks)
    sentences = re.split(r"[.!?]+", answer)
    grounded = 0
    total = 0
    for s in sentences:
        words = [w for w in s.lower().split() if w not in stop and len(w) > 2]
        if not words:
            continue
        total += 1
        if any(w in corpus for w in words):
            grounded += 1
    return grounded / total if total else 1.0


def safety_filter(text: str) -> str:
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "[REDACTED_EMAIL]",
        text,
    )
    text = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[REDACTED_PHONE]", text)
    return text


def post_process(
    raw_answer: str,
    chunks: List[RetrievedChunk],
) -> Tuple[str, List[Citation], float]:
    answer, citations = resolve_citations(raw_answer, chunks)
    faith = faithfulness_heuristic(answer, chunks)
    answer = safety_filter(answer)
    answer = re.sub(r"\n+Question:\s*$", "", answer).strip()
    return answer, citations, faith
