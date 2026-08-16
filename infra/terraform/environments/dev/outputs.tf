output "vpc_network" {
  value = module.vpc.network_name
}

output "subnet_cidrs" {
  value = module.vpc.subnet_cidrs
}

output "documents_bucket" {
  value = module.services.documents_bucket_name
}

output "redis_host" {
  value     = module.services.redis_host
  sensitive = true
}

output "ingestion_sa" {
  value = module.iam.ingestion_sa_email
}

output "serving_sa" {
  value = module.iam.serving_sa_email
}

output "vpc_access_connector" {
  value = google_vpc_access_connector.rag_connector.id
}

output "artifact_registry" {
  value = module.services.artifact_registry_url
}

output "ingestion_service" {
  value = module.eventarc.ingestion_service_name
}

output "ingestion_uri" {
  value = module.eventarc.ingestion_service_uri
}

output "eventarc_trigger" {
  value = module.eventarc.eventarc_trigger_name
}
