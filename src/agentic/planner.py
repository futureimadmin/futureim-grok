"""
Planner — decompose a user query into sub-goals (Agent Core).

BIAN-aware: banking fleets get explicit dual-retrieve goals and optional
codegen goals that stay inside active BIAN service domains.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Sequence

from src.common.config import RAGConfig, get_config

logger = logging.getLogger(__name__)

CODEGEN_HINTS = (
    "generate code",
    "codegen",
    "code gen",
    "service stub",
    "stubs",
    "scaffold",
    "implement service",
    "api stub",
    "skeleton",
    "boilerplate",
    "generate api",
    "create service",
)


class Planner:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.cfg = config or get_config()

    def is_codegen_intent(self, query: str) -> bool:
        lower = (query or "").lower()
        return any(h in lower for h in CODEGEN_HINTS)

    def decompose(
        self,
        query: str,
        *,
        bian_domains: Optional[Sequence[str]] = None,
        dual_pull: bool = False,
        mode: Optional[str] = None,
    ) -> List[str]:
        q = (query or "").strip()
        if not q:
            return ["retrieve relevant context", "synthesize answer"]

        goals: List[str] = []
        lower = q.lower()
        domains = list(bian_domains or [])
        want_codegen = (mode == "codegen") or self.is_codegen_intent(q)

        if any(w in lower for w in ("compare", "difference", "vs", "versus", "better")):
            parts = re.split(r"\b(?:vs\.?|versus|compared to|compare)\b", q, flags=re.I)
            parts = [p.strip(" ?." ) for p in parts if p.strip(" ?.")]
            if len(parts) >= 2:
                goals.append(f"retrieve facts about: {parts[0]}")
                goals.append(f"retrieve facts about: {parts[1]}")
                goals.append("synthesize comparative answer")
            else:
                goals.append(f"retrieve context for: {q}")
                goals.append("synthesize answer")
        elif any(w in lower for w in ("how to", "steps", "procedure", "process")):
            goals.append(f"retrieve procedure for: {q}")
            goals.append("synthesize step-by-step answer")
        elif want_codegen:
            if dual_pull and domains:
                goals.append("retrieve BIAN reference context for: " + ", ".join(domains))
                goals.append(f"retrieve product policy context for: {q}")
            else:
                goals.append(f"retrieve context for: {q}")
            goals.append("generate BIAN-aligned service stubs")
            goals.append("evaluate accuracy of generated design")
        else:
            if dual_pull and domains:
                goals.append("retrieve BIAN reference context for: " + ", ".join(domains))
                goals.append(f"retrieve product context for: {q}")
            else:
                goals.append(f"retrieve context for: {q}")
            goals.append("synthesize answer")
            goals.append("evaluate answer quality")

        if not any("evaluat" in g.lower() for g in goals):
            goals.append("evaluate answer quality")

        logger.info(
            "plan goals=%s codegen=%s dual=%s domains=%s",
            goals, want_codegen, dual_pull, domains,
        )
        return goals
