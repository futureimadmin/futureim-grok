#!/usr/bin/env python3
"""Seed BIAN reference markdown into DocStore (and Vector Store when GCP available)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common.models import AccessLevel, DocType
from src.ingestion.chunker import Chunker
from src.query.doc_store import DocStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed-bian")
BIAN_ROOT = ROOT / "fleets" / "bian"


def main() -> int:
    if not BIAN_ROOT.exists():
        logger.error("Missing %s", BIAN_ROOT)
        return 1
    chunker = Chunker()
    store = DocStore()
    total = 0
    files = sorted(BIAN_ROOT.rglob("*.md"))
    logger.info("Found %d BIAN markdown files", len(files))
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        parts = path.relative_to(BIAN_ROOT).parts
        rack_id = parts[0] if parts else "general"
        domain = rack_id.replace("_", " ").title()
        chunks = chunker.chunk_document(
            text,
            source_path=rel,
            doc_type=DocType.REFERENCE,
            product="bian",
            fleet_id="bian",
            rack_id=rack_id,
            bian_service_domain=domain,
            bian_version="12",
            is_bian_reference=True,
            access_level=AccessLevel.INTERNAL,
        )
        records = [
            {"id": c.chunk_id, "text": c.text, "metadata": c.metadata.model_dump(mode="json")}
            for c in chunks
        ]
        n = store.put_many(records)
        total += n
        logger.info("Seeded %s → %d chunks (%s)", rel, n, domain)
        try:
            from src.ingestion.embedder import Embedder
            from src.query.vector_store import VectorStore

            embedder = Embedder()
            vec_records = embedder.process_chunks(chunks)
            for rec, ch in zip(vec_records, chunks):
                md = rec.setdefault("metadata", {})
                md.update(ch.metadata.model_dump(mode="json"))
                md["namespace"] = f"bian/{rack_id}"
            VectorStore().upsert(vec_records)
        except Exception as e:
            logger.info("Vector upsert skipped (%s)", e)
    logger.info("Done. Total BIAN chunks: %d", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
