"""
Vertex AI Vector Search client with fleet/rack metadata filters.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(
        self,
        project_id: Optional[str] = None,
        region: Optional[str] = None,
        index_endpoint: Optional[str] = None,
        deployed_index_id: Optional[str] = None,
    ):
        self.project_id = project_id or os.getenv("GCP_PROJECT")
        self.region = region or os.getenv("GCP_REGION", "us-central1")
        self.index_endpoint = index_endpoint or os.getenv("VECTOR_ENDPOINT_ID")
        self.deployed_index_id = deployed_index_id or os.getenv(
            "VECTOR_DEPLOYED_INDEX_ID", "rag_deployed"
        )
        self._endpoint = None

    def _ensure_client(self):
        if self._endpoint is not None:
            return
        if not self.index_endpoint:
            logger.warning("VECTOR_ENDPOINT_ID not set – dense search disabled")
            return
        try:
            from google.cloud import aiplatform

            aiplatform.init(project=self.project_id, location=self.region)
            self._endpoint = aiplatform.MatchingEngineIndexEndpoint(self.index_endpoint)
            logger.info("Connected to Vector Search endpoint %s", self.index_endpoint)
        except Exception as e:
            logger.warning("Vector Search client init failed: %s", e)
            self._endpoint = None

    @staticmethod
    def _build_restricts(filters: Optional[Dict]) -> List[dict]:
        if not filters:
            return []
        restricts = []
        for key in (
            "fleet_id",
            "rack_id",
            "tier_id",
            "tenant_id",
            "access_level",
            "namespace",
            "product",
            "doc_type",
            "bian_service_domain",
            "bian_version",
        ):
            val = filters.get(key)
            if val:
                restricts.append({"namespace": key, "allow_list": [str(val)]})
        return restricts

    def upsert(self, records: List[dict]) -> int:
        self._ensure_client()
        if self._endpoint is None:
            logger.info("Upsert skipped (no endpoint) – %d records", len(records))
            return 0

        datapoints = []
        for r in records:
            meta = r.get("metadata") or {}
            restricts = []
            for key in (
                "fleet_id",
                "rack_id",
                "tier_id",
                "tenant_id",
                "access_level",
                "namespace",
                "product",
                "doc_type",
                "bian_service_domain",
                "bian_version",
            ):
                if meta.get(key):
                    restricts.append({"namespace": key, "allow_list": [str(meta[key])]})
            datapoints.append(
                {
                    "datapoint_id": r["id"],
                    "feature_vector": r["embedding"],
                    "restricts": restricts,
                }
            )

        try:
            index_name = os.getenv("VECTOR_INDEX_ID")
            if not index_name:
                logger.warning("VECTOR_INDEX_ID not set – cannot stream upsert")
                return 0
            from google.cloud import aiplatform

            index = aiplatform.MatchingEngineIndex(index_name)
            index.upsert_datapoints(datapoints=datapoints)
            logger.info("Upserted %d datapoints", len(datapoints))
            return len(datapoints)
        except Exception as e:
            logger.exception("Upsert failed: %s", e)
            return 0

    def search(
        self,
        query_vector: List[float],
        top_k: int = 50,
        filters: Optional[Dict] = None,
    ) -> List[Tuple[str, float]]:
        self._ensure_client()
        if self._endpoint is None:
            return []

        restricts = self._build_restricts(filters)
        try:
            response = self._endpoint.find_neighbors(
                deployed_index_id=self.deployed_index_id,
                queries=[query_vector],
                num_neighbors=top_k,
                filter=restricts or None,
            )
            hits: List[Tuple[str, float]] = []
            if response and response[0]:
                for n in response[0]:
                    score = float(getattr(n, "distance", 0.0))
                    hits.append((n.id, score))
            return hits
        except Exception as e:
            logger.exception("Dense search failed: %s", e)
            return []
