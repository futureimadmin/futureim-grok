"""
Doc Store – Tier 1 dual-write companion to the Vector Store.

Vector Store holds (chunk_id, embedding, metadata) — no raw text
Doc Store holds   (chunk_id → raw text + full metadata)

At query time the retriever:
  1. ANN / BM25 → list of chunk_ids
  2. Doc Store  → hydrate text by chunk_id
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DocStore:
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        prefix: str = "docstore/",
    ):
        self.bucket_name = bucket_name or os.getenv("PROCESSED_BUCKET") or os.getenv(
            "DOCUMENTS_BUCKET", ""
        )
        self.prefix = prefix.rstrip("/") + "/"
        self._local: Dict[str, dict] = {}
        self._gcs = None

        if self.bucket_name:
            try:
                from google.cloud import storage

                self._gcs = storage.Client()
                logger.info("DocStore GCS bucket=%s prefix=%s", self.bucket_name, self.prefix)
            except Exception as e:
                logger.warning("GCS unavailable for DocStore (%s) – local memory", e)
                self._gcs = None
        else:
            logger.info("DocStore local-memory mode (set PROCESSED_BUCKET for GCS)")

    def _blob_path(self, chunk_id: str) -> str:
        safe = chunk_id.replace("/", "_")
        return f"{self.prefix}{safe}.json"

    def put(self, chunk_id: str, text: str, metadata: Optional[dict] = None) -> None:
        record = {"chunk_id": chunk_id, "text": text, "metadata": metadata or {}}
        self._local[chunk_id] = record

        if not self._gcs or not self.bucket_name:
            return
        try:
            bucket = self._gcs.bucket(self.bucket_name)
            blob = bucket.blob(self._blob_path(chunk_id))
            blob.upload_from_string(
                json.dumps(record, default=str),
                content_type="application/json",
            )
        except Exception as e:
            logger.warning("DocStore put failed for %s: %s", chunk_id, e)

    def put_many(self, records: List[dict]) -> int:
        n = 0
        for r in records:
            cid = r.get("id") or r.get("chunk_id")
            text = r.get("text", "")
            if not cid or not text:
                continue
            self.put(cid, text, r.get("metadata"))
            n += 1
        return n

    def get(self, chunk_id: str) -> Optional[dict]:
        if chunk_id in self._local:
            return self._local[chunk_id]

        if not self._gcs or not self.bucket_name:
            return None
        try:
            bucket = self._gcs.bucket(self.bucket_name)
            blob = bucket.blob(self._blob_path(chunk_id))
            if not blob.exists():
                return None
            data = json.loads(blob.download_as_text())
            self._local[chunk_id] = data
            return data
        except Exception as e:
            logger.warning("DocStore get failed for %s: %s", chunk_id, e)
            return None

    def get_many(self, chunk_ids: List[str]) -> Dict[str, dict]:
        out: Dict[str, dict] = {}
        for cid in chunk_ids:
            rec = self.get(cid)
            if rec:
                out[cid] = rec
        return out
