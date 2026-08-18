/**
 * Eventarc + Cloud Run ingestion pipeline.
 *
 * GCS object finalized → Eventarc → Cloud Run (rag-ingestion)
 * Dead-letter → Pub/Sub DLQ topic
 */

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.30"
    }
  }
}

resource "google_cloud_run_v2_service" "ingestion" {
  name     = "rag-ingestion"
  project  = var.project_id
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

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
        value = "256"
      }
      env {
        name  = "CHUNK_OVERLAP"
        value = "32"
      }

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
  }

  labels = {
    component = "rag-ingestion"
    plane     = "ingestion"
  }
}

resource "google_cloud_run_v2_service_iam_member" "eventarc_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ingestion.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.eventarc_sa_email}"
}

resource "google_cloud_run_v2_service_iam_member" "ingestion_self_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ingestion.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.ingestion_sa_email}"
}

resource "google_eventarc_trigger" "gcs_object_finalized" {
  name     = "rag-gcs-object-finalized"
  project  = var.project_id
  location = var.region

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
      path    = "/events"
    }
  }

  service_account = var.eventarc_sa_email

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
