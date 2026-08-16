output "vpc_network" {
  value = module.vpc.network_name
}

output "documents_bucket" {
  value = module.services.documents_bucket_name
}

output "redis_host" {
  value     = module.services.redis_host
  sensitive = true
}

output "vector_index_id" {
  value = module.vector_search.index_id
}

output "vector_endpoint_id" {
  value = module.vector_search.endpoint_id
}

output "ingestion_service" {
  value = module.eventarc.ingestion_service_name
}

output "eventarc_trigger" {
  value = module.eventarc.eventarc_trigger_name
}

output "artifact_registry" {
  value = module.services.artifact_registry_url
}
