#!/usr/bin/env python3
"""
Seed BIAN reference markdown into the DocStore (and optionally Vector Store).

Usage (from repo root):
  set PYTHONPATH=.
  python scripts/seed_bian_knowledge.py

Walks fleets/bian/**/*.md, chunks with fleet_id=bian metadata, dual-writes
to DocStore. Volume is not capped.
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
        rack_id = path.parent.name
        chunks = chunker.chunk_text(
            text,
            source_uri=rel,
            doc_type=DocType.MARKDOWN,
            access_level=AccessLevel.INTERNAL,
            fleet_id="bian",
            rack_id=rack_id,
            product="bian",
            section_heading=path.stem,
        )
        for ch in chunks:
            store.put(ch.chunk_id, ch.text, ch.metadata.model_dump())
            total_chunks += 1
        logger.info("Seeded %s → %d chunks", rel, len(chunks))

    logger.info("Done. Total chunks written: %d", total_chunks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
