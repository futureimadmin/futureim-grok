"""
Four-slot prompt builder with Fleet / Rack / Tier / BIAN domain hints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from src.common.models import RetrievedChunk

if TYPE_CHECKING:
    from src.fleet.models import Fleet, Rack, Tier

SYSTEM_PROMPT_BASE = """You are a helpful assistant for the organisation's documentation.
Answer ONLY from the provided context below.
If the context does not contain sufficient information to answer the question,
say exactly: "I don't have enough information in the documentation."
Do not use your prior training knowledge — only the provided sources.
Always cite your sources using [Source N] notation immediately after each claim.
Format: answer in clear prose, then a "Sources:" section with full references."""

BIAN_PLATFORM_HINT = """This fleet runs on the BIAN (Banking Industry Architecture Network) base platform.
When discussing or designing services, use official BIAN service domain and business object names
from the reference context. Keep bank-specific product policy in product sources; keep structural
boundaries aligned to BIAN. Prefer clear separation between domains (e.g. Loan vs Credit Management
vs Customer Offer vs Payment Order / Payment Execution)."""

GROUNDING_GUARDRAIL = """Using ONLY the sources above, answer the question below.
Do not use prior knowledge. If you are unsure, say so."""


def build_prompt(
    query: str,
    chunks: List[RetrievedChunk],
    fleet: Optional["Fleet"] = None,
    rack: Optional["Rack"] = None,
    tier: Optional["Tier"] = None,
    bian_domains: Optional[List[str]] = None,
) -> str:
    domain_lines = []
    if fleet:
        domain_lines.append(f"Domain fleet: {fleet.name} ({fleet.fleet_id}).")
        if fleet.platform == "bian":
            domain_lines.append(
                f"Platform: BIAN base (version {fleet.bian_version or '12'})."
            )
            domain_lines.append(BIAN_PLATFORM_HINT)
        if fleet.system_prompt_hint:
            domain_lines.append(fleet.system_prompt_hint)
    if rack:
        domain_lines.append(f"Specialty rack: {rack.name} — {rack.description}")
        if rack.bian_service_domains:
            domain_lines.append(
                "Rack BIAN service domains: " + ", ".join(rack.bian_service_domains)
            )
    if tier:
        domain_lines.append(f"Logical tier: {tier.name} ({tier.tier_id}) — {tier.description}")
    if bian_domains:
        domain_lines.append(
            "Active BIAN reference domains in context: " + ", ".join(bian_domains)
        )

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
        if c.metadata and getattr(c.metadata, "bian_service_domain", None):
            header += f" [BIAN:{c.metadata.bian_service_domain}]"
        if c.metadata and getattr(c.metadata, "is_bian_reference", False):
            header += " [reference]"
        context_parts.append(f"{header}\n{c.text}")

    context_block = "\n\n".join(context_parts) if context_parts else "(no sources retrieved)"

    return (
        f"{system}\n\n"
        f"Context:\n\n{context_block}\n\n"
        f"{GROUNDING_GUARDRAIL}\n\n"
        f"Question: {query}"
    )
