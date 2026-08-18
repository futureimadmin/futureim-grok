/**
 * Core GCP services required by the RAG system.
 * Enables APIs and provisions shared managed services behind VPC boundaries.
 */

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.30"
    }
  }
}

locals {
  required_apis = [
    "compute.googleapis.com",
    "run.googleapis.com",
    "aiplatform.googleapis.com",
    "storage.googleapis.com",
    "pubsub.googleapis.com",
    "eventarc.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "vpcaccess.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudtrace.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each = toset(local.required_apis)

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "documents" {
  name                        = "${var.project_id}-rag-documents"
  project                     = var.project_id
  location                    = var.region
  force_destroy               = var.force_destroy
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket" "processed" {
  name                        = "${var.project_id}-rag-processed"
  project                     = var.project_id
  location                    = var.region
  force_destroy               = var.force_destroy
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  depends_on = [google_project_service.apis]
}

resource "google_compute_global_address" "private_ip_alloc" {
  name          = "rag-private-services"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = var.network_id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = var.network_id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]

  depends_on = [google_project_service.apis]
}

resource "google_redis_instance" "semantic_cache" {
  name                    = "rag-semantic-cache"
  project                 = var.project_id
  region                  = var.region
  memory_size_gb          = var.redis_memory_gb
  tier                    = "STANDARD_HA"
  redis_version           = "REDIS_7_0"
  display_name            = "RAG Semantic Cache"
  authorized_network      = var.network_id
  connect_mode            = "PRIVATE_SERVICE_ACCESS"
  auth_enabled            = true
  transit_encryption_mode = "SERVER_AUTHENTICATION"

  depends_on = [
    google_project_service.apis,
    google_service_networking_connection.private_vpc_connection,
  ]
}

resource "google_pubsub_topic" "document_events" {
  name    = "rag-document-events"
  project = var.project_id

  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "ingestion_dlq" {
  name    = "rag-ingestion-dlq"
  project = var.project_id

  depends_on = [google_project_service.apis]
}

resource "google_artifact_registry_repository" "rag" {
  location      = var.region
  project       = var.project_id
  repository_id = "rag"
  description   = "Container images for RAG ingestion and query services"
  format        = "DOCKER"

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "redis_auth" {
  secret_id = "rag-redis-auth"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}
