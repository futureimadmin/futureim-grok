output "network_id" {
  description = "The ID of the RAG VPC"
  value       = google_compute_network.rag_vpc.id
}

output "network_name" {
  description = "The name of the RAG VPC"
  value       = google_compute_network.rag_vpc.name
}

output "network_self_link" {
  value = google_compute_network.rag_vpc.self_link
}

output "public_ingress_subnet_id" {
  value = google_compute_subnetwork.public_ingress.id
}

output "private_ingestion_subnet_id" {
  value = google_compute_subnetwork.private_ingestion.id
}

output "private_serving_subnet_id" {
  value = google_compute_subnetwork.private_serving.id
}

output "private_data_subnet_id" {
  value = google_compute_subnetwork.private_data.id
}

output "subnet_cidrs" {
  value = {
    public_ingress    = google_compute_subnetwork.public_ingress.ip_cidr_range
    private_ingestion = google_compute_subnetwork.private_ingestion.ip_cidr_range
    private_serving   = google_compute_subnetwork.private_serving.ip_cidr_range
    private_data      = google_compute_subnetwork.private_data.ip_cidr_range
  }
}
