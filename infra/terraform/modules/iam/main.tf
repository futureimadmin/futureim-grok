/**
 * IAM for the RAG system — plane-specific service accounts (least privilege).
 */

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.30"
    }
  }
}

resource "google_service_account" "ingestion" {
  account_id   = "rag-ingestion"
  display_name = "RAG Ingestion Plane"
  description  = "Offline write pipeline – chunk, embed, upsert."
  project      = var.project_id
}

resource "google_service_account" "serving" {
  account_id   = "rag-serving"
  display_name = "RAG Serving / Query Plane"
  description  = "Online query path – orchestrator, retrieval, LLM calls."
  project      = var.project_id
}

resource "google_service_account" "orchestrator" {
  account_id   = "rag-orchestrator"
  display_name = "RAG Orchestrator"
  description  = "Central decision engine – cache, classify, fan-out."
  project      = var.project_id
}

resource "google_service_account" "eventarc" {
  account_id   = "rag-eventarc"
  display_name = "RAG Eventarc Invoker"
  description  = "Used by Eventarc to invoke the ingestion Cloud Run service."
  project      = var.project_id
}

resource "google_project_iam_member" "ingestion_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_project_iam_member" "ingestion_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_project_iam_member" "ingestion_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_project_iam_member" "ingestion_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_project_iam_member" "serving_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.serving.email}"
}

resource "google_project_iam_member" "serving_storage_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.serving.email}"
}

resource "google_project_iam_member" "serving_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.serving.email}"
}

resource "google_project_iam_member" "orchestrator_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.orchestrator.email}"
}

resource "google_project_iam_member" "orchestrator_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.orchestrator.email}"
}

resource "google_project_iam_member" "eventarc_eventReceiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.eventarc.email}"
}

resource "google_project_iam_member" "eventarc_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.eventarc.email}"
}

resource "google_service_account_iam_member" "ingestion_run_user" {
  service_account_id = google_service_account.ingestion.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:service-${var.project_number}@serverless-robot-prod.iam.gserviceaccount.com"
}

resource "google_service_account_iam_member" "serving_run_user" {
  service_account_id = google_service_account.serving.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:service-${var.project_number}@serverless-robot-prod.iam.gserviceaccount.com"
}
