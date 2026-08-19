"""
Tier 4 — Query Expansion + HyDE
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from src.common.config import RAGConfig, get_config
from src.ingestion.embedder import Embedder

logger = logging.getLogger(__name__)

_SYNONYMS = {
    "fnol": ["first notice of loss", "claim intake", "loss report"],
    "ltv": ["loan to value", "loan-to-value ratio"],
    "kyc": ["know your customer", "identity verification", "customer due diligence"],
    "sla": ["service level agreement", "service level"],
    "pii": ["personally identifiable information", "personal data"],
    "underwriting": ["risk assessment", "risk evaluation", "credit decision"],
    "delinquency": ["past due", "arrears", "late payment"],
    "retention": ["churn prevention", "win-back", "customer keep"],
}


class QueryExpander:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.cfg = config or get_config()

    def expand(self, query: str, max_variants: int = 3) -> List[str]:
        variants = [query]
        q_lower = query.lower()
        for term, syns in _SYNONYMS.items():
            if term in q_lower or any(s in q_lower for s in syns):
                for s in syns[:2]:
                    if term in q_lower:
                        v = re.sub(re.escape(term), s, query, flags=re.IGNORECASE)
                    else:
                        v = f"{query} ({s})"
                    if v not in variants:
                        variants.append(v)
                    if len(variants) >= max_variants + 1:
                        return variants
        return variants


class HyDE:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.cfg = config or get_config()
        self.embedder = Embedder()
        self._llm = None

    def _ensure_llm(self):
        if self._llm is not None:
            return
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel, GenerationConfig

            vertexai.init(project=self.cfg.project_id, location=self.cfg.region)
            self._llm = GenerativeModel(self.cfg.llm.model)
            self._gen_cfg = GenerationConfig(
                temperature=0.3,
                max_output_tokens=256,
                top_p=0.9,
            )
        except Exception as e:
            logger.warning("HyDE LLM unavailable (%s)", e)
            self._llm = False

    def hypothetical_document(self, query: str) -> str:
        self._ensure_llm()
        if not self._llm:
            return query
        prompt = (
            "Write a short, factual paragraph that would answer this question "
            "in a corporate knowledge base. Do not say you don't know. "
            "Be specific and use domain terminology.\n\n"
            f"Question: {query}\n\nHypothetical answer:"
        )
        try:
            resp = self._llm.generate_content(prompt, generation_config=self._gen_cfg)
            text = (resp.text or "").strip()
            return text if text else query
        except Exception as e:
            logger.warning("HyDE generation failed: %s", e)
            return query

    def embed_hypothesis(self, query: str) -> List[float]:
        hypo = self.hypothetical_document(query)
        logger.info("HyDE hypothesis length=%d", len(hypo))
        return self.embedder.embed_query(hypo)
