#!/usr/bin/env python3
"""
Upload all BIAN knowledge documents to the RAG documents Cloud Storage bucket.

Object layout (matches apps/ingestion/_infer_metadata path conventions):

  gs://{DOCUMENTS_BUCKET}/fleets/bian/{rack_id}/service_domain.md

When Eventarc is wired (Terraform modules/eventarc), each object finalize
triggers Cloud Run ingestion:

  GCS finalize → Eventarc → rag-ingestion → chunk → embed → vector + doc store

Prerequisites
-------------
- GCP project with documents bucket provisioned
  (Terraform: ${project_id}-rag-documents)
- ADC credentials: gcloud auth application-default login
- Env (optional):
    DOCUMENTS_BUCKET=my-project-rag-documents
    GCP_PROJECT / GOOGLE_CLOUD_PROJECT

Usage
-----
  # Dry-run (list only)
  python scripts/upload_bian_to_gcs.py --dry-run

  # Upload
  set DOCUMENTS_BUCKET=my-project-rag-documents
  python scripts/upload_bian_to_gcs.py

  # Explicit bucket / prefix
  python scripts/upload_bian_to_gcs.py --bucket my-project-rag-documents

  # Also upload knowledge/bian mirrors
  python scripts/upload_bian_to_gcs.py --include-knowledge

  # Force re-upload even if generation matches size
  python scripts/upload_bian_to_gcs.py --force
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("upload-bian-gcs")

BIAN_FLEET_ROOT = ROOT / "fleets" / "bian"
KNOWLEDGE_BIAN_ROOT = ROOT / "knowledge" / "bian"


def _discover_docs(include_knowledge: bool) -> List[Tuple[Path, str]]:
    """
    Returns list of (local_path, gcs_object_name).

    Canonical object names always under fleets/bian/... so ingestion
    sets fleet_id=bian, rack_id=<dir>, is_bian_reference=True.
    """
    pairs: List[Tuple[Path, str]] = []
    seen_objects: set = set()

    def add_tree(base: Path, object_prefix: str) -> None:
        if not base.exists():
            logger.warning("Skip missing tree: %s", base)
            return
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".md", ".markdown", ".txt", ".html", ".pdf", ".docx"}:
                continue
            rel = path.relative_to(base).as_posix()
            object_name = f"{object_prefix.rstrip('/')}/{rel}"
            if object_name in seen_objects:
                continue
            seen_objects.add(object_name)
            pairs.append((path, object_name))

    add_tree(BIAN_FLEET_ROOT, "fleets/bian")
    if include_knowledge and KNOWLEDGE_BIAN_ROOT.exists():
        add_tree(KNOWLEDGE_BIAN_ROOT, "fleets/bian")

    return pairs


def _content_type(path: Path) -> str:
    return {
        ".md": "text/markdown",
        ".markdown": "text/markdown",
        ".txt": "text/plain",
        ".html": "text/html",
        ".htm": "text/html",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }.get(path.suffix.lower(), "application/octet-stream")


def upload(
    pairs: Iterable[Tuple[Path, str]],
    bucket_name: str,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> int:
    if dry_run:
        n = 0
        for local, obj in pairs:
            logger.info("[dry-run] would upload %s → gs://%s/%s", local, bucket_name, obj)
            n += 1
        logger.info("[dry-run] %d object(s)", n)
        return n

    try:
        from google.cloud import storage
    except ImportError as e:
        logger.error(
            "google-cloud-storage is required: pip install google-cloud-storage (%s)", e
        )
        raise SystemExit(2) from e

    project = (
        os.getenv("GCP_PROJECT")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("PROJECT_ID")
        or None
    )
    client = storage.Client(project=project)
    bucket = client.bucket(bucket_name)
    if not bucket.exists():
        logger.error(
            "Bucket gs://%s does not exist. Provision via Terraform "
            "(module.services → ${project_id}-rag-documents) first.",
            bucket_name,
        )
        raise SystemExit(3)

    uploaded = 0
    skipped = 0
    for local, obj in pairs:
        blob = bucket.blob(obj)
        size = local.stat().st_size
        if not force and blob.exists():
            try:
                blob.reload()
                if blob.size == size:
                    logger.info("skip (unchanged) gs://%s/%s", bucket_name, obj)
                    skipped += 1
                    continue
            except Exception:
                pass

        blob.metadata = {
            "fleet_id": "bian",
            "is_bian_reference": "true",
            "source": "upload_bian_to_gcs",
            "local_path": str(local.relative_to(ROOT)).replace("\\", "/"),
        }
        blob.upload_from_filename(
            str(local),
            content_type=_content_type(local),
        )
        logger.info("uploaded %s → gs://%s/%s (%d bytes)", local.name, bucket_name, obj, size)
        uploaded += 1

    logger.info("Done. uploaded=%d skipped=%d bucket=gs://%s", uploaded, skipped, bucket_name)
    logger.info(
        "If Eventarc → rag-ingestion is deployed, each new/updated object "
        "will be chunked, embedded, and dual-written to Vector + Doc store."
    )
    return uploaded


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upload BIAN knowledge docs to GCS documents bucket")
    parser.add_argument(
        "--bucket",
        default=os.getenv("DOCUMENTS_BUCKET", ""),
        help="GCS documents bucket (default: $DOCUMENTS_BUCKET or ${PROJECT}-rag-documents)",
    )
    parser.add_argument(
        "--include-knowledge",
        action="store_true",
        help="Also upload knowledge/bian/** into fleets/bian/ object prefix",
    )
    parser.add_argument("--dry-run", action="store_true", help="List objects only")
    parser.add_argument("--force", action="store_true", help="Re-upload even if size matches")
    args = parser.parse_args(argv)

    bucket = (args.bucket or "").strip()
    if not bucket:
        project = (
            os.getenv("GCP_PROJECT")
            or os.getenv("GOOGLE_CLOUD_PROJECT")
            or os.getenv("PROJECT_ID")
            or ""
        )
        if project:
            bucket = f"{project}-rag-documents"
            logger.info("Using inferred bucket name: %s", bucket)
        else:
            logger.error(
                "Set --bucket or DOCUMENTS_BUCKET (or GCP_PROJECT to infer "
                "{project}-rag-documents)"
            )
            return 1

    pairs = _discover_docs(include_knowledge=args.include_knowledge)
    if not pairs:
        logger.error("No BIAN documents found under fleets/bian or knowledge/bian")
        return 1

    logger.info("Discovered %d BIAN document(s) for gs://%s", len(pairs), bucket)
    upload(pairs, bucket, dry_run=args.dry_run, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
