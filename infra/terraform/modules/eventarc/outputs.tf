output "ingestion_service_name" {
  value = google_cloud_run_v2_service.ingestion.name
}

output "ingestion_service_uri" {
  value = google_cloud_run_v2_service.ingestion.uri
}

output "eventarc_trigger_id" {
  value = google_eventarc_trigger.gcs_object_finalized.id
}

output "eventarc_trigger_name" {
  value = google_eventarc_trigger.gcs_object_finalized.name
}
