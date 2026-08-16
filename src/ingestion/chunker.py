"""
Semantic chunker with fleet/rack metadata support.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import List, Optional

import tiktoken

from src.common.config import ChunkConfig, get_config
from src.common.models import AccessLevel, Chunk, ChunkMetadata, DocType


class Chunker:
    def __init__(self, config: Optional[ChunkConfig] = None):
        self.cfg = config or get_config().chunk
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.encoder = None

    def _count_tokens(self, text: str) -> int:
        if self.encoder:
            return len(self.encoder.encode(text))
        return max(1, len(text.split()) * 4 // 3)

    def _make_chunk_id(self, source_path: str, index: int, text: str) -> str:
        digest = hashlib.sha256(f"{source_path}:{index}:{text[:64]}".encode()).hexdigest()[:12]
        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(source_path).stem)[:40]
        return f"{safe}_chunk_{index:04d}_{digest}"

    def _split_semantic(self, text: str) -> List[str]:
        parts = re.split(r"(?=\n#{1,6}\s)", text)
        if len(parts) == 1:
            parts = re.split(r"\n\s*\n", text)
        chunks: List[str] = []
        current: List[str] = []
        current_tokens = 0
        for part in parts:
            part = part.strip()
            if not part:
                continue
            t = self._count_tokens(part)
            if current_tokens + t > self.cfg.chunk_size and current:
                chunks.append("\n\n".join(current))
                if self.cfg.overlap > 0:
                    overlap_text = self._take_last_tokens("\n\n".join(current), self.cfg.overlap)
                    current = [overlap_text, part] if overlap_text else [part]
                    current_tokens = self._count_tokens("\n\n".join(current))
                else:
                    current = [part]
                    current_tokens = t
            else:
                current.append(part)
                current_tokens += t
        if current:
            chunks.append("\n\n".join(current))
        return [c for c in chunks if self._count_tokens(c) >= self.cfg.min_chunk_size]

    def _take_last_tokens(self, text: str, n: int) -> str:
        if not self.encoder:
            words = text.split()
            return " ".join(words[-n:]) if words else ""
        tokens = self.encoder.encode(text)
        if len(tokens) <= n:
            return text
        return self.encoder.decode(tokens[-n:])

    def _split_fixed(self, text: str) -> List[str]:
        if not self.encoder:
            words = text.split()
            size = self.cfg.chunk_size
            step = max(1, size - self.cfg.overlap)
            return [" ".join(words[i : i + size]) for i in range(0, len(words), step)]
        tokens = self.encoder.encode(text)
        size = self.cfg.chunk_size
        step = max(1, size - self.cfg.overlap)
        chunks = []
        for i in range(0, len(tokens), step):
            chunk_tokens = tokens[i : i + size]
            if len(chunk_tokens) < self.cfg.min_chunk_size:
                continue
            chunks.append(self.encoder.decode(chunk_tokens))
        return chunks

    def chunk_document(
        self,
        text: str,
        source_path: str,
        *,
        doc_type: DocType = DocType.OTHER,
        product: Optional[str] = None,
        tenant_id: str = "default",
        fleet_id: Optional[str] = None,
        rack_id: Optional[str] = None,
        access_level: AccessLevel = AccessLevel.PUBLIC,
        language: str = "en",
        section_heading: Optional[str] = None,
    ) -> List[Chunk]:
        if self.cfg.strategy == "semantic":
            raw_chunks = self._split_semantic(text)
        elif self.cfg.strategy == "sentence":
            sentences = re.split(r"(?<=[.!?])\s+", text)
            raw_chunks = self._pack_sentences(sentences)
        else:
            raw_chunks = self._split_fixed(text)

        results: List[Chunk] = []
        for i, chunk_text in enumerate(raw_chunks):
            meta = ChunkMetadata(
                source_path=source_path,
                section_heading=section_heading,
                doc_type=doc_type,
                product=product,
                language=language,
                tenant_id=tenant_id,
                fleet_id=fleet_id,
                rack_id=rack_id,
                access_level=access_level,
            )
            results.append(
                Chunk(
                    chunk_id=self._make_chunk_id(source_path, i, chunk_text),
                    text=chunk_text,
                    token_count=self._count_tokens(chunk_text),
                    metadata=meta,
                )
            )
        return results

    def _pack_sentences(self, sentences: List[str]) -> List[str]:
        chunks: List[str] = []
        current: List[str] = []
        current_tokens = 0
        for s in sentences:
            t = self._count_tokens(s)
            if current_tokens + t > self.cfg.chunk_size and current:
                chunks.append(" ".join(current))
                current = [s]
                current_tokens = t
            else:
                current.append(s)
                current_tokens += t
        if current:
            chunks.append(" ".join(current))
        return chunks
