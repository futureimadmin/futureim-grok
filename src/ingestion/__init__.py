"""Ingestion package — lazy exports to avoid hard GCP deps at import time."""

from .chunker import Chunker

__all__ = ["Chunker", "Embedder"]


def __getattr__(name: str):
    if name == "Embedder":
        from .embedder import Embedder
        return Embedder
    raise AttributeError(name)
