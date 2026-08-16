"""
Cloud Run ingestion worker.

Triggered by Eventarc when a new object is finalized in the documents bucket.

Accepts CloudEvents (application/cloudevents+json or the Eventarc-wrapped
format) and runs the offline pipeline:

  1. Download object from GCS
  2. Extract text (PDF / MD / TXT / HTML / DOCX – basic handlers)
  3. Chunk (semantic)
  4. Embed (Vertex AI)
  5. Dual-write: vector store upsert + doc-store write
  6. Copy / mark as processed

This service never serves user queries – it is the pure write path.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from google.cloud import storage

# Local imports – available because the same image packages src/
from src.common.config import get_config
from src.common.models import AccessLevel, DocType
from src.ingestion.chunker import Chunker
from src.ingestion.embedder import Embedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag-ingestion")

app = FastAPI(title="RAG Ingestion Worker", version="0.1.0")

cfg = get_config()
storage_client = storage.Client(project=cfg.project_id or None)


def _parse_cloudevent(body: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    """
    Normalise Eventarc / CloudEvents payload into a simple dict:
      { "bucket": "...", "name": "...", "contentType": "...", "size": ... }
    """
    # Binary mode (Ce- headers)
    if headers.get("ce-type") or headers.get("Ce-Type"):
        data = body
        bucket = headers.get("ce-bucket") or headers.get("Ce-Bucket") or data.get("bucket")
        name = headers.get("ce-subject") or headers.get("Ce-Subject") or data.get("name")
        if name and name.startswith("objects/"):
            name = name[len("objects/") :]
        return {
            "bucket": bucket or data.get("bucket"),
            "name": name or data.get("name"),
            "contentType": data.get("contentType") or data.get("content_type"),
            "size": data.get("size"),
            "metageneration": data.get("metageneration"),
        }

    # Structured mode
    if "data" in body and isinstance(body["data"], dict):
        data = body["data"]
    else:
        data = body

    # Pub/Sub push wrapper (if using subscription path)
    if "message" in data and "data" in data["message"]:
        raw = base64.b64decode(data["message"]["data"]).decode("utf-8")
        data = json.loads(raw)

    return {
        "bucket": data.get("bucket"),
        "name": data.get("name"),
        "contentType": data.get("contentType") or data.get("content_type"),
        "size": data.get("size"),
        "metageneration": data.get("metageneration"),
    }


def _extract_text(local_path: Path, content_type: Optional[str]) -> str:
    """Minimal text extractors. Extend with Document AI / unstructured for production."""
    suffix = local_path.suffix.lower()
    raw = local_path.read_bytes()

    if suffix in {".txt", ".md", ".markdown", ".html", ".htm"} or (
        content_type and content_type.startswith("text/")
    ):
        return raw.decode("utf-8", errors="replace")

    if suffix == ".pdf" or (content_type and "pdf" in content_type):
        try:
            from pypdf import PdfReader  # optional dependency
            reader = PdfReader(str(local_path))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            logger.warning("PDF extraction failed: %s – falling back to empty", e)
            return ""

    if suffix in {".docx"}:
        try:
            import docx  # python-docx
            doc = docx.Document(str(local_path))
            return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            logger.warning("DOCX extraction failed: %s", e)
            return ""

    # Fallback: try utf-8
    try:
        return raw.decode("utf-8")
    except Exception:
        logger.error("Unsupported content type %s / %s", content_type, suffix)
        return ""


def _infer_metadata(object_name: str) -> Dict[str, Any]:
    """Derive basic metadata from the object path convention.
    Example path: tenants/acme/product=API/docs/v3/auth.md
    """
    parts = object_name.split("/")
    meta = {
        "tenant_id": "default",
        "product": None,
        "doc_type": DocType.OTHER,
        "access_level": AccessLevel.PUBLIC,
        "language": "en",
    }
    for p in parts:
        if p.startswith("tenant=") or p.startswith("tenants/"):
            meta["tenant_id"] = p.split("=")[-1] if "=" in p else p
        if p.startswith("product="):
            meta["product"] = p.split("=", 1)[1]
        if "release" in p.lower() or "changelog" in p.lower():
            meta["doc_type"] = DocType.RELEASE_NOTES
        if "tutorial" in p.lower() or "guide" in p.lower():
            meta["doc_type"] = DocType.TUTORIAL
        if "reference" in p.lower() or "api" in p.lower():
            meta["doc_type"] = DocType.REFERENCE
        if p in {"internal", "confidential"}:
            meta["access_level"] = AccessLevel(p)
    return meta


@app.get("/health")
def health():
    return {"status": "ok", "service": "rag-ingestion"}


@app.post("/events")
async def handle_event(request: Request):
    """
    Eventarc / CloudEvents entrypoint.
    Returns 204 on success so Eventarc considers the delivery complete.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    headers = {k.lower(): v for k, v in request.headers.items()}
    event = _parse_cloudevent(body, headers)

    bucket_name = event.get("bucket")
    object_name = event.get("name")

    if not bucket_name or not object_name:
        logger.error("Malformed event: %s", event)
        raise HTTPException(status_code=400, detail="Missing bucket or object name")

    # Ignore folder placeholders and already-processed markers
    if object_name.endswith("/") or object_name.endswith(".processed"):
        return Response(status_code=204)

    logger.info("Ingesting gs://%s/%s", bucket_name, object_name)

    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)

        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / Path(object_name).name
            blob.download_to_filename(str(local))

            text = _extract_text(local, event.get("contentType"))
            if not text.strip():
                logger.warning("No text extracted from %s – skipping", object_name)
                return Response(status_code=204)

            meta = _infer_metadata(object_name)

            chunker = Chunker()
            chunks = chunker.chunk_document(
                text,
                source_path=object_name,
                doc_type=meta["doc_type"],
                product=meta["product"],
                tenant_id=meta["tenant_id"],
                access_level=meta["access_level"],
                language=meta["language"],
            )
            logger.info("Produced %d chunks for %s", len(chunks), object_name)

            if not chunks:
                return Response(status_code=204)

            embedder = Embedder()
            records = embedder.process_chunks(chunks)

            # TODO: real vector-store upsert once Vertex AI Vector Search / RAG Engine is wired
            # For now we log and write a processed marker so the pipeline is observable.
            logger.info(
                "Ready to upsert %d vectors (model=%s). Vector store integration pending.",
                len(records),
                cfg.embedding.model,
            )

            # Write processed marker / copy to processed bucket
            processed_bucket_name = os.getenv("PROCESSED_BUCKET") or cfg.processed_bucket
            if processed_bucket_name:
                dest = storage_client.bucket(processed_bucket_name)
                dest.blob(f"{object_name}.processed").upload_from_string(
                    json.dumps(
                        {
                            "source": object_name,
                            "chunks": len(chunks),
                            "status": "embedded",
                        }
                    ),
                    content_type="application/json",
                )

        return Response(status_code=204)

    except Exception as e:
        logger.exception("Ingestion failed for gs://%s/%s", bucket_name, object_name)
        # Returning 5xx makes Eventarc retry (and eventually hit the DLQ)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
