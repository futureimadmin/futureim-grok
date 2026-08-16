"""
Four-slot prompt builder with optional Fleet / Rack domain hints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from src.common.models import RetrievedChunk

if TYPE_CHECKING:
    from src.fleet.models import Fleet, Rack

SYSTEM_PROMPT_BASE = """You are a helpful assistant for the organisation's documentation.
Answer ONLY from the provided context below.
If the context does not contain sufficient information to answer the question,
say exactly: "I don't have enough information in the documentation."
Do not use your prior training knowledge — only the provided sources.
Always cite your sources using [Source N] notation immediately after each claim.
Format: answer in clear prose, then a "Sources:" section with full references."""

GROUNDING_GUARDRAIL = """Using ONLY the sources above, answer the question below.
Do not use prior knowledge. If you are unsure, say so."""


def build_prompt(
    query: str,
    chunks: List[RetrievedChunk],
    fleet: Optional["Fleet"] = None,
    rack: Optional["Rack"] = None,
) -> str:
    domain_lines = []
    if fleet:
        domain_lines.append(f"Domain fleet: {fleet.name} ({fleet.fleet_id}).")
        if fleet.system_prompt_hint:
            domain_lines.append(fleet.system_prompt_hint)
    if rack:
        domain_lines.append(f"Specialty rack: {rack.name} — {rack.description}")

    system = SYSTEM_PROMPT_BASE
    if domain_lines:
        system = system + "\n\n" + "\n".join(domain_lines)

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
        f"{system}\n\n"
        f"Context:\n\n{context_block}\n\n"
        f"{GROUNDING_GUARDRAIL}\n\n"
        f"Question: {query}"
    )
