"""
Embedder – Vertex AI embeddings + dual-write records (vector metadata, no raw text).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.common.config import EmbeddingConfig, get_config
from src.common.models import Chunk

logger = logging.getLogger(__name__)


class Embedder:
    def __init__(
        self,
        project_id: Optional[str] = None,
        region: Optional[str] = None,
        config: Optional[EmbeddingConfig] = None,
    ):
        cfg = get_config()
        self.project = project_id or cfg.project_id
        self.region = region or cfg.region
        self.cfg = config or cfg.embedding
        self.model = None
        self._init_error: Optional[str] = None
        try:
            from google.cloud import aiplatform
            from vertexai.language_models import TextEmbeddingModel

            aiplatform.init(project=self.project, location=self.region)
            self.model = TextEmbeddingModel.from_pretrained(self.cfg.model)
        except Exception as e:
            self._init_error = str(e)
            logger.warning("Embedder Vertex init deferred/unavailable: %s", e)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self.model is None:
            raise RuntimeError(f"Vertex embedder unavailable: {self._init_error}")
        from vertexai.language_models import TextEmbeddingInput

        inputs = [TextEmbeddingInput(text=t, task_type="RETRIEVAL_DOCUMENT") for t in texts]
        batch_size = self.cfg.batch_size
        all_embeddings: List[List[float]] = []
        for i in range(0, len(inputs), batch_size):
            batch = inputs[i : i + batch_size]
            embeddings = self.model.get_embeddings(batch)
            all_embeddings.extend([e.values for e in embeddings])
        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        if self.model is None:
            raise RuntimeError(f"Vertex embedder unavailable: {self._init_error}")
        from vertexai.language_models import TextEmbeddingInput

        inp = TextEmbeddingInput(text=query, task_type="RETRIEVAL_QUERY")
        result = self.model.get_embeddings([inp])
        return result[0].values

    def process_chunks(self, chunks: List[Chunk]) -> List[dict]:
        texts = [c.text for c in chunks]
        vectors = self.embed_texts(texts)
        records = []
        for chunk, vec in zip(chunks, vectors):
            meta = chunk.metadata.model_dump(mode="json")
            meta["token_count"] = chunk.token_count
            records.append(
                {
                    "id": chunk.chunk_id,
                    "embedding": vec,
                    "metadata": meta,
                }
            )
        logger.info("Embedded %d chunks with model %s", len(records), self.cfg.model)
        return records
