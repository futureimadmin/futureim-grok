"""
Cloud Run ingestion worker – Eventarc → chunk → embed → vector upsert.

Path convention for fleets:
  fleets/{fleet_id}/{rack_id}/.../doc.md
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

from src.common.config import get_config
from src.common.models import AccessLevel, DocType
from src.ingestion.chunker import Chunker
from src.ingestion.embedder import Embedder
from src.query.vector_store import VectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag-ingestion")

app = FastAPI(title="RAG Ingestion Worker", version="0.2.0")
cfg = get_config()
storage_client = storage.Client(project=cfg.project_id or None)


def _parse_cloudevent(body: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
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
        }
    if "data" in body and isinstance(body["data"], dict):
        data = body["data"]
    else:
        data = body
    if "message" in data and "data" in data["message"]:
        raw = base64.b64decode(data["message"]["data"]).decode("utf-8")
        data = json.loads(raw)
    return {
        "bucket": data.get("bucket"),
        "name": data.get("name"),
        "contentType": data.get("contentType") or data.get("content_type"),
        "size": data.get("size"),
    }


def _extract_text(local_path: Path, content_type: Optional[str]) -> str:
    suffix = local_path.suffix.lower()
    raw = local_path.read_bytes()
    if suffix in {".txt", ".md", ".markdown", ".html", ".htm"} or (
        content_type and content_type.startswith("text/")
    ):
        return raw.decode("utf-8", errors="replace")
    if suffix == ".pdf" or (content_type and "pdf" in content_type):
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(local_path))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            logger.warning("PDF extraction failed: %s", e)
            return ""
    if suffix in {".docx"}:
        try:
            import docx
            doc = docx.Document(str(local_path))
            return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            logger.warning("DOCX extraction failed: %s", e)
            return ""
    try:
        return raw.decode("utf-8")
    except Exception:
        return ""


def _infer_metadata(object_name: str) -> Dict[str, Any]:
    """Parse fleets/{fleet_id}/{rack_id}/... and legacy tenant/product paths."""
    parts = [p for p in object_name.split("/") if p]
    meta = {
        "tenant_id": "default",
        "product": None,
        "fleet_id": None,
        "rack_id": None,
        "doc_type": DocType.OTHER,
        "access_level": AccessLevel.PUBLIC,
        "language": "en",
    }
    if "fleets" in parts:
        i = parts.index("fleets")
        if i + 1 < len(parts):
            meta["fleet_id"] = parts[i + 1]
            meta["product"] = parts[i + 1]
        if i + 2 < len(parts):
            candidate = parts[i + 2]
            if "." not in candidate and candidate not in {"docs", "doc", "files"}:
                meta["rack_id"] = candidate
    for p in parts:
        if p.startswith("tenant="):
            meta["tenant_id"] = p.split("=", 1)[1]
        if p == "tenants" and parts.index(p) + 1 < len(parts):
            meta["tenant_id"] = parts[parts.index(p) + 1]
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
    try:
        body = await request.json()
    except Exception:
        body = {}
    headers = {k.lower(): v for k, v in request.headers.items()}
    event = _parse_cloudevent(body, headers)
    bucket_name = event.get("bucket")
    object_name = event.get("name")
    if not bucket_name or not object_name:
        raise HTTPException(status_code=400, detail="Missing bucket or object name")
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
                logger.warning("No text extracted from %s", object_name)
                return Response(status_code=204)

            meta = _infer_metadata(object_name)
            chunker = Chunker()
            chunks = chunker.chunk_document(
                text,
                source_path=object_name,
                doc_type=meta["doc_type"],
                product=meta["product"],
                tenant_id=meta["tenant_id"],
                fleet_id=meta.get("fleet_id"),
                rack_id=meta.get("rack_id"),
                access_level=meta["access_level"],
                language=meta["language"],
            )
            if not chunks:
                return Response(status_code=204)

            embedder = Embedder()
            records = embedder.process_chunks(chunks)
            for rec, ch in zip(records, chunks):
                md = rec.setdefault("metadata", {})
                md["fleet_id"] = ch.metadata.fleet_id
                md["rack_id"] = ch.metadata.rack_id
                md["tenant_id"] = ch.metadata.tenant_id
                md["access_level"] = (
                    ch.metadata.access_level.value
                    if hasattr(ch.metadata.access_level, "value")
                    else ch.metadata.access_level
                )
                if ch.metadata.fleet_id:
                    ns = ch.metadata.fleet_id
                    if ch.metadata.rack_id:
                        ns = f"{ch.metadata.fleet_id}/{ch.metadata.rack_id}"
                    md["namespace"] = ns

            upserted = VectorStore().upsert(records)
            logger.info("chunks=%d upserted=%d fleet=%s rack=%s",
                        len(records), upserted, meta.get("fleet_id"), meta.get("rack_id"))

            processed_bucket_name = os.getenv("PROCESSED_BUCKET") or cfg.processed_bucket
            if processed_bucket_name:
                dest = storage_client.bucket(processed_bucket_name)
                dest.blob(f"{object_name}.processed").upload_from_string(
                    json.dumps({
                        "source": object_name,
                        "chunks": len(chunks),
                        "fleet_id": meta.get("fleet_id"),
                        "rack_id": meta.get("rack_id"),
                        "status": "embedded",
                    }),
                    content_type="application/json",
                )
        return Response(status_code=204)
    except Exception as e:
        logger.exception("Ingestion failed for gs://%s/%s", bucket_name, object_name)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
