/**
 * Eventarc + Cloud Run ingestion pipeline.
 *
 * Flow:
 *   GCS object finalized (documents bucket)
 *        │
 *        ▼
 *   Eventarc trigger  ──►  Cloud Run (rag-ingestion)
 *        │                       │
 *        │                       ├─ download object
 *        │                       ├─ chunk (semantic)
 *        │                       ├─ embed (Vertex AI)
 *        │                       ├─ upsert vector store
 *        │                       └─ write doc store / mark processed
 *        │
 *   Dead-letter → Pub/Sub DLQ topic (already created in services module)
 *
 * The Cloud Run service runs in the private-ingestion network plane
 * via the Serverless VPC Access connector.
 */

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.30"
    }
  }
}

# -----------------------------------------------------------------------------
# Cloud Run – Ingestion worker
# -----------------------------------------------------------------------------

resource "google_cloud_run_v2_service" "ingestion" {
  name     = "rag-ingestion"
  project  = var.project_id
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY" # only Eventarc / internal callers

  template {
    service_account = var.ingestion_sa_email

    scaling {
      min_instance_count = 0
      max_instance_count = var.max_instances
    }

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = var.ingestion_image

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "DOCUMENTS_BUCKET"
        value = var.documents_bucket
      }
      env {
        name  = "PROCESSED_BUCKET"
        value = var.processed_bucket
      }
      env {
        name  = "EMBEDDING_MODEL"
        value = var.embedding_model
      }
      env {
        name  = "CHUNK_STRATEGY"
        value = "semantic"
      }
      env {
        name  = "CHUNK_SIZE"
        value = "512"
      }
      env {
        name  = "CHUNK_OVERLAP"
        value = "64"
      }

      # Optional: vector index / endpoint once provisioned
      dynamic "env" {
        for_each = var.vector_index_id != "" ? [1] : []
        content {
          name  = "VECTOR_INDEX_ID"
          value = var.vector_index_id
        }
      }
      dynamic "env" {
        for_each = var.vector_endpoint_id != "" ? [1] : []
        content {
          name  = "VECTOR_ENDPOINT_ID"
          value = var.vector_endpoint_id
        }
      }
    }

    timeout = "900s" # long-running docs
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [var.apis_dependency]
}

# Allow Eventarc (and Pub/Sub push if used) to invoke the service
resource "google_cloud_run_v2_service_iam_member" "eventarc_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ingestion.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.eventarc_sa_email}"
}

# Also allow the ingestion SA itself (for retries / manual triggers)
resource "google_cloud_run_v2_service_iam_member" "ingestion_self_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ingestion.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.ingestion_sa_email}"
}

# -----------------------------------------------------------------------------
# Eventarc trigger – GCS object finalized → Cloud Run
# -----------------------------------------------------------------------------

resource "google_eventarc_trigger" "gcs_object_finalized" {
  name     = "rag-gcs-object-finalized"
  project  = var.project_id
  location = var.region

  # Cloud Storage as the event source
  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }

  matching_criteria {
    attribute = "bucket"
    value     = var.documents_bucket
  }

  destination {
    cloud_run_service {
      service = google_cloud_run_v2_service.ingestion.name
      region  = var.region
      path    = "/events" # dedicated CloudEvent endpoint
    }
  }

  service_account = var.eventarc_sa_email

  # Send failed deliveries to the DLQ topic
  transport {
    pubsub {
      topic = "projects/${var.project_id}/topics/${var.dlq_topic}"
    }
  }

  labels = {
    component = "rag-ingestion"
    plane     = "ingestion"
  }

  depends_on = [
    google_cloud_run_v2_service.ingestion,
    google_cloud_run_v2_service_iam_member.eventarc_invoker,
  ]
}
