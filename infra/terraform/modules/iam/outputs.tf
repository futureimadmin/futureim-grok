output "ingestion_sa_email" {
  value = google_service_account.ingestion.email
}

output "serving_sa_email" {
  value = google_service_account.serving.email
}

output "orchestrator_sa_email" {
  value = google_service_account.orchestrator.email
}

output "eventarc_sa_email" {
  value = google_service_account.eventarc.email
}
