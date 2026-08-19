#!/usr/bin/env python3
"""
Seed BIAN reference markdown into the DocStore (and optionally Vector Store).

Usage (from repo root):
  set PYTHONPATH=.
  python scripts/seed_bian_knowledge.py

This walks fleets/bian/**/*.md, chunks with fleet_id=bian metadata, and dual-writes
to DocStore. When GCP/Vertex is configured, embeddings are upserted as well.

Volume is not capped — add as many service domain files as needed under fleets/bian/.
"""

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
        logger.error("Missing %s — create BIAN markdown under fleets/bian/", BIAN_ROOT)
        return 1

    chunker = Chunker()
    store = DocStore()
    total_chunks = 0
    files = sorted(BIAN_ROOT.rglob("*.md"))
    logger.info("Found %d BIAN markdown files under %s", len(files), BIAN_ROOT)

    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        # fleets/bian/{rack}/file.md
        parts = path.relative_to(BIAN_ROOT).parts
        rack_id = parts[0] if parts else "general"
        # Scenario/pattern docs: tag domain from filename or keep structural rack
        if rack_id in {"_scenarios", "_patterns", "_standards", "_bom", "_api"}:
            domain = path.stem.replace("_", " ").title()
            section = {"_scenarios": "scenario", "_patterns": "pattern", "_standards": "standard", "_bom": "bom", "_api": "api"}.get(rack_id, path.stem)
        else:
            domain = rack_id.replace("_", " ").title()
            section = path.stem
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
            section_heading=section,
        )
        records = [
            {
                "id": c.chunk_id,
                "text": c.text,
                "metadata": c.metadata.model_dump(mode="json"),
            }
            for c in chunks
        ]
        n = store.put_many(records)
        total_chunks += n
        logger.info("Seeded %s → %d chunks (domain=%s)", rel, n, domain)

        # Best-effort vector upsert when GCP is configured
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
            logger.info("Vector upsert skipped (%s) — DocStore seed still OK", e)

    logger.info("Done. Total BIAN chunks written: %d", total_chunks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
