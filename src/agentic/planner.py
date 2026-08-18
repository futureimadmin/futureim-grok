"""
Planner — decompose a user query into sub-goals (Agent Core).
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from src.common.config import RAGConfig, get_config

logger = logging.getLogger(__name__)


class Planner:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.cfg = config or get_config()

    def decompose(self, query: str) -> List[str]:
        q = (query or "").strip()
        if not q:
            return ["retrieve relevant context", "synthesize answer"]

        goals: List[str] = []
        lower = q.lower()

        if any(w in lower for w in ("compare", "difference", "vs", "versus", "better")):
            parts = re.split(r"\b(?:vs\.?|versus|compared to|compare)\b", q, flags=re.I)
            parts = [p.strip(" ?.") for p in parts if p.strip(" ?.")]
            if len(parts) >= 2:
                goals.append(f"retrieve facts about: {parts[0]}")
                goals.append(f"retrieve facts about: {parts[1]}")
                goals.append("compare the retrieved facts")
            else:
                goals.append(f"retrieve comparative context for: {q}")
                goals.append("synthesize comparison")
        elif any(w in lower for w in ("and also", "as well as", "list", "steps", "how to")):
            clauses = re.split(r"\b(?:and also|as well as|;)\b", q, flags=re.I)
            clauses = [c.strip(" ?.") for c in clauses if c.strip(" ?.")]
            if len(clauses) > 1:
                for c in clauses[:4]:
                    goals.append(f"retrieve context for: {c}")
            else:
                goals.append(f"retrieve step-by-step context for: {q}")
            goals.append("synthesize structured answer")
        elif any(w in lower for w in ("summarise", "summarize", "overview", "explain")):
            goals.append(f"retrieve broad context for: {q}")
            goals.append("synthesize summary")
        else:
            goals.append(f"retrieve relevant context for: {q}")
            goals.append("synthesize factual answer")

        if "evaluate answer quality" not in goals:
            goals.append("evaluate answer quality")

        logger.info("Planner produced %d sub-goals", len(goals))
        return goals
