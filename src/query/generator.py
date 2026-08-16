"""
LLM generation via Vertex AI Gemini (section 9 of the architecture guide).
Temperature kept low for factual RAG.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.common.config import RAGConfig, get_config

logger = logging.getLogger(__name__)


class Generator:
    def __init__(self, config: Optional[RAGConfig] = None):
        self.cfg = config or get_config()
        self._model = None

    def _ensure_model(self):
        if self._model is not None:
            return
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel, GenerationConfig

            vertexai.init(project=self.cfg.project_id, location=self.cfg.region)
            self._model = GenerativeModel(self.cfg.llm.model)
            self._gen_config = GenerationConfig(
                temperature=self.cfg.llm.temperature,
                max_output_tokens=self.cfg.llm.max_output_tokens,
                top_p=self.cfg.llm.top_p,
            )
        except Exception as e:
            logger.warning("Vertex AI init failed (%s) – using echo fallback", e)
            self._model = None

    def generate(self, prompt: str) -> str:
        self._ensure_model()
        if self._model is None:
            return (
                "[Generator fallback] Vertex AI not configured. "
                "Prompt length=%d chars. Wire GCP credentials to enable Gemini."
                % len(prompt)
            )
        try:
            response = self._model.generate_content(
                prompt,
                generation_config=self._gen_config,
            )
            return response.text or ""
        except Exception as e:
            logger.exception("Generation failed")
            return f"I encountered an error generating the answer: {e}"
