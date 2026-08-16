output "index_id" {
  value = google_vertex_ai_index.rag.id
}

output "index_name" {
  value = google_vertex_ai_index.rag.name
}

output "endpoint_id" {
  value = google_vertex_ai_index_endpoint.rag.id
}

output "endpoint_name" {
  value = google_vertex_ai_index_endpoint.rag.name
}

output "deployed_index_id" {
  value = google_vertex_ai_index_endpoint_deployed_index.rag.deployed_index_id
}

output "public_endpoint_domain" {
  value = try(google_vertex_ai_index_endpoint.rag.public_endpoint_domain_name, null)
}
