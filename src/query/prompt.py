"""
Four-slot prompt builder (section 8 of the architecture guide).

Slot 1 – System prompt (role + grounding + citation format)
Slot 2 – Retrieved context (top-K chunks with source metadata)
Slot 3 – Grounding guardrail (repeated immediately before the query)
Slot 4 – User query
"""

from __future__ import annotations

from typing import List

from src.common.models import RetrievedChunk

SYSTEM_PROMPT = """You are a helpful assistant for the organisation's documentation.
Answer ONLY from the provided context below.
If the context does not contain sufficient information to answer the question,
say exactly: "I don't have enough information in the documentation."
Do not use your prior training knowledge — only the provided sources.
Always cite your sources using [Source N] notation immediately after each claim.
Format: answer in clear prose, then a "Sources:" section with full references."""

GROUNDING_GUARDRAIL = """Using ONLY the sources above, answer the question below.
Do not use prior knowledge. If you are unsure, say so."""


def build_prompt(query: str, chunks: List[RetrievedChunk]) -> str:
    context_parts = []
    for i, c in enumerate(chunks, start=1):
        path = c.metadata.source_path if c.metadata else "unknown"
        section = c.metadata.section_heading if c.metadata else None
        header = f"[Source {i}] {path}"
        if section:
            header += f" — {section}"
        context_parts.append(f"{header}\n{c.text}")

    context_block = "\n\n".join(context_parts) if context_parts else "(no sources retrieved)"

    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Context:\n\n{context_block}\n\n"
        f"{GROUNDING_GUARDRAIL}\n\n"
        f"Question: {query}"
    )
