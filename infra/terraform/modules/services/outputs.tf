output "documents_bucket_name" {
  value = google_storage_bucket.documents.name
}

output "processed_bucket_name" {
  value = google_storage_bucket.processed.name
}

output "redis_host" {
  value = google_redis_instance.semantic_cache.host
}

output "redis_port" {
  value = google_redis_instance.semantic_cache.port
}

output "document_events_topic" {
  value = google_pubsub_topic.document_events.name
}

output "artifact_registry_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/rag"
}

output "private_vpc_connection" {
  value = google_service_networking_connection.private_vpc_connection.id
}
