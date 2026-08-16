"""
Embedder – converts Chunk objects into vectors using Vertex AI embeddings
and performs the dual write described in the architecture:

  1. Vector store upsert (id + float[] + metadata)  – no raw text
  2. Doc store write (id → raw text + full metadata)

This component never touches a live user request.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

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

        aiplatform.init(project=self.project, location=self.region)
        self.model = TextEmbeddingModel.from_pretrained(self.cfg.model)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Batch embed with Vertex AI. Returns list of float vectors."""
        if not texts:
            return []
        inputs = [TextEmbeddingInput(text=t, task_type="RETRIEVAL_DOCUMENT") for t in texts]
        batch_size = self.cfg.batch_size
        all_embeddings: List[List[float]] = []
        for i in range(0, len(inputs), batch_size):
            batch = inputs[i : i + batch_size]
            embeddings = self.model.get_embeddings(batch)
            all_embeddings.extend([e.values for e in embeddings])
        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        """Single query embedding (task_type=RETRIEVAL_QUERY)."""
        inp = TextEmbeddingInput(text=query, task_type="RETRIEVAL_QUERY")
        result = self.model.get_embeddings([inp])
        return result[0].values

    def process_chunks(self, chunks: List[Chunk]) -> List[dict]:
        """
        Returns a list of records ready for vector-store upsert:
        {
          "id": chunk_id,
          "embedding": [...],
          "metadata": {...}   # no raw text
        }
        and (separately) the caller should write the raw text to the doc store.
        """
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
                    # raw text is intentionally NOT stored in the vector index
                }
            )
        logger.info("Embedded %d chunks with model %s", len(records), self.cfg.model)
        return records
